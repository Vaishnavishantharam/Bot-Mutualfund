"""
Phase 3: Build answer from retrieved evidence using Groq. ≤3 sentences, one citation URL, "Last updated" footer.
citation_url MUST be the exact source_url of the chunk used to answer.
"""
from __future__ import annotations

from typing import Any, List, Optional

from . import config as cfg

def _fallback_last_updated() -> str:
    """Get last_scraped from data/schemes.json for refusal/fallback citation."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent  # project root
    path = root / "data" / "schemes.json"
    if path.exists():
        import json
        try:
            with open(path, encoding="utf-8") as f:
                meta = json.load(f).get("meta", {})
            return meta.get("last_scraped", "")
        except Exception:
            pass
    return ""

SYSTEM_PROMPT = """You are a factual assistant for Indian mutual fund scheme information. You must answer ONLY using the provided context below. Do not add any information from your own knowledge. Do not compute or compare returns. Reply in at most 3 short sentences. Be concise and factual. If the context does not contain the answer, say only that this information is not available in the corpus."""

REFUSAL_MESSAGE = "This chatbot only answers factual scheme details (e.g. expense ratio, exit load, minimum SIP) from its corpus. It does not give investment advice. For investment decisions, please consult a SEBI-registered adviser."

PERSONAL_INFO_MESSAGE = "This chatbot only answers factual scheme details from its corpus. It does not handle personal information (e.g. PAN, Aadhaar, account details). Please do not share such details."

NOT_IN_CORPUS_MESSAGE = "This scheme is not available in our current sources. We only have factual details for 5 HDFC schemes from INDMoney (Large Cap, Flexi Cap, Mid Cap, Small Cap, Nifty 100 Index)."


def _chunks_to_context(chunks: List[dict[str, Any]]) -> str:
    """Turn retrieved chunks into a single context string for the LLM."""
    if not chunks:
        return "(No relevant context found.)"
    parts = []
    for i, c in enumerate(chunks, 1):
        text = c.get("evidence_text") or ""
        if text:
            parts.append(f"[{i}] {text}")
    return "\n".join(parts) if parts else "(No relevant context found.)"


def _truncate_sentences(text: str, max_sentences: int = 3) -> str:
    """Keep at most max_sentences sentences."""
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:max_sentences]).strip()


def generate_from_chunks(
    chunks: List[dict[str, Any]],
    query: str,
) -> dict[str, str]:
    """
    Use Groq to generate an answer from retrieved chunks only. Returns answer, citation_url, last_updated.
    citation_url = source_url of the top chunk (correct source).
    """
    if not chunks:
        last_updated_fallback = _fallback_last_updated()
        return {
            "answer": "This information is not available in our corpus. We only have factual details for the 5 HDFC schemes from INDMoney."
            + (f" Last updated from sources: {last_updated_fallback}." if last_updated_fallback else ""),
            "citation_url": cfg.APPROVED_URLS[0],
            "last_updated": last_updated_fallback,
        }
    top = chunks[0]
    citation_url = top.get("source_url") or cfg.APPROVED_URLS[0]
    last_updated = top.get("scraped_at") or ""

    context = _chunks_to_context(chunks)
    user_content = f"Context from our corpus:\n{context}\n\nUser question: {query}\n\nAnswer (only from the context above, at most 3 sentences):"

    try:
        from groq import Groq
        client = Groq(api_key=cfg.GROQ_API_KEY)
        if not cfg.GROQ_API_KEY:
            return {
                "answer": _truncate_sentences(
                    "Based on the corpus: " + (chunks[0].get("evidence_text") or "").strip()
                ) + f" Last updated from sources: {last_updated}." if last_updated else "",
                "citation_url": citation_url,
                "last_updated": last_updated,
            }
        resp = client.chat.completions.create(
            model=cfg.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=200,
        )
        raw = (resp.choices[0].message.content or "").strip()
        answer = _truncate_sentences(raw)
    except Exception as e:
        # Fallback: use first chunk evidence only (no LLM)
        answer = (top.get("evidence_text") or "").strip()
        if not answer:
            answer = "This information is not available in our corpus."
        answer = _truncate_sentences(answer)

    if last_updated and "last updated" not in answer.lower():
        answer = answer.rstrip()
        if not answer.endswith("."):
            answer += "."
        answer += f" Last updated from sources: {last_updated}."
    return {
        "answer": answer,
        "citation_url": citation_url,
        "last_updated": last_updated,
    }


def generate_refusal(
    kind: str,
    citation_url: str,
    last_updated: Optional[str] = None,
) -> dict[str, str]:
    """Generate refusal or out-of-scope message. kind in ('refusal', 'personal_info')."""
    if last_updated is None:
        last_updated = _fallback_last_updated()
    if kind == "personal_info":
        msg = PERSONAL_INFO_MESSAGE
    else:
        msg = REFUSAL_MESSAGE
    if last_updated:
        msg = msg.rstrip()
        if not msg.endswith("."):
            msg += "."
        msg += f" Last updated from sources: {last_updated}."
    return {
        "answer": msg,
        "citation_url": citation_url,
        "last_updated": last_updated,
    }


def generate_not_in_corpus(
    citation_url: str,
    last_updated: Optional[str] = None,
) -> dict[str, str]:
    """Return message when the asked scheme is not in our corpus (e.g. Axis, ICICI)."""
    if last_updated is None:
        last_updated = _fallback_last_updated()
    msg = NOT_IN_CORPUS_MESSAGE
    if last_updated:
        msg = msg.rstrip()
        if not msg.endswith("."):
            msg += "."
        msg += f" Last updated from sources: {last_updated}."
    return {
        "answer": msg,
        "citation_url": citation_url,
        "last_updated": last_updated,
    }
