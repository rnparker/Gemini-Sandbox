# API Specification: Bank of Canada Bond Yields (Valet API)

## 1. Endpoint Configuration
**URL:** `https://www.bankofcanada.ca/valet/observations/BD.CDN.2YR.DQ.YLD%2CBD.CDN.5YR.DQ.YLD/json`
**Method:** GET
**Format:** JSON
**Query Parameters:**
- `start_date`: (Optional) Filter observations from this date (YYYY-MM-DD).
- `recent`: (Optional) Returns the N most recent observations.

---

## 2. Data Schema & Extraction Mapping
The AI Agent should extract the following specific fields from the `observations` array:

| Metric | JSON Path | Type | Description |
| :--- | :--- | :--- | :--- |
| **Observation Date** | `observations[].d` | String | The date of the yield observation (YYYY-MM-DD). |
| **CAN 2Y Yield** | `observations[].BD.CDN.2YR.DQ.YLD.v` | Float | 2-Year Benchmark Bond Yield (Series ID: `BD.CDN.2YR.DQ.YLD`). |
| **CAN 5Y Yield** | `observations[].BD.CDN.5YR.DQ.YLD.v` | Float | 5-Year Benchmark Bond Yield (Series ID: `BD.CDN.5YR.DQ.YLD`). |

### Logic for "Yield Spread":
To calculate the yield spread for the dashboard:
1. **Calculation:** `Spread = CAN 5Y Yield - CAN 2Y Yield`.
2. **Inversion Tracking:** Any value where `Spread < 0` is considered an inversion.
3. **Visual Requirement:** Inverted data points must be visually distinct (e.g., Red) in dashboard visualizations.

---

## 3. Validation Logic (Sanity Checks)
To ensure data integrity, the following bounds are applied:
- **Bond Yields:** Flag if `abs(yield) > 15.0`.
- **Data Completeness:** Observations are only added if both 2Y and 5Y yields are present.

---

## 4. Sample Response Data (Reference)
```json
{
    "observations": [
        {
            "d": "2024-03-20",
            "BD.CDN.2YR.DQ.YLD": {
                "v": "4.15"
            },
            "BD.CDN.5YR.DQ.YLD": {
                "v": "3.55"
            }
        },
        {
            "d": "2024-03-21",
            "BD.CDN.2YR.DQ.YLD": {
                "v": "4.12"
            },
            "BD.CDN.5YR.DQ.YLD": {
                "v": "3.58"
            }
        }
    ]
}
```
