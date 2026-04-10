import requests
import csv
import os
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# Bank of Canada Valet API Series IDs
SERIES_2Y = "BD.CDN.2YR.DQ.YLD"
SERIES_5Y = "BD.CDN.5YR.DQ.YLD"
SERIES_CORRA = "AVG.INTWO"
OUTPUT_FILE = "docs/historical_spread.csv"

def fetch_historical_data():
    """
    Fetches the last 12 months of daily yields for 2Y, 5Y bonds and CORRA
    from the Bank of Canada and calculates the daily spread and repo rate.
    Preserves existing columns (like mortgage rates) if the file exists.
    """
    
    # 1. Load existing data if available
    existing_data = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_data[row['date']] = row
        except Exception as e:
            print(f"⚠️ Warning: Could not read existing file for merge: {e}")

    # 2. Calculate the start date (approximately 12 months ago)
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    url = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}%2C{SERIES_CORRA}/json?start_date={start_date}"
    
    print(f"Fetching data from: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        observations = data.get('observations', [])
        
        if not observations:
            print("No observations found for the requested period.")
            return

        # 3. Extract and format the observations, merging with existing data
        processed_dates = set()
        for obs in observations:
            date = obs.get('d')
            val_2y = obs.get(SERIES_2Y, {}).get('v')
            val_5y = obs.get(SERIES_5Y, {}).get('v')
            val_corra = obs.get(SERIES_CORRA, {}).get('v')
            
            if val_2y and val_5y:
                y2 = float(val_2y)
                y5 = float(val_5y)
                spread = round(y5 - y2, 4)
                
                repo_rate = None
                if val_corra:
                    repo_rate = round(float(val_corra) + 0.5, 4)
                
                row_data = {
                    'date': date,
                    'yield_2y': y2,
                    'yield_5y': y5,
                    'repo_rate': repo_rate,
                    'spread': spread
                }

                # Merge with existing columns
                if date in existing_data:
                    existing_row = existing_data[date]
                    # Preserve columns not fetched by this script
                    for key, val in existing_row.items():
                        if key not in row_data or row_data[key] is None:
                            row_data[key] = val
                
                existing_data[date] = row_data
                processed_dates.add(date)
        
        # 4. Sort all rows by date (Ascending)
        sorted_rows = [existing_data[d] for d in sorted(existing_data.keys())]

        # 5. Write to CSV
        fieldnames = ['date', 'yield_2y', 'yield_5y', 'repo_rate', 'spread', 'mortgage_5y', 'lending_margin']
        with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in sorted_rows:
                # Ensure all fieldnames exist in row
                row_to_write = {fn: row.get(fn, '') for fn in fieldnames}
                writer.writerow(row_to_write)
        
        print(f"Successfully saved {len(sorted_rows)} days of data to {OUTPUT_FILE}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error while connecting to Valet API: {e}")
    except ValueError as e:
        print(f"❌ Data processing error: {e}")
    except IOError as e:
        print(f"❌ File system error: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    fetch_historical_data()
