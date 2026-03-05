"""
Phase 3: Full query pipeline — PII/personal check → classify → retrieve → generate.
Returns answer, citation_url (correct source URL), last_updated.
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, Dict

from . import config as cfg
from .classifier import classify, is_other_amc
from .generator import generate_from_chunks, generate_not_in_corpus, generate_refusal
from .retrieval import retrieve
from .scheme_matching import filter_chunks_by_scheme, get_preferred_source_url

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def run_pipeline(query: str) -> Dict[str, Any]:
    """
    Run the full pipeline: classify → retrieve (if factual) → generate.
    Returns dict with keys: answer, citation_url, last_updated.
    """
    query = (query or "").strip()
    if not query:
        return generate_refusal(
            "refusal",
            citation_url=cfg.APPROVED_URLS[0],
        )

    label = classify(query)

    if label == "personal_info":
        return generate_refusal(
            "personal_info",
            citation_url=cfg.APPROVED_URLS[0],
        )

    if label == "refusal":
        return generate_refusal(
            "refusal",
            citation_url=cfg.APPROVED_URLS[0],
        )

    if is_other_amc(query):
        return generate_not_in_corpus(citation_url=cfg.APPROVED_URLS[0])

    # Factual: if query mentions a scheme, retrieve more and use only that scheme's chunks (right fund + link)
    preferred_url = get_preferred_source_url(query)
    if preferred_url:
        chunks = retrieve(query, top_k=cfg.TOP_K_RETRIEVE_FOR_SCHEME)
        chunks = filter_chunks_by_scheme(chunks, preferred_url)[: cfg.TOP_K]
    else:
        chunks = retrieve(query, top_k=cfg.TOP_K)
    return generate_from_chunks(chunks, query)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 3: Ask a factual question about HDFC scheme details (from corpus only)."
    )
    parser.add_argument("--query", "-q", type=str, help="User question")
    parser.add_argument("--repl", action="store_true", help="Run in REPL mode (prompt for queries)")
    args = parser.parse_args()

    if args.repl:
        print("Phase 3 REPL. Ask a factual question about the 5 HDFC schemes (or type 'quit').", file=sys.stderr)
        while True:
            try:
                q = input("Query> ").strip()
                if q.lower() in ("quit", "exit", "q"):
                    break
                if not q:
                    continue
                out = run_pipeline(q)
                print(out["answer"])
                print(f"Source: {out['citation_url']}")
            except EOFError:
                break
            except KeyboardInterrupt:
                break
        return

    if not args.query:
        parser.error("Provide --query or --repl")
        return

    out = run_pipeline(args.query)
    print(out["answer"])
    print(f"Source: {out['citation_url']}")


if __name__ == "__main__":
    main()
