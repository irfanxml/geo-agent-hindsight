"""Single Groq LLM boundary for the GEO Visibility Agent.

The rest of the project only calls ``call_llm``.  Set MOCK_MODE=1 to run the
pipeline without API keys or the OpenAI-compatible package.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class LLMError(RuntimeError):
    """Raised when an LLM request cannot be completed."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = True,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.retry_after = retry_after


def configured_groq_model() -> str:
    """Return a supported default, migrating the retired starter model alias."""
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
    if model.casefold() == "llama-3.3-70b-versatile":
        return "openai/gpt-oss-120b"
    return model or "openai/gpt-oss-120b"


def _mock_query_generation(user: str) -> str:
    match = re.search(r"exactly\s+(\d+)\s+unique", user, flags=re.IGNORECASE)
    count = int(match.group(1)) if match else 10
    category_match = re.search(r"category:\s*(.+?)(?:\n|$)", user, flags=re.IGNORECASE)
    category = category_match.group(1).strip() if category_match else "this category"
    templates = [
        f"What are the most reliable options for {category}?",
        f"How should a small team choose {category}?",
        f"What features matter most when comparing {category} tools?",
        f"What are good alternatives for someone evaluating {category}?",
        f"Which {category} products are easiest to adopt?",
        f"What should I budget for {category} this year?",
        f"What are the common mistakes when choosing {category}?",
        f"Which {category} tools work well for remote teams?",
        f"How do the leading {category} products compare?",
        f"What is a good {category} option for a growing business?",
        f"Which {category} tools have the best integrations?",
        f"What is the simplest way to get started with {category}?",
    ]
    return json.dumps(templates[:count])


def _mock_scan_answer(system: str, user: str) -> str:
    brand_match = re.search(r"brand under evaluation:\s*(.+?)(?:\n|$)", system, re.IGNORECASE)
    brand = brand_match.group(1).strip() if brand_match else "the evaluated brand"
    index = sum(ord(character) for character in user) % 12
    leaders = ["Asana", "Trello", "Monday.com"]
    competitor = leaders[index % len(leaders)]
    if index % 3 == 0:
        return (
            f"For this question, {brand} is a strong option for teams that want a "
            f"focused workflow. {competitor} is another commonly considered choice."
        )
    return (
        f"Common recommendations include {competitor} and other established tools. "
        "Compare integrations, onboarding effort, and total cost before choosing."
    )


def _mock_competitor_extraction(user: str) -> str:
    known = ["Asana", "Trello", "Monday.com", "Jira", "ClickUp", "Airtable"]
    lower = user.lower()
    return json.dumps({"competitors": [name for name in known if name.lower() in lower]})


def _mock_scan_analysis(user: str) -> str:
    payload = json.loads(user)
    brand = payload["brand"]
    search_results = payload.get("tavily_results", []) + payload.get("serper_results", [])
    evidence_parts: list[str] = []
    seen_evidence: set[str] = set()
    for result in search_results:
        if not isinstance(result, dict):
            continue
        content = result.get("content", result.get("snippet", "")).strip()
        fingerprint = " ".join(content.casefold().split())
        if content and fingerprint not in seen_evidence:
            seen_evidence.add(fingerprint)
            evidence_parts.append(content)
    evidence = "\n".join(evidence_parts)
    lower_evidence = evidence.lower()
    competitors: list[str] = []
    for match in re.finditer(r"competitors discussed:\s*([^\n]*)", evidence, flags=re.IGNORECASE):
        for candidate in match.group(1).strip().rstrip(".").split(";"):
            name = candidate.strip()
            if name and name.casefold() != brand.casefold() and name.casefold() not in {
                known.casefold() for known in competitors
            }:
                competitors.append(name)
    return json.dumps(
        {
            "brand_mentioned": bool(
                re.search(rf"(?<!\w){re.escape(brand.casefold())}(?!\w)", lower_evidence)
            ),
            "competitors": competitors,
            "evidence_snippet": evidence[:280],
        }
    )


