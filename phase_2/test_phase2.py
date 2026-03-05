"""
Phase 2 tests: chunk building (no API), and optional index + query (needs OPENAI_API_KEY).
Run from project root: python -m phase_2.test_phase2
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Project root on path + load .env so OPENAI_API_KEY is available
_root = Path(__file__).resolve().parent.parent
for _p in (_root / ".env", Path(__file__).resolve().parent / ".env"):
    if _p.is_file():
        try:
            from dotenv import load_dotenv
            load_dotenv(_p)
        except ImportError:
            pass
        break
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from phase_2.indexer import (
    load_schemes_json,
    build_chunks,
    rebuild_index,
    query_store,
)
from phase_2 import config as cfg


def test_load_and_chunks() -> None:
    """Test loading schemes.json and building chunks (no API key)."""
    data = load_schemes_json()
    schemes = data.get("schemes", [])
    evidence = data.get("evidence", [])
    assert len(schemes) >= 1, "Expected at least one scheme"
    assert len(evidence) >= 1, "Expected at least one evidence item"
    documents, metadatas, ids = build_chunks(data)
    assert len(documents) == len(ids) == len(metadatas)
    assert len(documents) >= 1
    for m in metadatas:
        assert "source_url" in m and "scheme_name" in m
    print(f"  OK load + chunks: {len(schemes)} schemes, {len(documents)} chunks")


def test_index_and_query() -> None:
    """Rebuild index and run one query (requires OPENAI_API_KEY)."""
    if not os.environ.get("OPENAI_API_KEY"):
        print("  SKIP index + query: OPENAI_API_KEY not set")
        return
    n = rebuild_index()
    assert n >= 1, "Expected at least one chunk indexed"
    print(f"  OK indexed {n} chunks ({cfg.VECTOR_STORE_TYPE})")
    chunks = query_store("What is the expense ratio of HDFC Large Cap Fund?", top_k=3)
    assert len(chunks) >= 1
    c = chunks[0]
    assert "evidence_text" in c and "source_url" in c
    print(f"  OK query_store: got {len(chunks)} chunks, top source_url: {c['source_url'][:50]}...")
    print(f"     sample: {c['evidence_text'][:80]}...")


if __name__ == "__main__":
    print("Phase 2 tests")
    print("- load_schemes_json + build_chunks")
    test_load_and_chunks()
    print("- rebuild_index + query_store (needs OPENAI_API_KEY)")
    test_index_and_query()
    print("Done.")
