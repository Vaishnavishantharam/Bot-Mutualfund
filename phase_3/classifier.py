"""
Phase 3: Classify user query as factual, refusal (opinionated/portfolio), or personal_info (out of scope).
"""
from __future__ import annotations

import re
from typing import Literal

QueryLabel = Literal["factual", "refusal", "personal_info"]

# Refusal: opinionated / portfolio / investment advice / comparison
REFUSAL_PATTERNS = [
    r"\bshould\s+i\s+invest\b",
    r"\bwhich\s+(is\s+)?best\b",
    r"\bwhich\s+fund\s+is\s+best\b",
    r"\bwhich\s+.*\bbest\s+(for\s+)?(me|investing)?\b",
    r"\bcompare\s+(returns?|funds?|performance)\b",
    r"\bbuy\s+or\s+sell\b",
    r"\b(should|can)\s+i\s+(buy|sell)\b",
    r"\bgood\s+(to\s+)?invest\b",
    r"\bworth\s+investing\b",
    r"\b(which|what)\s+fund\s+to\s+(invest|choose)\b",
    r"\breturn(s)?\s+(comparison|compare)\b",
    r"\bperformance\s+comparison\b",
    r"\b(advice|recommend)\b.*\b(invest|fund)\b",
    # Good investment / right now
    r"\bgood\s+investment\b",
    r"\binvestment\s+right\s+now\b",
    r"\bis\s+.*\s+good\s+investment\b",
    # Switch / comparison
    r"\bshould\s+i\s+switch\b",
    r"\bswitch\s+from\b",
    r"\bswitch\s+to\b.*\s+from\b",
    # Better returns / which fund will give
    r"\bbetter\s+returns?\b",
    r"\breturns?\s+in\s+\d{4}\b",
    r"\bwhich\s+(fund|scheme)\s+will\s+give\b",
    r"\bwill\s+give\s+better\s+returns\b",
    # Safer than / comparison + advisory
    r"\bsafer\s+than\b",
    r"\bis\s+.*\s+safer\s+than\b",
    r"\bis\s+.*\s+better\s+than\b",
]
REFUSAL_REGEX = re.compile("|".join(REFUSAL_PATTERNS), re.IGNORECASE)

# Personal information / PII: out of scope
PII_PATTERNS = [
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
    # Generic personal questions (name/address)
    r"\bwhat\s+is\s+my\s+name\b",
    r"\bmy\s+name\s+is\b",
    r"\bwhat\s+is\s+my\s+address\b",
    r"\bmy\s+address\b",
    r"\bwhat\s+is\s+address\b",
    r"\baddress\b",
]
PII_REGEX = re.compile("|".join(PII_PATTERNS), re.IGNORECASE)


# Other AMCs not in our corpus (we only have 5 HDFC schemes)
OTHER_AMC_PATTERN = re.compile(
    r"\b(axis|icici|sbi|uti|kotak|mirae|ppfas|quant|nippon)\s+",
    re.IGNORECASE,
)


def is_other_amc(query: str) -> bool:
    """True if the query clearly asks about a scheme from an AMC we don't have."""
    if not query or not query.strip():
        return False
    return bool(OTHER_AMC_PATTERN.search(query.strip()))


def classify(query: str) -> QueryLabel:
    """
    Classify query as factual (answer from corpus), refusal (opinionated/portfolio),
    or personal_info (out of scope; do not answer).
    """
    if not query or not query.strip():
        return "refusal"
    q = query.strip()
    if PII_REGEX.search(q):
        return "personal_info"
    if REFUSAL_REGEX.search(q):
        return "refusal"
    return "factual"
