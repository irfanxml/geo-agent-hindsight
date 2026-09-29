"""Local standard-library API linking the dashboard to the GEO agents."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
import math
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load this project's .env before applying the no-credentials default, otherwise
# setdefault would pin MOCK_MODE=1 and silently ignore a live-mode setting.
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass

# Make the out-of-box app runnable without provider credentials.
os.environ.setdefault("MOCK_MODE", "1")

from integration.pipeline import run_pipeline
from hindsight_memory import hindsight_memory as memory


LIVE_PROVIDER_KEYS = {
    "GROQ_API_KEY": "Groq (query generation, evidence analysis, recommendations)",
    "TAVILY_API_KEY": "Tavily (web search)",
    "SERPER_API_KEY": "Serper (web search)",
}


def _mock_mode() -> bool:
    return os.getenv("MOCK_MODE", "1").strip() == "1"


def _missing_live_keys() -> list[str]:
    return [key for key in LIVE_PROVIDER_KEYS if not os.getenv(key, "").strip()]


def _recommendation_cache_path(brand: str) -> Path:
    key = hashlib.sha256(brand.casefold().encode("utf-8")).hexdigest()
    return Path(memory.DATA_DIR) / ".recommendations" / f"{key}.json"


def _cache_recommendation(brand: str, scan: dict[str, Any], recommendation: dict[str, Any]) -> None:
    path = _recommendation_cache_path(brand)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"brand": brand, "scan_timestamp": scan["timestamp"], "recommendation": recommendation}, indent=2),
        encoding="utf-8",
    )


def _saved_recommendation(brand: str, scan: dict[str, Any]) -> dict[str, Any] | None:
    path = _recommendation_cache_path(brand)
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    recommendation = cached.get("recommendation")
    if (
        cached.get("brand", "").casefold() == brand.casefold()
        and cached.get("scan_timestamp") == scan.get("timestamp")
        and isinstance(recommendation, dict)
    ):
        return recommendation
    return None


def _restored_recommendation(brand: str, scan_number: int, history: dict[str, Any]) -> dict[str, Any]:
    """Restore legacy scans without spending tokens or making a model call on GET."""
    actions = history.get("actions_log", [])
    latest_action = actions[-1] if actions else None
    if latest_action:
        recommendation = (
            f"Review the result of '{latest_action['action']}' against this saved scan, "
            f"then run a new scan for {brand} to refresh its recommendation."
        )
        based_on = latest_action["action"]
    else:
        recommendation = f"Run another scan for {brand} with the same query set to compare against this saved baseline."
        based_on = None
    return {
        "brand": brand,
        "recommendation": recommendation,
        "based_on_past_action": based_on,
        "confidence_note": "Restored from saved history; a fresh AI recommendation is generated on the next scan.",
        "scan_number": scan_number,
    }


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def run_brand_scan(payload: dict[str, Any]) -> dict[str, Any]:
    brand = payload.get("brand")
    category = payload.get("category")
    count = payload.get("num_queries", 10)
    if not isinstance(brand, str) or not brand.strip():
        raise ValueError("Enter a brand name.")
    if not isinstance(category, str) or not category.strip():
        raise ValueError("Enter a category.")
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 20:
        raise ValueError("Query count must be between 1 and 20.")
    if not _mock_mode():
        missing = _missing_live_keys()
        if missing:
            labels = ", ".join(LIVE_PROVIDER_KEYS[key] for key in missing)
            raise ValueError(
                f"Live mode is enabled, but API credentials are missing: {labels}. "
                "Add the keys to the project's .env file and restart the Python API."
            )
    result = run_pipeline(brand.strip(), category.strip(), count)
    try:
        _cache_recommendation(brand.strip(), result["scan"], result["recommendation"])
    except OSError as exc:
        # A cache-disk problem must not turn a scan that was already saved into
        # an apparent failure; dashboard reads can restore a safe fallback.
        print(f"Could not cache recommendation: {exc}")
    return result


def log_brand_action(payload: dict[str, Any]) -> dict[str, Any]:
    brand = payload.get("brand")
    action = payload.get("action")
    outcome = payload.get("outcome_summary")
    delta = payload.get("visibility_delta")
    if not isinstance(brand, str) or not brand.strip():
        raise ValueError("Brand is required to save an action.")
    if not isinstance(action, str) or not action.strip():
        raise ValueError("Describe the action you tried.")
    if not isinstance(outcome, str) or not outcome.strip():
        raise ValueError("Describe the observed result.")
    if not isinstance(delta, (int, float)) or isinstance(delta, bool) or not math.isfinite(delta):
        raise ValueError("Visibility change must be a number of mentions.")
    record = {
        "action": action.strip(),
        "date": datetime.now(timezone.utc).isoformat(),
        "outcome_summary": outcome.strip(),
        "visibility_delta": delta,
    }
    memory.write_action(brand.strip(), record)
    return {"history": memory.read_history(brand.strip()), "action": record}


class ApiHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, result: dict[str, Any]) -> None:
        body = json.dumps(result).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/health":
                mock_mode = _mock_mode()
                self._send(200, {
                    "status": "ok",
                    "mode": "mock" if mock_mode else "live",
                    "ready": mock_mode or not _missing_live_keys(),
                    "missing_keys": [] if mock_mode else _missing_live_keys(),
                })
                return
            if path.startswith("/api/dashboard/"):
                brand = unquote(path.removeprefix("/api/dashboard/"))
                history = memory.read_history(brand)
                if not history["scan_history"]:
                    self._send(200, {"history": history, "scan": None, "recommendation": None})
                    return
                latest_scan = history["scan_history"][-1]
                recommendation = _saved_recommendation(brand, latest_scan)
                if recommendation is None:
                    recommendation = _restored_recommendation(
                        brand, len(history["scan_history"]), history
                    )
                self._send(200, {
                    "history": history,
                    "scan": latest_scan,
                    "recommendation": recommendation,
                })
                return
            if path.startswith("/api/history/"):
                brand = unquote(path.removeprefix("/api/history/"))
                self._send(200, memory.read_history(brand))
                return
            self._send(404, {"detail": "API route not found."})
        except Exception as exc:
            self._send(502, {"detail": f"Could not load dashboard data: {exc}"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/api/scan", "/api/action"}:
            self._send(404, {"detail": "API route not found."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 32_768:
                raise ValueError("Request is too large.")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")
            result = run_brand_scan(payload) if path == "/api/scan" else log_brand_action(payload)
            self._send(200, result)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            self._send(400, {"detail": str(exc)})
        except Exception as exc:
            self._send(502, {"detail": str(exc)})


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), ApiHandler)
    print("GEO Agent API running at http://127.0.0.1:8000")
    print(f"Pipeline mode: {'mock data' if _mock_mode() else 'live providers'}.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping GEO Agent API.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
