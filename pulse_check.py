import requests
import csv
import os
from datetime import datetime

# Bank of Canada Valet API Series IDs:
# BD.CDN.2YR.DQ.YLD = 2-Year Benchmark Bond Yield
# BD.CDN.5YR.DQ.YLD = 5-Year Benchmark Bond Yield
# AVG.INTWO = CORRA (Canadian Overnight Repo Rate Average)
# V39079 = Bank of Canada Target for the Overnight Rate
SERIES_2Y = "BD.CDN.2YR.DQ.YLD"
SERIES_5Y = "BD.CDN.5YR.DQ.YLD"
SERIES_CORRA = "AVG.INTWO"
SERIES_TARGET = "V39079"

# Ratehub API Configuration
RATEHUB_URL = "https://api.ratehub.ca/mortgage-rates/all/purchase-rates?amortization=25&downPaymentPercent=0.05&homePrice=400000&isCashBack=0&isOpen=0&isOwnerOccupied=1&isPreApproval=0&language=en&province=BC&term=60&type=fixed"

# Allow overriding the CSV file path via environment variable for PR previews
CSV_FILE = os.getenv("SPREAD_CSV_PATH", "docs/historical_spread.csv")
EVENTS_FILE = os.getenv("MARKET_EVENTS_PATH", "docs/market_events.json")

# Numeric columns of the historical CSV, in write order after 'date'.
NUMERIC_FIELDS = ('yield_2y', 'yield_5y', 'repo_rate', 'spread', 'mortgage_5y', 'lending_margin')


class HistoricalDataError(Exception):
    """
    Raised when the historical CSV exists but cannot be read completely.

    Callers must treat this as "abort", never as "no history": the CSV is
    rewritten from whatever get_all_rows() returns, so a partial read that is
    mistaken for an empty file destroys every record it failed to reach.
    """


