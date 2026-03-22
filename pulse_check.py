import requests
import json

# Bank of Canada Valet API Series IDs:
# BD.CDN.2YR.DQ.YLD = 2-Year Benchmark Bond Yield
# BD.CDN.5YR.DQ.YLD = 5-Year Benchmark Bond Yield
SERIES_2Y = "BD.CDN.2YR.DQ.YLD"
SERIES_5Y = "BD.CDN.5YR.DQ.YLD"

def get_can_spread():
    url = f"https://www.bankofcanada.ca/valet/observations/{SERIES_2Y}%2C{SERIES_5Y}/json?recent=1"
    
    try:
        response = requests.get(url)
        response.raise_for_status() # Check for HTTP errors (like a 404 or 500)
        data = response.json()
        
        # Pulling the latest observation from the JSON structure
        # Note: The BoC API nests data inside 'observations'
        latest_obs = data['observations'][-1]
        
        yield_2y = float(latest_obs[SERIES_2Y]['v'])
        yield_5y = float(latest_obs[SERIES_5Y]['v'])
        
        # The Spread (CAN 2-5)
        spread = yield_5y - yield_2y
        
        print(f"--- CAN 2-5 SPREAD REPORT ---")
        print(f"Date: {latest_obs['d']}")
        print(f"CAN 2Y: {yield_2y}%")
        print(f"CAN 5Y: {yield_5y}%")
        print(f"Spread: {spread:.3f}%")
        
        if spread < 0:
            print("⚠️ ALERT: The 2-5 curve is INVERTED.")
        else:
            print("✅ The curve is currently positive.")
            
    except Exception as e:
        print(f"❌ Error fetching BoC data: {e}")

if __name__ == "__main__":
    get_can_spread()