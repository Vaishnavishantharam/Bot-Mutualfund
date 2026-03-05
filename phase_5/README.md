# Phase 5: Scheduler (data refresh pipeline)

The scheduler runs on a schedule to **update the latest data into Phase 1**, then **trigger all other phases** in order so the entire system uses the latest data every time.

## Flow (run in order)

1. **Phase 1** — Run scraper → update `data/schemes.json` from the 5 INDMoney URLs.
2. **Phase 2** — Run indexer → re-build vector store from updated `schemes.json`.
3. **Phase 3 / Phase 4** — Trigger reload or cache invalidation so the query pipeline and chat backend use the new index (e.g. call backend `POST /admin/reload` or write a sentinel file that the backend checks and reloads on).

## Contents

- `config.py` — refresh interval; commands for Phase 1 and Phase 2; optional backend reload URL or sentinel file path.
- `run_refresh.py` — run Phase 1 → Phase 2 → trigger Phase 3/4 reload; log success/failure per step.

## Run

**Manual refresh (run all phases in order):**

```bash
# From project root
python -m phase_5.run_refresh
```

**Scheduled in-process (refresh every N hours, e.g. 24):**

```bash
python -m phase_5.run_refresh --schedule
```

Configure `REFRESH_INTERVAL_HOURS` in `phase_5/config.py` (default: 24). Requires `pip install apscheduler`.

**Cron (e.g. daily at 2 AM):**

```cron
0 2 * * * cd /path/to/Mutual\ funds && .venv/bin/python -m phase_5.run_refresh
```
