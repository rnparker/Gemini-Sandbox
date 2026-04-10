# Specification: Market Event Annotations

## 1. Objective
Provide visual context on the dashboard charts by highlighting significant Canadian market events, such as Bank of Canada (BoC) interest rate announcements and Consumer Price Index (CPI) release dates.

## 2. Data Structure (`docs/market_events.json`)
The events are stored in a static JSON file with the following schema:

```json
{
  "events": [
    {
      "date": "YYYY-MM-DD",
      "label": "Short Label (e.g., BoC, CPI)",
      "type": "boc | cpi"
    }
  ]
}
```

### Event Types:
- **boc:** Bank of Canada Interest Rate Announcement.
- **cpi:** Statistics Canada Consumer Price Index release.

## 3. Visualization Logic
The dashboard uses the `chartjs-plugin-annotation` library to render these events as vertical dashed lines.

### Styling Requirements:
| Element | Dark Mode | Light Mode |
| :--- | :--- | :--- |
| **BoC Line** | Grey (`--text-muted`) | Dark Grey (`--text-muted`) |
| **CPI Line** | OrangeRed (`--accent-mortgage`) | Deep Red (`--accent-mortgage`) |
| **Labels** | Small, Start of line, White text on event color | Small, Start of line, White text on event color |

## 4. Maintenance
As these dates are typically released by the BoC and Statistics Canada at the end of each year for the following year, this file should be updated annually.

- **BoC Source:** [Bank of Canada Press Release Schedule](https://www.bankofcanada.ca/press/scheduled-announcement-dates/)
- **CPI Source:** [Statistics Canada Release Schedule](https://www150.statcan.gc.ca/n1/dai-quo/cal-en.htm)
