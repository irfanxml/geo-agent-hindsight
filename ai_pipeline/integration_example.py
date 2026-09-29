"""Minimal teammate-facing integration example.

The real Hindsight teammate can replace ``memory_record`` with the record it
loads from storage. No Hindsight implementation is required here.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from recommendation_agent import get_recommendation


def recommend_from_hindsight(
    current_scan: dict[str, Any], memory_record: dict[str, Any]
) -> dict[str, Any]:
    """Pass Hindsight's exact memory record into the Recommendation Agent."""

    return get_recommendation(current_scan, memory_record)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python integration_example.py current_scan.json memory_record.json"
        )

    with open(sys.argv[1], encoding="utf-8") as current_scan_file:
        current_scan = json.load(current_scan_file)
    with open(sys.argv[2], encoding="utf-8") as memory_file:
        memory_record = json.load(memory_file)

    recommendation = recommend_from_hindsight(current_scan, memory_record)
    print(json.dumps(recommendation, indent=2))


if __name__ == "__main__":
    main()