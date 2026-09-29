"""Recommendation Agent: turn current scans and Hindsight history into one action."""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

try:  # Support both package imports and running this module as a script.
    from .llm import LLMError, call_llm, parse_json_response
    from .scan_agent import validate_scan_result
except ImportError:  # pragma: no cover - exercised by direct script invocation
    from llm import LLMError, call_llm, parse_json_response
    from scan_agent import validate_scan_result


RECOMMENDATION_SYSTEM_PROMPT = """You are the Recommendation Agent for GEO visibility.
RECOMMENDATION_AGENT
Analyze the current scan and the compact Hindsight memory summary. Compare the
current result with recent scan trends and inspect every supplied previous action and outcome.
Only refer to an action included in the supplied memory summary; older scan details may be omitted.
and produce exactly one concrete, actionable recommendation.

When history exists, explicitly reference a previous action and explain whether it
appears to have worked. Do not repeat an action that did not improve visibility
without a new reason. Make the recommendation visibly more specific as evidence
accumulates. When there is no history, give an honest baseline recommendation and
set based_on_past_action to null. Return only the required JSON object with these
fields: brand, recommendation, based_on_past_action, confidence_note, scan_number."""

RECOMMENDATION_FIELDS = {
    "brand",
    "recommendation",
    "based_on_past_action",
    "confidence_note",
    "scan_number",
}


def _validate_memory(memory_record: dict[str, Any], brand: str) -> None:
    if not isinstance(memory_record, dict) or set(memory_record) != {
        "brand",
        "scan_history",
        "actions_log",
    }:
        raise ValueError("memory_record must contain exactly brand, scan_history, and actions_log.")
    if memory_record["brand"] != brand:
        raise ValueError("memory_record brand must match the current scan.")
    if not isinstance(memory_record["scan_history"], list):
        raise ValueError("scan_history must be a list.")
    for scan in memory_record["scan_history"]:
        validate_scan_result(scan)
        if scan["brand"] != brand:
            raise ValueError("Every historical scan must match the current brand.")
    if not isinstance(memory_record["actions_log"], list):
        raise ValueError("actions_log must be a list.")
    for action in memory_record["actions_log"]:
        if not isinstance(action, dict) or set(action) != {
            "action",
            "date",
            "outcome_summary",
            "visibility_delta",
        }:
            raise ValueError("Each action must match the locked actions_log shape.")
        if not isinstance(action["action"], str) or not action["action"].strip():
            raise ValueError("Action names must be non-empty strings.")
        if not isinstance(action["outcome_summary"], str):
            raise ValueError("outcome_summary must be a string.")
        if not isinstance(action["visibility_delta"], (int, float)) or isinstance(
            action["visibility_delta"], bool
        ):
            raise ValueError("visibility_delta must be numeric.")
        try:
            datetime.fromisoformat(action["date"].replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise ValueError("Action date must be ISO8601.") from exc


def validate_recommendation(
    recommendation: dict[str, Any],
    current_scan: dict[str, Any],
    memory_record: dict[str, Any],
) -> dict[str, Any]:
    """Validate the exact Recommendation Output contract."""

    if not isinstance(recommendation, dict) or set(recommendation) != RECOMMENDATION_FIELDS:
        raise ValueError(
            f"Recommendation must contain exactly these fields: {sorted(RECOMMENDATION_FIELDS)}"
        )
    expected_scan_number = len(memory_record["scan_history"]) + 1
    if recommendation["brand"] != current_scan["brand"]:
        raise ValueError("Recommendation brand must match the current scan.")
    if not isinstance(recommendation["recommendation"], str) or not recommendation[
        "recommendation"
    ].strip():
        raise ValueError("recommendation must be a non-empty string.")
    if not isinstance(recommendation["confidence_note"], str) or not recommendation[
        "confidence_note"
    ].strip():
        raise ValueError("confidence_note must be a non-empty string.")
    if recommendation["scan_number"] != expected_scan_number:
        raise ValueError("scan_number must match the current position in history.")
    action_names = {action["action"] for action in memory_record["actions_log"]}
    based_on = recommendation["based_on_past_action"]
    if based_on is not None and based_on not in action_names:
        raise ValueError("based_on_past_action must be null or a valid historical action.")
    if not memory_record["scan_history"] and based_on is not None:
        raise ValueError("The first recommendation cannot claim a past action.")
    return recommendation


def _recommendation_with_retry(user: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            result = parse_json_response(
                call_llm(RECOMMENDATION_SYSTEM_PROMPT, user, json_mode=True)
            )
            if not isinstance(result, dict):
                raise ValueError("Recommendation model must return a JSON object.")
            return result
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
    raise LLMError(f"Could not parse recommendation after 2 attempts: {last_error}")


def get_recommendation(current_scan: dict[str, Any], memory_record: dict[str, Any]) -> dict[str, Any]:
    """Return one validated recommendation for the current scan."""

    validate_scan_result(current_scan)
    _validate_memory(memory_record, current_scan["brand"])
    recent_scans = memory_record["scan_history"][-12:]
    recent_actions = memory_record["actions_log"][-12:]
    compact_current_scan = {
        key: current_scan[key]
        for key in (
            "brand", "timestamp", "queries_tested", "mentions", "total_queries",
            "competitors_mentioned",
        )
    }
    compact_memory = {
        "brand": memory_record["brand"],
        "total_prior_scans": len(memory_record["scan_history"]),
        "older_scans_omitted": max(0, len(memory_record["scan_history"]) - len(recent_scans)),
        "recent_scans": [
            {
                "timestamp": scan["timestamp"],
                "mentions": scan["mentions"],
                "total_queries": scan["total_queries"],
                "competitors_mentioned": dict(
                    sorted(scan["competitors_mentioned"].items(), key=lambda item: item[1], reverse=True)[:4]
                ),
            }
            for scan in recent_scans
        ],
        "actions_log": [
            {
                "action": action["action"][:240],
                "date": action["date"],
                "outcome_summary": action["outcome_summary"][:360],
                "visibility_delta": action["visibility_delta"],
            }
            for action in recent_actions
        ],
    }
    user = json.dumps(
        {"current_scan": compact_current_scan, "memory_record": compact_memory},
        indent=2,
        sort_keys=True,
    )
    result = _recommendation_with_retry(user)
    return validate_recommendation(result, current_scan, memory_record)
