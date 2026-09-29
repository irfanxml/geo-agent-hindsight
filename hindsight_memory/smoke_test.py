import os
import time
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

def run_smoke_test():
    api_url = os.getenv("HINDSIGHT_API_URL")
    api_key = os.getenv("HINDSIGHT_API_KEY")

    if not api_key or api_key == "your_key_here":
        print("Please set a valid HINDSIGHT_API_KEY in .env")
        return

    print("Initializing client...")
    try:
        client = Hindsight(base_url=api_url, api_key=api_key, timeout=120)
    except Exception as e:
        print(f"Failed to initialize client: {e}")
        return

    bank_id = "smoke-test"
    print(f"Creating or attaching to bank '{bank_id}'...")
    try:
        # Create bank if it doesn't exist
        try:
            client.create_bank(bank_id=bank_id, name=bank_id)
            print("Bank created.")
        except Exception as e:
            # If it already exists, just continue
            if "already exists" in str(e).lower() or "409" in str(e) or "500" in str(e):
                print("Bank might already exist (or 500 error), continuing.")
            else:
                client.create_bank(bank_id=bank_id, name=bank_id) # Let it crash if not 409
    except Exception as e:
        print(f"Failed to create bank: {e}")

    print("Retaining memory...")
    try:
        client.retain(
            bank_id=bank_id,
            content="Scan 1 for BrandX: mentioned in 4 of 20 queries. Competitors: AlphaCo 11, BetaCo 7.",
            tags=["brand:brandx", "type:scan"]
        )
        print("Memory retained successfully.")
    except Exception as e:
        print(f"Failed to retain memory: {e}")
        return

    print("Waiting 5s for processing...")
    time.sleep(5)

    print("Recalling memory...")
    try:
        recall_resp = client.recall(
            bank_id=bank_id,
            query="How visible is BrandX?",
            tags=["brand:brandx"],
            tags_match="any"
        )
        print(f"Recall results count: {len(recall_resp.results)}")
        for r in recall_resp.results:
            print(f"- {r.text}")
    except Exception as e:
        print(f"Failed to recall: {e}")
        return

    print("Reflecting on memory...")
    try:
        reflect_resp = client.reflect(
            bank_id=bank_id,
            query="What should BrandX do to improve AI visibility?"
        )
        print(f"Reflect result: {reflect_resp.text}")
    except Exception as e:
        print(f"Failed to reflect: {e}")
        return

    print("Smoke test completed successfully!")

if __name__ == "__main__":
    run_smoke_test()
