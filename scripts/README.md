# Scripts

## Check if the app is using fresh (today’s) data

```bash
python scripts/check_data_freshness.py
```

- Reads `data/schemes.json` (or `api/schemes.json`) and prints `last_scraped` and whether it’s **today** (UTC), yesterday, or older.
- Exit code **0** = data from today; **1** = not from today or file missing.

To get **today’s** data:

1. **Manual (local):**  
   `python -m phase_1.scraper.run` (live) or `python -m phase_1.scraper.run --from-dir phase_1/html_fixtures` (fixtures).  
   Then `cp data/schemes.json api/schemes.json` if you use the API copy.

2. **Daily (GitHub):**  
   The workflow **Refresh data (Phase 5 scheduler)** runs at **10:00 UTC**.  
   Trigger it manually: Actions → “Refresh data (Phase 5 scheduler)” → Run workflow.  
   After it pushes, Vercel redeploys and the app shows the new “Data last updated”.
