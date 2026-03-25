from google import genai
import csv
import os
import json
from datetime import datetime

# Configuration
CSV_FILE = os.getenv("SPREAD_CSV_PATH", "docs/historical_spread.csv")
# Save summary in the same directory as the CSV
SUMMARY_FILE = os.path.join(os.path.dirname(CSV_FILE), "summary.json")
API_KEY = os.getenv("GEMINI_API_KEY")

# Context gathered on March 24, 2026:
# - BoC and Fed held rates at 2.25% and 3.5-3.75% on March 18.
# - Canada CPI slowed to 1.8% (March 16).
# - Yield surge late in the month (Canada 5Y reached 3.218% by March 20).
# - Weak US 2Y auction on March 24 (cleared at 3.936%).
# - Geopolitical tensions in the Middle East driving oil prices over $100/barrel.

MARKET_CONTEXT = """
Current Market Context (March 24, 2026):
1. Central Bank Policy: Both the Bank of Canada (2.25%) and the US Federal Reserve (3.50% – 3.75%) maintained their policy rates on March 18, 2026.
2. Yield Surge: Yields have reached multi-month highs recently. The Canada 5-year yield surged to 3.218% by March 20.
3. US Treasury Auctions: A weak US 2-year note auction on March 24 cleared at 3.936% with a significant 'tail', signaling low investor demand and pushing yields higher globally.
4. Inflation & Energy: Canadian CPI slowed to 1.8% (March 16), but rising oil prices (over $100/barrel) due to Middle East tensions are creating inflationary concerns.
5. US-Canada Link: Canadian yields are closely tracking US Treasury movements, especially after the weak US auctions.
"""

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

    data = get_latest_data(CSV_FILE)
    if not data:
        print("❌ Error: No data found in CSV to summarize.")
        return

    # Prepare data for prompt
    data_summary = "\n".join([
        f"Date: {r['date']}, 2Y: {r['yield_2y']}%, 5Y: {r['yield_5y']}%, Spread: {r['spread']}%"
        for r in data
    ])

    prompt = f"""
You are a senior market analyst for a Canadian Credit Union. 
Analyze the following Canadian Government Bond Yield data (2Y vs 5Y) and provide a concise summary (2-3 paragraphs) for a dashboard.

{MARKET_CONTEXT}

Recent Yield Data (Last 30 Days):
{data_summary}

Your summary should:
1. Explain the current trend in the 2-year and 5-year yields.
2. Correlate the data with the provided US/Canada market context (especially the recent yield surge and US auction results).
3. Explain what this means for a Canadian Financial Institution (FI) specifically regarding:
   - Setting mortgage rates (how the 5Y yield impacts fixed rates).
   - Setting deposit rates (how the 2Y yield impacts GICs).
   - Lending margins and profitability.
4. Keep the tone professional, insightful, and concise.
5. Highlight the impact of the US-Canada bond market link.

Output the summary in plain text.
"""

    try:
        client = genai.Client(api_key=API_KEY)
        
        print("📡 Generating AI summary from Gemini 3 Flash (Preview)...")
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt
        )
        summary_text = response.text.strip()
        
        # Save to JSON
        output = {
            "summary": summary_text,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(SUMMARY_FILE, "w", encoding='utf-8') as f:
            json.dump(output, f, indent=4)
        
        print(f"✅ Summary generated and saved to {SUMMARY_FILE}")
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")

if __name__ == "__main__":
    generate_summary()
