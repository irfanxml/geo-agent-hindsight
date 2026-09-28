import json
import os
import time
import logging
import atexit
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("hindsight_memory")

BANK_ID = os.environ.get("GEO_MEMORY_BANK_ID", "geo-agent")
_DATA_DIR_DEFAULT = os.path.join(os.path.dirname(__file__), "data")
DATA_DIR = os.environ.get("GEO_MEMORY_DATA_DIR", _DATA_DIR_DEFAULT)
os.makedirs(DATA_DIR, exist_ok=True)

_client: Optional[Hindsight] = None

def get_hindsight_client() -> Hindsight:
    api_url = os.environ.get("HINDSIGHT_API_URL")
    api_key = os.environ.get("HINDSIGHT_API_KEY")
    if not api_url or not api_key or api_key == "your_key_here":
        raise ValueError("Missing or invalid Hindsight environment variables.")
    return Hindsight(base_url=api_url, api_key=api_key, timeout=120)

def initialize():
    global _client
    if _client is None:
        _client = get_hindsight_client()
        try:
            _client.create_bank(bank_id=BANK_ID, name=BANK_ID)
        except Exception as e:
            if "already exists" not in str(e).lower() and "409" not in str(e) and "500" not in str(e):
                logger.error(f"Failed to create bank: {e}")

@atexit.register
def close_client():
    global _client
    if _client is not None:
        try:
            _client.close()
        except:
            pass

def with_retries(func, *args, **kwargs):
    delays = [2, 4, 8]
    for attempt, delay in enumerate(delays, 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Try {attempt} failed for {func.__name__}: {e}")
            if attempt == len(delays):
                raise
            time.sleep(delay)

def wait_after_retain(seconds: int = 5):
    logger.info(f"Waiting {seconds}s after retain for Hindsight processing...")
    time.sleep(seconds)

def read_mirror(brand: str) -> dict:
    file_path = os.path.join(DATA_DIR, f"{brand}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"brand": brand, "scan_history": [], "actions_log": []}

def write_mirror(brand: str, data: dict):
    file_path = os.path.join(DATA_DIR, f"{brand}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def validate_scan(scan: dict):
    required = ["brand", "timestamp", "queries_tested", "mentions", "total_queries", "competitors_mentioned", "raw_snippets"]
    for r in required:
        if r not in scan:
            raise ValueError(f"Missing required field in scan: {r}")

def validate_action(action: dict):
    required = ["action", "date", "outcome_summary", "visibility_delta"]
    for r in required:
        if r not in action:
            raise ValueError(f"Missing required field in action: {r}")

def write_scan(brand: str, scan: dict) -> dict:
    validate_scan(scan)
    initialize()
    history = read_mirror(brand)
    history["scan_history"].append(scan)
    n = len(history["scan_history"])
    write_mirror(brand, history)

    def _do_retain():
        _client.retain(
            bank_id=BANK_ID,
            content=json.dumps(scan),
            tags=[f"brand:{brand}", "type:scan", f"scan_number:{n}"]
        )
    try:
        with_retries(_do_retain)
        wait_after_retain()
    except Exception as e:
        logger.error(f"Hindsight retention failed: {e}. Run in mirror-only mode.")
        
    return {"ok": True, "scan_number": n}

def write_action(brand: str, action: dict) -> dict:
    validate_action(action)
    initialize()
    history = read_mirror(brand)
    history["actions_log"].append(action)
    write_mirror(brand, history)

    def _do_retain():
        # Tag both brand and type
        _client.retain(
            bank_id=BANK_ID,
            content=json.dumps(action),
            tags=[f"brand:{brand}", "type:action"]
        )
    try:
        with_retries(_do_retain)
        wait_after_retain()
    except Exception as e:
        logger.error(f"Hindsight retention failed: {e}. Run in mirror-only mode.")

    return {"ok": True}

def read_history(brand: str) -> dict:
    """Returns the exact Hindsight record shape; unknown brand returns empty lists."""
    return read_mirror(brand)

def _extract_json_from_text(text: str) -> dict:
    # Attempt to extract JSON if markdown code blocks are used
    match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    # Attempt raw parsing
    try:
        return json.loads(text)
    except:
        raise ValueError(f"Could not parse JSON from: {text}")

def find_similar_precedent(brand: str, current_scan: dict) -> dict:
    initialize()
    try:
        def _do_recall():
            return _client.recall(
                bank_id=BANK_ID,
                query=f"Action history and outcomes for any brands. Looking for improvements in visibility.",
                tags=["type:action"],
                tags_match="any"
            )
        recall_resp = with_retries(_do_recall)
        if not recall_resp.results:
            return {"precedent": None, "reason": "no history yet", "source": "none"}
            
        context_docs = []
        for i, r in enumerate(recall_resp.results):
            context_docs.append(f"[Record {i}]: {r.text}")
        context_str = "\n".join(context_docs)
        
        mentions = current_scan.get('mentions', 0)
        total = current_scan.get('total_queries', 1)
        rate = mentions / total if total > 0 else 0
        comps = current_scan.get('competitors_mentioned', {})
        queries = current_scan.get('queries_tested', [])
        
        reflect_query = f"""
We want to improve AI engine visibility for brand '{brand}'.
Current scan key facts:
- Mention rate: {mentions}/{total} ({rate:.0%})
- Competitors: {json.dumps(comps)}
- Queries tested: {json.dumps(queries)}

Analyze the past actions provided in context. Choose the SINGLE past action whose starting situation is MOST SIMILAR to our current one (e.g. similar mention rate, similar competitor gap, or similar type of problem). Do not simply pick the one with the biggest visibility delta.
If a past action failed (zero or negative delta) but was done in a highly relevant situation, you may return it as a precedent and advise to avoid it.

Return EXACTLY a pure JSON object (no markdown, no quotes outside JSON) with this exact schema:
{{
  "precedent": {{
    "action": "string",
    "date": "string",
    "outcome_summary": "string",
    "visibility_delta": 0
  }},
  "reason": "1-2 sentences explicitly comparing the current and past situations, explicitly mentioning whether it worked or failed.",
  "source": "same_brand" or "similar_brand" or "none"
}}
"""
        def _do_reflect():
            return _client.reflect(
                bank_id=BANK_ID,
                query=reflect_query,
                context=context_str
            )
        reflect_resp = with_retries(_do_reflect)
        
        try:
            return _extract_json_from_text(reflect_resp.text)
        except Exception as json_err:
            logger.warning(f"Failed to parse reflect JSON: {json_err}. Trying again making query more specific.")
            # Retry reflect 
            def _do_reflect_retry():
                return _client.reflect(
                    bank_id=BANK_ID,
                    query=reflect_query + "\nREMINDER: OUTPUT ONLY VALID JSON. NO MARKDOWN.",
                    context=context_str
                )
            reflect_resp = with_retries(_do_reflect_retry)
            return _extract_json_from_text(reflect_resp.text)
            
    except Exception as e:
        logger.error(f"find_similar_precedent failed: {e}")
        return {"precedent": None, "reason": f"error: {str(e)}", "source": "none"}
