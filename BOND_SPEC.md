# API Specification: Bank of Canada Bond Yields (Valet API)

## 1. Endpoint Configuration
**URL:** `https://www.bankofcanada.ca/valet/observations/BD.CDN.2YR.DQ.YLD%2CBD.CDN.5YR.DQ.YLD%2CAVG.INTWO/json`
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
| **CORRA** | `observations[].AVG.INTWO.v` | Float | Canadian Overnight Repo Rate Average (Series ID: `AVG.INTWO`). |

### Logic for "Yield Spread":
To calculate the yield spread for the dashboard:
1. **Calculation:** `Spread = CAN 5Y Yield - CAN 2Y Yield`.
2. **Inversion Tracking:** Any value where `Spread < 0` is considered an inversion.
3. **Visual Requirement:** Inverted data points must be visually distinct (e.g., Red) in dashboard visualizations.

### Logic for "Reference Repo Rate":
To calculate the reference repo rate:
1. **Calculation:** `Repo Rate = CORRA + 0.50` (50 bps margin).
2. **Context:** Represents the estimated margin over CORRA an FI would pay to purchase a repo.

---

## 3. Validation Logic (Sanity Checks)
To ensure data integrity, the following bounds are applied:
- **Bond Yields & CORRA:** Flag if `abs(yield) > 15.0`.
- **Data Completeness:** Observations are only added if both 2Y and 5Y yields are present. CORRA is optional but highly recommended.

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
            },
            "AVG.INTWO": {
                "v": "4.50"
            }
        },
        {
            "d": "2024-03-21",
            "BD.CDN.2YR.DQ.YLD": {
                "v": "4.12"
            },
            "BD.CDN.5YR.DQ.YLD": {
                "v": "3.58"
            },
            "AVG.INTWO": {
                "v": "4.50"
            }
        }
    ]
}
```
