"""Small end-to-end smoke check for the mock pipeline; run with python -m integration.test_full_pipeline."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile

os.environ["MOCK_MODE"] = "1"
_temporary_memory = tempfile.TemporaryDirectory(prefix="geo-agent-smoke-")
os.environ["GEO_MEMORY_DATA_DIR"] = _temporary_memory.name

from integration.pipeline import run_pipeline


def main() -> None:
    result = run_pipeline("SmokeBrand", "project management software", num_queries=3)
    assert result["scan"]["total_queries"] == 3
    assert result["recommendation"]["scan_number"] == 1
    assert len(result["memory"]["scan_history"]) == 1
    print("Full pipeline smoke check passed (mock scan, local memory, recommendation).")


if __name__ == "__main__":
    try:
        main()
    finally:
        _temporary_memory.cleanup()
