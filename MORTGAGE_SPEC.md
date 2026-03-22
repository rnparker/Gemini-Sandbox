# API Specification: Ratehub Mortgage Rates

## 1. Endpoint Configuration
**URL:** `https://api.ratehub.ca/mortgage-rates/all/purchase-rates?amortization=25&downPaymentPercent=0.05&homePrice=400000&isCashBack=0&isOpen=0&isOwnerOccupied=1&isPreApproval=0&language=en&province=BC&term=60&type=fixed`
**Method:** GET
**Format:** JSON

---

## 2. Data Schema & Extraction Mapping
The AI Agent should extract the following specific fields from the response:

| Metric | JSON Path | Type | Description |
| :--- | :--- | :--- | :--- |
| **Prime Rate** | `data.primeRate` | Float | The current Canadian Prime Rate. |
| **Qualifying Rate** | `data.qualifyingRate` | Float | The stress test benchmark rate. |
| **Rate List** | `data.rates` | Array | A collection of specific lender products. |

### Logic for "Best 5-Year Fixed" Rate:
To find the representative market rate for the dashboard:
1. Iterate through the `data.rates` array.
2. Filter for objects where `description == "5-yr Fixed"`.
3. Filter for `insuranceBucket == "insured"` (to match the 5% down payment scenario).
4. **Target Value:** Select the minimum `value` from this filtered set.

---

## 3. Sample Response Data (Reference)
```json
{
    "data": {
        "primeRate": 4.45,
        "qualifyingRate": 5.25,
        "rates": [
            {
                "value": 3.94,
                "description": "5-yr Fixed",
                "provider": "big-6-bank",
                "insuranceBucket": "insured"
            }
        ]
    }
}