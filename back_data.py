import requests
import csv
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# Bank of Canada Valet API Series IDs
SERIES_2Y = "BD.CDN.2YR.DQ.YLD"
SERIES_5Y = "BD.CDN.5YR.DQ.YLD"
OUTPUT_FILE = "historical_spread.csv"

def fetch_historical_data():
    """
    Fetches the last 12 months of daily yields for 2Y and 5Y bonds 
    from the Bank of Canada and calculates the daily spread.
    """
    
    # 1. Calculate the start date (approximately 12 months ago)
    # We use 365 days for a simple 12-month lookback.
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    # Construct the URL for multiple series with a start_date filter
    # The '%2C' is the URL-encoded comma used to separate multiple series IDs.
    url = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}/json?start_date={start_date}"
    
    print(f"Fetching data from: {url}")
    
    try:
        # 2. Execute the HTTP GET request
        response = requests.get(url)
        
        # Raise an exception if the request returned an unsuccessful status code (e.g., 404, 500)
        # This is better than manually checking status_code == 200.
        response.raise_for_status()
        
        data = response.json()
        observations = data.get('observations', [])
        
        if not observations:
            print("No observations found for the requested period.")
            return

        # 3. Prepare to write to CSV
        # We use a context manager ('with') to ensure the file is closed properly even if an error occurs.
        with open(OUTPUT_FILE, mode='w', newline='') as csv_file:
            fieldnames = ['date', 'yield_2y', 'yield_5y', 'spread']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for obs in observations:
                # The API might have missing data points for specific days (weekends/holidays)
                # so we use .get() to avoid KeyErrors.
                date = obs.get('d')
                val_2y = obs.get(SERIES_2Y, {}).get('v')
                val_5y = obs.get(SERIES_5Y, {}).get('v')
                
                # Only process if both yields are present for that date
                if val_2y and val_5y:
                    y2 = float(val_2y)
                    y5 = float(val_5y)
                    spread = round(y5 - y2, 4)
                    
                    writer.writerow({
                        'date': date,
                        'yield_2y': y2,
                        'yield_5y': y5,
                        'spread': spread
                    })
        
        print(f"Successfully saved {len(observations)} days of data to {OUTPUT_FILE}")

    except requests.exceptions.RequestException as e:
        # This catches any network-related errors (DNS, Timeout, etc.)
        print(f"❌ Network error while connecting to Valet API: {e}")
    except ValueError as e:
        # This catches errors in data conversion (e.g., float parsing) or JSON decoding
        print(f"❌ Data processing error: {e}")
    except IOError as e:
        # This catches file system errors (e.g., permission denied)
        print(f"❌ File system error: {e}")
    except Exception as e:
        # Fallback for any other unexpected errors
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    fetch_historical_data()
