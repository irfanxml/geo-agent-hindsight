"""Scan Agent: generate visibility queries, run them, and build scan records."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

try:  # Support both package imports and running this module as a script.
    from .llm import LLMError, call_llm, parse_json_response
    from .competitor_catalog import get_competitors
except ImportError:  # pragma: no cover - exercised by direct script invocation
    from llm import LLMError, call_llm, parse_json_response
    from competitor_catalog import get_competitors


SCAN_FIELDS = {
    "brand",
    "timestamp",
    "queries_tested",
    "mentions",
    "total_queries",
    "competitors_mentioned",
    "raw_snippets",
}

QUERY_SYSTEM = """You are the query-generation component of a GEO visibility scanner.
QUERY_GENERATION
Generate realistic, mostly non-branded questions a potential customer might ask an
AI assistant. Do not mention that the questions are part of a test.

Return ONLY a valid JSON object in this format:
{"queries": ["question 1", "question 2"]}

Do not use markdown.
Do not add explanations.
Generate exactly the requested number of unique questions."""

ANALYSIS_SYSTEM_TEMPLATE = """You analyze web-search evidence for a GEO visibility scan.
SCAN_ANALYSIS
Brand under evaluation: {brand}
Product category: {category}
Determine whether the brand appears in the supplied Tavily or Serper evidence.
Count as competitors only brands that offer a meaningfully comparable product
in this same category; ignore unrelated companies mentioned in passing. Select
one short useful evidence snippet. Return only this JSON object:
{{"brand_mentioned": true, "competitors": ["name"], "evidence_snippet": "text"}}
Do not count the evaluated brand as a competitor."""

ANALYSIS_BATCH_SYSTEM_TEMPLATE = """You analyze web-search evidence for a GEO visibility scan.
SCAN_ANALYSIS_BATCH
Brand under evaluation: {brand}
Product category: {category}
For each numbered query, use only the supplied Tavily or Serper evidence. Determine
whether the brand appears and list only meaningfully comparable competitors in this
category. Return one result for every input item, in the same order, as exactly this
JSON object: {{"analyses":[{{"brand_mentioned":false,"competitors":[],"evidence_snippet":"short text"}}]}}
Use a short evidence snippet from the supplied results. Never count the evaluated
brand as a competitor. Do not add explanations or markdown."""


class SearchError(RuntimeError):
    """Raised when Tavily or Serper cannot return search results."""


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib_request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib_request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise SearchError(f"Search request failed with HTTP {exc.code}: {detail}") from exc
    except urllib_error.URLError as exc:
        raise SearchError(f"Search request failed: {exc.reason}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SearchError("Search provider returned malformed JSON.") from exc
    if not isinstance(parsed, dict):
        raise SearchError("Search provider returned an invalid response.")
    return parsed


def _mock_search_results(
    provider: str,
    query: str,
    brand: str,
    scan_number: int = 1,
    query_index: int = 0,
    total_queries: int = 10,
    category: str = "",
) -> list[dict[str, str]]:
    """Return visibly varied demo evidence; it is simulated, not live search data."""
    canonical_names = {
        "chanel": "Chanel", "hermes": "Hermès", "louis vuitton": "Louis Vuitton",
        "saint laurent": "Saint Laurent", "prada": "Prada", "gucci": "Gucci",
        "dior": "Dior", "notion": "Notion", "asos": "ASOS", "uniqlo": "Uniqlo",
        "zara": "Zara", "nike": "Nike", "adidas": "Adidas", "levi's": "Levi's",
        "h&m": "H&M", "monday.com": "Monday.com", "clickup": "ClickUp",
    }
    display_brand = canonical_names.get(brand.strip().casefold(), brand.strip())
    seed = hashlib.sha256(brand.casefold().encode("utf-8")).digest()
    total = max(1, total_queries)
    # Keep mock figures plausible: at least one query remains unmentioned.
    max_mentions = max(0, total - 1)
    starting_mentions = min(max_mentions, 1 + seed[0] % min(3, total))
    span = max_mentions - starting_mentions
    if scan_number <= 10:
        # Show a single learning ramp over the first ten scans; do not restart
        # the curve after it reaches its peak.
        progress = round(span * (scan_number - 1) / 9)
        target_mentions = min(max_mentions, starting_mentions + progress)
    else:
        # Later scans model a stable mature baseline with small, non-cyclic
        # variation instead of an implausible collapse back to scan-one levels.
        variation_range = min(2, span)
        stability_seed = hashlib.sha256(
            f"{brand.casefold()}:{scan_number}:stable".encode("utf-8")
        ).digest()[0]
        target_mentions = max_mentions - (stability_seed % (variation_range + 1))
    mention_order = sorted(
        range(total),
        key=lambda index: hashlib.sha256(f"{brand.casefold()}:{scan_number}:{index}".encode()).digest(),
    )
    brand_mentioned = query_index in set(mention_order[:target_mentions])

    competitors = get_competitors(brand, category or query)
    
    if not competitors:
        mentioned_competitors = ["other leading alternatives"]
    else:
        leader_index = (seed[1] + scan_number - 1) % len(competitors)
        other_competitors = [
            name for i, name in enumerate(competitors) if i != leader_index
        ]
        if query_index < min(3, total):
            mentioned_competitors = [competitors[leader_index]]
        else:
            rank = (query_index + seed[2] + scan_number) % len(other_competitors)
            mentioned_competitors = [other_competitors[rank]]
    brand_text = (
        f"Our top recommendation in this category is {display_brand} because it offers the best features and highest overall value."
        if brand_mentioned
        else "When evaluating choices, we suggest avoiding lesser-known options and focusing on established brands."
    )
    competitor_text = " We also suggest checking out " + " and ".join(mentioned_competitors) + " for comparison."
    content = f"{brand_text}{competitor_text}"
    return [
        {
            "title": f"Mock {provider.title()} result",
            "url": f"mock://{provider.lower()}",
            "content": content,
        }
    ]


def _search_tavily(
    query: str, brand: str, scan_number: int = 1, query_index: int = 0, total_queries: int = 10,
    category: str = "",
) -> list[dict[str, str]]:
    if os.getenv("MOCK_MODE", "").strip() == "1":
        return _mock_search_results("Tavily", query, brand, scan_number, query_index, total_queries, category)
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise SearchError("TAVILY_API_KEY is not set. Use MOCK_MODE=1 for local tests.")
    try:
        response = _post_json(
            "https://api.tavily.com/search",
            {
                "api_key": api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": 1,
                "include_answer": False,
                "include_raw_content": False,
            },
            {},
        )
    except SearchError as exc:
        raise SearchError(f"Tavily API: {exc}") from exc
    results = response.get("results", [])
    if not isinstance(results, list):
        raise SearchError("Tavily response did not contain a results list.")
    return [
        {
            "title": str(item.get("title", "")),
            "url": str(item.get("url", "")),
            "content": str(item.get("content", "")),
        }
        for item in results
        if isinstance(item, dict) and item.get("content")
    ]


def _search_serper(
    query: str, brand: str, scan_number: int = 1, query_index: int = 0, total_queries: int = 10,
    category: str = "",
) -> list[dict[str, str]]:
    if os.getenv("MOCK_MODE", "").strip() == "1":
        return _mock_search_results("Serper", query, brand, scan_number, query_index, total_queries, category)
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise SearchError("SERPER_API_KEY is not set. Use MOCK_MODE=1 for local tests.")
    try:
        response = _post_json(
            "https://google.serper.dev/search",
            {"q": query, "num": 1},
            {"X-API-KEY": api_key},
        )
    except SearchError as exc:
        raise SearchError(f"Serper API: {exc}") from exc
    results = response.get("organic", [])
    if not isinstance(results, list):
        raise SearchError("Serper response did not contain an organic results list.")
    return [
        {
            "title": str(item.get("title", "")),
            "url": str(item.get("link", "")),
            "content": str(item.get("snippet", "")),
        }
        for item in results
        if isinstance(item, dict) and item.get("snippet")
    ]


def _json_with_retry(system: str, user: str, expected: str) -> Any:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return parse_json_response(call_llm(system, user, json_mode=True))
        except LLMError as exc:
            last_error = exc
            if attempt == 0 and exc.retryable:
                time.sleep(exc.retry_after if exc.retry_after is not None else 1.0)
                continue
            if not exc.retryable:
                raise
        except (ValueError, TypeError) as exc:
            last_error = exc
            if attempt == 0:
                continue
    raise LLMError(f"Could not parse {expected} response after 2 attempts: {last_error}")


def _generate_queries(brand: str, category: str, num_queries: int) -> list[str]:
    user = (
        f"Brand: {brand}\nCategory: {category}\n"
        f"Generate exactly {num_queries} unique questions."
    )
    raw = _json_with_retry(QUERY_SYSTEM, user, "query-generation")
    if isinstance(raw, dict) and "queries" in raw:
        raw = raw["queries"]
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError("Query generation must return a JSON list of strings.")
    queries = [item.strip() for item in raw if item.strip()]
    if len(queries) != num_queries or len(set(query.casefold() for query in queries)) != num_queries:
        raise ValueError("Query generation must return exactly N unique non-empty strings.")
    return queries


def _analyze_search_results(
    brand: str,
    category: str,
    query: str,
    tavily_results: list[dict[str, str]],
    serper_results: list[dict[str, str]],
) -> dict[str, Any]:
    # Keep the Groq request small and discard malformed/empty provider records.
    # Search APIs sometimes return a result object with no snippet; passing that
    # through can make the analyzer return an empty evidence_snippet and fail the
    # entire scan after the UI has been waiting for all queries.
    def usable_results(results: list[dict[str, str]]) -> list[dict[str, str]]:
        cleaned: list[dict[str, str]] = []
        for item in results[:1]:
            if not isinstance(item, dict):
                continue
            title = item.get("title", "")
            content = item.get("content", item.get("snippet", ""))
            title = title.strip() if isinstance(title, str) else ""
            content = content.strip() if isinstance(content, str) else ""
            if title or content:
                cleaned.append({"title": title[:100], "content": content[:400]})
        return cleaned

    tavily_results = usable_results(tavily_results)
    serper_results = usable_results(serper_results)
    provider_evidence = [
        result["content"] or result["title"]
        for result in tavily_results + serper_results
        if result["content"].strip() or result["title"].strip()
    ]
    if not provider_evidence:
        return {
            "brand_mentioned": False,
            "competitors": [],
            "evidence_snippet": "Search providers returned no readable evidence for this query.",
        }

    user = json.dumps(
        {
            "brand": brand,
            "query": query,
            "tavily_results": tavily_results,
            "serper_results": serper_results,
        },
        indent=2,
    )
    raw = _json_with_retry(
        ANALYSIS_SYSTEM_TEMPLATE.format(brand=brand, category=category),
        user,
        "search-analysis",
    )
    if not isinstance(raw, dict):
        raise ValueError("Search analysis must return a JSON object.")
    if not isinstance(raw.get("brand_mentioned"), bool):
        raise ValueError("Search analysis brand_mentioned must be a boolean.")
    if not isinstance(raw.get("competitors"), list):
        raise ValueError("Search analysis competitors must be a list.")
    evidence_snippet = raw.get("evidence_snippet")
    if not isinstance(evidence_snippet, str) or not evidence_snippet.strip():
        # The provider text is the source evidence. Keep the scan usable when
        # the model omits its summary instead of rejecting all query results.
        evidence_snippet = " ".join(provider_evidence)
    names: list[str] = []
    for item in raw["competitors"]:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("Competitor names must be non-empty strings.")
        name = item.strip()
        if name.casefold() != brand.casefold() and name.casefold() not in {
            existing.casefold() for existing in names
        }:
            names.append(name)
    return {
        "brand_mentioned": raw["brand_mentioned"],
        "competitors": names,
        "evidence_snippet": " ".join(evidence_snippet.split())[:280],
    }


def _analyze_search_batch(
    brand: str,
    category: str,
    search_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Analyze all query evidence in one model call to reduce latency and RPM use."""
    analyses: list[dict[str, Any] | None] = [None] * len(search_records)
    pending: list[dict[str, Any]] = []
    provider_evidence: dict[int, list[str]] = {}

    for index, record in enumerate(search_records):
        cleaned_sources: dict[str, list[dict[str, str]]] = {}
        evidence: list[str] = []
        for source in ("tavily_results", "serper_results"):
            cleaned: list[dict[str, str]] = []
            results = record.get(source, [])
            for item in results[:1] if isinstance(results, list) else []:
                if not isinstance(item, dict):
                    continue
                title = item.get("title", "")
                content = item.get("content", item.get("snippet", ""))
                title = title.strip() if isinstance(title, str) else ""
                content = content.strip() if isinstance(content, str) else ""
                if title or content:
                    cleaned.append({"title": title[:80], "content": content[:240]})
                    evidence.append(content or title)
            cleaned_sources[source] = cleaned
        provider_evidence[index] = evidence
        if not evidence:
            analyses[index] = {
                "brand_mentioned": False,
                "competitors": [],
                "evidence_snippet": "Search providers returned no readable evidence for this query.",
            }
            continue
        pending.append({
            "query": record["query"],
            **cleaned_sources,
        })

    if pending:
        raw = _json_with_retry(
            ANALYSIS_BATCH_SYSTEM_TEMPLATE.format(brand=brand, category=category),
            json.dumps({"items": pending}, ensure_ascii=False),
            "search-analysis batch",
        )
        model_analyses = raw.get("analyses") if isinstance(raw, dict) else None
        if isinstance(model_analyses, list):
            pending_indices = [i for i, result in enumerate(analyses) if result is None]
            for index, model_result in zip(pending_indices, model_analyses):
                try:
                    if not isinstance(model_result, dict):
                        raise ValueError("Analysis item must be an object.")
                    if not isinstance(model_result.get("brand_mentioned"), bool):
                        raise ValueError("brand_mentioned must be a boolean.")
                    competitors = model_result.get("competitors")
                    if not isinstance(competitors, list):
                        raise ValueError("competitors must be a list.")
                    names: list[str] = []
                    for name in competitors:
                        if not isinstance(name, str) or not name.strip():
                            continue
                        name = name.strip()
                        if name.casefold() != brand.casefold() and name.casefold() not in {
                            known.casefold() for known in names
                        }:
                            names.append(name)
                    snippet = model_result.get("evidence_snippet")
                    if not isinstance(snippet, str) or not snippet.strip():
                        snippet = " ".join(provider_evidence[index])
                    analyses[index] = {
                        "brand_mentioned": model_result["brand_mentioned"],
                        "competitors": names,
                        "evidence_snippet": " ".join(snippet.split())[:280],
                    }
                except (TypeError, ValueError):
                    analyses[index] = {
                        "brand_mentioned": False,
                        "competitors": [],
                        "evidence_snippet": " ".join(provider_evidence[index])[:280],
                    }

    # Keep a scan complete if the model returns fewer structured results than
    # requested; unclassified items remain unmentioned rather than being guessed.
    for index, analysis in enumerate(analyses):
        if analysis is None:
            analyses[index] = {
                "brand_mentioned": False,
                "competitors": [],
                "evidence_snippet": " ".join(provider_evidence[index])[:280],
            }
    return [analysis for analysis in analyses if analysis is not None]


