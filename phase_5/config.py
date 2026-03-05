"""
Phase 5: Scheduler config — update Phase 1 data, then trigger Phase 2, 3, 4.
"""

# Phase 1: update latest data (scrape → data/schemes.json)
PHASE_1_RUN = "python -m phase_1.scraper.run"

# Phase 2: re-index vector store from schemes.json
PHASE_2_RUN = "python -m phase_2.indexer"

# Phase 3/4: trigger reload so queries use latest data (choose one or none)
# Option A: backend reload endpoint (backend must implement POST /admin/reload)
BACKEND_RELOAD_URL = None  # e.g. "http://localhost:8000/admin/reload"
# Option B: sentinel file — scheduler writes data/last_indexed_at; backend checks and reloads
SENTINEL_FILE = "data/last_indexed_at"

# Schedule interval if using APScheduler (e.g. hours=24 for daily)
REFRESH_INTERVAL_HOURS = 24
