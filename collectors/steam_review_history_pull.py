#!/usr/bin/env python3
"""Steam review-language history (PRD §9.17), for the English-language
fandom decomposition subsystem (see
analysis/fandom_region_decomposition.py's module docstring) — an
independent playerbase signal (owners who write reviews, not people
watching streams), on the same `en`-ambiguous language axis as Twitch but
a completely separate population.

**Endpoint status, checked live 2026-09-12**: `store.steampowered.com/
appreviews/<appid>` is Valve's own first-party server (it powers their
own store page) but UNDOCUMENTED — not covered by the Steam Web API's
official terms (steamcommunity.com/dev/apiterms). Included per explicit
user sign-off: low request volume, cached (see resumability below), and
flagged here plainly rather than treated as a documented guarantee the
way `steam_release_history`'s `steam_store_api` source is.

**One-time/resumable crawl, not a scheduled poll — confirmed live that
individual reviews carry `timestamp_created`/`timestamp_updated`
alongside `language`**, which is fixed historical fact (a review's
creation date never changes) exactly like `steam_release_history`, not a
live-state snapshot the way Twitch/YouTube/Steam-player-count are
(CLAUDE.md's "one rule" doesn't apply here). Walks `filter=recent`
(newest-first) via cursor pagination and stops as soon as it reaches a
`recommendationid` already in `steam_review_history` for that app — a
rerun only fetches reviews posted since the last crawl, mirroring
`steam_catalog_backfill.py`'s own "already known, skip" resumability.
Pass `--refresh` to instead walk a subject's entire review history
regardless of what's already stored (e.g. after widening what fields this
collector stores).

Only `language` + `timestamp_created` + the review's own id are stored —
no review text or vote counts, since nothing this subsystem asks needs
them (same "don't build speculatively" reasoning
`platform_viewership_below_threshold`'s own schema comment gives for a
different table).

Reads `config/fandom_decomposition_subjects.yaml` for which subjects have
`steam_app_id` configured — a subject without one is skipped, not an
error.

Usage:
    python collectors/steam_review_history_pull.py
    python collectors/steam_review_history_pull.py --subjects apex_legends,pubg
    python collectors/steam_review_history_pull.py --refresh
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from etl.db import get_connection, utcnow_iso  # noqa: E402
from analysis.fandom_region_decomposition import load_subjects  # noqa: E402
from collectors.steam_catalog_common import RateLimiter  # noqa: E402

USER_AGENT = (
    "FandomDataPuller/1.0 "
    "(https://github.com/JacobH1994/fandomdatapuller; jacob.harrison1994@gmail.com)"
)
APPREVIEWS_URL = "https://store.steampowered.com/appreviews/{app_id}"
NUM_PER_PAGE = 100
MAX_RETRIES = 3

# Undocumented endpoint, no published rate limit -- same conservative,
# proactive-pacing posture collectors/steam_catalog_common.py already
# takes with appdetails (also undocumented in this respect), not a
# confirmed published term.
_limiter = RateLimiter(min_interval=1.5)


def _fetch_page(client: httpx.Client, app_id: int, cursor: str) -> dict | None:
    params = {
        "json": 1, "filter": "recent", "language": "all",
        "purchase_type": "all", "num_per_page": NUM_PER_PAGE, "cursor": cursor,
    }
    for attempt in range(1, MAX_RETRIES + 1):
        _limiter.wait()
        try:
            resp = client.get(APPREVIEWS_URL.format(app_id=app_id), params=params, timeout=30)
        except httpx.RequestError as exc:
            if attempt == MAX_RETRIES:
                print(f"[error] app {app_id}: request failed after {MAX_RETRIES} attempts: {exc}", file=sys.stderr)
                return None
            time.sleep(2**attempt)
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == MAX_RETRIES:
                print(f"[error] app {app_id}: status {resp.status_code} after {MAX_RETRIES} attempts", file=sys.stderr)
                return None
            time.sleep(2**attempt)
            continue
        if resp.status_code >= 400:
            print(f"[error] app {app_id}: status {resp.status_code}", file=sys.stderr)
            return None
        return resp.json()
    return None


def crawl_reviews(client: httpx.Client, app_id: int, known_ids: set[str], *, stop_at_known: bool) -> list[dict]:
    """Walks filter=recent from newest to oldest. Stops when reviews run
    out, the cursor stops advancing (Steam's own end-of-results signal),
    or (unless --refresh) a review already in known_ids is reached --
    everything older than that was already crawled in a prior run."""
    reviews: list[dict] = []
    cursor = "*"
    while True:
        body = _fetch_page(client, app_id, cursor)
        if body is None or not body.get("success"):
            break
        page = body.get("reviews", [])
        if not page:
            break
        for review in page:
            review_id = review["recommendationid"]
            if stop_at_known and review_id in known_ids:
                return reviews
            reviews.append(review)
        next_cursor = body.get("cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    return reviews


def upsert_reviews(conn, subject_id: str, app_id: int, reviews: list[dict]) -> int:
    fetched_at = utcnow_iso()
    for review in reviews:
        conn.execute(
            """
            INSERT INTO steam_review_history
                (subject_id, app_id, review_id, language, timestamp_created, fetched_at, source, confidence)
            VALUES (?, ?, ?, ?, ?, ?, 'steam_appreviews_undocumented', 'verified')
            ON CONFLICT (app_id, review_id) DO NOTHING
            """,
            (subject_id, app_id, review["recommendationid"], review["language"], review["timestamp_created"], fetched_at),
        )
    conn.commit()
    return len(reviews)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--subjects", help="comma-separated subject ids (default: every subject with steam_app_id configured)")
    parser.add_argument("--refresh", action="store_true", help="walk each subject's entire review history, not just reviews newer than what's already stored")
    args = parser.parse_args()

    subjects = load_subjects()
    if args.subjects:
        wanted = set(args.subjects.split(","))
        subjects = {sid: s for sid, s in subjects.items() if sid in wanted}

    conn = get_connection()
    started_at = utcnow_iso()
    total_written = 0

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for subject_id, subject in subjects.items():
            app_id = subject.get("steam_app_id")
            if not app_id:
                continue
            known_ids: set[str] = set()
            if not args.refresh:
                known_ids = {
                    row[0] for row in
                    conn.execute("SELECT review_id FROM steam_review_history WHERE app_id = ?", (app_id,)).fetchall()
                }
            reviews = crawl_reviews(client, app_id, known_ids, stop_at_known=not args.refresh)
            written = upsert_reviews(conn, subject_id, app_id, reviews)
            total_written += written
            print(f"[info] {subject_id} (app {app_id}): {written} new review(s)")

    finished_at = utcnow_iso()
    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('steam_review_history_pull', NULL, ?, ?, 'ok', ?, NULL)
        """,
        (started_at, finished_at, total_written),
    )
    conn.commit()
    conn.close()
    print(f"wrote {total_written} review(s) total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
