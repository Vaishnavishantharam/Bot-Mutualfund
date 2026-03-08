# Corpus: Fields vs HDFC Plans

Clear division of **fields** (rows) vs **HDFC schemes** (columns).  
Source: `data/schemes.json` (INDMoney, Direct Plan – Growth only).

---

## Plans (5 schemes)

| Short name     | Full scheme name |
|----------------|------------------|
| **Large Cap**  | HDFC Large Cap Fund - Direct Plan - Growth Option |
| **Flexi Cap**  | HDFC Flexi Cap Fund - Direct Plan - Growth Option |
| **Mid Cap**    | HDFC Mid Cap Fund - Direct Plan - Growth Option |
| **Small Cap**  | HDFC Small Cap Fund - Direct Plan - Growth Option |
| **Nifty 100 Index** | HDFC Nifty 100 Index Fund - Direct Plan - Growth Option |

---

## Field × Plan matrix

| Field | Large Cap | Flexi Cap | Mid Cap | Small Cap | Nifty 100 Index |
|-------|-----------|-----------|---------|-----------|-----------------|
| **category** | Large Cap | Flexi Cap | Mid Cap | Small Cap | Index |
| **plan_type** | Direct | Direct | Direct | Direct | Direct |
| **option_type** | Growth | Growth | Growth | Growth | Growth |
| **expense_ratio** | 0.98% | 0.67% | 0.74% | 0.67% | 0.3% |
| **exit_load** | 1.0% | 1.0% | 1.0% | 1.0% | 0% |
| **min_sip_raw** | ₹100 | ₹100 | ₹100 | ₹100 | ₹100 |
| **min_lumpsum_raw** | ₹100 | ₹100 | ₹100 | ₹100 | ₹100 |
| **lock_in** | No Lock-in | No Lock-in | No Lock-in | No Lock-in | No Lock-in |
| **risk_level** | Very High Risk | Very High Risk | Very High Risk | Very High Risk | Very High Risk |
| **benchmark** | Nifty 100 TR INR | Nifty 500 TR INR | Nifty Midcap 150 TR INR | BSE 250 SmallCap TR INR | Nifty 100 TR INR |
| **aum** | ₹39621 Cr | ₹97452 Cr | ₹92187 Cr | ₹36941 Cr | ₹397 Cr |
| **inception_date** | 1 January, 2013 | 1 January, 2013 | 1 January, 2013 | 1 January, 2013 | 23 February, 2022 |
| **fund_manager** | Rahul Baijal, Dhruv Muchhal | Amit Ganatra, Dhruv Muchhal | Dhruv Muchhal, Chirag Setalvad | Chirag Setalvad, Dhruv Muchhal | Arun Agarwal, Nandita Menezes |

---

## Metadata (same for all)

| Field | Value |
|-------|--------|
| **amc_name** | HDFC |
| **source** | INDMoney (see `meta.source_urls` in schemes.json) |
| **last_scraped** | 2026-03-08T06:41:47Z |

---

## Summary

- **Rows** = fields the bot can answer from (expense ratio, exit load, minimum SIP, benchmark, AUM, risk, fund manager, etc.).
- **Columns** = the 5 HDFC plans in the corpus; each plan has every field above.
- **Not in corpus:** returns, NAV, portfolio turnover, ratings, comparisons.
