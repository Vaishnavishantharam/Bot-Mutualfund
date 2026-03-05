"""
Phase 1: Parse INDMoney scheme page HTML — label-based extraction of scheme facts and evidence.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .config import APPROVED_URLS
from . import field_mapping as fm

logger = logging.getLogger(__name__)

# User-Agent that may help with 403 on some sites
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_page_html(url: str, session: Optional[requests.Session] = None) -> str:
    """Fetch page HTML. Uses session if provided."""
    sess = session or requests.Session()
    resp = sess.get(url, headers=DEFAULT_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def _normalize_whitespace(s: str) -> str:
    return " ".join(s.split()).strip() if s else ""


def _parse_rupee_value(raw: str) -> Tuple[Optional[int], str]:
    """Parse numeric value from strings like '₹100', '100', '₹1,000'. Returns (number or None, raw_text)."""
    raw = _normalize_whitespace(raw)
    if not raw:
        return None, raw
    cleaned = re.sub(r"[₹,\s]", "", raw)
    match = re.search(r"(\d+)", cleaned)
    if match:
        return int(match.group(1)), raw
    return None, raw


def _parse_min_lumpsum_sip(value: str) -> dict[str, Any]:
    """Parse '₹100/₹100' or '₹500/₹500' into min_lumpsum, min_sip (numeric + raw)."""
    value = _normalize_whitespace(value)
    parts = re.split(r"\s*/\s*", value, maxsplit=1)
    lump_raw = parts[0].strip() if len(parts) > 0 else ""
    sip_raw = parts[1].strip() if len(parts) > 1 else lump_raw
    lump_num, _ = _parse_rupee_value(lump_raw)
    sip_num, _ = _parse_rupee_value(sip_raw)
    return {
        "min_lumpsum": lump_num,
        "min_lumpsum_raw": lump_raw or None,
        "min_sip": sip_num,
        "min_sip_raw": sip_raw or None,
    }


def _extract_value_from_table(soup: BeautifulSoup, label: str) -> Optional[str]:
    """Find a table cell containing label; return text of adjacent cell (same row)."""
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            for i, cell in enumerate(cells):
                text = _normalize_whitespace(cell.get_text())
                if label.lower() in text.lower() and len(label) >= 3:
                    if i + 1 < len(cells):
                        return _normalize_whitespace(cells[i + 1].get_text())
                    return None
    return None


def _extract_label_value_pairs_from_text(text: str) -> dict[str, str]:
    """Fallback: find 'Label | Value' or 'Label: Value' or 'Label\\nValue' in page text."""
    pairs: dict[str, str] = {}
    # Pattern: label followed by | or : or newline and value (until next label or end)
    # Prefer matching known labels
    for label in fm.LABEL_TO_FIELDS:
        if not label or not fm.LABEL_TO_FIELDS[label]:
            continue
        # Match "Label" then | or : then value (non-greedy, stop at newline or next pipe)
        escaped = re.escape(label)
        for sep in [r"\|\s*", r":\s*", r"\s+"]:
            pat = rf"{escaped}\s*{sep}\s*([^\n|]+)"
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = _normalize_whitespace(m.group(1))
                if val and val not in pairs.values():
                    # Use first matched label for this value (prefer longer label)
                    key = label
                    if key not in pairs or len(key) > len(next((k for k in pairs if pairs[k] == val), "")):
                        pairs[key] = val
                break
    return pairs


def _extract_from_overview_section(soup: BeautifulSoup) -> dict[str, str]:
    """Extract label -> value from Fund Overview / Key Facts section (tables or structured blocks)."""
    label_to_value: dict[str, str] = {}
    # Strategy 1: tables
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) >= 2:
                first = _normalize_whitespace(cells[0].get_text())
                second = _normalize_whitespace(cells[1].get_text())
                if first and second:
                    for label in fm.LABEL_TO_FIELDS:
                        if label and label.lower() in first.lower():
                            label_to_value[label] = second
                            break
    # Strategy 2: if we have little, try definition lists or divs
    if not label_to_value:
        full_text = soup.get_text(separator="\n")
        label_to_value = _extract_label_value_pairs_from_text(full_text)
    return label_to_value


def _derive_scheme_name_and_category(soup: BeautifulSoup, url: str) -> tuple[str, str, str, str]:
    """Derive scheme_name, category, plan_type, option_type from page (title, h1, breadcrumbs)."""
    scheme_name = ""
    category = ""
    plan_type = "Direct"
    option_type = "Growth"

    title = soup.find("title")
    if title:
        scheme_name = _normalize_whitespace(title.get_text()).split("|")[0].strip()
    h1 = soup.find("h1")
    if h1:
        scheme_name = _normalize_whitespace(h1.get_text()) or scheme_name
    if not scheme_name:
        # Fallback from URL slug (e.g. hdfc-large-cap-fund-direct-plan-growth-option-2989)
        path = urlparse(url).path or ""
        slug = path.rstrip("/").split("/")[-1] or ""
        scheme_name = slug.replace("-", " ").title() if slug else "Unknown Scheme"

    # Append plan/option if not already present
    if "direct" not in scheme_name.lower():
        scheme_name = f"{scheme_name} - Direct Plan - Growth Option"
    if "growth" not in scheme_name.lower() and "option" not in scheme_name.lower():
        scheme_name = f"{scheme_name} - Growth Option"

    # Category from links (Large-Cap, Mid-Cap, etc.)
    for a in soup.find_all("a", href=True):
        t = _normalize_whitespace(a.get_text())
        href = (a.get("href") or "").lower()
        if "large-cap" in href or t == "Large-Cap":
            category = "Large Cap"
            break
        if "mid-cap" in href or t == "Mid-Cap":
            category = "Mid Cap"
            break
        if "small-cap" in href or t == "Small-Cap":
            category = "Small Cap"
            break
        if "flexi" in href or "flexi-cap" in href:
            category = "Flexi Cap"
            break
        if "index" in href and "nifty" in href:
            category = "Index"
            break
    if not category and "index" in url.lower():
        category = "Index"
    if not category and "small" in url.lower():
        category = "Small Cap"
    if not category and "mid" in url.lower():
        category = "Mid Cap"
    if not category and "flexi" in url.lower():
        category = "Flexi Cap"
    if not category and "large" in url.lower():
        category = "Large Cap"

    return scheme_name, category, plan_type, option_type


def _extract_fund_managers(soup: BeautifulSoup) -> Optional[str]:
    """Try to get fund manager names from page (e.g. FAQ or Overview section)."""
    text = soup.get_text()
    # Common pattern: "Fund Manager" or "fund managers are X, Y"
    m = re.search(r"(?:fund manager|fund managers)[\s:]+(?:are\s+)?([^.]+?)(?:\.|\n|$)", text, re.IGNORECASE)
    if m:
        return _normalize_whitespace(m.group(1))
    return None


def parse_scheme_page(html: str, source_url: str) -> Tuple[dict[str, Any], List[dict[str, Any]]]:
    """
    Parse INDMoney scheme page HTML. Returns (scheme_record, evidence_list).
    scheme_record conforms to docs/schema.md; evidence has field_name, field_value, evidence_text, source_url.
    """
    soup = BeautifulSoup(html, "html.parser")
    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    scheme_name, category, plan_type, option_type = _derive_scheme_name_and_category(soup, source_url)
    amc_name = "HDFC"

    # Build empty scheme with required fields
    scheme: dict[str, Any] = {
        "scheme_name": scheme_name,
        "amc_name": amc_name,
        "category": category or None,
        "plan_type": plan_type,
        "option_type": option_type,
        "expense_ratio": None,
        "exit_load": None,
        "min_sip": None,
        "min_sip_raw": None,
        "min_lumpsum": None,
        "min_lumpsum_raw": None,
        "lock_in": None,
        "risk_level": None,
        "benchmark": None,
        "aum": None,
        "inception_date": None,
        "fund_manager": None,
        "source_url": source_url,
        "scraped_at": scraped_at,
    }

    label_to_value = _extract_from_overview_section(soup)
    # Fallback: try full-page text for any missing key labels
    if len(label_to_value) < 5:
        full_text = soup.get_text(separator="\n")
        fallback = _extract_label_value_pairs_from_text(full_text)
        for k, v in fallback.items():
            if k not in label_to_value:
                label_to_value[k] = v

    evidence: list[dict[str, Any]] = []

    for label, value in label_to_value.items():
        if not value:
            continue
        fields = fm.LABEL_TO_FIELDS.get(label, [])
        if not fields:
            continue
        evidence_text = f"{label} | {value}"

        if "min_lumpsum" in fields or "min_sip" in fields:
            parsed = _parse_min_lumpsum_sip(value)
            scheme["min_lumpsum"] = parsed.get("min_lumpsum")
            scheme["min_lumpsum_raw"] = parsed.get("min_lumpsum_raw")
            scheme["min_sip"] = parsed.get("min_sip")
            scheme["min_sip_raw"] = parsed.get("min_sip_raw")
            evidence.append({
                "field_name": "min_lumpsum",
                "field_value": parsed.get("min_lumpsum_raw") or parsed.get("min_lumpsum"),
                "evidence_text": evidence_text,
                "source_url": source_url,
                "scheme_name": scheme_name,
            })
            evidence.append({
                "field_name": "min_sip",
                "field_value": parsed.get("min_sip_raw") or parsed.get("min_sip"),
                "evidence_text": evidence_text,
                "source_url": source_url,
                "scheme_name": scheme_name,
            })
            continue

        for field in fields:
            scheme[field] = value
            evidence.append({
                "field_name": field,
                "field_value": value,
                "evidence_text": evidence_text,
                "source_url": source_url,
                "scheme_name": scheme_name,
            })

    # Fund manager from dedicated section if not in overview
    if not scheme["fund_manager"]:
        scheme["fund_manager"] = _extract_fund_managers(soup)

    # Log missing fields
    for f in fm.SCHEME_FIELD_NAMES:
        if f in ("source_url", "scraped_at", "scheme_name", "amc_name", "plan_type", "option_type"):
            continue
        if scheme.get(f) is None or scheme.get(f) == "":
            logger.info("Missing field %s for %s", f, source_url)

    return scheme, evidence


def scrape_url(url: str, session: Optional[requests.Session] = None) -> Tuple[dict[str, Any], List[dict[str, Any]]]:
    """Fetch URL and parse; returns (scheme, evidence)."""
    if url not in APPROVED_URLS:
        raise ValueError(f"URL not in approved list: {url}")
    html = get_page_html(url, session=session)
    return parse_scheme_page(html, url)


def scrape_from_html_file(file_path: str, source_url: str) -> Tuple[dict[str, Any], List[dict[str, Any]]]:
    """Load HTML from a local file and parse. Use when the site returns 403 for direct requests."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"HTML file not found: {file_path}")
    html = path.read_text(encoding="utf-8", errors="replace")
    return parse_scheme_page(html, source_url)
