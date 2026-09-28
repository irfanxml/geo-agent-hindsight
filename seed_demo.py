import json
from datetime import datetime, timedelta
from hindsight_memory import write_scan, write_action, read_history

def seed():
    brand = "ZenBookX"
    competitors = ["MacBookAir", "DellXPS", "ThinkPad"]
    
    start_date = datetime(2026, 8, 1)
    
    # 10 scans and 5 actions
    # Actions happen between scans
    for i in range(1, 11):
        scan_date = start_date + timedelta(days=i*7)
        # Gradual improvement in mentions
        mentions = min(5 + i, 20)
        
        scan_data = {
            "brand": brand,
            "timestamp": scan_date.isoformat(),
            "queries_tested": ["best laptop 2026", "lightweight laptop for students", "windows laptop alternative to mac"],
            "mentions": mentions,
            "total_queries": 20,
            "competitors_mentioned": {
                "MacBookAir": 15 - (i//2),
                "DellXPS": 10,
                "ThinkPad": 8
            },
            "raw_snippets": [f"The {brand} is gaining traction...", "Reviewers love the new screen."]
        }
        print(f"Writing scan {i}...")
        write_scan(brand, scan_data)
        
        if i == 2:
            action_data = {
                "action": "Published 'Mac vs Windows' comparison page focusing on weight and battery",
                "date": (scan_date + timedelta(days=2)).isoformat(),
                "outcome_summary": "Slight bump in 'alternative to mac' queries.",
                "visibility_delta": 2
            }
            write_action(brand, action_data)
        elif i == 4:
            action_data = {
                "action": "Added FAQ page with Structured Data (Schema.org)",
                "date": (scan_date + timedelta(days=2)).isoformat(),
                "outcome_summary": "Major improvement in AI snippet extraction.",
                "visibility_delta": 3
            }
            write_action(brand, action_data)
        elif i == 6:
            action_data = {
                "action": "Sponsorship of random gaming podcast (no written transcript)",
                "date": (scan_date + timedelta(days=2)).isoformat(),
                "outcome_summary": "Failed. Did not yield any readable text for AI to ingest.",
                "visibility_delta": 0
            }
            write_action(brand, action_data)
        elif i == 7:
            action_data = {
                "action": "Got listed in 'Top 10 Windows Laptops of 2026' on CNET",
                "date": (scan_date + timedelta(days=2)).isoformat(),
                "outcome_summary": "High authority link improved overall brand presence.",
                "visibility_delta": 4
            }
            write_action(brand, action_data)
        elif i == 9:
            action_data = {
                "action": "Updated Wikipedia page and Wikidata entry with current models",
                "date": (scan_date + timedelta(days=2)).isoformat(),
                "outcome_summary": "Knowledge graph recognized the new product line.",
                "visibility_delta": 2
            }
            write_action(brand, action_data)

    print("Seeding complete.")
    
    # Write to fake_history.json
    history = read_history(brand)
    with open("fake_history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
    print("Wrote fake_history.json")

if __name__ == "__main__":
    seed()
