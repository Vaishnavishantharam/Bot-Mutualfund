# Phase 1: Data Ingestion & Storage

All Phase 1 code lives only in this folder. Scrape the 5 INDMoney HDFC scheme pages and write normalized scheme records + evidence to `data/schemes.json`.

## Contents

- `scraper/` — `config.py`, `field_mapping.py`, `parser.py`, `run.py`.
- `html_fixtures/` — optional: local HTML files (e.g. `2989.html`) for testing or when live requests get 403.
- Output: shared `data/schemes.json` at project root.

## Run

**Live scrape** (from project root):

```bash
python -m phase_1.scraper.run
```

If INDMoney returns 403 or blocks requests (e.g. Cloudflare), use **Playwright** (headless browser):

```bash
python -m phase_1.scraper.run --use-playwright
```

Install Playwright’s Chromium once: `playwright install chromium`

Alternatively, use local HTML files:

**From local HTML files** (files named by URL id: `2989.html`, `3184.html`, `3097.html`, `3580.html`, `1040567.html`):

```bash
python -m phase_1.scraper.run --from-dir phase_1/html_fixtures
```

Save pages manually (e.g. “Save as” in browser) or with Playwright into the fixtures dir; the scraper will parse only URLs that have a matching file and skip the rest.

## Dependencies

- `requests`, `beautifulsoup4` (see project root `requirements.txt`).
- For `--use-playwright`: `playwright`; run `playwright install chromium` once.
