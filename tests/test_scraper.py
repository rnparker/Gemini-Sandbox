import pytest
import requests_mock
import os
import csv
import pulse_check
from pulse_check import get_best_5y_fixed, get_all_rows, update_dashboard_data, HistoricalDataError, SERIES_2Y, SERIES_5Y, SERIES_CORRA, SERIES_TARGET, RATEHUB_URL

HEADER = 'date,yield_2y,yield_5y,repo_rate,spread,mortgage_5y,lending_margin\n'
BOC_URL = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}%2C{SERIES_CORRA}%2C{SERIES_TARGET}/json?recent=10"


@pytest.fixture(autouse=True)
def restore_csv_path():
    """Tests below repoint the module-level CSV_FILE; put it back afterwards."""
    original = pulse_check.CSV_FILE
    yield
    pulse_check.CSV_FILE = original

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

def test_get_all_rows_preserves_rows_after_a_bad_cell(tmp_path):
    """
    A value that will not parse must not cost us that row or the rows after it.
    Regression test: the read used to abort on the first bad cell and return a
    truncated list, which the caller then wrote back as the whole file.
    """
    csv_file = tmp_path / "corrupt.csv"
    csv_file.write_text(
        HEADER +
        "2026-01-01,2.5,3.0,3.5,0.5,4.0,1.0\n"
        "2026-01-02,2.5,BAD,3.5,0.5,4.0,1.0\n"
        "2026-01-03,2.6,3.1,3.5,0.5,4.0,1.0\n",
        encoding='utf-8'
    )

    rows = get_all_rows(str(csv_file))

    assert [r['date'] for r in rows] == ['2026-01-01', '2026-01-02', '2026-01-03']
    # The unparseable cell is kept verbatim rather than discarded.
    assert rows[1]['yield_5y'] == 'BAD'
    # Its neighbours in the same row are still parsed normally.
    assert rows[1]['yield_2y'] == 2.5


def test_get_all_rows_raises_when_an_existing_file_cannot_be_read(tmp_path):
    """
    A failed read must be distinguishable from 'no history yet'. Returning []
    here would make the caller rewrite the file from scratch.
    """
    headerless = tmp_path / "headerless.csv"
    headerless.write_text("2026-01-01,2.5,3.0\n", encoding='utf-8')

    with pytest.raises(HistoricalDataError):
        get_all_rows(str(headerless))

    # A genuinely absent file is still an empty history, not an error.
    assert get_all_rows(str(tmp_path / "does_not_exist.csv")) == []


def test_update_dashboard_data_keeps_every_row_when_csv_has_a_bad_cell(tmp_path):
    """
    End-to-end guard: a corrupt cell must not shrink the file on rewrite.
    """
    csv_file = tmp_path / "corrupt_roundtrip.csv"
    pulse_check.CSV_FILE = str(csv_file)
    original_dates = ['2020-01-01', '2020-01-02', '2020-01-03', '2020-01-06']
    csv_file.write_text(
        HEADER + "".join(
            f"{d},2.5,{'BAD' if d == '2020-01-02' else '3.0'},3.5,0.5,4.0,1.0\n"
            for d in original_dates
        ),
        encoding='utf-8'
    )

    mock_boc_data = {
        "observations": [
            {"d": "2026-03-25", SERIES_2Y: {"v": "2.5"}, SERIES_5Y: {"v": "3.0"}, SERIES_CORRA: {"v": "4.0"}}
        ]
    }
    mock_ratehub_data = {
        "data": {"rates": [{"value": 3.99, "description": "5-yr Fixed", "insuranceBucket": "insured"}]}
    }

    with requests_mock.Mocker() as m:
        m.get(BOC_URL, json=mock_boc_data)
        m.get(RATEHUB_URL, json=mock_ratehub_data)
        update_dashboard_data()

    with open(csv_file, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # Every original row survives, plus the newly fetched observation.
    assert [r['date'] for r in rows] == original_dates + ['2026-03-25']
    # The corrupt cell round-trips untouched instead of being silently zeroed.
    assert rows[1]['yield_5y'] == 'BAD'


def test_update_dashboard_data_refuses_to_shrink_the_csv(tmp_path, monkeypatch):
    """
    Defence in depth: if anything ever drops rows between read and write, the
    write is refused and the good file stays on disk.
    """
    csv_file = tmp_path / "shrink.csv"
    pulse_check.CSV_FILE = str(csv_file)
    contents = HEADER + "".join(f"2020-01-0{i},2.5,3.0,3.5,0.5,4.0,1.0\n" for i in range(1, 5))
    csv_file.write_text(contents, encoding='utf-8')

    real_get_all_rows = pulse_check.get_all_rows

    def lose_rows_after_read(filename):
        rows = real_get_all_rows(filename)
        # Simulate a downstream bug that drops records.
        return rows[:1] if len(rows) > 1 else rows

    monkeypatch.setattr(pulse_check, 'get_all_rows', lose_rows_after_read)

    mock_boc_data = {"observations": [{"d": "2020-01-01", SERIES_2Y: {"v": "2.5"}, SERIES_5Y: {"v": "3.0"}}]}

    with requests_mock.Mocker() as m:
        m.get(BOC_URL, json=mock_boc_data)
        m.get(RATEHUB_URL, json={"data": {"rates": []}})
        assert update_dashboard_data() is False

    assert csv_file.read_text(encoding='utf-8') == contents


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
    boc_url = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}%2C{SERIES_CORRA}%2C{SERIES_TARGET}/json?recent=10"
    mock_boc_data = {
        "observations": [
            {"d": "2026-03-25", SERIES_2Y: {"v": "2.5"}, SERIES_5Y: {"v": "3.0"}, SERIES_CORRA: {"v": "4.0"}, SERIES_TARGET: {"v": "4.25"}},
            {"d": "2026-03-24", SERIES_2Y: {"v": "2.4"}, SERIES_5Y: {"v": "2.9"}, SERIES_CORRA: {"v": "4.0"}, SERIES_TARGET: {"v": "4.25"}}
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

    boc_url = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}%2C{SERIES_CORRA}%2C{SERIES_TARGET}/json?recent=10"
    mock_boc_data = {
        "observations": [
            {"d": "2026-03-25", SERIES_2Y: {"v": "2.5"}, SERIES_5Y: {"v": "3.0"}, SERIES_CORRA: {"v": "4.0"}, SERIES_TARGET: {"v": "4.25"}}
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