def is_number(value):
    """True if value is a usable numeric reading (not a preserved bad cell)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)

def update_event_outcomes(date, target_rate, prev_target_rate=None):
    """
    Updates market_events.json with the outcome of a BoC meeting.
    """
    if not os.path.exists(EVENTS_FILE):
        return

    import json
    try:
        with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        events = data.get('events', [])
        changed = False

        # Calculate outcome string
        if prev_target_rate is not None:
            diff = float(target_rate) - float(prev_target_rate)
            bps = int(round(diff * 100))
            if bps == 0:
                outcome = "Hold"
            else:
                outcome = f"{bps:+}bps"
        else:
            outcome = f"{target_rate}%"

        # Find the BoC event for this date
        for event in events:
            if event['date'] == date and event['type'] == 'boc':
                if event.get('outcome') != outcome:
                    event['outcome'] = outcome
                    changed = True
                    print(f"📊 Updated BoC event outcome for {date}: {outcome}")

        if changed:
            with open(EVENTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Warning: Could not update event outcomes: {e}")

def get_best_5y_fixed():
    """
    Fetches the best 5-year fixed insured mortgage rate from Ratehub.
    Ref: @MORTGAGE_SPEC.md
    """
    try:
        print("📡 Fetching latest Ratehub mortgage rates...")
        response = requests.get(RATEHUB_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        rates = data.get('data', {}).get('rates', [])
        # Filter: description == "5-yr Fixed" AND insuranceBucket == "insured"
        filtered_rates = [
            float(r['value']) for r in rates 
            if r.get('description') == "5-yr Fixed" and r.get('insuranceBucket') == "insured"
        ]
        
        if not filtered_rates:
            print("⚠️ Warning: No matching 5-yr Fixed insured rates found on Ratehub.")
            return None
            
        best_rate = min(filtered_rates)
        
        # Sanity Check: flag rates > 15% or < 1% as anomalies
        if best_rate > 15.0 or best_rate < 1.0:
            print(f"⚠️ Anomaly Detected: Ratehub reported {best_rate}% which is outside sanity bounds (1%-15%).")
            return None
            
        return best_rate
    except Exception as e:
        print(f"❌ Error fetching Ratehub data: {e}")
        return None

def parse_row(row, filename, line_num):
    """
    Converts one CSV row to typed values.

    A cell that will not parse as a float is preserved verbatim instead of being
    dropped, so one bad value costs at most that value - never the observation,
    and never the rows that follow it.
    """
    parsed = {'date': row['date']}
    for field in NUMERIC_FIELDS:
        raw = row.get(field)
        if raw is None or raw == '':
            parsed[field] = None
            continue
        try:
            parsed[field] = float(raw)
        except (TypeError, ValueError):
            print(f"⚠️ Warning: {filename} line {line_num}: could not parse {field}={raw!r}. Preserving the original value.")
            parsed[field] = raw
    return parsed

def count_existing_dates(filename):
    """
    Counts distinct observation dates on disk.

    Deliberately does not reuse get_all_rows(): the write guard has to stay
    independent of the parsing path it is meant to catch mistakes in.
    """
    if not os.path.exists(filename):
        return 0

    try:
        with open(filename, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header or 'date' not in header:
                raise HistoricalDataError(f"{filename} has no 'date' column (header: {header})")
            date_col = header.index('date')
            return len({row[date_col] for row in reader if len(row) > date_col and row[date_col]})
    except HistoricalDataError:
        raise
    except Exception as e:
        raise HistoricalDataError(f"Could not count observations in {filename}: {e}") from e

def get_all_rows(filename):
    """
    Reads the existing CSV and returns a list of dictionaries.

    Returns [] only when the file genuinely does not exist yet. Any failure to
    read an existing file raises HistoricalDataError rather than returning a
    partial list, because the caller rewrites the CSV from this result.
    """
    if not os.path.exists(filename):
        return []

    rows = []
    try:
        with open(filename, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or 'date' not in reader.fieldnames:
                raise HistoricalDataError(f"{filename} has no 'date' column (header: {reader.fieldnames})")
            for row in reader:
                if not row.get('date'):
                    print(f"⚠️ Warning: {filename} line {reader.line_num}: skipping row with no date.")
                    continue
                rows.append(parse_row(row, filename, reader.line_num))
    except HistoricalDataError:
        raise
    except Exception as e:
        raise HistoricalDataError(f"Could not read {filename}: {e}") from e

    return rows

def update_dashboard_data():
    """
    Fetches BoC and Ratehub data, calculates spread and margin, and updates CSV.
    Returns True if new data was added or existing data updated, False otherwise.
    """
    # 1. Fetch Latest BoC Bond Yields to determine the most recent observation date
    boc_url = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}%2C{SERIES_CORRA}%2C{SERIES_TARGET}/json?recent=10"
    
    try:
        # Fetch bond yields, CORRA and Target Rate
        print(f"📡 Fetching BoC data for {SERIES_2Y}, {SERIES_5Y}, {SERIES_CORRA}, and {SERIES_TARGET}...")
        boc_resp = requests.get(boc_url, timeout=15)
        boc_resp.raise_for_status()
        boc_data = boc_resp.json()
        observations = boc_data.get('observations', [])
        
        if not observations:
            print("No BoC observations found.")
            return False

        # 2. Check if we already have complete data for the latest observation date
        latest_date = max(obs['d'] for obs in observations)
        all_rows = get_all_rows(CSV_FILE)
        existing_data = {row['date']: row for row in all_rows}
        
        latest_row = existing_data.get(latest_date) or {}
        cached_mortgage = latest_row.get('mortgage_5y')

        if is_number(cached_mortgage):
            print(f"✨ Latest observation date {latest_date} already has mortgage data in CSV. Skipping Ratehub API call.")
            best_mortgage = cached_mortgage
        else:
            best_mortgage = get_best_5y_fixed()

        data_changed = False

        # 3. Process observations (sorted by date to track target rate changes)
        prev_target = None
        # We need the observation before the first one in this set to calculate the first change
        # But for simplicity, we'll just track it within this set
        for obs in sorted(observations, key=lambda x: x['d']):
            date = obs['d']
            val_2y = obs.get(SERIES_2Y, {}).get('v')
            val_5y = obs.get(SERIES_5Y, {}).get('v')
            val_corra = obs.get(SERIES_CORRA, {}).get('v')
            val_target = obs.get(SERIES_TARGET, {}).get('v')
            
            # If target rate exists, update events
            if val_target:
                update_event_outcomes(date, val_target, prev_target)
                prev_target = val_target
            
            if val_2y and val_5y:
                y2 = float(val_2y)
                y5 = float(val_5y)
                spread = round(y5 - y2, 4)
                
                # Sanity Check for yields (e.g., flag rates > 15% as per GEMINI.md)
                if abs(y2) > 15.0 or abs(y5) > 15.0:
                    print(f"⚠️ Anomaly Detected: Bond yields for {date} outside sanity bounds.")
                    continue

                # Calculate Repo Rate if CORRA is available (CORRA + 50bps)
                repo_rate = None
                if val_corra:
                    repo_rate = round(float(val_corra) + 0.5, 4)

                # Calculate Lending Margin if we have a mortgage rate
                margin = None
                if best_mortgage is not None:
                    margin = round(best_mortgage - y5, 4)

                row_data = {
                    'date': date,
                    'yield_2y': y2,
                    'yield_5y': y5,
                    'repo_rate': repo_rate,
                    'spread': spread,
                    'mortgage_5y': best_mortgage,
                    'lending_margin': margin
                }

                if date in existing_data:
                    # Only update if current data is incomplete or changed
                    current = existing_data[date]
                    needs_update = False
                    # A cell preserved as a raw string is not a usable reading,
                    # so treat it like a gap and let fresh data heal it.
                    if not is_number(current.get('mortgage_5y')) and best_mortgage is not None:
                        needs_update = True
                    elif current.get('yield_5y') != y5:
                        needs_update = True
                    elif not is_number(current.get('repo_rate')) and repo_rate is not None:
                        needs_update = True
                    
                    if needs_update:
                        existing_data[date].update({k: v for k, v in row_data.items() if v is not None})
                        data_changed = True
                        print(f"✅ Updated existing data for {date}")
                else:
                    existing_data[date] = row_data
                    data_changed = True
                    print(f"✅ Prepared new data for {date}: Spread = {spread}%")
        
        # 4. Prepare sorted output
        sorted_rows = [existing_data[d] for d in sorted(existing_data.keys())]

        # Sanity Check: the history only ever grows. Compare against a count taken
        # straight from disk so a faulty read cannot vouch for its own output.
        existing_count = count_existing_dates(CSV_FILE)
        if len(sorted_rows) < existing_count:
            print(f"❌ Refusing to write {CSV_FILE}: would shrink from {existing_count} to {len(sorted_rows)} observations. Existing data left unchanged.")
            return False

        # Ensure directory exists
        os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)

        # 5. Write to CSV
        fieldnames = ['date', 'yield_2y', 'yield_5y', 'repo_rate', 'spread', 'mortgage_5y', 'lending_margin']
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in sorted_rows:
                writer.writerow(row)
        
        print(f"📁 Dashboard data updated and sorted: {CSV_FILE}")
        return data_changed

    except HistoricalDataError as e:
        print(f"❌ Aborting update to protect existing data: {e}")
        return False
    except Exception as e:
        print(f"❌ Error updating dashboard data: {e}")
        return False

if __name__ == "__main__":
    update_dashboard_data()
