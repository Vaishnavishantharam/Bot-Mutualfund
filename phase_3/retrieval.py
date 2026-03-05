"""
Phase 3: Query vector store (Phase 2) and return top-k chunks with metadata.
Each chunk includes source_url so the generator can return the correct citation URL.
"""
from __future__ import annotations

from typing import Any, List

# Phase 2 query_store returns chunks from approved URLs only (our corpus)
def retrieve(query: str, top_k: int = 5) -> List[dict[str, Any]]:
    """
    Embed query and return top-k chunks with evidence_text, source_url, scheme_name, field_name, scraped_at.
    Uses phase_2.indexer.query_store (FAISS + sentence-transformers).
    """
    from phase_2.indexer import query_store
    from . import config as cfg
    return query_store(query, top_k=top_k or cfg.TOP_K)
