"""
Phase 5: Scheduler — update latest data into Phase 1, then trigger Phase 2, then reload.

Flow:
  1. Run Phase 1 scraper → data/schemes.json updated.
  2. Run Phase 2 indexer → vector store updated.
  3. Trigger Phase 3/4 reload: POST to BACKEND_RELOAD_URL or write SENTINEL_FILE with ISO timestamp.

Run from project root:
  python -m phase_5.run_refresh           # one-shot refresh
  python -m phase_5.run_refresh --schedule   # run refresh every REFRESH_INTERVAL_HOURS (APScheduler)
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import config as cfg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("phase_5")


def get_project_root() -> Path:
    """Project root = parent of phase_5."""
    return Path(__file__).resolve().parent.parent


def run_phase_1(cwd: Path) -> bool:
    """Run Phase 1 scraper. Returns True on success."""
    logger.info("Step 1: Running Phase 1 scraper -> data/schemes.json")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "phase_1.scraper.run"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error("Phase 1 failed (exit %s): %s", result.returncode, result.stderr or result.stdout)
            return False
        logger.info("Phase 1 completed successfully")
        return True
    except subprocess.TimeoutExpired:
        logger.error("Phase 1 timed out")
        return False
    except Exception as e:
        logger.exception("Phase 1 error: %s", e)
        return False


def run_phase_2(cwd: Path) -> bool:
    """Run Phase 2 indexer (rebuild vector store). Returns True on success."""
    logger.info("Step 2: Running Phase 2 indexer -> vector store")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "phase_2.indexer"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            logger.error("Phase 2 failed (exit %s): %s", result.returncode, result.stderr or result.stdout)
            return False
        logger.info("Phase 2 completed successfully")
        return True
    except subprocess.TimeoutExpired:
        logger.error("Phase 2 timed out")
        return False
    except Exception as e:
        logger.exception("Phase 2 error: %s", e)
        return False


def trigger_reload(cwd: Path) -> bool:
    """Trigger Phase 3/4 to use new data: POST to BACKEND_RELOAD_URL or write SENTINEL_FILE."""
    logger.info("Step 3: Triggering reload for Phase 3/4")

    if cfg.BACKEND_RELOAD_URL:
        try:
            import urllib.request
            req = urllib.request.Request(
                cfg.BACKEND_RELOAD_URL,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if 200 <= resp.status < 300:
                    logger.info("Backend reload endpoint returned %s", resp.status)
                    return True
                logger.warning("Backend reload returned %s", resp.status)
                return False
        except Exception as e:
            logger.warning("Backend reload request failed: %s", e)
            return False

    if cfg.SENTINEL_FILE:
        sentinel_path = cwd / cfg.SENTINEL_FILE
        sentinel_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            sentinel_path.write_text(timestamp, encoding="utf-8")
            logger.info("Wrote sentinel file %s with timestamp %s", sentinel_path, timestamp)
            return True
        except Exception as e:
            logger.warning("Failed to write sentinel file: %s", e)
            return False

    logger.info("No BACKEND_RELOAD_URL or SENTINEL_FILE set; Phase 3 loads store on each request, so no action needed")
    return True


def run_refresh() -> int:
    """Run full refresh: Phase 1 -> Phase 2 -> reload. Returns 0 on success, non-zero on failure."""
    root = get_project_root()
    if not root.exists():
        logger.error("Project root not found: %s", root)
        return 1

    if not run_phase_1(root):
        logger.error("Aborting: Phase 1 failed")
        return 2
    if not run_phase_2(root):
        logger.error("Aborting: Phase 2 failed")
        return 3
    if not trigger_reload(root):
        logger.warning("Reload step had issues (data is still updated)")
    logger.info("Refresh pipeline completed")
    return 0


def run_scheduled() -> None:
    """Run refresh every REFRESH_INTERVAL_HOURS using APScheduler. First run is immediate."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError:
        logger.error("APScheduler not installed. Run: pip install apscheduler")
        sys.exit(1)

    logger.info("Running initial refresh now, then every %s hours", cfg.REFRESH_INTERVAL_HOURS)
    run_refresh()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_refresh,
        "interval",
        hours=cfg.REFRESH_INTERVAL_HOURS,
        id="refresh",
    )
    logger.info("Scheduler started: next refresh in %s hours", cfg.REFRESH_INTERVAL_HOURS)
    scheduler.start()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 5: Run data refresh (Phase 1 -> Phase 2 -> reload)."
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run refresh every REFRESH_INTERVAL_HOURS (APScheduler); otherwise run once.",
    )
    args = parser.parse_args()

    if args.schedule:
        run_scheduled()
    else:
        sys.exit(run_refresh())


if __name__ == "__main__":
    main()
