"""Hindsight-compatible memory with local JSON and optional remote storage."""

from .hindsight_memory import (
    validate_scan,
    validate_action,
    write_scan,
    write_action,
    read_history,
    find_similar_precedent,
    initialize
)
