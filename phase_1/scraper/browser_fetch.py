"""
Phase 1: Playwright-based page fetch for JS-rendered or strict sites.
Use when requests get 403 or content is missing. Run from project root.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def get_page_html_playwright(url: str, timeout_ms: int = 60000) -> str:
    """
    Fetch page HTML using Playwright (headless browser).
    INDMoney is behind Cloudflare; we wait for the challenge to pass and real content to load.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ImportError("Install playwright: pip install playwright && playwright install chromium")

    with sync_playwright() as p:
        # Use headed=False but with args that may help pass Cloudflare (real browser fingerprint)
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-IN",
            )
            page = context.new_page()
            page.set_default_timeout(timeout_ms)
            page.goto(url, wait_until="domcontentloaded")
            # Wait for Cloudflare challenge to complete and fund content to appear (up to 45s)
            try:
                page.wait_for_function(
                    """() => {
                        const t = document.body.innerText;
                        const isChallenge = t.includes('Just a moment') || t.includes('Performing security verification');
                        const hasContent = t.includes('Expense ratio') || t.includes('Benchmark') || t.includes('AUM') || t.includes('Fund Overview');
                        return !isChallenge && (hasContent || document.title.includes('HDFC') || document.title.includes('Large Cap'));
                    }""",
                    timeout=45000,
                )
            except Exception:
                pass
            time.sleep(3)
            html = page.content()
            context.close()
            return html
        finally:
            browser.close()
    return ""
