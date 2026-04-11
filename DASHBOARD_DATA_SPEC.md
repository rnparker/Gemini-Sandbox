# Specification: Dashboard Data Pipeline

## 1. Objective
Orchestrate the collection of Bank of Canada (BoC) bond yields and Ratehub mortgage rates into a unified historical dataset for the Market Pulse Dashboard.

## 2. Data Sources
### 2.1. Bank of Canada (Valet API)
- **URL:** `https://www.bankofcanada.ca/valet/observations/BD.CDN.2YR.DQ.YLD%2CBD.CDN.5YR.DQ.YLD%2CAVG.INTWO/json`
- **Series IDs:**
  - `BD.CDN.2YR.DQ.YLD`: 2-Year Benchmark Bond Yield
  - `BD.CDN.5YR.DQ.YLD`: 5-Year Benchmark Bond Yield
  - `AVG.INTWO`: CORRA (Canadian Overnight Repo Rate Average)
- **Parameters:** `recent=10` (to capture the latest observations).

### 2.2. Ratehub API
- **URL:** `https://api.ratehub.ca/mortgage-rates/all/purchase-rates?amortization=25&downPaymentPercent=0.05&homePrice=400000&isCashBack=0&isOpen=0&isOwnerOccupied=1&isPreApproval=0&language=en&province=BC&term=60&type=fixed`
- **Selection Logic:**
  - Filter by `description == "5-yr Fixed"`.
  - Filter by `insuranceBucket == "insured"`.
  - **Result:** Minimum `value` from the filtered set.

### 2.3. Market Events (`docs/market_events.json`)
- **Type:** Static JSON file.
- **Content:** Scheduled BoC meeting dates and CPI release dates.
- **Purpose:** Provide visual annotations on dashboard charts.
- **Reference:** `MARKET_EVENTS_SPEC.md`.

## 3. Calculated Metrics
- **Yield Spread:** `CAN 5Y Yield - CAN 2Y Yield`.
- **Reference Repo Rate:** `CORRA + 0.50` (50 bps margin).
- **Lending Margin:** `Best 5Y Fixed Mortgage Rate - CAN 5Y Yield`.

## 4. Storage Schema (`docs/historical_spread.csv`)
The data is stored in a CSV file with the following columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| `date` | String | Observation date (YYYY-MM-DD). |
| `yield_2y` | Float | 2-Year Benchmark Bond Yield (%). |
| `yield_5y` | Float | 5-Year Benchmark Bond Yield (%). |
| `repo_rate` | Float | Calculated Reference Repo Rate (%). |
| `spread` | Float | Calculated Yield Spread (%). |
| `mortgage_5y` | Float | Best 5-Year Fixed Insured Mortgage Rate (%). |
| `lending_margin` | Float | Calculated Lending Margin (%). |

## 5. Validation Logic (Sanity Checks)
To ensure data integrity, the following bounds are applied:
- **Bond Yields:** Flag if `abs(yield) > 15.0`.
- **Mortgage Rates:** Flag if `rate < 1.0` or `rate > 15.0`.
- **Data Completeness:** Observations are only added if both 2Y and 5Y yields are present.

## 6. Execution Strategy & Rate Limiting
1. **BoC First:** Fetch latest yields to determine the current observation date.
2. **Cache Check:** If the latest date already exists in `docs/historical_spread.csv` AND contains a `mortgage_5y` value, the Ratehub API call is skipped to avoid unnecessary hits.
3. **Merge & Sort:** New data is merged with existing records and sorted by date (ascending) before writing back to CSV.
