"""
Phase 1: Run scraper for all approved INDMoney URLs; write data/schemes.json.
Run from project root: python -m phase_1.scraper.run
Optional: python -m phase_1.scraper.run --from-dir path/to/html_files
  (HTML files named by URL id, e.g. 2989.html, 3184.html, ... for each approved URL)
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from .config import APPROVED_URLS, OUTPUT_PATH
from .parser import scrape_url, scrape_from_html_file

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Project root = parent of phase_1 (parent of scraper's parent)."""
    # run.py lives at phase_1/scraper/run.py
    here = Path(__file__).resolve().parent
    phase_1 = here.parent  # phase_1
    root = phase_1.parent   # project root
    return root


def _url_to_id(url: str) -> str:
    """Extract trailing id from URL, e.g. ...-2989 -> 2989, ...-1040567 -> 1040567."""
    match = re.search(r"-(\d+)/?$", url.rstrip("/"))
    return match.group(1) if match else ""


def run(from_dir: Optional[str] = None) -> None:
    project_root = get_project_root()
    output_file = project_root / OUTPUT_PATH
    output_file.parent.mkdir(parents=True, exist_ok=True)

    schemes: list = []
    evidence: list = []
    session = requests.Session()
    html_dir = Path(from_dir).resolve() if from_dir else None

    for url in APPROVED_URLS:
        try:
            if html_dir:
                url_id = _url_to_id(url)
                html_file = html_dir / f"{url_id}.html"
                if html_file.exists():
                    scheme, ev = scrape_from_html_file(str(html_file), url)
                    schemes.append(scheme)
                    evidence.extend(ev)
                    logger.info("Parsed from file: %s", scheme.get("scheme_name", url))
                else:
                    logger.warning("No HTML file %s for %s; skipping.", html_file.name, url)
            else:
                scheme, ev = scrape_url(url, session=session)
                schemes.append(scheme)
                evidence.extend(ev)
                logger.info("Scraped: %s", scheme.get("scheme_name", url))
        except Exception as e:
            logger.exception("Failed for %s: %s", url, e)

    meta = {
        "last_scraped": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_urls": list(APPROVED_URLS),
    }
    payload = {
        "meta": meta,
        "schemes": schemes,
        "evidence": evidence,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    logger.info("Wrote %d schemes and %d evidence items to %s", len(schemes), len(evidence), output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1: Scrape INDMoney scheme pages -> data/schemes.json")
    parser.add_argument(
        "--from-dir",
        type=str,
        default=None,
        help="Directory containing HTML files named by URL id (e.g. 2989.html). Use when live requests get 403.",
    )
    args = parser.parse_args()
    run(from_dir=args.from_dir)
