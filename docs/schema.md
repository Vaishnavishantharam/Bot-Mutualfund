# JSON schema for `data/schemes.json`

## Top-level structure

```json
{
  "meta": {
    "last_scraped": "2026-03-02T12:00:00Z",
    "source_urls": ["https://www.indmoney.com/...", ...]
  },
  "schemes": [ ... ],
  "evidence": [ ... ]
}
```

## Scheme object

Each item in `schemes`:

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `scheme_name` | string | yes | Full scheme title |
| `amc_name` | string | yes | e.g. "HDFC" |
| `category` | string \| null | no | Large Cap / Flexi Cap / Mid Cap / Small Cap / Index |
| `plan_type` | string | yes | "Direct" |
| `option_type` | string | yes | "Growth" |
| `expense_ratio` | string \| null | no | e.g. "0.98%" |
| `exit_load` | string \| null | no | Full text |
| `min_sip` | number \| null | no | Numeric value (e.g. 100) |
| `min_sip_raw` | string \| null | no | Raw text e.g. "₹100" |
| `min_lumpsum` | number \| null | no | Numeric value |
| `min_lumpsum_raw` | string \| null | no | Raw text e.g. "₹100" |
| `lock_in` | string \| null | no | e.g. "No Lock-in" |
| `risk_level` | string \| null | no | e.g. "Very High Risk" |
| `benchmark` | string \| null | no | e.g. "Nifty 100 TR INR" |
| `aum` | string \| null | no | e.g. "₹39621 Cr" |
| `inception_date` | string \| null | no | e.g. "1 January, 2013" |
| `fund_manager` | string \| null | no | e.g. "Rahul Baijal, Dhruv Muchhal" |
| `source_url` | string | yes | One of the 5 approved URLs |
| `scraped_at` | string | yes | ISO 8601 timestamp |

## Evidence object

Each item in `evidence` (for citations):

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `field_name` | string | yes | e.g. "expense_ratio" |
| `field_value` | string \| number | yes | Extracted value |
| `evidence_text` | string | yes | 1–2 lines from the page |
| `source_url` | string | yes | Same as scheme's source_url |
| `scheme_id` | string | no | Optional: index or scheme_name for linking |

## Example (minimal)

```json
{
  "meta": {
    "last_scraped": "2026-03-02T12:00:00Z",
    "source_urls": ["https://www.indmoney.com/mutual-funds/hdfc-large-cap-fund-direct-plan-growth-option-2989"]
  },
  "schemes": [
    {
      "scheme_name": "HDFC Large Cap Fund - Direct Plan - Growth Option",
      "amc_name": "HDFC",
      "category": "Large Cap",
      "plan_type": "Direct",
      "option_type": "Growth",
      "expense_ratio": "0.98%",
      "exit_load": "1.0%",
      "min_sip": 100,
      "min_sip_raw": "₹100",
      "min_lumpsum": 100,
      "min_lumpsum_raw": "₹100",
      "lock_in": "No Lock-in",
      "risk_level": "Very High Risk",
      "benchmark": "Nifty 100 TR INR",
      "aum": "₹39621 Cr",
      "inception_date": "1 January, 2013",
      "fund_manager": "Rahul Baijal, Dhruv Muchhal",
      "source_url": "https://www.indmoney.com/mutual-funds/hdfc-large-cap-fund-direct-plan-growth-option-2989",
      "scraped_at": "2026-03-02T12:00:00Z"
    }
  ],
  "evidence": [
    {
      "field_name": "expense_ratio",
      "field_value": "0.98%",
      "evidence_text": "Expense ratio | 0.98%",
      "source_url": "https://www.indmoney.com/mutual-funds/hdfc-large-cap-fund-direct-plan-growth-option-2989"
    }
  ]
}
```
