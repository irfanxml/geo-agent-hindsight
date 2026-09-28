import os
import asyncio
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

async def cleanup_async():
    api_url = os.environ.get("HINDSIGHT_API_URL")
    api_key = os.environ.get("HINDSIGHT_API_KEY")
    if not api_url or not api_key:
        print("Missing Hindsight environment variables.")
        return

    client = Hindsight(base_url=api_url, api_key=api_key, timeout=120)
    bank_id = "geo-agent"
    
    test_brands = ["brand:RoundTripBrand", "brand:FallbackBrand", "brand:UnknownBrand12345"]
    docs_removed = 0
    
    # We will collect document IDs using recall, then delete them
    docs_to_delete = set()
    for tag in test_brands:
        try:
            brand_name = tag.split(":")[1]
            recall_resp = await client.arecall(bank_id=bank_id, query=brand_name, tags=[tag], budget="high")
            for result in recall_resp.results:
                if result.document_id:
                    docs_to_delete.add(result.document_id)
        except Exception as e:
            print(f"Error recalling for tag {tag}: {e}")
            
    try:
        for doc_id in docs_to_delete:
            await client.documents.delete_document(bank_id=bank_id, document_id=doc_id)
            print(f"Removed document {doc_id} associated with test brands")
            docs_removed += 1
    except Exception as e:
        print(f"Cleanup encountered an error during deletion: {e}")
        
    print(f"Cleanup finished. Removed {docs_removed} test brand items from {bank_id}.")
    try:
        client.close()
    except:
        pass

def cleanup():
    asyncio.run(cleanup_async())

if __name__ == "__main__":
    cleanup()
