"""Run one scan -> memory read -> recommendation -> memory write cycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_pipeline.recommendation_agent import get_recommendation
from ai_pipeline.scan_agent import run_scan
from hindsight_memory import hindsight_memory as memory


def run_pipeline(brand: str, category: str, num_queries: int = 10) -> dict[str, Any]:
    """Run the full local pipeline and persist the scan after recommending."""
    prior_memory = memory.read_history(brand)
    current_scan = run_scan(
        brand,
        category,
        num_queries,
        scan_number=len(prior_memory["scan_history"]) + 1,
    )
    recommendation = get_recommendation(current_scan, prior_memory)
    write_result = memory.write_scan(brand, current_scan)
    return {
        "scan": current_scan,
        "recommendation": recommendation,
        "memory": memory.read_history(brand),
        "memory_write": write_result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the GEO visibility agent pipeline.")
    parser.add_argument("--brand", required=True, help="Brand being evaluated")
    parser.add_argument("--category", required=True, help="Brand's product category")
    parser.add_argument("--num-queries", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(run_pipeline(args.brand, args.category, args.num_queries), indent=2))


if __name__ == "__main__":
    main()
