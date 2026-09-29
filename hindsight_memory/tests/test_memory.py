import pytest
import os
import sys
import json
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(autouse=True)
def isolate_environment(tmp_path, monkeypatch):
    monkeypatch.setattr("hindsight_memory.DATA_DIR", str(tmp_path))
    test_bank_id = "geo-agent-test"
    monkeypatch.setattr("hindsight_memory.BANK_ID", test_bank_id)
    # We must explicitly initialize so it creates the test bank if missing
    import hindsight_memory
    hindsight_memory.initialize()

from hindsight_memory import (
    validate_scan, validate_action, write_scan, write_action,
    read_history, find_similar_precedent
)

def test_contract_validation():
    with pytest.raises(ValueError, match="Missing required field in scan"):
        validate_scan({"brand": "Test"})
        
    with pytest.raises(ValueError, match="Missing required field in action"):
        validate_action({"action": "Test"})

    valid_scan = {
        "brand": "Valid",
        "timestamp": "2026-09-01T12:00:00Z",
        "queries_tested": ["q1"],
        "mentions": 1,
        "total_queries": 10,
        "competitors_mentioned": {},
        "raw_snippets": []
    }
    validate_scan(valid_scan) # Should not raise

def test_unknown_brand():
    history = read_history("UnknownBrand12345")
    assert history["brand"] == "UnknownBrand12345"
    assert history["scan_history"] == []
    assert history["actions_log"] == []

@patch("hindsight_memory.with_retries")
def test_similar_precedent_without_history(mock_retries):
    from hindsight_client_api.models.recall_response import RecallResponse
    # Return empty results for recall
    mock_retries.return_value = RecallResponse(results=[], trace=None)
    result = find_similar_precedent("UnknownBrand12345", {"mentions": 0, "total_queries": 10})
    assert result["precedent"] is None
    assert result["reason"] == "no history yet"

@patch("hindsight_memory.with_retries")
def test_hindsight_down_fallback(mock_retries):
    mock_retries.side_effect = Exception("Mocked connection error")
    
    # Should use mirror and not crash
    result = write_scan("FallbackBrand", {
        "brand": "FallbackBrand",
        "timestamp": "2026-09-01T12:00:00Z",
        "queries_tested": ["q"],
        "mentions": 1,
        "total_queries": 1,
        "competitors_mentioned": {},
        "raw_snippets": []
    })
    assert result["ok"] is True
    
    # Check mirror
    history = read_history("FallbackBrand")
    assert len(history["scan_history"]) == 1

def test_write_read_roundtrip():
    brand = "RoundTripBrand"
    scan = {
        "brand": brand,
        "timestamp": "2026-09-01T12:00:00Z",
        "queries_tested": ["rt"],
        "mentions": 5,
        "total_queries": 10,
        "competitors_mentioned": {},
        "raw_snippets": []
    }
    write_scan(brand, scan)
    history = read_history(brand)
    assert len(history["scan_history"]) >= 1
    assert history["scan_history"][-1]["brand"] == brand

def test_similar_precedent_with_history():
    brand = "ZenBookX"
    scan = {"mentions": 5, "total_queries": 20}
    # ZenBookX was seeded with actions, should find one
    result = find_similar_precedent(brand, scan)
    
    assert "precedent" in result
    assert "reason" in result
    assert "source" in result
