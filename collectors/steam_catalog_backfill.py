#!/usr/bin/env python3
"""Steam catalog historical backfill (PRD §9.12a, Track A).

One-time, patient sweep of the ENTIRE Steam catalog (100K+ apps) —
release date, genres (including Indie), categories (including VR
support), developer/publisher, and recommendations.total as a rough
relevance signal — stored permanently in `steam_release_history`.

**On-demand, not scheduled — modeled directly on collectors/liquipedia.py**:
release metadata is fixed historical fact, not something that decays the
way live viewer/player counts do (CLAUDE.md's "one rule" doesn't apply
here), so there's no urgency and no reason to run this on a clock. Writes
straight to research.db via etl/db.py:get_connection(), not the raw-file/
git-commit pattern the live collectors use.

**Resumable, same as liquipedia.py**: any app_id already present in
steam_release_history is skipped by default — a rerun (or a resume after
an interrupted run) only fetches what's actually new, not the whole
catalog again. Pass --refresh to force re-fetching and re-classifying
apps already present (e.g. to pick up a corrected genre/category after
Valve's own data changes).

**Expect this to run for 1-2 weeks in the background**, per its own
design: the full catalog is 100K+ apps, appdetails has no batching (one
call per app), and Steam's appdetails endpoint is known to rate-limit
fairly aggressively if hit too fast — this script deliberately paces
itself at APPDETAILS_MIN_INTERVAL seconds between calls (conservative,
not tuned against a documented limit since Valve doesn't publish one for
this specific endpoint) rather than trying to go as fast as possible and
risk getting throttled or blocked mid-crawl. Safe to interrupt (Ctrl-C)
and resume later — nothing is lost, the next run picks up exactly where
this one left off via the same "already in steam_release_history" check.

Usage:
    python collectors/steam_catalog_backfill.py                # crawl, or resume: only new apps
    python collectors/steam_catalog_backfill.py --refresh       # also re-fetch/re-classify known apps
    python collectors/steam_catalog_backfill.py --max-apps 500  # process at most this many new apps this run (for testing, or splitting a session into chunks)

Requires STEAM_API_KEY — see .env.example.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from etl.db import get_connection  # noqa: E402
from collectors.steam_catalog_common import (  # noqa: E402
    RunErrors,
    classify_app,
    fetch_appdetails,
    paginate_app_list,
)

DOTENV_PATH = REPO_ROOT / ".env"
APPDETAILS_MIN_INTERVAL = 1.5  # seconds — conservative, appdetails isn't documented but is known to rate-limit aggressively


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_dotenv(path: Path) -> None:
    """Minimal .env loader, same approach as the other collectors — real
    environment variables always win."""
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


def upsert_release(conn, app_id: int, fields: dict) -> None:
    conn.execute(
        """
        INSERT INTO steam_release_history
            (app_id, name, app_type, release_date_raw, release_date, is_released,
             genres, is_indie, categories, has_vr_support, vr_only,
             developers, publishers, recommendations_total, low_relevance_flag,
             fetched_at, source, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'steam_store_api', 'verified')
        ON CONFLICT (app_id) DO UPDATE SET
            name=excluded.name, app_type=excluded.app_type,
            release_date_raw=excluded.release_date_raw, release_date=excluded.release_date,
            is_released=excluded.is_released, genres=excluded.genres, is_indie=excluded.is_indie,
            categories=excluded.categories, has_vr_support=excluded.has_vr_support,
            vr_only=excluded.vr_only, developers=excluded.developers, publishers=excluded.publishers,
            recommendations_total=excluded.recommendations_total,
            low_relevance_flag=excluded.low_relevance_flag, fetched_at=excluded.fetched_at
        """,
        (
            app_id, fields["name"], fields["app_type"], fields["release_date_raw"], fields["release_date"],
            fields["is_released"], fields["genres"], fields["is_indie"], fields["categories"],
            fields["has_vr_support"], fields["vr_only"], fields["developers"], fields["publishers"],
            fields["recommendations_total"], fields["low_relevance_flag"], utcnow_iso(),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="force re-fetch/re-classify apps already in steam_release_history")
    parser.add_argument("--max-apps", type=int, default=None, help="stop after processing this many NEW apps this run (default: no limit)")
    args = parser.parse_args()

    load_dotenv(DOTENV_PATH)
    api_key = os.environ.get("STEAM_API_KEY")
    if not api_key:
        print("STEAM_API_KEY must be set in the environment", file=sys.stderr)
        return 1

    conn = get_connection()
    started_at = utcnow_iso()
    errors = RunErrors()

    known_app_ids: set[int] = set()
    if not args.refresh:
        known_app_ids = {row[0] for row in conn.execute("SELECT app_id FROM steam_release_history").fetchall()}
        print(f"[info] {len(known_app_ids)} app(s) already classified — resuming, skipping those")

    rows_written = 0
    apps_seen = 0
    last_call = 0.0

    with httpx.Client() as client:
        for page in paginate_app_list(client, api_key, errors):
            for app in page:
                apps_seen += 1
                app_id = app["appid"]
                if not args.refresh and app_id in known_app_ids:
                    continue
                if args.max_apps is not None and rows_written >= args.max_apps:
                    print(f"[info] reached --max-apps {args.max_apps}, stopping (resumable — rerun to continue)")
                    conn.commit()
                    _log_run(conn, started_at, "partial", rows_written, errors)
                    conn.close()
                    return 0

                elapsed = time.monotonic() - last_call
                if elapsed < APPDETAILS_MIN_INTERVAL:
                    time.sleep(APPDETAILS_MIN_INTERVAL - elapsed)
                last_call = time.monotonic()

                data = fetch_appdetails(client, app_id, errors, f"appdetails/{app_id}")
                if data is None:
                    continue  # logged by fetch_appdetails; no store data for this app, not fatal

                fields = classify_app(data)
                upsert_release(conn, app_id, fields)
                conn.commit()  # short-lived transaction per app, matching liquipedia.py's per-page commit pattern
                rows_written += 1

                if rows_written % 25 == 0:
                    print(f"[info] {rows_written} app(s) classified so far ({apps_seen} seen in GetAppList so far)", flush=True)

    status = "ok" if not errors.items else ("partial" if rows_written else "failed")
    _log_run(conn, started_at, status, rows_written, errors)
    conn.close()

    print(f"wrote {rows_written} app classification(s) (status={status}, apps_seen={apps_seen}, errors={len(errors.items)})")
    return 0 if status != "failed" else 1


def _log_run(conn, started_at: str, status: str, rows_written: int, errors: RunErrors) -> None:
    finished_at = utcnow_iso()
    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('steam_catalog_backfill', NULL, ?, ?, ?, ?, ?)
        """,
        (started_at, finished_at, status, rows_written, "; ".join(e["message"] for e in errors.items[:20]) or None),
    )
    conn.commit()


if __name__ == "__main__":
    sys.exit(main())
