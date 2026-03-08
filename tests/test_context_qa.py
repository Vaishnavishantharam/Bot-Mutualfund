"""
Context-based Q&A tests: model retrieves from corpus and answers correctly.
Case-insensitive: questions work with any capitalization (HDFC, NIFTY, etc.).
Tests align with expected formats: context-based answering, citations, refusals, edge cases.
"""
from pathlib import Path

import pytest

# Project root
ROOT = Path(__file__).resolve().parent.parent


def _answer(query: str) -> dict:
    from phase_4.backend.fallback import answer_from_corpus
    return answer_from_corpus(query, ROOT)


# ----- Q1–Q7: Context-based (retrieve from corpus) -----

@pytest.mark.parametrize("question", [
    "What is the expense ratio of HDFC Large Cap Fund Direct Plan Growth?",
    "what is the expense ratio of hdfc large cap fund direct plan growth?",
    "EXPENSE RATIO of HDFC LARGE CAP?",
])
def test_q1_expense_ratio_large_cap(question):
    out = _answer(question)
    assert "0.98%" in out["answer"]
    assert "expense ratio" in out["answer"].lower()
    assert "2989" in out["citation_url"] or "large" in out["citation_url"].lower()


def test_q2_exit_load_flexi_cap():
    out = _answer("What is the exit load for HDFC Flexi Cap Fund Direct Plan Growth?")
    assert "1" in out["answer"] and ("%" in out["answer"] or "exit load" in out["answer"].lower())
    assert "3184" in out["citation_url"] or "flexi" in out["citation_url"].lower()


def test_q3_min_sip_mid_cap():
    out = _answer("What is the minimum SIP amount for HDFC Mid Cap Fund Direct Plan Growth?")
    assert "₹100" in out["answer"] or "100" in out["answer"]
    assert "sip" in out["answer"].lower()
    assert "3097" in out["citation_url"] or "mid" in out["citation_url"].lower()


def test_q4_risk_small_cap():
    out = _answer("What is the risk level of HDFC Small Cap Fund Direct Growth?")
    assert "very high" in out["answer"].lower() or "risk" in out["answer"].lower()
    assert "3580" in out["citation_url"] or "small" in out["citation_url"].lower()


@pytest.mark.parametrize("question", [
    "What benchmark does HDFC NIFTY 100 Index Fund Direct Growth follow?",
    "what benchmark does hdfc nifty 100 index fund direct growth follow?",
])
def test_q5_benchmark_nifty_100(question):
    out = _answer(question)
    assert "nifty" in out["answer"].lower() and "100" in out["answer"]
    assert "benchmark" in out["answer"].lower() or "track" in out["answer"].lower()
    assert "1040567" in out["citation_url"] or "nifty" in out["citation_url"].lower()


def test_q6_lock_in_large_cap():
    out = _answer("Is there any lock-in period for HDFC Large Cap Fund Direct Plan Growth?")
    assert "lock" in out["answer"].lower()
    assert "no" in out["answer"].lower() or "not" in out["answer"].lower()
    assert "2989" in out["citation_url"] or "large" in out["citation_url"].lower()


def test_q7_lump_sum_flexi_cap():
    out = _answer("What is the minimum lump sum investment for HDFC Flexi Cap Fund Direct Plan Growth?")
    assert "₹100" in out["answer"] or "100" in out["answer"]
    assert "lump" in out["answer"].lower() or "investment" in out["answer"].lower()
    assert "3184" in out["citation_url"] or "flexi" in out["citation_url"].lower()


# ----- Q8–Q9: Refusal (no investment advice / no comparison) -----

def test_q8_refusal_should_i_invest():
    out = _answer("Should I invest in HDFC Mid Cap Fund?")
    assert "cannot" in out["answer"].lower() or "can only" in out["answer"].lower()
    assert "advice" in out["answer"].lower() or "factual" in out["answer"].lower()
    assert "invest" in out["answer"].lower() or "advice" in out["answer"].lower()


def test_q9_refusal_which_fund_better():
    out = _answer("Which fund is better: HDFC Large Cap or HDFC Flexi Cap?")
    assert "cannot" in out["answer"].lower() or "can only" in out["answer"].lower()
    assert "compare" in out["answer"].lower() or "recommend" in out["answer"].lower() or "factual" in out["answer"].lower()


# ----- Q10: Edge case – scheme not in corpus -----

def test_q10_scheme_not_available():
    out = _answer("What is the expense ratio of SBI Bluechip Fund?")
    assert "not available" in out["answer"].lower() or "not in" in out["answer"].lower()
    assert "scheme" in out["answer"].lower() or "dataset" in out["answer"].lower() or "sources" in out["answer"].lower()


# ----- Case insensitivity -----

@pytest.mark.parametrize("question", [
    "WHAT IS THE EXPENSE RATIO OF HDFC LARGE CAP?",
    "What is the expense ratio of HDFC Large Cap Fund Direct Plan Growth?",
])
def test_case_insensitive_expense_ratio(question):
    out = _answer(question)
    assert "0.98%" in out["answer"]


# ----- Freshness: app pulls last_updated from same corpus -----

def test_app_uses_fresh_data_timestamp():
    """Answer includes last_updated from schemes.json meta.last_scraped (same source as corpus)."""
    import json
    path = ROOT / "data" / "schemes.json"
    if not path.exists():
        path = ROOT / "api" / "schemes.json"
    assert path.exists(), "schemes.json must exist"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    expected_ts = (data.get("meta") or {}).get("last_scraped", "")
    assert expected_ts, "meta.last_scraped must be set"
    out = _answer("What is the expense ratio of HDFC Large Cap?")
    assert out.get("last_updated") == expected_ts, (
        "App must return same last_updated as in corpus (meta.last_scraped)"
    )
    assert expected_ts in out.get("answer", "") or out.get("last_updated") == expected_ts
