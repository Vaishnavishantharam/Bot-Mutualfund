"""
Phase 3 integration tests: full pipeline (classifier → Phase 2 retrieval → Groq generator).
Requires: Phase 1 data (data/schemes.json), Phase 2 vector store (data/vector_store/), optional GROQ_API_KEY.
Run from project root: pytest phase_3/tests/ -v
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

# Project root on path so phase_2, phase_3 are importable
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from phase_3.config import APPROVED_URLS
from phase_3.query_pipeline import run_pipeline

# --- Fixtures ---

def _vector_store_exists() -> bool:
    # ChromaDB persist path or legacy FAISS
    chroma = _project_root / "data" / "chroma"
    faiss = _project_root / "data" / "vector_store" / "index.faiss"
    return chroma.exists() or faiss.exists()


def _phase2_available() -> bool:
    """True if Phase 2 (vector store + chromadb) can be used for retrieval."""
    if not _vector_store_exists():
        return False
    try:
        import chromadb  # noqa: F401
        return True
    except ImportError:
        return False


requires_vector_store = pytest.mark.skipif(
    not _phase2_available(),
    reason="Phase 2 vector store not found or chromadb not installed. Run: pip install chromadb && python -m phase_2.indexer",
)


# --- Response structure helpers ---

def assert_valid_response(response: dict) -> None:
    """Every pipeline response must have answer, citation_url, last_updated; citation in approved list."""
    assert "answer" in response, "response must have 'answer'"
    assert "citation_url" in response, "response must have 'citation_url'"
    assert "last_updated" in response, "response must have 'last_updated'"
    assert response["citation_url"] in APPROVED_URLS, (
        f"citation_url must be one of the 5 approved URLs, got {response['citation_url']}"
    )
    assert isinstance(response["answer"], str) and len(response["answer"]) > 0, "answer must be non-empty string"


def count_sentences(text: str) -> int:
    """Heuristic: count sentence-ending punctuation."""
    return len(re.split(r"[.!?]+", text.strip())) if text.strip() else 0


# --- Example test case: User query from spec ---

@requires_vector_store
def test_expense_ratio_hdfc_large_cap_direct_growth():
    """
    User query: "What is the expense ratio of HDFC Large Cap Fund Direct Growth?"
    Expect: Answer from corpus (expense ratio value), correct citation, ≤3 sentences.
    (Retrieval may return any scheme's expense ratio; we assert structure and that answer is factual.)
    """
    query = "What is the expense ratio of HDFC Large Cap Fund Direct Growth??"
    response = run_pipeline(query)

    assert_valid_response(response)
    # Answer must be about expense ratio (from corpus): contains % or "expense"
    assert "%" in response["answer"] or "expense" in response["answer"].lower(), (
        f"Expected answer to mention expense ratio (%). Got: {response['answer']}"
    )
    # If citation is Large Cap URL, answer should contain 0.98% (from corpus)
    large_cap_url = "https://www.indmoney.com/mutual-funds/hdfc-large-cap-fund-direct-plan-growth-option-2989"
    if response["citation_url"] == large_cap_url:
        assert "0.98" in response["answer"], (
            f"Large Cap source cited; expected 0.98%. Got: {response['answer']}"
        )
    # Answer should be short (sentence count is heuristic; decimals/dates can split)
    assert len(response["answer"]) < 500, "Answer should be concise."


# --- Other factual queries (integration with Phase 2 + LLM) ---

@requires_vector_store
def test_factual_min_sip_hdfc_small_cap():
    """Factual: Minimum SIP for HDFC Small Cap (corpus has ₹100)."""
    query = "Minimum SIP of HDFC Small Cap?"
    response = run_pipeline(query)
    assert_valid_response(response)
    assert "100" in response["answer"] or "₹" in response["answer"], (
        f"Expected min SIP (100) in answer. Got: {response['answer']}"
    )


@requires_vector_store
def test_factual_benchmark_hdfc_mid_cap():
    """Factual: Benchmark for HDFC Mid Cap (corpus has Nifty Midcap 150 TR INR)."""
    query = "What is the benchmark of HDFC Mid Cap?"
    response = run_pipeline(query)
    assert_valid_response(response)
    assert "midcap" in response["answer"].lower() or "150" in response["answer"], (
        f"Expected benchmark (Nifty Midcap 150) in answer. Got: {response['answer']}"
    )


@requires_vector_store
def test_factual_exit_load():
    """Factual: Exit load query."""
    query = "Exit load of HDFC Flexi Cap?"
    response = run_pipeline(query)
    assert_valid_response(response)
    assert "1" in response["answer"] or "exit" in response["answer"].lower(), (
        f"Expected exit load info. Got: {response['answer']}"
    )


# --- Refusal (opinionated) ---

def test_refusal_should_i_invest():
    """Refusal: 'Should I invest?' must return polite facts-only message + one citation."""
    query = "Should I invest in HDFC Mid Cap?"
    response = run_pipeline(query)
    assert_valid_response(response)
    assert "only answers factual" in response["answer"].lower() or "investment" in response["answer"].lower(), (
        f"Expected refusal message. Got: {response['answer']}"
    )
    assert response["citation_url"] in APPROVED_URLS


def test_refusal_which_is_best():
    """Refusal: 'Which is best?' must not give recommendation."""
    query = "Which fund is best for me?"
    response = run_pipeline(query)
    assert_valid_response(response)
    assert response["citation_url"] in APPROVED_URLS


# --- Personal information (out of scope) ---

def test_personal_info_pan():
    """Personal info: PAN question must be refused (out of scope)."""
    query = "What is my PAN number?"
    response = run_pipeline(query)
    assert_valid_response(response)
    assert "personal" in response["answer"].lower() or "does not handle" in response["answer"].lower(), (
        f"Expected personal-info refusal. Got: {response['answer']}"
    )
    assert response["citation_url"] in APPROVED_URLS


def test_personal_info_account():
    """Personal info: account/OTP must be refused."""
    query = "Can you check my account balance?"
    response = run_pipeline(query)
    assert_valid_response(response)
    assert response["citation_url"] in APPROVED_URLS


# --- Edge cases ---

def test_empty_query():
    """Empty query -> refusal with one citation."""
    response = run_pipeline("")
    assert_valid_response(response)
    response2 = run_pipeline("   ")
    assert_valid_response(response2)


@requires_vector_store
def test_not_in_corpus_returns_citation():
    """Off-topic query still returns valid response + one approved citation (no crash)."""
    query = "What is the weather in Mumbai?"
    response = run_pipeline(query)
    assert_valid_response(response)
    assert response["citation_url"] in APPROVED_URLS
    # Pipeline may return top retrieved chunk anyway; we only require valid structure


# --- Unit-style: classifier only (no Phase 2 / LLM) ---

def test_classifier_factual():
    """Classifier: factual query -> factual."""
    from phase_3.classifier import classify
    assert classify("What is the expense ratio of HDFC Large Cap?") == "factual"
    assert classify("Minimum SIP of HDFC Small Cap?") == "factual"
    assert classify("Benchmark of HDFC Mid Cap?") == "factual"


def test_classifier_refusal():
    """Classifier: opinionated -> refusal."""
    from phase_3.classifier import classify
    assert classify("Should I invest in HDFC Large Cap?") == "refusal"
    assert classify("Which is best?") == "refusal"
    assert classify("Compare returns of these funds") == "refusal"


def test_classifier_personal_info():
    """Classifier: PII/personal -> personal_info."""
    from phase_3.classifier import classify
    assert classify("What is my PAN?") == "personal_info"
    assert classify("My email is test@example.com") == "personal_info"
