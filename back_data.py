import requests
import csv
import os
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# Bank of Canada Valet API Series IDs
SERIES_2Y = "BD.CDN.2YR.DQ.YLD"
SERIES_5Y = "BD.CDN.5YR.DQ.YLD"
OUTPUT_FILE = "docs/historical_spread.csv"

def fetch_historical_data():
    """
    Fetches the last 12 months of daily yields for 2Y and 5Y bonds 
    from the Bank of Canada and calculates the daily spread.
    Ensures the data is saved in ascending chronological order.
    """
    
    # 1. Calculate the start date (approximately 12 months ago)
    # We use 365 days for a simple 12-month lookback.
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    # Construct the URL for multiple series with a start_date filter
    url = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}/json?start_date={start_date}"
    
    print(f"Fetching data from: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        observations = data.get('observations', [])
        
        if not observations:
            print("No observations found for the requested period.")
            return

        # 2. Extract and format the observations
        all_rows = []
        for obs in observations:
            date = obs.get('d')
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
        
        # 3. Sort by date (Ascending)
        # Even though the BoC API usually returns data chronologically, 
        # this step ensures we meet the 'ascending order' requirement regardless.
        all_rows.sort(key=lambda x: x['date'])

        # 4. Write to CSV
        with open(OUTPUT_FILE, mode='w', newline='') as csv_file:
            fieldnames = ['date', 'yield_2y', 'yield_5y', 'spread']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in all_rows:
                writer.writerow(row)
        
        print(f"Successfully saved {len(all_rows)} days of data to {OUTPUT_FILE}")

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
