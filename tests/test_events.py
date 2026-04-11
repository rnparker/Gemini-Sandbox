import json
import os

def test_market_events_valid_json():
    """
    Test that docs/market_events.json exists and is valid JSON.
    """
    events_file = "docs/market_events.json"
    assert os.path.exists(events_file)
    
    with open(events_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "events" in data
    assert isinstance(data["events"], list)
    
    for event in data["events"]:
        assert "date" in event
        assert "label" in event
        assert "type" in event
        assert "outcome" in event
        assert "details" in event
        assert event["type"] in ["boc", "cpi"]
        # Basic date format check (YYYY-MM-DD)
        parts = event["date"].split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4
        assert len(parts[1]) == 2
        assert len(parts[2]) == 2
