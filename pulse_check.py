import requests
import csv
import os

# Bank of Canada Valet API Series IDs:
# BD.CDN.2YR.DQ.YLD = 2-Year Benchmark Bond Yield
# BD.CDN.5YR.DQ.YLD = 5-Year Benchmark Bond Yield
SERIES_2Y = "BD.CDN.2YR.DQ.YLD"
SERIES_5Y = "BD.CDN.5YR.DQ.YLD"
CSV_FILE = "docs/historical_spread.csv"

def get_all_rows(filename):
    """
    Reads the existing CSV and returns a list of dictionaries.
    """
    rows = []
    if not os.path.exists(filename):
        return rows
    
    try:
        with open(filename, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Ensure values are stored as floats for consistency
                rows.append({
                    'date': row['date'],
                    'yield_2y': float(row['yield_2y']),
                    'yield_5y': float(row['yield_5y']),
                    'spread': float(row['spread'])
                })
    except Exception as e:
        print(f"⚠️ Warning: Could not read existing file {filename}: {e}")
    
    return rows

def update_can_spread():
    """
    Fetches the latest spread data, merges it with existing data, 
    sorts by date, and rewrites the CSV.
    """
    # Fetching the last 10 observations to ensure we don't miss days 
    # if the action didn't run for a while (e.g., over a long weekend).
    url = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}/json?recent=10"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        observations = data.get('observations', [])
        if not observations:
            print("No observations found.")
            return

        # 1. Get all current rows
        all_rows = get_all_rows(CSV_FILE)
        existing_dates = {row['date'] for row in all_rows}
        new_data_found = False

        # 2. Filter for new observations only
        for obs in observations:
            date = obs['d']
            
            # Skip if date is already in our CSV
            if date in existing_dates:
                continue
                
            val_2y = obs.get(SERIES_2Y, {}).get('v')
            val_5y = obs.get(SERIES_5Y, {}).get('v')
            
            if val_2y and val_5y:
                y2 = float(val_2y)
                y5 = float(val_5y)
                spread = round(y5 - y2, 4)
                
                all_rows.append({
                    'date': date,
                    'yield_2y': y2,
                    'yield_5y': y5,
                    'spread': spread
                })
                new_data_found = True
                print(f"✅ Prepared data for {date}: Spread = {spread}%")
        
        if not new_data_found:
            print("✨ No new data to add.")
            # We still sort and rewrite just to be absolutely sure the file is in order
            # as requested by the user, even if no new data was found.
        
        # 3. Sort all rows by date (Ascending)
        # Python's sort is stable, and date strings (YYYY-MM-DD) sort correctly.
        all_rows.sort(key=lambda x: x['date'])

        # 4. Rewrite the CSV with sorted data
        with open(CSV_FILE, mode='w', newline='') as f:
            fieldnames = ['date', 'yield_2y', 'yield_5y', 'spread']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in all_rows:
                writer.writerow(row)
        
        if new_data_found:
            print(f"📁 CSV updated and sorted: {CSV_FILE}")
        else:
            print(f"📁 CSV verified and sorted: {CSV_FILE}")
            
    except Exception as e:
        print(f"❌ Error updating data: {e}")

if __name__ == "__main__":
    update_can_spread()
