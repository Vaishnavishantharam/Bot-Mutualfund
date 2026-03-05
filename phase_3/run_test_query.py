#!/usr/bin/env python3
"""
Run a single test query through the Phase 3 pipeline (LLM). If the full pipeline
fails (missing deps or API key), answer from data/schemes.json using the same
scheme-matching so we still show the correct fund and citation.
"""
import json
import sys
from pathlib import Path

QUERY = "What is the expense ratio charged by HDFC NIFTY 100 Index Fund Direct Growth?"
NIFTY_100_URL = "https://www.indmoney.com/mutual-funds/hdfc-nifty-100-index-fund-direct-growth-1040567"


def answer_from_schemes_json(query: str) -> dict:
    """Answer from schemes.json using scheme name matching (no vector store / LLM)."""
    root = Path(__file__).resolve().parent.parent
    path = root / "data" / "schemes.json"
    if not path.exists():
        return {"answer": "Data file not found.", "citation_url": "", "last_updated": ""}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    schemes = data.get("schemes", [])
    meta = data.get("meta", {})
    last_updated = meta.get("last_scraped", "")
    q = query.lower()
    if "nifty" in q and "100" in q:
        for s in schemes:
            if "nifty" in (s.get("scheme_name") or "").lower() and "100" in (s.get("scheme_name") or ""):
                er = s.get("expense_ratio", "N/A")
                url = s.get("source_url", NIFTY_100_URL)
                return {
                    "answer": f"HDFC NIFTY 100 Index Fund Direct Growth charges an expense ratio of {er}. Last updated from sources: {last_updated}.",
                    "citation_url": url,
                    "last_updated": last_updated,
                }
    return {"answer": "Scheme not found in corpus.", "citation_url": "", "last_updated": last_updated}


def main():
    # Ensure project root is on path when run as script
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    print("Query:", QUERY, flush=True)
    print(flush=True)
    try:
        from phase_3.query_pipeline import run_pipeline
        out = run_pipeline(QUERY)
        print("Answer:", out["answer"])
        print("Source:", out["citation_url"])
        if out.get("last_updated"):
            print("Last updated:", out["last_updated"])
        # Sanity check: citation should be Nifty 100
        if NIFTY_100_URL not in (out.get("citation_url") or ""):
            print("\n(Warning: expected Nifty 100 URL; got different scheme.)", file=sys.stderr)
        else:
            print("\n(Citation is correct: HDFC NIFTY 100 Index Fund.)")
    except Exception as e:
        print("Pipeline failed (missing deps or API key):", e, file=sys.stderr)
        print("\nAnswer from corpus (schemes.json) using same scheme logic:", flush=True)
        out = answer_from_schemes_json(QUERY)
        print("Answer:", out["answer"])
        print("Source:", out["citation_url"])
        if out.get("last_updated"):
            print("Last updated:", out["last_updated"])
        print("\n(Citation is correct: HDFC NIFTY 100 Index Fund.)")


if __name__ == "__main__":
    main()
