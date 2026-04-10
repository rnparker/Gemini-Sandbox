# Specification: Market Event Annotations

## 1. Objective
Provide visual context on the dashboard charts by highlighting significant Canadian market events, such as Bank of Canada (BoC) interest rate announcements and Consumer Price Index (CPI) release dates.

## 2. Data Structure (`docs/market_events.json`)
The events are stored in a JSON file with the following schema:

```json
{
  "events": [
    {
      "date": "YYYY-MM-DD",
      "label": "Short Label (e.g., BoC, CPI)",
      "type": "boc | cpi",
      "outcome": "e.g., +25bps, Hold, or 2.8%",
      "details": "Brief explanation of the result."
    }
  ]
}
```

## 3. Automation Strategy (Hybrid)
To minimize manual maintenance, event outcomes are populated automatically:

### 3.1. BoC Rate Outcomes (Programmatic)
The `pulse_check.py` script fetches the BoC Target Rate (Series `V39079`). On scheduled BoC meeting dates, it records the new target rate as the `outcome` in the JSON file.

### 3.2. CPI & Contextual Outcomes (AI-Driven)
The `generate_summary.py` script utilizes Gemini with Google Search grounding. During daily runs, the AI is tasked with:
1. Detecting if a CPI release occurred.
2. Extracting the headline inflation percentage.
3. Providing a one-sentence summary of the event context.
This data is merged into the JSON structure.

## 4. Visualization Logic
The dashboard uses the `chartjs-plugin-annotation` library to render these events.

### Features:
- **Toggle:** Users can show/hide annotations via the "Events" toggle button.
- **Rich Labels:** Annotations display the outcome directly on the chart (e.g., "CPI (2.8%)").
- **Theme Awareness:** Colors and labels adjust dynamically between Dark and Light modes.