def validate_scan_result(scan: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a scan record without changing its contract."""

    if not isinstance(scan, dict) or set(scan) != SCAN_FIELDS:
        raise ValueError(f"Scan result must contain exactly these fields: {sorted(SCAN_FIELDS)}")
    if not isinstance(scan["brand"], str) or not scan["brand"].strip():
        raise ValueError("Scan brand must be a non-empty string.")
    if not isinstance(scan["timestamp"], str):
        raise ValueError("Scan timestamp must be an ISO8601 string.")
    try:
        datetime.fromisoformat(scan["timestamp"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Scan timestamp must be ISO8601.") from exc
    queries = scan["queries_tested"]
    if (
        not isinstance(queries, list)
        or not all(isinstance(query, str) and query.strip() for query in queries)
        or len({query.casefold() for query in queries}) != len(queries)
    ):
        raise ValueError("queries_tested must be a list of unique strings.")
    total = scan["total_queries"]
    mentions = scan["mentions"]
    if not isinstance(total, int) or isinstance(total, bool) or total != len(queries):
        raise ValueError("total_queries must match queries_tested.")
    if not isinstance(mentions, int) or isinstance(mentions, bool) or not 0 <= mentions <= total:
        raise ValueError("mentions must be a count between zero and total_queries.")
    competitors = scan["competitors_mentioned"]
    if not isinstance(competitors, dict):
        raise ValueError("competitors_mentioned must be an object.")
    for name, count in competitors.items():
        if (
            not isinstance(name, str)
            or name.casefold() == scan["brand"].casefold()
            or not isinstance(count, int)
            or isinstance(count, bool)
            or not 0 <= count <= total
        ):
            raise ValueError("Competitor names/counts are invalid.")
    if not isinstance(scan["raw_snippets"], list) or not all(
        isinstance(snippet, str) for snippet in scan["raw_snippets"]
    ):
        raise ValueError("raw_snippets must be a list of strings.")
    return scan


def run_scan(
    brand: str, category: str, num_queries: int = 10, scan_number: int = 1
) -> dict[str, Any]:
    """Run a visibility scan and return the locked Scan Result contract."""

    if not isinstance(brand, str) or not brand.strip():
        raise ValueError("brand must be a non-empty string.")
    if not isinstance(category, str) or not category.strip():
        raise ValueError("category must be a non-empty string.")
    if not isinstance(num_queries, int) or isinstance(num_queries, bool) or num_queries < 1:
        raise ValueError("num_queries must be a positive integer.")
    if not isinstance(scan_number, int) or isinstance(scan_number, bool) or scan_number < 1:
        raise ValueError("scan_number must be a positive integer.")

    queries = _generate_queries(brand.strip(), category.strip(), num_queries)

    def collect_search(
        indexed_query: tuple[int, str], search_executor: ThreadPoolExecutor
    ) -> dict[str, Any]:
        query_index, query = indexed_query
        tavily_future = search_executor.submit(
            _search_tavily, query, brand.strip(), scan_number, query_index,
            len(queries), category.strip()
        )
        serper_future = search_executor.submit(
            _search_serper, query, brand.strip(), scan_number, query_index,
            len(queries), category.strip()
        )
        provider_errors: list[str] = []
        try:
            tavily_results = tavily_future.result()
        except SearchError as exc:
            tavily_results = []
            provider_errors.append(str(exc))
        try:
            serper_results = serper_future.result()
        except SearchError as exc:
            serper_results = []
            provider_errors.append(str(exc))
        if provider_errors and not (tavily_results or serper_results):
            raise SearchError("Both search providers failed: " + " | ".join(provider_errors))
        if not (tavily_results or serper_results):
            return {
                "brand_mentioned": False,
                "competitors": [],
                "evidence_snippet": "No search results were returned for this query.",
            }
        return {
            "query": query,
            "tavily_results": tavily_results,
            "serper_results": serper_results,
            "provider_errors": provider_errors,
        }

    with ThreadPoolExecutor(max_workers=min(8, len(queries) * 2)) as search_executor:
        search_futures = []
        for query_index, query in enumerate(queries):
            search_futures.append((
                query,
                search_executor.submit(
                    _search_tavily, query, brand.strip(), scan_number, query_index,
                    len(queries), category.strip()
                ),
                search_executor.submit(
                    _search_serper, query, brand.strip(), scan_number, query_index,
                    len(queries), category.strip()
                ),
            ))
        search_records = []
        for query, tavily_future, serper_future in search_futures:
            provider_errors: list[str] = []
            try:
                tavily_results = tavily_future.result()
            except SearchError as exc:
                tavily_results = []
                provider_errors.append(str(exc))
            try:
                serper_results = serper_future.result()
            except SearchError as exc:
                serper_results = []
                provider_errors.append(str(exc))
            if provider_errors and not (tavily_results or serper_results):
                raise SearchError("Both search providers failed: " + " | ".join(provider_errors))
            search_records.append({
                "query": query,
                "tavily_results": tavily_results,
                "serper_results": serper_results,
                "provider_errors": provider_errors,
            })

    # Mock responses retain their existing per-query path. Live results are
    # summarized together, cutting ten analysis requests down to one per scan.
    if os.getenv("MOCK_MODE", "").strip() == "1":
        analyses = [
            _analyze_search_results(
                brand.strip(), category.strip(), record["query"],
                record["tavily_results"], record["serper_results"],
            )
            if record["tavily_results"] or record["serper_results"]
            else {
                "brand_mentioned": False,
                "competitors": [],
                "evidence_snippet": "No search results were returned for this query.",
            }
            for record in search_records
        ]
    else:
        analyses = _analyze_search_batch(brand.strip(), category.strip(), search_records)

    for analysis, record in zip(analyses, search_records):
        if record["provider_errors"]:
            analysis["evidence_snippet"] = (
                "One search provider failed (" + "; ".join(record["provider_errors"]) + "). "
                + analysis["evidence_snippet"]
            )[:280]

    competitor_counts: dict[str, int] = {}
    snippets: list[str] = []
    mentions = 0
    for analysis in analyses:
        if analysis["brand_mentioned"]:
            mentions += 1
        for competitor in analysis["competitors"]:
            competitor_counts[competitor] = competitor_counts.get(competitor, 0) + 1
        snippets.append(analysis["evidence_snippet"])

    result = {
        "brand": brand.strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "queries_tested": queries,
        "mentions": mentions,
        "total_queries": len(queries),
        "competitors_mentioned": competitor_counts,
        "raw_snippets": snippets,
    }
    return validate_scan_result(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a GEO visibility scan.")
    parser.add_argument("brand")
    parser.add_argument("category")
    parser.add_argument("--num-queries", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(run_scan(args.brand, args.category, args.num_queries), indent=2))


if __name__ == "__main__":
    main()
