import requests
import csv
import os
from datetime import datetime

# Bank of Canada Valet API Series IDs:
# BD.CDN.2YR.DQ.YLD = 2-Year Benchmark Bond Yield
# BD.CDN.5YR.DQ.YLD = 5-Year Benchmark Bond Yield
SERIES_2Y = "BD.CDN.2YR.DQ.YLD"
SERIES_5Y = "BD.CDN.5YR.DQ.YLD"

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
    """
    # 1. Fetch Latest BoC Bond Yields
    boc_url = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}/json?recent=10"
    
    try:
        # Fetch bond yields
        print(f"📡 Fetching BoC yields for {SERIES_2Y} and {SERIES_5Y}...")
        boc_resp = requests.get(boc_url, timeout=15)
        boc_resp.raise_for_status()
        boc_data = boc_resp.json()
        observations = boc_data.get('observations', [])
        
        if not observations:
            print("No BoC observations found.")
            return

        # Fetch latest mortgage rate
        print("📡 Fetching latest Ratehub mortgage rates...")
        best_mortgage = get_best_5y_fixed()

        # 2. Load existing data
        all_rows = get_all_rows(CSV_FILE)
        existing_data = {row['date']: row for row in all_rows}
        new_data_found = False

        # 3. Process observations
        for obs in observations:
            date = obs['d']
            val_2y = obs.get(SERIES_2Y, {}).get('v')
            val_5y = obs.get(SERIES_5Y, {}).get('v')
            
            if val_2y and val_5y:
                y2 = float(val_2y)
                y5 = float(val_5y)
                spread = round(y5 - y2, 4)
                
                # Sanity Check for yields (e.g., flag rates > 15% as per GEMINI.md)
                if abs(y2) > 15.0 or abs(y5) > 15.0:
                    print(f"⚠️ Anomaly Detected: Bond yields for {date} outside sanity bounds.")
                    continue

                # Calculate Lending Margin if we have a mortgage rate
                # Per GEMINI.md: Lending Margin = Best 5Y Fixed Rate - CAN 5Y Bond Yield
                margin = None
                if best_mortgage is not None:
                    margin = round(best_mortgage - y5, 4)

                row_data = {
                    'date': date,
                    'yield_2y': y2,
                    'yield_5y': y5,
                    'spread': spread,
                    'mortgage_5y': best_mortgage,
                    'lending_margin': margin
                }

                if date in existing_data:
                    # Update existing record with latest calculations
                    existing_data[date].update({k: v for k, v in row_data.items() if v is not None})
                else:
                    existing_data[date] = row_data
                    new_data_found = True
                    print(f"✅ Prepared new data for {date}: Spread = {spread}%")
        
        # 4. Prepare sorted output
        sorted_rows = [existing_data[d] for d in sorted(existing_data.keys())]

        # Ensure directory exists
        os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)

        # 5. Write to CSV
        fieldnames = ['date', 'yield_2y', 'yield_5y', 'spread', 'mortgage_5y', 'lending_margin']
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in sorted_rows:
                writer.writerow(row)
        
        print(f"📁 Dashboard data updated and sorted: {CSV_FILE}")
            
    except Exception as e:
        print(f"❌ Error updating dashboard data: {e}")

if __name__ == "__main__":
    update_dashboard_data()