def _mock_recommendation(user: str) -> str:
    payload = json.loads(user)
    current = payload["current_scan"]
    history = payload["memory_record"].get(
        "recent_scans", payload["memory_record"].get("scan_history", [])
    )
    actions = payload["memory_record"].get("actions_log", [])
    brand = current["brand"]
    current_rate = current["mentions"] / max(current["total_queries"], 1)
    history_count = payload["memory_record"].get("total_prior_scans", len(history))
    scan_number = history_count + 1

    if history_count == 0 and not actions:
        recommendation = (
            f"Establish a baseline for {brand} by publishing one comparison page "
            "that answers the highest-intent category question and names the product "
            "with verifiable strengths."
        )
        based_on = None
        confidence = (
            "Baseline recommendation: there is no previous scan or action history, "
            "so impact cannot be attributed yet."
        )
    else:
        last_action = actions[-1]["action"] if actions else None
        positive = [action for action in actions if action["visibility_delta"] > 0]
        if positive:
            best = max(positive, key=lambda action: action["visibility_delta"])
            recommendation = (
                f"Extend the successful '{best['action']}' action with two "
                f"category-specific comparison pages targeting the questions where "
                f"{brand} is still absent, then rescan the same query set."
            )
            based_on = best["action"]
            confidence = (
                f"Scan {scan_number} follows {history_count} prior scans. The action "
                f"'{best['action']}' previously improved visibility by "
                f"{best['visibility_delta']}; current visibility is "
                f"{current['mentions']}/{current['total_queries']} "
                f"({current_rate:.0%})."
            )
        elif last_action:
            recommendation = (
                f"Do not repeat '{last_action}' yet; replace it with a targeted "
                f"comparison page for the top missing use case, include independent "
                f"proof points for {brand}, and rescan before expanding the effort."
            )
            based_on = last_action
            confidence = (
                f"Scan {scan_number} has {history_count} prior scans, but the latest "
                f"recorded action '{last_action}' has not shown improvement yet."
            )
        else:
            recommendation = (
                f"Create a focused comparison page for the most common missing "
                f"category use case, then rescan {brand} using the same queries."
            )
            based_on = None
            confidence = (
                f"Scan {scan_number} has historical scans but no recorded actions; "
                "the recommendation is based on visibility movement only."
            )

    return json.dumps(
        {
            "brand": brand,
            "recommendation": recommendation,
            "based_on_past_action": based_on,
            "confidence_note": confidence,
            "scan_number": scan_number,
        }
    )


def _mock_response(system: str, user: str, json_mode: bool) -> str:
    marker = system.upper()
    if "QUERY_GENERATION" in marker:
        return _mock_query_generation(user)
    if "COMPETITOR_EXTRACTION" in marker:
        return _mock_competitor_extraction(user)
    if "SCAN_ANALYSIS" in marker:
        return _mock_scan_analysis(user)
    if "RECOMMENDATION_AGENT" in marker:
        return _mock_recommendation(user)
    if "SCAN_ANSWER" in marker:
        return _mock_scan_answer(system, user)
    return json.dumps({"ok": True}) if json_mode else "Mock response."


def call_llm(system: str, user: str, json_mode: bool = False) -> str:
    """Call the configured model and return its text response.

    ``MOCK_MODE=1`` deliberately avoids importing the OpenAI SDK, which keeps
    local tests and teammate integration tests dependency-free.
    """

    if os.getenv("MOCK_MODE", "").strip() == "1":
        return _mock_response(system, user, json_mode)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise LLMError("GROQ_API_KEY is not set. Use MOCK_MODE=1 for local tests.")

    model = configured_groq_model()

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMError(
            "The OpenAI-compatible SDK is not installed. Install it with: pip install openai"
        ) from exc

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=float(os.getenv("GROQ_TIMEOUT_SECONDS", "35")),
            max_retries=0,
        )
        kwargs: dict[str, Any] = {
            "model": model,
            "max_completion_tokens": int(os.getenv("GROQ_MAX_TOKENS", "512")),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if model in {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}:
            kwargs["reasoning_effort"] = os.getenv("GROQ_REASONING_EFFORT", "low")
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            kwargs["messages"][0]["content"] += (
                "\nReturn a valid JSON object. Do not return a JSON array."
            )
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if not content:
            raise LLMError("The model returned an empty response.")
        return content
    except LLMError:
        raise
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)
        if status_code == 429:
            response = getattr(exc, "response", None)
            headers = getattr(response, "headers", {}) or {}
            retry_after: float | None = None
            for header_name in ("retry-after", "x-ratelimit-reset-tokens"):
                value = headers.get(header_name) if hasattr(headers, "get") else None
                if value:
                    match = re.search(r"([\d.]+)", str(value))
                    if match:
                        retry_after = float(match.group(1))
                        break
            if retry_after is None:
                match = re.search(r"try again in\s+([\d.]+)\s*s", str(exc), re.IGNORECASE)
                if match:
                    retry_after = float(match.group(1))
            retry_after = max(1.0, retry_after or 5.0)
            raise LLMError(
                f"Groq token rate limit reached; retrying after {retry_after:g} seconds.",
                retryable=True,
                retry_after=retry_after,
            ) from exc
        if status_code == 404:
            raise LLMError(
                f"Groq does not recognize model '{model}'. Check GROQ_MODEL in .env; "
                "a currently supported option is 'openai/gpt-oss-120b'.",
                retryable=False,
            ) from exc
        if status_code in {400, 401, 403}:
            raise LLMError(
                f"Groq rejected the request (HTTP {status_code}). Check the API key, "
                f"model access, and request settings: {exc}",
                retryable=False,
            ) from exc
        raise LLMError(f"Groq request failed: {exc}") from exc


def parse_json_response(text: str) -> Any:
    """Parse JSON, accepting the markdown fences models sometimes add."""

    cleaned = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model returned malformed JSON: {exc}") from exc
