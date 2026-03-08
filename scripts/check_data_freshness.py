#!/usr/bin/env python3
"""
Check if the app is using fresh data: read last_scraped from data/schemes.json
and report whether it's from today, yesterday, or older.
Run from project root: python scripts/check_data_freshness.py
Exit code: 0 if data is from today (UTC), 1 otherwise.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    for path in [ROOT / "data" / "schemes.json", ROOT / "api" / "schemes.json"]:
        if not path.exists():
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            meta = data.get("meta", {})
            last = meta.get("last_scraped", "").strip()
            if not last:
                print(f"{path.name}: no last_scraped in meta")
                return 1
            # Parse ISO timestamp (e.g. 2026-03-08T06:41:47Z)
            try:
                if last.endswith("Z"):
                    ts = datetime.fromisoformat(last.replace("Z", "+00:00"))
                else:
                    ts = datetime.fromisoformat(last)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except ValueError:
                print(f"{path.name}: invalid last_scraped format: {last!r}")
                return 1
            now = datetime.now(timezone.utc)
            age = now - ts
            days = age.days
            hours = age.seconds // 3600
            if days == 0:
                if hours == 0:
                    mins = age.seconds // 60
                    print(f"Data source: {path.relative_to(ROOT)}")
                    print(f"Last scraped: {last} ({mins} minutes ago) — fresh (today)")
                    return 0
                print(f"Data source: {path.relative_to(ROOT)}")
                print(f"Last scraped: {last} ({hours}h ago today) — fresh (today)")
                return 0
            elif days == 1:
                print(f"Data source: {path.relative_to(ROOT)}")
                print(f"Last scraped: {last} (yesterday) — not today's data")
            else:
                print(f"Data source: {path.relative_to(ROOT)}")
                print(f"Last scraped: {last} ({days} days ago) — not fresh")
            return 1
        except Exception as e:
            print(f"{path}: error: {e}", file=sys.stderr)
    print("No schemes.json found in data/ or api/")
    return 1


if __name__ == "__main__":
    sys.exit(main())
