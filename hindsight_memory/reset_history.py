"""Clear all persisted local scan and action history for a fresh start."""

import argparse
import json
from pathlib import Path

from .hindsight_memory import DATA_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--brand",
        help="clear only this brand's history (for example: Keka); omit to clear all brands",
    )
    args = parser.parse_args()
    data_dir = Path(DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    histories = sorted(data_dir.glob("*.json"))
    recommendation_dir = data_dir / ".recommendations"
    recommendations = sorted(recommendation_dir.glob("*.json")) if recommendation_dir.exists() else []
    if args.brand:
        removed = [
            history_file for history_file in histories
            if history_file.stem.casefold() == args.brand.strip().casefold()
        ]
        removed_recommendations = []
        for cache_file in recommendations:
            try:
                cache = json.loads(cache_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            cached_brand = cache.get("brand", "") if isinstance(cache, dict) else ""
            if isinstance(cached_brand, str) and cached_brand.casefold() == args.brand.strip().casefold():
                removed_recommendations.append(cache_file)
    else:
        removed = histories
        removed_recommendations = recommendations
    for history_file in removed:
        history_file.unlink()
    for cache_file in removed_recommendations:
        cache_file.unlink()

    if removed or removed_recommendations:
        print(
            f"Removed {len(removed)} saved brand history file(s) and "
            f"{len(removed_recommendations)} recommendation cache file(s) from {data_dir}."
        )
    else:
        target = f" for {args.brand}" if args.brand else ""
        print(f"No saved brand histories{target} found in {data_dir}; already fresh.")


if __name__ == "__main__":
    main()
