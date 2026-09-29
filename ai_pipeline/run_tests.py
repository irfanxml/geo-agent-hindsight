"""Dependency-free test runner for the GEO Visibility Agent modules."""

from __future__ import annotations

import json
import os

os.environ["MOCK_MODE"] = "1"

from fake_data import get_current_scan, get_scan_1_memory, get_scan_5_memory, get_scan_10_memory
from integration_example import recommend_from_hindsight
from llm import parse_json_response
from recommendation_agent import get_recommendation
from scan_agent import run_scan, validate_scan_result


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    scan = run_scan("Notion", "project management software", num_queries=6)
    _assert(scan["total_queries"] == 6, "scan query count")
    _assert(len(scan["queries_tested"]) == 6, "scan query list")
    _assert(isinstance(scan["mentions"], int), "scan mentions type")
    print("===== INDEPENDENT SCAN AGENT =====")
    print(json.dumps(scan, indent=2))

    recommendation_1 = get_recommendation(get_current_scan(1), get_scan_1_memory())
    recommendation_5 = get_recommendation(get_current_scan(5), get_scan_5_memory())
    recommendation_10 = get_recommendation(get_current_scan(10), get_scan_10_memory())

    print("\n===== SCAN 1 =====")
    print(json.dumps(recommendation_1, indent=2))
    print("\n===== SCAN 5 =====")
    print(json.dumps(recommendation_5, indent=2))
    print("\n===== SCAN 10 =====")
    print(json.dumps(recommendation_10, indent=2))

    _assert(recommendation_1["based_on_past_action"] is None, "scan 1 baseline")
    _assert(recommendation_5["based_on_past_action"] is not None, "scan 5 action reference")
    _assert(recommendation_10["based_on_past_action"] is not None, "scan 10 action reference")
    _assert(recommendation_10["scan_number"] == 10, "scan 10 number")

    empty_actions_memory = get_scan_5_memory()
    empty_actions_memory["actions_log"] = []
    empty_actions_result = get_recommendation(get_current_scan(5), empty_actions_memory)
    _assert(empty_actions_result["based_on_past_action"] is None, "empty actions")

    integration_result = recommend_from_hindsight(
        get_current_scan(5), get_scan_5_memory()
    )
    _assert(integration_result["scan_number"] == 5, "Hindsight integration boundary")

    fenced = parse_json_response('```json\n{"ok": true}\n```')
    _assert(fenced == {"ok": True}, "markdown JSON fences")

    malformed = dict(scan)
    malformed["total_queries"] = malformed["total_queries"] + 1
    try:
        validate_scan_result(malformed)
    except ValueError:
        pass
    else:
        raise AssertionError("malformed scan data should fail validation")

    print("\nAll tests passed.")


if __name__ == "__main__":
    main()