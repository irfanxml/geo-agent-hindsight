"""Deterministic Hindsight-shaped data for testing the two agents independently."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone, timedelta
from typing import Any


BRAND = "Notion"


def _scan(number: int, mentions: int, total: int = 10) -> dict[str, Any]:
    return {
        "brand": BRAND,
        "timestamp": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=number)).isoformat(),
        "queries_tested": [f"Historical category question {index + 1}" for index in range(total)],
        "mentions": mentions,
        "total_queries": total,
        "competitors_mentioned": {"Asana": 5, "Trello": 3},
        "raw_snippets": [f"Historical evidence snippet for scan {number}." for _ in range(total)],
    }


def _action(name: str, days: int, outcome: str, delta: int) -> dict[str, Any]:
    return {
        "action": name,
        "date": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=days)).isoformat(),
        "outcome_summary": outcome,
        "visibility_delta": delta,
    }


def _memory(history: list[dict[str, Any]], actions: list[dict[str, Any]]) -> dict[str, Any]:
    return {"brand": BRAND, "scan_history": history, "actions_log": actions}


def get_scan_1_memory() -> dict[str, Any]:
    return deepcopy(_memory([], []))


def get_scan_5_memory() -> dict[str, Any]:
    return deepcopy(
        _memory(
            [_scan(1, 1), _scan(2, 1), _scan(3, 2), _scan(4, 2)],
            [
                _action(
                    "Publish a general product overview",
                    5,
                    "Traffic increased but AI visibility did not move.",
                    0,
                ),
                _action(
                    "Publish a customer-use-case comparison page",
                    12,
                    "Brand appeared in two additional category answers.",
                    2,
                ),
                _action(
                    "Add a broad homepage keyword section",
                    19,
                    "No measurable visibility improvement.",
                    0,
                ),
            ],
        )
    )


def get_scan_10_memory() -> dict[str, Any]:
    return deepcopy(
        _memory(
            [
                _scan(1, 1),
                _scan(2, 1),
                _scan(3, 2),
                _scan(4, 2),
                _scan(5, 3),
                _scan(6, 3),
                _scan(7, 4),
                _scan(8, 4),
                _scan(9, 5),
            ],
            [
                _action(
                    "Publish a general product overview",
                    5,
                    "No measurable visibility improvement.",
                    0,
                ),
                _action(
                    "Publish a customer-use-case comparison page",
                    12,
                    "Visibility increased by two queries.",
                    2,
                ),
                _action(
                    "Add integration proof to the comparison page",
                    28,
                    "Visibility increased by one query.",
                    1,
                ),
                _action(
                    "Repeat the broad homepage keyword section",
                    36,
                    "No measurable visibility improvement.",
                    0,
                ),
                _action(
                    "Create an evidence-led remote-team comparison page",
                    48,
                    "Visibility increased by three queries.",
                    3,
                ),
            ],
        )
    )


def get_current_scan(number: int) -> dict[str, Any]:
    """Return the scan that follows the requested fake memory snapshot."""

    mentions_by_scan = {1: 1, 5: 3, 10: 6}
    if number not in mentions_by_scan:
        raise ValueError("Fake current scans are available for scan numbers 1, 5, and 10.")
    return deepcopy(_scan(number, mentions_by_scan[number]))