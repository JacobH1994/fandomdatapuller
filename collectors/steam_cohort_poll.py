#!/usr/bin/env python3
"""Steam release-cohort lifecycle polling (PRD §9.12a, Track B, part 2).

Scheduled, ephemeral-runner-safe (steam_cohort_poll.yml, daily). Unlike
every other scheduled collector in this project, this one genuinely needs
to READ existing state (which app_ids are due for a poll today) before it
can do anything — so its workflow runs `python etl/load_snapshots.py`
FIRST to rebuild a working research.db from committed history (same
pattern scripts/local_refresh.sh already uses), and only then invokes
this script, which queries that freshly-rebuilt DB directly for
`steam_release_cohort` rows with `next_poll_due <= today`.

Reuses collectors/steam_poll.py's fetch_player_count/
parse_player_count_response — the query mechanism (GetNumberOfCurrentPlayers,
one key-authenticated call per appid) is identical to the 11 curated
esports titles' current-player collector; only WHICH app_ids get polled,
and on what schedule, differs.

**Same unbackfillable property as every other live-poll table in this
project**: a missed day during a cohort title's tracked window is
permanent loss — this is exactly why Track B's lifecycle polling runs on
a schedule (CLAUDE.md's "one rule," extended) rather than being left as
an on-demand script like Track A's historical backfill.

Writes results BOTH directly into the local (freshly-rebuilt) research.db
(steam_cohort_player_counts, plus updating steam_release_cohort's
last_polled_at/next_poll_due) AND as a raw JSON snapshot file under
data/raw/steam_cohort/ — the DB write makes today's run self-consistent
(so a title polled once already this run isn't polled twice), and the raw
file is what makes the whole history reproducible from git alone, the
same as every other live-data table here.

**Tapering schedule**: daily for the first ~90 days since discovery,
weekly after that out to ~365 days (tracking_window_end), then the app
drops out of active polling (next_poll_due left as-is — this script simply
stops selecting it once tracking_window_end has passed, no separate
"done" flag needed since next_poll_due > today is naturally
never-selected again once the window has closed).

If steam_release_cohort is empty (Track B discovery hasn't found/loaded
any new apps yet), this is a clean no-op — same handling as
collectors/youtube_poll.py's no-channels-configured case.

Usage:
    python collectors/steam_cohort_poll.py

Requires STEAM_API_KEY — see .env.example. Requires research.db to
already reflect current steam_release_cohort state (run
etl/load_snapshots.py first if running locally against fresh raw files).
"""

from __future__ import annotations

import gzip
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from etl.db import get_connection  # noqa: E402
from collectors.steam_poll import RunErrors, fetch_player_count  # noqa: E402

RAW_DIR = REPO_ROOT / "data" / "raw" / "steam_cohort"
DOTENV_PATH = REPO_ROOT / ".env"

DAILY_PHASE_DAYS = 90
DAILY_INTERVAL = timedelta(days=1)
WEEKLY_INTERVAL = timedelta(days=7)


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


def next_interval(discovered_at: datetime, now: datetime) -> timedelta:
    age = now - discovered_at
    return DAILY_INTERVAL if age < timedelta(days=DAILY_PHASE_DAYS) else WEEKLY_INTERVAL


def main() -> int:
    load_dotenv(DOTENV_PATH)
    api_key = os.environ.get("STEAM_API_KEY")
    if not api_key:
        print("STEAM_API_KEY must be set in the environment", file=sys.stderr)
        return 1

    run_started_at = utcnow_iso()
    errors = RunErrors()
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = get_connection()
    due = conn.execute(
        """
        SELECT app_id, discovered_at, tracking_window_end FROM steam_release_cohort
        WHERE next_poll_due <= ? AND tracking_window_end > ?
        """,
        (today, today),
    ).fetchall()

    if not due:
        print("[info] no cohort app_ids due for polling today — clean no-op")
        conn.close()
        return 0

    print(f"[info] {len(due)} app_id(s) due for polling")

    checked_at = utcnow_iso()
    results: list[dict] = []

    with httpx.Client() as client:
        for app_id, discovered_at_raw, _tracking_window_end in due:
            count = fetch_player_count(client, app_id, api_key, errors, str(app_id))
            results.append({"app_id": app_id, "player_count": count, "checked_at": checked_at})

            discovered_at = datetime.strptime(discovered_at_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            interval = next_interval(discovered_at, now)
            next_due = (now + interval).strftime("%Y-%m-%dT%H:%M:%SZ")

            conn.execute(
                "UPDATE steam_release_cohort SET last_polled_at = ?, next_poll_due = ? WHERE app_id = ?",
                (checked_at, next_due, app_id),
            )
            if count is not None:
                conn.execute(
                    """
                    INSERT INTO steam_cohort_player_counts (app_id, captured_at, player_count, source, confidence)
                    VALUES (?, ?, ?, 'steam_api', 'verified')
                    ON CONFLICT (app_id, captured_at) DO NOTHING
                    """,
                    (app_id, checked_at, count),
                )
            conn.commit()

    run_finished_at = utcnow_iso()
    succeeded = sum(1 for r in results if r["player_count"] is not None)
    status = "ok" if not errors.items else ("partial" if succeeded else "failed")

    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('steam_cohort_poll', NULL, ?, ?, ?, ?, ?)
        """,
        (run_started_at, run_finished_at, status, succeeded, "; ".join(e["message"] for e in errors.items[:20]) or None),
    )
    conn.commit()
    conn.close()

    snapshot = {
        "captured_at": run_finished_at,
        "run_started_at": run_started_at,
        "run_finished_at": run_finished_at,
        "status": status,
        "apps": results,
        "errors": errors.items,
    }

    out_dir = RAW_DIR / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{now.strftime('%Y%m%dT%H%M%SZ')}.json.gz"
    with gzip.open(out_path, "wt") as f:
        json.dump(snapshot, f, separators=(",", ":"), sort_keys=True)

    print(f"wrote {out_path} (status={status}, due={len(due)}, succeeded={succeeded})")
    return 0 if status != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
