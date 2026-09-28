import json
from hindsight_memory import find_similar_precedent

scan = {
    "brand": "ZenBookX",
    "timestamp": "2026-09-28T12:00:00Z",
    "queries_tested": ["best laptop for students", "lightweight laptop under 80000"],
    "mentions": 6,
    "total_queries": 20,
    "competitors_mentioned": {"AlphaCo": 11, "BetaCo": 7},
    "raw_snippets": ["Top picks include AlphaCo and BetaCo..."]
}

result = find_similar_precedent("ZenBookX", scan)
print(json.dumps(result, indent=2))