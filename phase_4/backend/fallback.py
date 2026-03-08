"""
Phase 4: Fallback answers from data/schemes.json when Phase 3 pipeline fails.
Handles refusal (advisory), edge cases (charges, risk, Hinglish), and scheme-not-in-corpus.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Scheme keywords (pattern, url) — same order as phase_3.scheme_matching; add fuzzy/informal
APPROVED_URLS = [
    "https://www.indmoney.com/mutual-funds/hdfc-large-cap-fund-direct-plan-growth-option-2989",
    "https://www.indmoney.com/mutual-funds/hdfc-flexi-cap-fund-direct-plan-growth-option-3184",
    "https://www.indmoney.com/mutual-funds/hdfc-mid-cap-fund-direct-plan-growth-option-3097",
    "https://www.indmoney.com/mutual-funds/hdfc-small-cap-fund-direct-growth-option-3580",
    "https://www.indmoney.com/mutual-funds/hdfc-nifty-100-index-fund-direct-growth-1040567",
]
SCHEME_KEYWORDS = [
    (r"\bnifty\s*100\b|\b100\s*index\b|nifty\s*100\s*index", APPROVED_URLS[4]),
    (r"\blarge\s*cap\b", APPROVED_URLS[0]),
    (r"\bflexi\s*cap\b|flexicap", APPROVED_URLS[1]),
    (r"\bmid\s*cap\b|midcap", APPROVED_URLS[2]),
    (r"\bsmall\s*cap\b|smallcap", APPROVED_URLS[3]),
    (r"\bindex\s*fund\b", APPROVED_URLS[4]),
]

# Refusal: same intent as phase_3 classifier so fallback also refuses advisory questions
REFUSAL_PATTERNS = [
    r"\bgood\s+investment\b", r"\bshould\s+i\s+switch\b", r"\bswitch\s+from\b",
    r"\bbetter\s+returns?\b", r"\breturns?\s+in\s+\d{4}\b", r"\bwhich\s+(fund|scheme)\s+will\s+give\b",
    r"\bsafer\s+than\b", r"\bis\s+.*\s+safer\s+than\b", r"\bis\s+.*\s+better\s+than\b",
    r"\bshould\s+i\s+invest\b", r"\bwhich\s+(is\s+)?best\b", r"\bgood\s+(to\s+)?invest\b",
    r"\bwhich\s+fund\s+is\s+better\b", r"\bcompare\s+.*\s+fund\b", r"\brecommend\b",
]
REFUSAL_REGEX = re.compile("|".join(REFUSAL_PATTERNS), re.IGNORECASE)

REFUSAL_MESSAGE = "I cannot provide investment advice. I can only share factual information about mutual fund schemes from official sources."
REFUSAL_COMPARE_MESSAGE = "I cannot compare or recommend mutual funds. I can only provide factual information about each scheme."

# Personal information / PII in fallback mode (name, address, PAN, etc.)
PERSONAL_INFO_PATTERNS = [
    r"\bpan\s*(card)?\b",
    r"\baadhaar\b",
    r"\baccount\s+number\b",
    r"\botp\b",
    r"\bemail\s*(address)?\b",
    r"\bphone\s*(number)?\b",
    r"\bmobile\s*(number)?\b",
    r"\bpassword\b",
    r"\b(my|user)\s+(pan|aadhaar|account|email|phone)\b",
    r"\b\d{10}\b",  # 10 digits (phone)
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",  # PAN-like
    r"\bwhat\s+is\s+my\s+name\b",
    r"\bmy\s+name\s+is\b",
    r"\bwhat\s+is\s+my\s+address\b",
    r"\bmy\s+address\b",
    r"\bwhat\s+is\s+address\b",
    r"\baddress\b",
]
PERSONAL_INFO_REGEX = re.compile("|".join(PERSONAL_INFO_PATTERNS), re.IGNORECASE)

PERSONAL_INFO_MESSAGE = (
    "This chatbot only answers factual scheme details from its corpus. "
    "It does not handle personal information (e.g. PAN, Aadhaar, account details). "
    "Please do not share such details."
)

# AMCs we don't have in corpus (we only have 5 HDFC schemes)
OTHER_AMCS = re.compile(
    r"\b(axis|icici|sbi|uti|kotak|mirae|ppfas|quant|nippon)\s+",
    re.IGNORECASE
)

# Default/welcome when user doesn't ask about a specific scheme (e.g. "hi", "hello")
WELCOME_ANSWER = (
    "I have details for all 5 HDFC schemes in our corpus: "
    "Large Cap, Flexi Cap, Mid Cap, Small Cap, and Nifty 100 Index Fund. "
    "You can ask about expense ratio, exit load, minimum SIP, benchmark, AUM, risk level, fund manager, or inception date for any of these schemes."
)


def _find_scheme_by_url(schemes: list, url: str) -> dict | None:
    for s in schemes:
        if (s.get("source_url") or "") == url:
            return s
    return None


def _detect_scheme_url(query: str) -> str | None:
    q = (query or "").strip().lower()
    if not q:
        return None
    for pattern, url in SCHEME_KEYWORDS:
        if re.search(pattern, q, re.IGNORECASE):
            return url
    return None


def answer_from_corpus(query: str, root: Path) -> dict[str, str]:
    """
    Answer from schemes.json. Handles refusal, scheme-not-in-corpus, charges, risk, etc.
    Returns dict with answer, citation_url, last_updated.
    """
    # Prefer data/schemes.json; on Vercel serverless we copy it to api/schemes.json at build
    path = root / "data" / "schemes.json"
    if not path.exists():
        path = root / "api" / "schemes.json"
    default = {
        "answer": "I can only answer factual questions about the 5 HDFC schemes (Large Cap, Flexi Cap, Mid Cap, Small Cap, Nifty 100 Index). Try asking about expense ratio, minimum SIP, or benchmark for a specific fund.",
        "citation_url": APPROVED_URLS[0],
        "last_updated": "",
    }
    q = (query or "").strip().lower()

    # 1) Personal information / PII questions (out of scope)
    if PERSONAL_INFO_REGEX.search(q):
        try:
            with open(path, encoding="utf-8") as f:
                meta = json.load(f).get("meta", {})
            lu = meta.get("last_scraped", "")
        except Exception:
            lu = ""
        msg = PERSONAL_INFO_MESSAGE
        if lu:
            msg = msg.rstrip()
            if not msg.endswith("."):
                msg += "."
            msg += f" Last updated from sources: {lu}."
        return {"answer": msg, "citation_url": APPROVED_URLS[0], "last_updated": lu}

    # 2) Refusal: advisory / comparison questions (case-insensitive)
    if REFUSAL_REGEX.search(q):
        try:
            with open(path, encoding="utf-8") as f:
                meta = json.load(f).get("meta", {})
            lu = meta.get("last_scraped", "")
        except Exception:
            lu = ""
        if re.search(r"\bwhich\s+fund\s+is\s+better\b|\bcompare\b|\brecommend\b", q, re.IGNORECASE):
            msg = REFUSAL_COMPARE_MESSAGE
        else:
            msg = REFUSAL_MESSAGE
        if lu:
            msg = msg.rstrip()
            if not msg.endswith("."):
                msg += "."
            msg += f" Last updated from sources: {lu}."
        return {"answer": msg, "citation_url": APPROVED_URLS[0], "last_updated": lu}

    # 3) Scheme not in corpus (other AMCs, e.g. SBI Bluechip)
    if OTHER_AMCS.search(q):
        return {
            "answer": "This scheme is not available in the current data sources. The assistant can only provide information for the schemes included in the dataset.",
            "citation_url": APPROVED_URLS[0],
            "last_updated": "",
        }

    if not path.exists():
        return default
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return default
    schemes = data.get("schemes", [])
    meta = data.get("meta", {})
    last_updated = meta.get("last_scraped", "")

    # Detect which scheme (HDFC only); normalize informal "smallcap", "small cap"
    scheme_url = _detect_scheme_url(query)
    scheme = _find_scheme_by_url(schemes, scheme_url) if scheme_url else None

    # No specific scheme mentioned (e.g. "hi", "hello") → show all schemes we have
    if scheme_url is None and schemes:
        ans = WELCOME_ANSWER
        if last_updated:
            ans += f" Last updated from sources: {last_updated}."
        return {"answer": ans, "citation_url": APPROVED_URLS[0], "last_updated": last_updated}

    if not scheme and schemes:
        scheme = schemes[0]
        scheme_url = scheme.get("source_url", APPROVED_URLS[0])

    name = scheme.get("scheme_name", "This scheme") if scheme else "This scheme"

    # 3) Charges → expense ratio + exit load
    if "charges" in q or "charge" in q:
        if scheme:
            er = scheme.get("expense_ratio", "N/A")
            el = scheme.get("exit_load", "N/A")
            ans = f"For {name}: expense ratio is {er} and exit load is {el}."
            if last_updated:
                ans += f" Last updated from sources: {last_updated}."
            return {
                "answer": ans,
                "citation_url": scheme.get("source_url", scheme_url),
                "last_updated": last_updated,
            }

    # 4) Risk (including "risk kya hai" / informal); case-insensitive
    if "risk" in q:
        if scheme:
            risk = scheme.get("risk_level", "N/A")
            ans = f"{name} is categorized as {risk} according to the riskometer."
            if last_updated:
                ans += f" Last updated from sources: {last_updated}."
            return {
                "answer": ans,
                "citation_url": scheme.get("source_url", scheme_url),
                "last_updated": last_updated,
            }

    # 5) Lock-in period (case-insensitive: "lock-in", "lock in")
    if "lock" in q and ("in" in q or "period" in q):
        if scheme:
            lock_val = scheme.get("lock_in", "N/A")
            if lock_val and "no lock" in str(lock_val).lower():
                ans = f"{name} does not have a lock-in period."
            else:
                ans = f"{name} has a lock-in of {lock_val}."
            if last_updated:
                ans += f" Last updated from sources: {last_updated}."
            return {
                "answer": ans,
                "citation_url": scheme.get("source_url", scheme_url),
                "last_updated": last_updated,
            }

    # 6) AUM (assets under management) — check early so "what is aum of small cap" is answered
    if "aum" in q or "assets under management" in q:
        if scheme:
            aum_val = scheme.get("aum", "N/A")
            ans = f"The AUM (assets under management) for {name} is {aum_val}."
            if last_updated:
                ans += f" Last updated from sources: {last_updated}."
            return {
                "answer": ans,
                "citation_url": scheme.get("source_url", scheme_url),
                "last_updated": last_updated,
            }

    # Answer by question type
    # Turnover / returns / NAV: we don't have this data — say so instead of giving expense+SIP
    if "turnover" in q:
        topics = "expense ratio, exit load, minimum SIP, benchmark, AUM, risk level, fund manager"
        ans = f"Portfolio turnover is not available in our current data. For these HDFC schemes we have: {topics}."
        if last_updated:
            ans += f" Last updated from sources: {last_updated}."
        return {"answer": ans, "citation_url": scheme_url or APPROVED_URLS[0], "last_updated": last_updated}
    if "return" in q and "exit" not in q and "load" not in q:
        # returns / performance — we don't have
        ans = "We don't have returns or performance data in our corpus. We have: expense ratio, exit load, minimum SIP, benchmark, AUM, risk level, fund manager."
        if last_updated:
            ans += f" Last updated from sources: {last_updated}."
        return {"answer": ans, "citation_url": scheme_url or APPROVED_URLS[0], "last_updated": last_updated}

    if "expense" in q or "expense ratio" in q or ("rate" in q and scheme):
        if scheme:
            er = scheme.get("expense_ratio", "N/A")
            ans = f"The expense ratio of {name} is {er}."
            if "rate" in q and "expense" not in q:
                ans = f"The expense ratio of {name} is {er}. (We do not have returns or NAV in our data.)"
            if last_updated:
                ans += f" Last updated from sources: {last_updated}."
            return {
                "answer": ans,
                "citation_url": scheme.get("source_url", scheme_url),
                "last_updated": last_updated,
            }
    if "minimum sip" in q or "min sip" in q or "sip" in q and ("minimum" in q or "min " in q or "start" in q or "invest" in q):
        if scheme:
            raw = scheme.get("min_sip_raw") or f"₹{scheme.get('min_sip', 100)}"
            ans = f"The minimum SIP for {name} is {raw}."
            if last_updated:
                ans += f" Last updated from sources: {last_updated}."
            return {
                "answer": ans,
                "citation_url": scheme.get("source_url", scheme_url),
                "last_updated": last_updated,
            }
    if "benchmark" in q or "index" in q and ("benchmark" in q or "track" in q):
        if scheme:
            bench = scheme.get("benchmark", "N/A")
            ans = f"{name} tracks the {bench} benchmark."
            if last_updated:
                ans += f" Last updated from sources: {last_updated}."
            return {
                "answer": ans,
                "citation_url": scheme.get("source_url", scheme_url),
                "last_updated": last_updated,
            }
    if "exit load" in q:
        if scheme:
            el = scheme.get("exit_load", "N/A")
            ans = f"The exit load for {name} is {el}."
            if el and ("1%" in str(el) or "1.0%" in str(el)):
                ans += " (if redeemed within 1 year.)"
            if last_updated:
                ans += f" Last updated from sources: {last_updated}."
            return {
                "answer": ans,
                "citation_url": scheme.get("source_url", scheme_url),
                "last_updated": last_updated,
            }
    if "lumpsum" in q or "lump sum" in q or "minimum investment" in q:
        if scheme:
            raw = scheme.get("min_lumpsum_raw") or f"₹{scheme.get('min_lumpsum', 100)}"
            ans = f"The minimum lump sum investment for {name} is {raw}."
            if last_updated:
                ans += f" Last updated from sources: {last_updated}."
            return {
                "answer": ans,
                "citation_url": scheme.get("source_url", scheme_url),
                "last_updated": last_updated,
            }
    if "fund manager" in q or ("manager" in q and ("fund" in q or "scheme" in q)):
        if scheme:
            fm = scheme.get("fund_manager", "N/A")
            ans = f"The fund manager(s) for {name}: {fm}."
            if last_updated:
                ans += f" Last updated from sources: {last_updated}."
            return {
                "answer": ans,
                "citation_url": scheme.get("source_url", scheme_url),
                "last_updated": last_updated,
            }
    if "inception" in q:
        if scheme:
            inc = scheme.get("inception_date", "N/A")
            ans = f"{name} inception date is {inc}."
            if last_updated:
                ans += f" Last updated from sources: {last_updated}."
            return {
                "answer": ans,
                "citation_url": scheme.get("source_url", scheme_url),
                "last_updated": last_updated,
            }

    # Generic: list what we can answer instead of always expense ratio + SIP
    if scheme:
        topics = "expense ratio, exit load, minimum SIP/lumpsum, benchmark, AUM, risk level, fund manager, inception date"
        ans = f"I have details for {name}. You can ask about: {topics}."
        if last_updated:
            ans += f" Last updated from sources: {last_updated}."
        return {
            "answer": ans,
            "citation_url": scheme.get("source_url", scheme_url),
            "last_updated": last_updated,
        }
    return default
