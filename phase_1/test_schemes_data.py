"""
Simple test: verify data/schemes.json is stored correctly (structure + required fields).
Run from project root: python phase_1/test_schemes_data.py
"""

import json
import sys
from pathlib import Path

# Project root = parent of phase_1
ROOT = Path(__file__).resolve().parent.parent
SCHEMES_PATH = ROOT / "data" / "schemes.json"

APPROVED_URLS = {
    "https://www.indmoney.com/mutual-funds/hdfc-large-cap-fund-direct-plan-growth-option-2989",
    "https://www.indmoney.com/mutual-funds/hdfc-flexi-cap-fund-direct-plan-growth-option-3184",
    "https://www.indmoney.com/mutual-funds/hdfc-mid-cap-fund-direct-plan-growth-option-3097",
    "https://www.indmoney.com/mutual-funds/hdfc-small-cap-fund-direct-growth-option-3580",
    "https://www.indmoney.com/mutual-funds/hdfc-nifty-100-index-fund-direct-growth-1040567",
}

REQUIRED_SCHEME_KEYS = {"scheme_name", "amc_name", "plan_type", "option_type", "source_url", "scraped_at"}
REQUIRED_EVIDENCE_KEYS = {"field_name", "field_value", "evidence_text", "source_url"}


def main():
    if not SCHEMES_PATH.exists():
        print("FAIL: data/schemes.json not found")
        return 1

    with open(SCHEMES_PATH, encoding="utf-8") as f:
        data = json.load(f)

    errors = []

    # Top-level structure
    if set(data.keys()) != {"meta", "schemes", "evidence"}:
        errors.append("Top-level keys must be meta, schemes, evidence")

    meta = data.get("meta", {})
    if "last_scraped" not in meta:
        errors.append("meta.last_scraped missing")
    if "source_urls" not in meta or len(meta["source_urls"]) != 5:
        errors.append("meta.source_urls must have 5 URLs")

    schemes = data.get("schemes", [])
    if len(schemes) != 5:
        errors.append(f"Expected 5 schemes, got {len(schemes)}")

    for i, s in enumerate(schemes):
        missing = REQUIRED_SCHEME_KEYS - set(s.keys())
        if missing:
            errors.append(f"Scheme {i} ({s.get('scheme_name', '?')}) missing keys: {missing}")
        if s.get("source_url") not in APPROVED_URLS:
            errors.append(f"Scheme {i} source_url not in approved list")

    evidence = data.get("evidence", [])
    if len(evidence) != 45:
        errors.append(f"Expected 45 evidence items (9 per scheme), got {len(evidence)}")

    for i, e in enumerate(evidence):
        missing = REQUIRED_EVIDENCE_KEYS - set(e.keys())
        if missing:
            errors.append(f"Evidence {i} missing keys: {missing}")
        if e.get("source_url") not in APPROVED_URLS:
            errors.append(f"Evidence {i} source_url not in approved list")

    # Spot-check: one scheme has expected values
    large_cap = next((s for s in schemes if "Large Cap" in s.get("scheme_name", "")), None)
    if large_cap:
        if large_cap.get("expense_ratio") != "0.98%":
            errors.append(f"Large Cap expense_ratio expected 0.98%, got {large_cap.get('expense_ratio')}")
        if large_cap.get("benchmark") != "Nifty 100 TR INR":
            errors.append(f"Large Cap benchmark expected Nifty 100 TR INR, got {large_cap.get('benchmark')}")
        if large_cap.get("min_sip") != 100:
            errors.append(f"Large Cap min_sip expected 100, got {large_cap.get('min_sip')}")

    if errors:
        print("FAIL: data/schemes.json validation failed")
        for e in errors:
            print("  -", e)
        return 1

    print("PASS: data/schemes.json is valid")
    print(f"  - meta.last_scraped: {meta.get('last_scraped')}")
    print(f"  - schemes: {len(schemes)}")
    print(f"  - evidence: {len(evidence)}")
    for s in schemes:
        print(f"  - {s['scheme_name'][:50]}... | expense_ratio={s.get('expense_ratio')} | benchmark={s.get('benchmark')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
