#!/usr/bin/env python3
"""Wikipedia article pageviews (PRD §9.17), for the English-language
fandom decomposition subsystem (see
analysis/fandom_region_decomposition.py's module docstring) — an
independent game-fandom signal (informational engagement, not
viewership), and a secondary input to that module's diurnal-pattern
correlation technique.

**Official Wikimedia Pageviews REST API, confirmed live 2026-09-12**:
documented (wikimedia.org/api/rest_v1), rate-limited but explicitly
positioned for exactly this kind of programmatic/research use — not the
undocumented-endpoint situation `collectors/steam_review_history_pull.py`
has to flag for its own source. Same discipline this project already
applies to Liquipedia: descriptive User-Agent, respect the documented
rate limit, don't re-fetch unchanged historical data.

**On-demand, not scheduled — daily pageview counts are fixed historical
fact once a day has closed**, the same reasoning `collectors/
liquipedia.py` and `collectors/steam_catalog_backfill.py` already give
for their own on-demand cadence (CLAUDE.md's "one rule" doesn't apply
here). Resumable: for each (subject, project, article), only fetches
days after the latest date already in `wikipedia_pageview_snapshots` —
achieves the same "don't re-request unchanged data" outcome Liquipedia's
own local wikitext cache does, via the database's own natural key instead
of a separate cache directory (simpler, and just as correct, since a
past day's pageview count never changes after Wikimedia finalizes it).

Reads `config/fandom_decomposition_subjects.yaml` for which subjects have
`wikipedia_articles` configured — a subject with none is skipped, not an
error.

Usage:
    python collectors/wikipedia_pageviews_pull.py
    python collectors/wikipedia_pageviews_pull.py --subjects apex_legends,pubg
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from etl.db import get_connection, utcnow_iso  # noqa: E402
from analysis.fandom_region_decomposition import load_subjects  # noqa: E402

USER_AGENT = (
    "FandomDataPuller/1.0 "
    "(https://github.com/JacobH1994/fandomdatapuller; jacob.harrison1994@gmail.com)"
)
PAGEVIEWS_URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/all-access/all-agents/{article}/daily/{start}/{end}"

# The API's own earliest coverage (Wikimedia's published pageview
# collection start) — used as the default start when a subject/article
# has no prior rows yet. A request reaching before real data exists
# simply returns fewer items than asked for, not an error.
EARLIEST_COVERAGE = date(2015, 7, 1)
MIN_INTERVAL = 0.5  # seconds — well within the documented per-client ceiling, proactive pacing same as every other collector in this project
MAX_RETRIES = 3


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fetch_with_retry(client: httpx.Client, url: str) -> dict | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(url, timeout=30)
        except httpx.RequestError as exc:
            if attempt == MAX_RETRIES:
                print(f"[error] request failed after {MAX_RETRIES} attempts: {exc}", file=sys.stderr)
                return None
            time.sleep(2**attempt)
            continue

        if resp.status_code == 404:
            return {"items": []}  # no data in this range for this article — not an error
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == MAX_RETRIES:
                print(f"[error] status {resp.status_code} after {MAX_RETRIES} attempts", file=sys.stderr)
                return None
            time.sleep(2**attempt)
            continue
        if resp.status_code >= 400:
            print(f"[error] status {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
            return None
        return resp.json()
    return None


def fetch_pageviews(client: httpx.Client, project: str, article: str, start: date, end: date) -> list[dict]:
    url = PAGEVIEWS_URL.format(
        project=project, article=article,
        start=start.strftime("%Y%m%d00"), end=end.strftime("%Y%m%d00"),
    )
    time.sleep(MIN_INTERVAL)
    body = _fetch_with_retry(client, url)
    return (body or {}).get("items", [])


def upsert_pageviews(conn, subject_id: str, items: list[dict]) -> int:
    fetched_at = utcnow_iso()
    written = 0
    for item in items:
        conn.execute(
            """
            INSERT INTO wikipedia_pageview_snapshots
                (subject_id, wiki_project, article_title, date, views, fetched_at, source, confidence)
            VALUES (?, ?, ?, ?, ?, ?, 'wikimedia_pageviews_api', 'verified')
            ON CONFLICT (subject_id, wiki_project, article_title, date) DO UPDATE SET
                views = excluded.views, fetched_at = excluded.fetched_at
            """,
            (
                subject_id, item["project"], item["article"],
                item["timestamp"][:8],  # 'YYYYMMDD00' -> 'YYYYMMDD'
                item["views"], fetched_at,
            ),
        )
        written += 1
    conn.commit()
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--subjects", help="comma-separated subject ids (default: every subject with wikipedia_articles configured)")
    args = parser.parse_args()

    subjects = load_subjects()
    if args.subjects:
        wanted = set(args.subjects.split(","))
        subjects = {sid: s for sid, s in subjects.items() if sid in wanted}

    conn = get_connection()
    started_at = utcnow_iso()
    today = utcnow().date() - timedelta(days=1)  # yesterday: today's own pageview count isn't finalized yet
    total_written = 0

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for subject_id, subject in subjects.items():
            for wp in subject.get("wikipedia_articles", []):
                project, article = wp["project"], wp["title"]
                latest = conn.execute(
                    "SELECT MAX(date) FROM wikipedia_pageview_snapshots WHERE subject_id = ? AND wiki_project = ? AND article_title = ?",
                    (subject_id, project, article),
                ).fetchone()[0]
                start = (datetime.strptime(latest, "%Y%m%d").date() + timedelta(days=1)) if latest else EARLIEST_COVERAGE
                if start > today:
                    print(f"[info] {subject_id}/{project}/{article}: already current")
                    continue

                items = fetch_pageviews(client, project, article, start, today)
                written = upsert_pageviews(conn, subject_id, items)
                total_written += written
                print(f"[info] {subject_id}/{project}/{article}: {written} day(s) written ({start} to {today})")

    finished_at = utcnow_iso()
    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('wikipedia_pageviews_pull', NULL, ?, ?, 'ok', ?, NULL)
        """,
        (started_at, finished_at, total_written),
    )
    conn.commit()
    conn.close()
    print(f"wrote {total_written} pageview row(s) total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
