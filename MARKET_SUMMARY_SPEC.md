# Specification: AI-Generated Market Summary

## 1. Objective
Generate professional, insightful, and concise market commentary for the dashboard using the Gemini API. The summary must provide context for the current bond yield trends and their impact on small Canadian financial institutions (FIs).

## 2. Model Configuration
- **Model:** `gemini-3-flash-preview` (via `google-genai` library).
- **Tools:** Google Search grounding enabled for real-time market event data.
- **Cache Policy:** Summaries are cached for 2 hours (based on `last_updated` in `summary.json`).

## 3. Data Context
The generation logic utilizes the following context:
- **Historical Data:** The last 30 entries from `docs/historical_spread.csv`.
- **Narrative Continuity:** The last 10 summaries from the history stored in `docs/summary.json`.

## 4. Persona & Tone Guidelines
- **Persona:** Senior Market Analyst.
- **Tone:** Professional, direct, and insightful.
- **Strict Constraint:** No first-person pronouns (no "we", "our", "us", "I").
- **Generic Commentary:** Avoid referring to specific institutions or ownership of rates (e.g., use "the market's best rate" instead of "our rate").

## 5. Summary Content Requirements
The generated commentary must cover:
1. **Market Happenings:** Latest major events in Canadian and US bond markets (e.g., central bank policy, economic indicators, geopolitical events). Commentary should correlate with the visual annotations (BoC/CPI) provided on the dashboard charts.
2. **Yield Trend Analysis:** Correlate current 2Y and 5Y yields and the resulting spread with market events.
3. **Repo Rate Analysis:** Analysis of the Reference Repo Rate (CORRA + 50 bps) and its relationship to bond yields and liquidity.
4. **Mortgage & Margin Impact:** Analysis of how the 'Best 5Y Fixed' mortgage rate and 'Lending Margin' are responding to bond moves.
5. **FI Operational Impact:** Generic explanation of impacts on mortgage rate setting, deposit rate setting, institutional borrowing costs (using Repo Rate as proxy), and institutional profitability.
6. **US-Canada Link:** Highlight the correlation between the US and Canadian bond markets.
7. **Narrative Arc:** Use history to treat recurring events as "continuing the story" rather than new information.

## 6. Storage Schema (`docs/summary.json`)
The summary and its history are stored in a JSON file with the following structure:

| Field | Type | Description |
| :--- | :--- | :--- |
| `summary` | String | The latest AI-generated text summary. |
| `last_updated` | String | Timestamp of generation (YYYY-MM-DD HH:MM:SS) in Mountain Time. |
| `history` | Array | A collection of the last 10 summary objects (`date`, `summary`). |

## 7. Execution Logic
1. **Cache Check:** Verify if `summary.json` exists and if the `last_updated` timestamp is < 2 hours old.
2. **Data Load:** Read the last 30 rows from the CSV and the history from the JSON.
3. **Prompt Construction:** Format the prompt with history and data summary.
4. **Gemini Call:** Invoke the Gemini API with Google Search grounding.
5. **Update History:** Append the new summary to history, keeping the last 10 entries.
6. **Persistence:** Save the updated structure to `docs/summary.json`.
