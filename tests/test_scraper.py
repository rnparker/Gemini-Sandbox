import pytest
import requests_mock
import os
import csv
from pulse_check import get_best_5y_fixed, update_dashboard_data, SERIES_2Y, SERIES_5Y, SERIES_CORRA, RATEHUB_URL

def test_get_best_5y_fixed_success():
    """
    Test successful extraction of the best 5-year fixed insured rate.
    Based on @MORTGAGE_SPEC.md logic.
    """
    mock_data = {
        "data": {
            "primeRate": 4.45,
            "qualifyingRate": 5.25,
            "rates": [
                {
                    "value": 4.10,
                    "description": "5-yr Fixed",
                    "provider": "bank-a",
                    "insuranceBucket": "insured"
                },
                {
                    "value": 3.94,
                    "description": "5-yr Fixed",
                    "provider": "bank-b",
                    "insuranceBucket": "insured"
                },
                {
                    "value": 4.50,
                    "description": "5-yr Fixed",
                    "provider": "bank-c",
                    "insuranceBucket": "uninsured"
                },
                {
                    "value": 4.20,
                    "description": "3-yr Fixed",
                    "provider": "bank-d",
                    "insuranceBucket": "insured"
                }
            ]
        }
    }
    
    with requests_mock.Mocker() as m:
        m.get(RATEHUB_URL, json=mock_data)
        rate = get_best_5y_fixed()
        # Should pick 3.94 as it is the minimum of "5-yr Fixed" + "insured"
        assert rate == 3.94

def test_get_best_5y_fixed_no_match():
    """
    Test scenario where no matching rates are found.
    """
    mock_data = {
        "data": {
            "rates": [
                {
                    "value": 4.50,
                    "description": "5-yr Fixed",
                    "provider": "bank-c",
                    "insuranceBucket": "uninsured"
                }
            ]
        }
    }
    
    with requests_mock.Mocker() as m:
        m.get(RATEHUB_URL, json=mock_data)
        rate = get_best_5y_fixed()
        assert rate is None

def test_get_best_5y_fixed_sanity_check_high():
    """
    Test sanity check for high rates (> 15%).
    """
    mock_data = {
        "data": {
            "rates": [
                {
                    "value": 16.0,
                    "description": "5-yr Fixed",
                    "insuranceBucket": "insured"
                }
            ]
        }
    }
    
    with requests_mock.Mocker() as m:
        m.get(RATEHUB_URL, json=mock_data)
        rate = get_best_5y_fixed()
        assert rate is None

def test_get_best_5y_fixed_sanity_check_low():
    """
    Test sanity check for low rates (< 1%).
    """
    mock_data = {
        "data": {
            "rates": [
                {
                    "value": 0.5,
                    "description": "5-yr Fixed",
                    "insuranceBucket": "insured"
                }
            ]
        }
    }
    
    with requests_mock.Mocker() as m:
        m.get(RATEHUB_URL, json=mock_data)
        rate = get_best_5y_fixed()
        assert rate is None

def test_get_best_5y_fixed_api_error():
    """
    Test API error handling.
    """
    with requests_mock.Mocker() as m:
        m.get(RATEHUB_URL, status_code=500)
        rate = get_best_5y_fixed()
        assert rate is None

def test_update_dashboard_data_rate_limit(tmp_path):
    """
    Test that Ratehub API is skipped if the latest BoC date already has mortgage data.
    """
    # Create a temporary CSV file
    csv_file = tmp_path / "test_spread.csv"
    import pulse_check
    pulse_check.CSV_FILE = str(csv_file)
    
    # Pre-populate CSV with "complete" data for the latest date
    with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'yield_2y', 'yield_5y', 'repo_rate', 'spread', 'mortgage_5y', 'lending_margin'])
        writer.writeheader()
        writer.writerow({
            'date': '2026-03-25',
            'yield_2y': 2.5,
            'yield_5y': 3.0,
            'repo_rate': 4.5,
            'spread': 0.5,
            'mortgage_5y': 4.0,
            'lending_margin': 1.0
        })

    # Mock BoC API to return observations (descending order)
    boc_url = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}%2C{SERIES_CORRA}/json?recent=10"
    mock_boc_data = {
        "observations": [
            {"d": "2026-03-25", SERIES_2Y: {"v": "2.5"}, SERIES_5Y: {"v": "3.0"}, SERIES_CORRA: {"v": "4.0"}},
            {"d": "2026-03-24", SERIES_2Y: {"v": "2.4"}, SERIES_5Y: {"v": "2.9"}, SERIES_CORRA: {"v": "4.0"}}
        ]
    }

    with requests_mock.Mocker() as m:
        m.get(boc_url, json=mock_boc_data)
        # RATEHUB_URL is NOT mocked, so it will error if called.
        
        update_dashboard_data()
        
        with open(csv_file, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[1]['date'] == '2026-03-25'
            assert rows[1]['mortgage_5y'] == '4.0'
            assert rows[1]['repo_rate'] == '4.5'

def test_update_dashboard_data_no_rate_limit(tmp_path):
    """
    Test that Ratehub API IS called if the latest BoC date is missing mortgage data.
    """
    csv_file = tmp_path / "test_spread_no_limit.csv"
    import pulse_check
    pulse_check.CSV_FILE = str(csv_file)
    
    with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'yield_2y', 'yield_5y', 'repo_rate', 'spread', 'mortgage_5y', 'lending_margin'])
        writer.writeheader()
        writer.writerow({
            'date': '2026-03-25',
            'yield_2y': 2.5,
            'yield_5y': 3.0,
            'repo_rate': 4.5,
            'spread': 0.5,
            'mortgage_5y': '', # Missing
            'lending_margin': ''
        })

    boc_url = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}%2C{SERIES_CORRA}/json?recent=10"
    mock_boc_data = {
        "observations": [
            {"d": "2026-03-25", SERIES_2Y: {"v": "2.5"}, SERIES_5Y: {"v": "3.0"}, SERIES_CORRA: {"v": "4.0"}}
        ]
    }
    
    mock_ratehub_data = {
        "data": {
            "rates": [
                {"value": 3.99, "description": "5-yr Fixed", "insuranceBucket": "insured"}
            ]
        }
    }

    with requests_mock.Mocker() as m:
        m.get(boc_url, json=mock_boc_data)
        m.get(RATEHUB_URL, json=mock_ratehub_data)
        
        update_dashboard_data()
        
        assert m.call_count == 2
        
        with open(csv_file, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert rows[0]['mortgage_5y'] == '3.99'
            assert rows[0]['repo_rate'] == '4.5'

