import requests
import csv
import os
from datetime import datetime

# Bank of Canada Valet API Series IDs:
# BD.CDN.2YR.DQ.YLD = 2-Year Benchmark Bond Yield
# BD.CDN.5YR.DQ.YLD = 5-Year Benchmark Bond Yield
# AVG.INTWO = CORRA (Canadian Overnight Repo Rate Average)
SERIES_2Y = "BD.CDN.2YR.DQ.YLD"
SERIES_5Y = "BD.CDN.5YR.DQ.YLD"
SERIES_CORRA = "AVG.INTWO"

# Ratehub API Configuration
RATEHUB_URL = "https://api.ratehub.ca/mortgage-rates/all/purchase-rates?amortization=25&downPaymentPercent=0.05&homePrice=400000&isCashBack=0&isOpen=0&isOwnerOccupied=1&isPreApproval=0&language=en&province=BC&term=60&type=fixed"

# Allow overriding the CSV file path via environment variable for PR previews
CSV_FILE = os.getenv("SPREAD_CSV_PATH", "docs/historical_spread.csv")

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

def get_all_rows(filename):
    """
    Reads the existing CSV and returns a list of dictionaries.
    """
    rows = []
    if not os.path.exists(filename):
        return rows
    
    try:
        with open(filename, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({
                    'date': row['date'],
                    'yield_2y': float(row['yield_2y']) if row.get('yield_2y') else None,
                    'yield_5y': float(row['yield_5y']) if row.get('yield_5y') else None,
                    'repo_rate': float(row['repo_rate']) if row.get('repo_rate') else None,
                    'spread': float(row['spread']) if row.get('spread') else None,
                    'mortgage_5y': float(row['mortgage_5y']) if row.get('mortgage_5y') else None,
                    'lending_margin': float(row['lending_margin']) if row.get('lending_margin') else None
                })
    except Exception as e:
        print(f"⚠️ Warning: Could not read existing file {filename}: {e}")
    
    return rows

def update_dashboard_data():
    """
    Fetches BoC and Ratehub data, calculates spread and margin, and updates CSV.
    Returns True if new data was added or existing data updated, False otherwise.
    """
    # 1. Fetch Latest BoC Bond Yields to determine the most recent observation date
    boc_url = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}%2CSERIES_CORRA/json?recent=10"
    # Actually, the string representation of SERIES_CORRA should be used in the URL
    boc_url = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}%2C{SERIES_CORRA}/json?recent=10"
    
    try:
        # Fetch bond yields and CORRA
        print(f"📡 Fetching BoC yields for {SERIES_2Y}, {SERIES_5Y}, and {SERIES_CORRA}...")
        boc_resp = requests.get(boc_url, timeout=15)
        boc_resp.raise_for_status()
        boc_data = boc_resp.json()
        observations = boc_data.get('observations', [])
        
        if not observations:
            print("No BoC observations found.")
            return False

        # 2. Check if we already have complete data for the latest observation date
        # This acts as a rate-limiting mechanism for the Ratehub API.
        # BoC API may return observations in descending order. Use max() for safety.
        latest_date = max(obs['d'] for obs in observations)
        all_rows = get_all_rows(CSV_FILE)
        existing_data = {row['date']: row for row in all_rows}
        
        best_mortgage = None
        latest_row = existing_data.get(latest_date)
        
        # If the latest date exists and already has mortgage data, skip Ratehub API call
        if latest_row and latest_row.get('mortgage_5y') is not None:
            print(f"✨ Latest observation date {latest_date} already has mortgage data in CSV. Skipping Ratehub API call.")
            best_mortgage = latest_row['mortgage_5y']
        else:
            # Fetch latest mortgage rate only if needed
            best_mortgage = get_best_5y_fixed()

        data_changed = False

        # 3. Process observations
        for obs in observations:
            date = obs['d']
            val_2y = obs.get(SERIES_2Y, {}).get('v')
            val_5y = obs.get(SERIES_5Y, {}).get('v')
            val_corra = obs.get(SERIES_CORRA, {}).get('v')
            
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
                    if current.get('mortgage_5y') is None and best_mortgage is not None:
                        needs_update = True
                    elif current.get('yield_5y') != y5:
                        needs_update = True
                    elif current.get('repo_rate') is None and repo_rate is not None:
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
            
    except Exception as e:
        print(f"❌ Error updating dashboard data: {e}")
        return False

if __name__ == "__main__":
    update_dashboard_data()
