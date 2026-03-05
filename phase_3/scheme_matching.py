"""
Phase 3: Detect which scheme the user is asking about so we retrieve and cite the correct fund.
Maps query keywords to the preferred source_url (one of the 5 approved INDMoney scheme pages).
"""
from __future__ import annotations

import re
from typing import Optional

from . import config as cfg

# Query phrases -> index into APPROVED_URLS (or explicit URL).
# Order matters: more specific (e.g. Nifty 100 Index) before generic (e.g. Index).
SCHEME_KEYWORDS = [
    # (pattern, url or index)
    (r"\bnifty\s*100\b|\b100\s*index\b|nifty\s*100\s*index", cfg.APPROVED_URLS[4]),   # Nifty 100 Index Fund
    (r"\blarge\s*cap\b", cfg.APPROVED_URLS[0]),
    (r"\bflexi\s*cap\b|flexicap", cfg.APPROVED_URLS[1]),
    (r"\bmid\s*cap\b|midcap", cfg.APPROVED_URLS[2]),
    (r"\bsmall\s*cap\b|smallcap", cfg.APPROVED_URLS[3]),
    (r"\bindex\s*fund\b", cfg.APPROVED_URLS[4]),  # generic "index fund" -> Nifty 100 in our set
]


def get_preferred_source_url(query: str) -> Optional[str]:
    """
    If the query clearly mentions one of the 5 schemes, return that scheme's source_url.
    Otherwise return None (use default retrieval order).
    """
    q = (query or "").strip().lower()
    if not q:
        return None
    for pattern, url in SCHEME_KEYWORDS:
        if re.search(pattern, q, re.IGNORECASE):
            return url
    return None


def filter_chunks_by_scheme(
    chunks: list,
    preferred_source_url: Optional[str],
) -> list:
    """
    When user asked for a specific scheme: return only chunks from that scheme
    so the answer and citation are always for the right fund.
    """
    if not preferred_source_url or not chunks:
        return chunks
    matching = [c for c in chunks if (c.get("source_url") or "") == preferred_source_url]
    return matching if matching else chunks


def rerank_chunks_by_scheme(
    chunks: list,
    preferred_source_url: Optional[str],
) -> list:
    """
    Put chunks from the preferred scheme first so the citation (first chunk) matches the asked fund.
    """
    if not preferred_source_url or not chunks:
        return chunks
    matching = [c for c in chunks if (c.get("source_url") or "") == preferred_source_url]
    rest = [c for c in chunks if (c.get("source_url") or "") != preferred_source_url]
    return matching + rest
