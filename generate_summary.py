from google import genai
from google.genai import types
import csv
import os
import json
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for systems without zoneinfo (though Python 3.9+ has it)
    from datetime import timezone
    ZoneInfo = None

# Configuration
CSV_FILE = os.getenv("SPREAD_CSV_PATH", "docs/historical_spread.csv")
# Save summary in the same directory as the CSV
SUMMARY_FILE = os.path.join(os.path.dirname(CSV_FILE), "summary.json")
API_KEY = os.getenv("GEMINI_API_KEY")

def get_mountain_time():
    if ZoneInfo:
        return datetime.now(ZoneInfo("America/Edmonton"))
    return datetime.now() # Fallback

def get_latest_data(filename, limit=30):
    """Reads the last 'limit' rows from the CSV."""
    rows = []
    if not os.path.exists(filename):
        return rows
    
    try:
        with open(filename, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        print(f"Error reading CSV: {e}")
    
    return rows[-limit:]

def generate_summary():
    if not API_KEY:
        print("❌ Error: GEMINI_API_KEY not found in environment variables.")
        return

    now_mt = get_mountain_time()
    
    # 1. Check Cache (2 hours)
    previous_summary = ""
    if os.path.exists(SUMMARY_FILE):
        try:
            with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
                prev_data = json.load(f)
                previous_summary = prev_data.get('summary', '')
                last_upd_str = prev_data.get('last_updated', '')
                
                if last_upd_str:
                    last_upd = datetime.strptime(last_upd_str, "%Y-%m-%d %H:%M:%S")
                    # If naive (no TZ), assume it was saved in MT
                    if now_mt.tzinfo:
                        last_upd = last_upd.replace(tzinfo=now_mt.tzinfo)
                    
                    if now_mt - last_upd < timedelta(hours=2):
                        print(f"✨ Summary is less than 2 hours old ({last_upd_str} MT). Skipping API call.")
                        return
        except Exception as e:
            print(f"⚠️ Warning: Could not read previous summary for cache check: {e}")

    data = get_latest_data(CSV_FILE)
    if not data:
        print("❌ Error: No data found in CSV to summarize.")
        return

    # Prepare data for prompt
    data_summary = "\n".join([
        f"Date: {r['date']}, 2Y: {r['yield_2y']}%, 5Y: {r['yield_5y']}%, Spread: {r['spread']}%"
        for r in data
    ])

    current_date_str = now_mt.strftime("%B %d, %Y")
    
    # 2. Integrate Previous Summary into Prompt for continuity
    prev_context = f"\n\nPrevious Analysis Context (to ensure continuity and avoid repetition):\n{previous_summary}" if previous_summary else ""

    prompt = f"""
You are a senior market analyst for a Small Canadian FI. 
Today's date is {current_date_str}.

Analyze the following Canadian Government Bond Yield data (2Y vs 5Y) from the last 30 days:

{data_summary}
{prev_context}

Your task is to provide a concise summary (2-3 paragraphs) for a dashboard.

Requirements:
1. Research and incorporate the LATEST market context for Canadian and US bond markets as of {current_date_str}. 
2. Explain the current trend in the 2-year and 5-year yields.
3. Correlate the data with current events (central bank decisions, inflation data, economic releases, and relevant US Treasury market dynamics).
4. Explain what this means for a Canadian Financial Institution (FI) specifically regarding:
   - Setting mortgage rates (how the 5Y yield impacts fixed rates).
   - Setting deposit rates (how the 2Y yield impacts GICs).
   - Lending margins and profitability.
5. Highlight the impact of the US-Canada bond market link.
6. Use the 'Previous Analysis Context' to maintain continuity in your narrative, but provide a fresh update based on {current_date_str} events.
7. Keep the tone professional, insightful, and concise.

Output the summary in plain text.
"""

    try:
        client = genai.Client(api_key=API_KEY)
        
        print(f"📡 Generating dynamic AI summary using Gemini 3 Flash (Preview) with Google Search grounding...")
        
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        summary_text = response.text.strip()
        
        # Save to JSON with MT timestamp
        output = {
            "summary": summary_text,
            "last_updated": now_mt.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(SUMMARY_FILE, "w", encoding='utf-8') as f:
            json.dump(output, f, indent=4)
        
        print(f"✅ Summary generated and saved to {SUMMARY_FILE} at {output['last_updated']} MT")
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")

if __name__ == "__main__":
    generate_summary()
