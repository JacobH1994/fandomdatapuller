#!/usr/bin/env python3
"""Pulls pro player bio/career data from LPDB v3 (docs/
liquipedia_lpdb_transition_plan.md Phase 4), built 2026-10-01 following a
direct request for a player database to support cohort analysis (age,
career duration, regionalization trends) as a playerbase proxy, extending
the streamer/community cohort work already done for post 3.

Two LPDB resources, confirmed live 2026-09-30:
  - `player`: one row per pro player -- nationality, region, birthdate,
    current team, status (Active/Retired/Inactive), total earnings, and a
    per-year earnings breakdown. This is the bio/career-summary layer.
  - `squadplayer`: one row per ROSTER STINT (a player joining/leaving one
    specific team) -- has real `joindate`/`leavedate`, which `player`
    alone can't reconstruct (it only has a player's CURRENT team). This is
    the actual source for career-duration and team-hopping/
    regionalization cohort analysis, not `player.status` alone.

Writes to `players_lpdb` / `player_earnings_by_year_lpdb` / `squadplayers_lpdb`
-- new tables, `etl/schema.sql`. Shares collectors/liquipedia_lpdb.py's
request-budget machinery (imported, not reimplemented) so this collector's
usage composes correctly against the same real 60/hour ceiling -- running
both collectors does not double the effective rate limit.

**Known, deliberate gap: the shared `fighters` wiki (tekken/street_fighter/
mortal_kombat/guilty_gear) is skipped entirely by this collector.** Checked
live (2026-09-30): the `player` resource has no per-title `game` field the
way `tournament` does -- instead `extradata.games` is a LIST of every game
a player has competed in (a real Mortal Kombat player sampled also listed
Street Fighter, Injustice, and 2XKO). Attributing one player row to a
single title_id would misrepresent genuinely multi-game careers, and no
safe per-title split is possible with data pulled so far. Left unscoped
rather than guessed -- a real Phase 4 follow-up, not silently done wrong.

Usage:
    python collectors/liquipedia_lpdb_players.py                      # all non-fighters-wiki active titles
    python collectors/liquipedia_lpdb_players.py --titles dota2,valorant
    python collectors/liquipedia_lpdb_players.py --max-requests 30
    python collectors/liquipedia_lpdb_players.py --status              # no API calls, shared budget status
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from etl.db import get_connection, seed_titles_and_aliases, utcnow_iso  # noqa: E402
from collectors.liquipedia_lpdb import (  # noqa: E402
    BASE_URL, DOTENV_PATH, GAME_CODES_BY_TITLE, MAX_REQUESTS_PER_RUN,
    PAGE_LIMIT, RequestBudget, load_dotenv, load_titles, print_budget_status,
    _normalize_lpdb_date,
)

# Titles on the shared `fighters` wiki -- see module docstring for why
# they're skipped by this collector specifically.
FIGHTERS_WIKI_TITLES = set(GAME_CODES_BY_TITLE.keys())


OFFSET_STATE_PATH = REPO_ROOT / "data" / "cache" / "liquipedia_lpdb" / "tournament_offsets.json"
_OFFSET_DONE = "done"


def _load_offset_state() -> dict:
    if not OFFSET_STATE_PATH.is_file():
        return {}
    try:
        return json.loads(OFFSET_STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_offset_state(state: dict) -> None:
    OFFSET_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_STATE_PATH.write_text(json.dumps(state, indent=2))


def fetch_resource(client: httpx.Client, budget: RequestBudget, resource: str, wiki: str) -> list[dict]:
    """Same resume-by-offset pattern as collectors/liquipedia_lpdb.py's
    fetch_tournaments -- shares its OFFSET_STATE_PATH (distinct keys, e.g.
    'player:dota2', so no collision with the tournament collector's own
    'dota2|' keys) so a budget-interrupted pull resumes instead of
    re-paying for already-fetched pages."""
    results: list[dict] = []
    resume_key = f"{resource}:{wiki}"
    offset_state = _load_offset_state()
    stored = offset_state.get(resume_key)
    if stored == _OFFSET_DONE:
        return results
    offset = stored if isinstance(stored, int) else 0

    while True:
        if not budget.check():
            break
        budget.wait_and_count()
        resp = client.get(resource, params={"wiki": wiki, "limit": PAGE_LIMIT, "offset": offset})
        if resp.status_code != 200:
            print(f"[warn] {wiki}/{resource}: HTTP {resp.status_code} at offset={offset}: {resp.text[:200]}", file=sys.stderr)
            break
        body = resp.json()
        if body.get("error"):
            print(f"[warn] {wiki}/{resource}: API error at offset={offset}: {body['error']}", file=sys.stderr)
            break
        page = body.get("result", [])
        results.extend(page)
        if len(page) < PAGE_LIMIT:
            offset_state[resume_key] = _OFFSET_DONE
            _save_offset_state(offset_state)
            break
        offset += PAGE_LIMIT
        offset_state[resume_key] = offset
        _save_offset_state(offset_state)
    return results


def upsert_player(conn, title_id: str, wiki: str, row: dict) -> bool:
    pagename = row.get("pagename")
    if not pagename:
        return False
    cur = conn.execute(
        """
        INSERT INTO players_lpdb
            (title_id, liquipedia_wiki, liquipedia_page, player_id, name,
             nationality, nationality2, nationality3, region, birthdate,
             deathdate, team_pagename, status, total_earnings,
             extradata_json, fetched_at, source, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'liquipedia_lpdb', 'verified')
        ON CONFLICT (liquipedia_wiki, liquipedia_page) DO UPDATE SET
            title_id=excluded.title_id, player_id=excluded.player_id, name=excluded.name,
            nationality=excluded.nationality, nationality2=excluded.nationality2,
            nationality3=excluded.nationality3, region=excluded.region,
            birthdate=excluded.birthdate, deathdate=excluded.deathdate,
            team_pagename=excluded.team_pagename, status=excluded.status,
            total_earnings=excluded.total_earnings, extradata_json=excluded.extradata_json,
            fetched_at=excluded.fetched_at
        RETURNING id
        """,
        (
            title_id, wiki, pagename, row.get("id"), row.get("name"),
            row.get("nationality"), row.get("nationality2"), row.get("nationality3"),
            row.get("region"), _normalize_lpdb_date(row.get("birthdate")),
            _normalize_lpdb_date(row.get("deathdate")), row.get("teampagename"),
            row.get("status"), row.get("earnings"),
            json.dumps(row.get("extradata")) if row.get("extradata") else None,
            utcnow_iso(),
        ),
    )
    player_row_id = cur.fetchone()[0]

    conn.execute("DELETE FROM player_earnings_by_year_lpdb WHERE player_row_id=?", (player_row_id,))
    earnings_by_year = row.get("earningsbyyear") or {}
    for year_str, amount in earnings_by_year.items():
        try:
            year = int(year_str)
        except (TypeError, ValueError):
            continue
        conn.execute(
            "INSERT INTO player_earnings_by_year_lpdb (player_row_id, year, earnings) VALUES (?, ?, ?)",
            (player_row_id, year, amount),
        )
    return True


def upsert_squadplayer(conn, title_id: str, wiki: str, row: dict) -> bool:
    objectname = row.get("objectname")
    team_pagename = row.get("pagename")
    if not objectname or not team_pagename:
        return False
    conn.execute(
        """
        INSERT INTO squadplayers_lpdb
            (title_id, liquipedia_wiki, objectname, team_pagename, player_id, player_link,
             nationality, position, role, new_team_pagename, status,
             join_date, leave_date, inactive_date, fetched_at, source, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'liquipedia_lpdb', 'verified')
        ON CONFLICT (liquipedia_wiki, objectname) DO UPDATE SET
            title_id=excluded.title_id, team_pagename=excluded.team_pagename,
            player_id=excluded.player_id, player_link=excluded.player_link,
            nationality=excluded.nationality, position=excluded.position, role=excluded.role,
            new_team_pagename=excluded.new_team_pagename, status=excluded.status,
            join_date=excluded.join_date, leave_date=excluded.leave_date,
            inactive_date=excluded.inactive_date, fetched_at=excluded.fetched_at
        """,
        (
            title_id, wiki, objectname, team_pagename, row.get("id"), row.get("link"),
            row.get("nationality"), row.get("position"), row.get("role"),
            row.get("newteam"), row.get("status"),
            _normalize_lpdb_date(row.get("joindate")), _normalize_lpdb_date(row.get("leavedate")),
            _normalize_lpdb_date(row.get("inactivedate")), utcnow_iso(),
        ),
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--titles", help="comma-separated title ids (default: all is_active, non-fighters-wiki titles)")
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
        titles = [t for t in all_titles if t.get("is_active") and t["id"] not in FIGHTERS_WIKI_TITLES]

    skipped_fighters = [t["id"] for t in titles if t["id"] in FIGHTERS_WIKI_TITLES]
    titles = [t for t in titles if t["id"] not in FIGHTERS_WIKI_TITLES]
    if skipped_fighters:
        print(f"[info] skipping fighters-wiki titles (see module docstring): {', '.join(skipped_fighters)}")

    conn = get_connection()
    seed_titles_and_aliases(conn, all_titles)

    headers = {
        "Authorization": f"Apikey {api_key}",
        "User-Agent": f"FandomDataPuller/1.0 (research; contact: {contact})",
        "Accept-Encoding": "gzip",
    }
    budget = RequestBudget(args.max_requests)
    started_at = utcnow_iso()
    players_written = 0
    squadplayers_written = 0
    errors: list[str] = []

    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0) as client:
        for t in titles:
            wiki = t.get("liquipedia_wiki")
            if not wiki:
                continue
            if not budget.check():
                errors.append(f"{t['id']}: skipped, request budget exhausted for this run")
                continue

            player_rows = fetch_resource(client, budget, "player", wiki)
            p_written = sum(1 for row in player_rows if upsert_player(conn, t["id"], wiki, row))
            players_written += p_written
            conn.commit()

            squad_rows = fetch_resource(client, budget, "squadplayer", wiki)
            s_written = sum(1 for row in squad_rows if upsert_squadplayer(conn, t["id"], wiki, row))
            squadplayers_written += s_written
            conn.commit()

            print(
                f"[info] {t['id']}: {p_written} players, {s_written} roster stints from wiki '{wiki}' "
                f"— {budget.count}/{budget.max_requests} requests used",
                flush=True,
            )

    finished_at = utcnow_iso()
    status = "ok" if not errors else "partial"
    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('liquipedia_lpdb_players', NULL, ?, ?, ?, ?, ?)
        """,
        (started_at, finished_at, status, players_written + squadplayers_written, "; ".join(errors[:20]) or None),
    )
    conn.commit()
    conn.close()

    print(f"wrote {players_written} players, {squadplayers_written} roster stints (status={status}, requests_used={budget.count}/{budget.max_requests})")
    if errors:
        print(f"errors: {'; '.join(errors[:5])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
