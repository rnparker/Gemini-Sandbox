import pytest
import requests_mock
from pulse_check import get_best_5y_fixed, RATEHUB_URL

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
