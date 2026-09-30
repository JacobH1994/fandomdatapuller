#!/usr/bin/env python3
"""Pulls structured per-match broadcast channel data from LPDB v3 (docs/
liquipedia_lpdb_transition_plan.md Phase 4), built 2026-10-01 following a
direct request to evaluate LPDB as a source for official/co-stream channel
data, to refit this project's channel-tiering structure.

Confirmed live 2026-09-30: the `match` resource's `stream` field returns
real, structured broadcast-channel identifiers per match (e.g.
`{"twitch_en_1": "Fragbite", "twitch": "Fragbite"}` on a real Svenska
Cupen 2026 match) -- a fundamentally different, more precise signal than
`config/channels.yaml`'s manually-curated static list or
`etl/classify_broadcast_tier.py`'s `detected_costream` text-matching
heuristic against stream titles. This is ground truth ("this channel
broadcasts this specific match"), not an inference from title text.

**Why this collector is scoped to tier-1/2 tournaments, and samples rather
than exhaustively backfills, stated plainly**: LPDB has no per-title
"all matches" shortcut -- pulling stream data means querying the `match`
resource once per TOURNAMENT page (conditions=[[tournament::<page>]]), not
once per wiki. Counter-Strike alone already has 1,293 tier-1/2 tournament
pages in `tournaments_lpdb` -- exhaustively pulling match data for every
tier-1/2 tournament across all 23 titles would need several thousand
requests, far beyond what the confirmed 60/hour ceiling supports in any
reasonable window without risking the access LPDB granted. This collector
instead takes the N most recent tier-1/2 tournaments per title (default
20, `--tournaments-per-title`) -- the ones most likely to matter for
"which channels are we tracking NOW" -- and is safely re-runnable to
extend coverage backward over time, not a one-shot exhaustive pull.

Also pulls the `broadcasters` resource (commentary talent: casters/
analysts/hosts) for the same sampled tournaments -- a different signal
(who casts, not which channel airs it), kept in its own table
(`broadcasters_lpdb`).

**Every `channel_name` value written here is `ai_assisted_unreviewed`, not
`verified`** -- see `match_streams_lpdb`'s own schema comment. LPDB's
stream value is a Liquipedia template parameter (e.g. "Fragbite"), not
confirmed to be the exact lowercase Twitch LOGIN `config/channels.yaml`
requires as its match key. Live Twitch Helix verification (the same step
already used to curate the 5 titles currently in that file) is a separate,
required step before any of this data can promote a channel into
`config/channels.yaml` -- see `scripts/build_channel_candidates_from_lpdb.py`.

Usage:
    python collectors/liquipedia_lpdb_broadcasts.py                              # all active titles, top 20 tier-1/2 tournaments each
    python collectors/liquipedia_lpdb_broadcasts.py --titles valorant --tournaments-per-title 50
    python collectors/liquipedia_lpdb_broadcasts.py --max-requests 30
    python collectors/liquipedia_lpdb_broadcasts.py --status
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from etl.db import get_connection, seed_titles_and_aliases, utcnow_iso  # noqa: E402
from collectors.liquipedia_lpdb import (  # noqa: E402
    BASE_URL, DOTENV_PATH, MAX_REQUESTS_PER_RUN, PAGE_LIMIT, RequestBudget,
    load_dotenv, load_titles, print_budget_status,
)

DEFAULT_TOURNAMENTS_PER_TITLE = 20


def sampled_tournament_pages(conn, title_id: str, n: int) -> list[str]:
    """Most recent tier-1/2 tournaments for this title, already in
    tournaments_lpdb from collectors/liquipedia_lpdb.py -- reuses that
    data rather than re-querying LPDB for the tournament list."""
    rows = conn.execute(
        "SELECT liquipedia_page FROM tournaments_lpdb "
        "WHERE title_id=? AND tier IN ('1','2') AND start_date IS NOT NULL "
        "ORDER BY start_date DESC LIMIT ?",
        (title_id, n),
    ).fetchall()
    return [r[0] for r in rows]


def fetch_for_tournament(client: httpx.Client, budget: RequestBudget, resource: str, wiki: str, tournament_page: str, condition_field: str) -> list[dict]:
    if not budget.check():
        return []
    budget.wait_and_count()
    resp = client.get(resource, params={
        "wiki": wiki, "limit": PAGE_LIMIT,
        "conditions": f"[[{condition_field}::{tournament_page}]]",
    })
    if resp.status_code != 200:
        print(f"[warn] {wiki}/{resource} for {tournament_page!r}: HTTP {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
        return []
    body = resp.json()
    if body.get("error"):
        print(f"[warn] {wiki}/{resource} for {tournament_page!r}: API error: {body['error']}", file=sys.stderr)
        return []
    return body.get("result", [])


def upsert_match_streams(conn, title_id: str, wiki: str, match_rows: list[dict]) -> int:
    written = 0
    fetched_at = utcnow_iso()
    for row in match_rows:
        objectname = row.get("objectname")
        stream = row.get("stream") or {}
        if not objectname or not stream:
            continue
        for stream_key, channel_name in stream.items():
            if not channel_name:
                continue
            conn.execute(
                """
                INSERT INTO match_streams_lpdb
                    (title_id, liquipedia_wiki, match_objectname, tournament_pagename,
                     match_date, stream_key, channel_name, fetched_at, source, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'liquipedia_lpdb', 'ai_assisted_unreviewed')
                ON CONFLICT (liquipedia_wiki, match_objectname, stream_key) DO UPDATE SET
                    channel_name=excluded.channel_name, fetched_at=excluded.fetched_at
                """,
                (title_id, wiki, objectname, row.get("tournament"), row.get("date"), stream_key, channel_name, fetched_at),
            )
            written += 1
    return written


def upsert_broadcasters(conn, title_id: str, wiki: str, rows: list[dict]) -> int:
    written = 0
    fetched_at = utcnow_iso()
    for row in rows:
        objectname = row.get("objectname")
        if not objectname:
            continue
        conn.execute(
            """
            INSERT INTO broadcasters_lpdb
                (title_id, liquipedia_wiki, objectname, tournament_pagename, person_id, person_name,
                 position, language, nationality, broadcast_date, fetched_at, source, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'liquipedia_lpdb', 'verified')
            ON CONFLICT (liquipedia_wiki, objectname) DO UPDATE SET
                tournament_pagename=excluded.tournament_pagename, person_id=excluded.person_id,
                person_name=excluded.person_name, position=excluded.position,
                language=excluded.language, nationality=excluded.nationality,
                broadcast_date=excluded.broadcast_date, fetched_at=excluded.fetched_at
            """,
            (
                title_id, wiki, objectname, row.get("parent"), row.get("id"), row.get("name"),
                row.get("position"), row.get("language"), row.get("flag"), row.get("date"), fetched_at,
            ),
        )
        written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--titles", help="comma-separated title ids (default: all is_active titles with tournaments_lpdb data)")
    parser.add_argument("--tournaments-per-title", type=int, default=DEFAULT_TOURNAMENTS_PER_TITLE, help=f"most-recent tier-1/2 tournaments to sample per title (default {DEFAULT_TOURNAMENTS_PER_TITLE})")
    parser.add_argument("--max-requests", type=int, default=MAX_REQUESTS_PER_RUN, help=f"per-run safety cap (default {MAX_REQUESTS_PER_RUN})")
    parser.add_argument("--status", action="store_true", help="report shared rolling-window request usage and exit -- no API calls")
    args = parser.parse_args()

    if args.status:
        print_budget_status()
        return 0

    load_dotenv(DOTENV_PATH)
    import os

    api_key = os.environ.get("LIQUIPEDIA_API_KEY")
    contact = os.environ.get("LIQUIPEDIA_CONTACT_EMAIL", "")
    if not api_key:
        print("[fatal] LIQUIPEDIA_API_KEY not set (check .env)", file=sys.stderr)
        return 1

    all_titles = load_titles(REPO_ROOT / "config" / "titles.yaml")
    if args.titles:
        wanted = set(args.titles.split(","))
        titles = [t for t in all_titles if t["id"] in wanted]
    else:
        titles = [t for t in all_titles if t.get("is_active")]

    conn = get_connection()
    seed_titles_and_aliases(conn, all_titles)

    headers = {
        "Authorization": f"Apikey {api_key}",
        "User-Agent": f"FandomDataPuller/1.0 (research; contact: {contact})",
        "Accept-Encoding": "gzip",
    }
    budget = RequestBudget(args.max_requests)
    started_at = utcnow_iso()
    streams_written = 0
    broadcasters_written = 0
    errors: list[str] = []

    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0) as client:
        for t in titles:
            wiki = t.get("liquipedia_wiki")
            if not wiki:
                continue
            pages = sampled_tournament_pages(conn, t["id"], args.tournaments_per_title)
            if not pages:
                print(f"[info] {t['id']}: no tier-1/2 tournaments in tournaments_lpdb yet -- run collectors/liquipedia_lpdb.py first")
                continue
            title_streams = 0
            title_broadcasters = 0
            for page in pages:
                if not budget.check():
                    errors.append(f"{t['id']}: stopped early, request budget exhausted (covered {pages.index(page)}/{len(pages)} sampled tournaments)")
                    break
                match_rows = fetch_for_tournament(client, budget, "match", wiki, page, "tournament")
                title_streams += upsert_match_streams(conn, t["id"], wiki, match_rows)
                if not budget.check():
                    errors.append(f"{t['id']}: stopped early after match pull, request budget exhausted")
                    break
                broadcaster_rows = fetch_for_tournament(client, budget, "broadcasters", wiki, page, "parent")
                title_broadcasters += upsert_broadcasters(conn, t["id"], wiki, broadcaster_rows)
            conn.commit()
            streams_written += title_streams
            broadcasters_written += title_broadcasters
            print(
                f"[info] {t['id']}: {title_streams} stream rows, {title_broadcasters} broadcaster rows "
                f"from {len(pages)} sampled tournaments — {budget.count}/{budget.max_requests} requests used",
                flush=True,
            )

    finished_at = utcnow_iso()
    status = "ok" if not errors else "partial"
    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('liquipedia_lpdb_broadcasts', NULL, ?, ?, ?, ?, ?)
        """,
        (started_at, finished_at, status, streams_written + broadcasters_written, "; ".join(errors[:20]) or None),
    )
    conn.commit()
    conn.close()

    print(f"wrote {streams_written} stream rows, {broadcasters_written} broadcaster rows (status={status}, requests_used={budget.count}/{budget.max_requests})")
    if errors:
        print(f"errors: {'; '.join(errors[:5])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
