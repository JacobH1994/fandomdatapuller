#!/usr/bin/env python3
"""Steam catalog go-forward discovery (PRD §9.12a, Track B, part 1).

Scheduled, ephemeral-runner-safe (steam_discovery_poll.yml, daily):
calls `IStoreService/GetAppList` with `if_modified_since` set to the last
run's cutoff, classifies every new/updated app the same way Track A does
(collectors/steam_catalog_common.py — one classification implementation,
not two), and writes the result as a timestamped gzipped JSON file under
data/raw/steam_discovery/ — the same git-scraping pattern every other
scheduled collector in this project uses, for the same reason (the
runner has no persistent local research.db between runs).

**No separate state file for the if_modified_since cutoff** — read back
from this collector's own last committed raw snapshot's `captured_at`,
same pattern collectors/youtube_poll.py already uses for prior-live-state
recovery, rather than inventing a second persistence mechanism.
**First-ever run** (no prior snapshot): bootstraps to
BOOTSTRAP_LOOKBACK_DAYS back (see that constant's own comment for why
it's 2, not the wider window an earlier draft used) rather than
attempting a full historical sweep here — that's Track A's job entirely
(collectors/steam_catalog_backfill.py), Track B is go-forward only by
design.

**Deliberately does NOT decide "is this app newly discovered" itself** —
that requires knowing what's already in steam_release_history/
steam_release_cohort, which only the ETL loader can cheaply check
(against a real, already-rebuilt research.db). This script just reports
everything if_modified_since returned, classified; etl/load_snapshots.py's
load_one_steam_discovery_file() does the new-vs-updated split at load
time.

Usage:
    python collectors/steam_discovery_poll.py

Requires STEAM_API_KEY — see .env.example.
"""

from __future__ import annotations

import glob
import gzip
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from collectors.steam_catalog_common import RunErrors, classify_app, fetch_appdetails, paginate_app_list  # noqa: E402

RAW_DIR = REPO_ROOT / "data" / "raw" / "steam_discovery"
DOTENV_PATH = REPO_ROOT / ".env"
# Was 7 until measured live (2026-09-08): a 7-day if_modified_since window
# returns ~10,300 modified apps (vs. ~2,200 for 24h) — appdetails has no
# batching and no documented rate limit from Valve, but is known in
# practice to throttle hard, so 10,300 unbatched sequential calls could
# take 4+ hours on the very first scheduled run alone. 2 days keeps the
# bootstrap run in the same ballpark as steady-state daily volume rather
# than a one-time multi-hour spike, and costs only a marginal, acceptable
# loss: collectors/steam_catalog_backfill.py (Track A) independently
# classifies every app in the full catalog regardless of this window, so
# shrinking it only affects how early a pre-deployment release's cohort
# lifecycle-tracking starts, not whether it ever gets classified at all.
BOOTSTRAP_LOOKBACK_DAYS = 2


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def find_last_cutoff(raw_dir: Path) -> int:
    """Reads back this collector's own last raw snapshot's captured_at
    (converted to a Unix timestamp) to use as the next if_modified_since —
    no separate state file, same pattern collectors/youtube_poll.py uses.
    No prior snapshot at all: bootstrap to BOOTSTRAP_LOOKBACK_DAYS back."""
    files = sorted(glob.glob(str(raw_dir / "**" / "*.json.gz"), recursive=True))
    if not files:
        bootstrap = datetime.now(timezone.utc) - timedelta(days=BOOTSTRAP_LOOKBACK_DAYS)
        return int(bootstrap.timestamp())
    with gzip.open(files[-1], "rt") as f:
        snapshot = json.load(f)
    captured = datetime.strptime(snapshot["captured_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return int(captured.timestamp())


def main() -> int:
    load_dotenv(DOTENV_PATH)
    api_key = os.environ.get("STEAM_API_KEY")
    if not api_key:
        print("STEAM_API_KEY must be set in the environment", file=sys.stderr)
        return 1

    run_started_at = utcnow_iso()
    errors = RunErrors()
    cutoff = find_last_cutoff(RAW_DIR)
    print(f"[info] if_modified_since={cutoff} ({datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()})")

    results: list[dict] = []

    with httpx.Client() as client:
        for page in paginate_app_list(client, api_key, errors, if_modified_since=cutoff):
            for app in page:
                app_id = app["appid"]
                data = fetch_appdetails(client, app_id, errors, f"appdetails/{app_id}")
                if data is None:
                    continue
                fields = classify_app(data)
                results.append({"app_id": app_id, **fields})

    run_finished_at = utcnow_iso()
    status = "ok" if not errors.items else ("partial" if results else "failed")

    snapshot = {
        "captured_at": run_finished_at,
        "run_started_at": run_started_at,
        "run_finished_at": run_finished_at,
        "status": status,
        "if_modified_since": cutoff,
        "apps": results,
        "errors": errors.items,
    }

    now = datetime.now(timezone.utc)
    out_dir = RAW_DIR / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{now.strftime('%Y%m%dT%H%M%SZ')}.json.gz"
    with gzip.open(out_path, "wt") as f:
        json.dump(snapshot, f, separators=(",", ":"), sort_keys=True)

    print(f"wrote {out_path} (status={status}, apps_classified={len(results)})")
    return 0 if status != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
