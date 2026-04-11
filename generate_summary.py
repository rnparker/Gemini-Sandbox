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

def generate_summary(force=False):
    if not API_KEY:
        print("❌ Error: GEMINI_API_KEY not found in environment variables.")
        return

    now_mt = get_mountain_time()
    
    # 1. Check Cache (2 hours) and Load History
    history = []
    previous_summary = ""
    if os.path.exists(SUMMARY_FILE):
        try:
            with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
                prev_data = json.load(f)
                previous_summary = prev_data.get('summary', '')
                last_upd_str = prev_data.get('last_updated', '')
                history = prev_data.get('history', [])
                
                # Migration: if no history but we have a summary, start history
                if not history and previous_summary and last_upd_str:
                    history = [{"date": last_upd_str, "summary": previous_summary}]

                if last_upd_str and not force:
                    last_upd = datetime.strptime(last_upd_str, "%Y-%m-%d %H:%M:%S")
                    # If naive (no TZ), assume it was saved in MT
                    if now_mt.tzinfo:
                        last_upd = last_upd.replace(tzinfo=now_mt.tzinfo)
                    
                    if now_mt - last_upd < timedelta(hours=2):
                        print(f"✨ Summary is less than 2 hours old ({last_upd_str} MT). Skipping API call.")
                        return
        except Exception as e:
            print(f"⚠️ Warning: Could not read previous summary for cache and history: {e}")

    data = get_latest_data(CSV_FILE)
    if not data:
        print("❌ Error: No data found in CSV to summarize.")
        return

    # 1b. Skip if the latest data point is already summarized (unless forced)
    if not force and history:
        latest_csv_date = data[-1]['date']
        # The history stores the timestamp of the SUMMARY generation, not the data date.
        # However, we can check if the summary text itself contains the date, 
        # but a more robust way is to check if we've already generated a summary 
        # since the CSV was last modified, OR if the latest date in CSV is old.
        # For now, we'll rely on the 2-hour cache OR a simple check:
        # If the latest date in CSV is already in our history context (approximate), skip.
        # Actually, the simplest way is to check if the caller told us to run.
        pass

    # Prepare data for prompt
    data_summary = "\n".join([
        f"Date: {r['date']}, 2Y: {r['yield_2y']}%, 5Y: {r['yield_5y']}%, Repo Rate (CORRA+50bps): {r.get('repo_rate', 'N/A')}%, Spread: {r['spread']}%, Best 5Y Fixed: {r.get('mortgage_5y', 'N/A')}%, Margin: {r.get('lending_margin', 'N/A')}%"
        for r in data
    ])

    current_date_str = now_mt.strftime("%B %d, %Y")
    
    # 2. Integrate Previous Summaries into Prompt for continuity
    # We provide the last 10 summaries from history
    history_context = ""
    if history:
        history_items = []
        # Sort history by date descending (newest first) and take top 10
        sorted_history = sorted(history, key=lambda x: x['date'], reverse=True)[:10]
        for item in sorted_history:
            history_items.append(f"--- Summary from {item['date']} ---\n{item['summary']}")
        
        history_context = "\n\n### PREVIOUS ANALYSIS HISTORY (Context to ensure continuity) ###\n"
        history_context += "\n\n".join(history_items)
        history_context += "\n\n### END OF HISTORY ###"

    prompt = f"""
You are a senior market analyst providing generic commentary for a Small Canadian Financial Institution (FI). 
Today's date is {current_date_str}.

Analyze the following Canadian Government Bond Yield data (2Y vs 5Y), the Reference Repo Rate (CORRA + 50 bps), and institutional mortgage data from the last 30 days:

{data_summary}

{history_context}

Your task is to provide two outputs:
1. A revised and improved concise market summary (2-3 paragraphs).
2. A JSON-formatted data extraction of any Canadian market events that occurred TODAY.

### MANDATORY GUIDELINES FOR SUMMARY ###
- **STRICTLY NO FIRST-PERSON PRONOUNS:** Do not use "we", "our", "us", or "I".
- **GENERIC COMMENTARY ONLY:** Do NOT refer to the dashboard's owner or host as "our institution" or "our rates". 
- **NO RATE OWNERSHIP:** The mortgage rates provided are from other institutions in the market, NOT the institution this summary is for. Do not imply ownership of these rates.
- **DO NOT USE PHRASES LIKE:** "For our institution", "While our best 5-year fixed mortgage...", "our lending margin". Use instead: "For a typical small FI", "The market's best 5-year fixed mortgage...", "The lending margin".

Summary Requirements:
1. Research and incorporate the LATEST major market happenings for Canadian and US bond markets as of {current_date_str}. Commentary should correlate with the visual annotations (BoC/CPI) provided on the dashboard charts.
2. Explicitly correlate the data with these happenings (e.g., specific central bank speeches, policy changes, geopolitical events, key economic data like CPI/Jobs, and US Treasury volatility).
3. Explain the current trend in the 2-year and 5-year yields and the resulting spread.
4. **REPO RATE ANALYSIS:** Discuss the Reference Repo Rate (CORRA + 50 bps). How does it relate to the 2-year and 5-year bond yields? What does its current level suggest about overnight funding costs and liquidity compared to longer-term bond yields?
5. Integrate the 'Best 5Y Fixed' mortgage rate and 'Lending Margin' into your analysis. How are these responding to the underlying bond moves?
6. Explain what this means for a small Canadian Financial Institution (FI) generically regarding:
   - Setting mortgage rates (how the 5Y yield impacts fixed rates).
   - Setting deposit rates (how the 2Y yield impacts GICs).
   - Funding costs (using the Repo Rate as a proxy for institutional borrowing costs).
   - Lending margins and institutional profitability.
   - **LIQUIDITY STRATEGY:** Discuss how a "net long" (surplus) vs "net short" (deficit) liquidity position changes an FI's pricing strategy. For example, how a net short position (high reliance on CORRA-indexed wholesale funding) requires more defensive loan pricing (higher margins) and aggressive deposit gathering, whereas a net long position allows for more aggressive asset pricing to deploy excess capital, especially when the 2-5 spread is volatile.
7. Highlight the impact of the US-Canada bond market link.
8. **CONTINUITY & CONTEXT:** Use the provided 'PREVIOUS ANALYSIS HISTORY' to maintain a narrative arc. 
   - DO NOT treat recurring events (e.g., ongoing geopolitical tension or already reported CPI data) as "net new" information if they appear in the history.
   - Instead, treat them as "continuing the story" or provide an update on how the situation has evolved since the last report.
   - Avoid repeating the same general observations from previous days unless there is a significant change in the data or market sentiment.
9. Keep the tone professional, insightful, and concise. 

### DATA EXTRACTION REQUIREMENTS ###
Research if a Bank of Canada meeting or a Statistics Canada CPI release occurred on {current_date_str}.
If found, provide a JSON block at the end of your response:
```json
{{
  "event_found": true,
  "type": "boc" or "cpi",
  "outcome": "e.g., +25bps, -50bps, Hold, or 2.8% (for CPI)",
  "details": "A very brief 1-sentence explanation of the result."
}}
```
If no event occurred, return:
```json
{{ "event_found": false }}
```

Output the summary first, followed by the JSON block.
"""

    try:
        client = genai.Client(api_key=API_KEY)
        
        print(f"📡 Generating dynamic AI summary and extracting events using Gemini 3 Flash (Preview)...")
        
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        full_text = response.text.strip()
        
        # Parse JSON extraction
        summary_text = full_text
        extraction = None
        if "```json" in full_text:
            parts = full_text.split("```json")
            summary_text = parts[0].strip()
            json_str = parts[1].split("```")[0].strip()
            try:
                extraction = json.loads(json_str)
            except:
                print("⚠️ Warning: Could not parse AI event extraction JSON.")

        # Update market_events.json if event found
        if extraction and extraction.get('event_found'):
            update_market_events(extraction, now_mt.strftime('%Y-%m-%d'))

        # 3. Update History and Save
        new_entry = {
            "date": now_mt.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary_text
        }
        
        # Append to history and keep last 10
        history.append(new_entry)
        # Sort by date to be sure, then keep last 10
        history = sorted(history, key=lambda x: x['date'], reverse=True)[:10]

        output = {
            "summary": summary_text,
            "last_updated": new_entry["date"],
            "history": history
        }
        
        with open(SUMMARY_FILE, "w", encoding='utf-8') as f:
            json.dump(output, f, indent=4)
        
        print(f"✅ Summary generated and saved to {SUMMARY_FILE} at {output['last_updated']} MT")
        print(f"📊 History now contains {len(history)} entries.")
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")

def update_market_events(extraction, date):
    """
    Merges AI-extracted event data into docs/market_events.json.
    """
    events_file = "docs/market_events.json"
    if not os.path.exists(events_file):
        return

    try:
        with open(events_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        events = data.get('events', [])
        changed = False
        
        for event in events:
            if event['date'] == date and event['type'] == extraction['type']:
                if event.get('outcome') != extraction['outcome']:
                    event['outcome'] = extraction['outcome']
                    event['details'] = extraction['details']
                    changed = True
                    print(f"📊 AI Updated event outcome for {date}: {extraction['outcome']}")
        
        if changed:
            with open(events_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Warning: Could not merge AI event data: {e}")


if __name__ == "__main__":
    generate_summary()
