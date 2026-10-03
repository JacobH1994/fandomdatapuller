#!/usr/bin/env python3
"""Pulls per-tournament, per-team/-player final standings from LPDB v3's
`placement` resource (docs/liquipedia_lpdb_transition_plan.md's own
long-flagged gap, "per-tournament participant lists" -- never pulled for
any title before this, built 2026-10-03 following a direct request to make
elite-tier *player* filtering possible, not just elite-tier *team*
filtering: players_lpdb/squadplayers_lpdb have a player's bio and
team/roster history, but nothing linking a player to WHICH specific
tournaments they competed in, or at what tier -- tier lives only on
tournaments_lpdb. `placement` is that link.

**Confirmed live 2026-10-03** (against a real completed tournament,
StarLadder StarSeries Fall 2026, wiki=counterstrike, tournament page
`StarLadder/StarSeries/2026/Fall`, cross-checked with a second,
solo-opponent-mode tournament on wiki=starcraft2):

  - One row per team/solo opponent's final standing in a tournament --
    `placement.parent` is the page-slug tournament reference (confirmed
    identical format to tournaments_lpdb.liquipedia_page, e.g.
    "StarLadder/StarSeries/2026/Fall"), NOT `placement.tournament` (a
    human-readable display name, "StarLadder StarSeries Fall 2026") --
    the exact same `tournament`-vs-`parent` trap that bit
    collectors/liquipedia_lpdb_broadcasts.py for the `match` resource,
    confirmed to independently apply here too, not assumed from that
    precedent.
  - `liquipediatier` is present directly on `placement` rows (not just on
    `tournament`), same clean digit-string format -- lets this collector
    filter by tier via `conditions` without a prior tournaments_lpdb
    lookup, unlike collectors/liquipedia_lpdb_broadcasts.py's
    sampled-tournament-pages approach.
  - `game` is also present per-row (e.g. "cs2") on both wikis sampled --
    unlike `player`/`squadplayer` (see collectors/liquipedia_lpdb_players.py's
    own docstring: no per-title game field there), this means the shared
    `fighters` wiki should be splittable by title here using the same
    GAME_CODES_BY_TITLE `conditions` pattern collectors/liquipedia_lpdb.py's
    tournament pull already uses. **NOT yet confirmed live against the
    fighters wiki specifically** -- the shared 60/hour budget was
    concurrently exhausted by scripts/lpdb_overnight_sync.py (running
    unattended in the background) before that specific check could run
    this session. Treat FIGHTERS_WIKI_TITLES below as a provisional,
    not-yet-verified inclusion -- re-check the first real fighters-wiki
    pull's row count against expectations before trusting it blindly.
  - `opponenttype` ('team' / 'solo', both confirmed live) is the reliable
    team-vs-solo signal -- `mode` (e.g. "team", "1v1") is NOT: a real
    StarCraft II show-match row had opponenttype='team' but mode='1v1'
    (mode describes match FORMAT, not this row's opponent shape).
  - `placement` itself is sometimes a tie-range ("7-8") and sometimes an
    empty string (seen on a non-standings show-match row) -- stored as
    TEXT, never parsed as an integer.
  - `prizemoney` (opponent-level) and `individualprizemoney` (per-player
    share) are both populated on every real standings row sampled --
    structured fields, not a template to parse, same finding the
    transition plan already documented for the `tournament` resource's
    own prizepool field.
  - **THE key finding this collector exists to confirm**: `opponentplayers`
    carries one "pN"/"cN" slot per player/coach, each with an identity
    value (the "pN" key itself, e.g. "Yuurih") and a separate "pNdn"
    display name (e.g. "yuurih") that can differ in case. The IDENTITY
    value -- not the display name -- was checked directly against a real
    sample of players_lpdb rows for counter_strike and matched
    `liquipedia_page` exactly, case-sensitive, for all 5 players checked
    (Yuurih, KSCERATO, ZywOo, Insani, B1t). **Players are individually
    identifiable per placement row.** Elite-tier player filtering (tier IN
    ('1','2')) from this data is real, not just elite-tier team filtering.
  - **Date-format gotcha, confirmed live, DIFFERENT from every other
    `_lpdb` table pulled so far**: this resource's null-date sentinel is
    "0000-01-01 00:00:00" (a full datetime), not the plain "0000-01-01"
    tournaments_lpdb/players_lpdb use. collectors/liquipedia_lpdb.py's own
    `_normalize_lpdb_date()` does exact-string equality against the
    date-only sentinel and would silently miss this -- this collector does
    its own `_normalize_placement_date()` (prefix check) instead. Imported
    `_normalize_lpdb_date` is deliberately NOT used on this resource's
    date fields.
  - A real per-wiki volume check (`query=count::objectname`, unconditioned)
    returned **217,843** placement rows for wiki=counterstrike alone --
    confirming this resource, like `tournament`/`player`, supports a cheap
    bulk paginated pull with NO per-tournament condition needed (unlike
    `match`/`broadcasters`, which collectors/liquipedia_lpdb_broadcasts.py
    had to sample tournament-by-tournament because no such bulk query
    exists for those resources). At PAGE_LIMIT=1000/page that's ~218
    requests for counter_strike's unconditioned total alone -- this
    collector instead filters server-side to `--tiers` (default "1,2")
    via `conditions`, since elite-tier filtering is the whole point and it
    cuts volume substantially; the real tier-1/2-filtered count per title
    was NOT measured this session (budget ran out before that specific
    query could be sent -- RequestBudget's own check blocked it for free,
    costing zero requests). Measure it early in any real sweep.

**Design: full-paginate-to-completion per title, resumable across runs --
NOT a fixed-N-tournaments sample like collectors/liquipedia_lpdb_broadcasts.py.**
That collector samples because no cheap "all matches for a wiki" query
exists for `match`/`broadcasters`. `placement` is different: it supports
the same offset-paginated bulk-per-wiki pull `tournament`/`player` already
use, so full coverage is genuinely reachable the same way those two
reached it (collectors/liquipedia_lpdb.py's own fetch_tournaments /
collectors/liquipedia_lpdb_players.py's fetch_resource) -- a multi-run,
budget-interrupted, resumable sweep via OFFSET_STATE_PATH, not a one-shot.
Reuses that same persisted offset file (distinct resume keys,
"placement:<wiki>:<title_id>", so shared-fighters-wiki sub-games and this
collector's own runs never collide with the tournament/player collectors'
keys in the same file).

Writes to `placements_lpdb` / `placement_participants_lpdb` (etl/schema.sql,
see those tables' own comments for the full field-shape writeup above,
condensed). Shares collectors/liquipedia_lpdb.py's request-budget machinery
(imported, not reimplemented) -- composes correctly against the real
60/hour ceiling alongside every other LPDB-facing script in this repo,
including scripts/lpdb_overnight_sync.py running concurrently.

Usage:
    python collectors/liquipedia_lpdb_placements.py                       # all active titles with tournaments_lpdb data, tier 1-2 only
    python collectors/liquipedia_lpdb_placements.py --titles counter_strike,dota2
    python collectors/liquipedia_lpdb_placements.py --tiers 1,2,3          # widen the server-side tier filter
    python collectors/liquipedia_lpdb_placements.py --max-requests 40
    python collectors/liquipedia_lpdb_placements.py --status               # no API calls -- shared budget status
    python collectors/liquipedia_lpdb_placements.py --refresh              # ignore persisted per-wiki pagination offsets, re-pull from offset 0
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from etl.db import get_connection, seed_titles_and_aliases, utcnow_iso  # noqa: E402
from collectors.liquipedia_lpdb import (  # noqa: E402
    BASE_URL, DOTENV_PATH, GAME_CODES_BY_TITLE, MAX_REQUESTS_PER_RUN,
    PAGE_LIMIT, RequestBudget, load_dotenv, load_titles, print_budget_status,
)

DEFAULT_TIERS = ["1", "2"]

# See module docstring: `placement` carries a per-row `game` field like
# `tournament` does (confirmed live on counterstrike/starcraft2 samples),
# so shared-fighters-wiki titles are provisionally INCLUDED here using the
# same GAME_CODES_BY_TITLE split the tournament collector uses -- unlike
# collectors/liquipedia_lpdb_players.py, which excludes them because
# `player`/`squadplayer` have no such field. NOT yet confirmed live against
# the fighters wiki specifically for THIS resource -- verify the first real
# pull's row counts look sane before trusting this blindly.
FIGHTERS_WIKI_TITLES = set(GAME_CODES_BY_TITLE.keys())

OFFSET_STATE_PATH = REPO_ROOT / "data" / "cache" / "liquipedia_lpdb" / "tournament_offsets.json"
_OFFSET_DONE = "done"

_SLOT_RE = re.compile(r"^([pc])(\d+)$")  # matches bare identity keys ("p1", "c1"), not their "dn"/"flag"/"faction"/"role1" siblings


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


def _normalize_placement_date(value: str | None) -> str | None:
    """`placement`'s own null-date sentinel is "0000-01-01 00:00:00" (a full
    datetime), NOT the plain "0000-01-01" tournaments_lpdb/players_lpdb use
    -- confirmed live, see module docstring. Prefix check, not exact
    equality, on purpose."""
    if not value or value.startswith("0000-01-01"):
        return None
    return value


def build_conditions(tiers: list[str], game_codes: list[str] | None) -> str:
    tier_clause = " OR ".join(f"[[liquipediatier::{t}]]" for t in tiers)
    if not game_codes:
        return tier_clause
    game_clause = " OR ".join(f"[[game::{g}]]" for g in game_codes)
    return f"({tier_clause}) AND ({game_clause})"


def fetch_placements(
    client: httpx.Client, budget: RequestBudget, wiki: str, conditions: str, resume_key: str,
) -> list[dict]:
    """Same resume-by-offset pattern as collectors/liquipedia_lpdb.py's
    fetch_tournaments / collectors/liquipedia_lpdb_players.py's
    fetch_resource -- shares OFFSET_STATE_PATH under a distinct key so a
    budget-interrupted pull resumes instead of re-paying for already-fetched
    pages."""
    results: list[dict] = []
    offset_state = _load_offset_state()
    stored = offset_state.get(resume_key)
    if stored == _OFFSET_DONE:
        return results
    offset = stored if isinstance(stored, int) else 0

    while True:
        if not budget.check():
            break
        budget.wait_and_count()
        resp = client.get("placement", params={
            "wiki": wiki, "limit": PAGE_LIMIT, "offset": offset, "conditions": conditions,
        })
        if resp.status_code != 200:
            print(f"[warn] {wiki}/placement: HTTP {resp.status_code} at offset={offset}: {resp.text[:200]}", file=sys.stderr)
            break
        body = resp.json()
        if body.get("error"):
            print(f"[warn] {wiki}/placement: API error at offset={offset}: {body['error']}", file=sys.stderr)
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


def upsert_placement(conn, title_id: str, wiki: str, row: dict) -> int | None:
    """Returns the written placements_lpdb row id, or None if this LPDB
    record had no objectname to key on and was skipped."""
    objectname = row.get("objectname")
    if not objectname:
        return None
    cur = conn.execute(
        """
        INSERT INTO placements_lpdb
            (title_id, liquipedia_wiki, objectname, tournament_pagename, tournament_display_name,
             tier, game, placement, opponent_type, opponent_name, opponent_template,
             prize_money, individual_prize_money, prize_pool_index, mode,
             match_date, start_date, extradata_json, fetched_at, source, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'liquipedia_lpdb', 'verified')
        ON CONFLICT (liquipedia_wiki, objectname) DO UPDATE SET
            title_id=excluded.title_id, tournament_pagename=excluded.tournament_pagename,
            tournament_display_name=excluded.tournament_display_name, tier=excluded.tier,
            game=excluded.game, placement=excluded.placement, opponent_type=excluded.opponent_type,
            opponent_name=excluded.opponent_name, opponent_template=excluded.opponent_template,
            prize_money=excluded.prize_money, individual_prize_money=excluded.individual_prize_money,
            prize_pool_index=excluded.prize_pool_index, mode=excluded.mode,
            match_date=excluded.match_date, start_date=excluded.start_date,
            extradata_json=excluded.extradata_json, fetched_at=excluded.fetched_at
        RETURNING id
        """,
        (
            title_id, wiki, objectname, row.get("parent"), row.get("tournament"),
            row.get("liquipediatier"), row.get("game"), row.get("placement"),
            row.get("opponenttype"), row.get("opponentname"), row.get("opponenttemplate"),
            row.get("prizemoney"), row.get("individualprizemoney"), row.get("prizepoolindex"),
            row.get("mode"), _normalize_placement_date(row.get("date")),
            _normalize_placement_date(row.get("startdate")),
            json.dumps(row.get("extradata")) if row.get("extradata") else None,
            utcnow_iso(),
        ),
    )
    placement_row_id = cur.fetchone()[0]

    conn.execute("DELETE FROM placement_participants_lpdb WHERE placement_row_id=?", (placement_row_id,))
    opponent_players = row.get("opponentplayers") or {}
    slots = sorted({m.group(0) for key in opponent_players if (m := _SLOT_RE.match(key))})
    for slot in slots:
        prefix, _ = _SLOT_RE.match(slot).groups()
        player_page = opponent_players.get(slot)
        if not player_page:
            continue
        conn.execute(
            """
            INSERT INTO placement_participants_lpdb
                (placement_row_id, slot, kind, player_page, display_name, nationality, faction, role_label)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                placement_row_id, slot, "coach" if prefix == "c" else "player", player_page,
                opponent_players.get(f"{slot}dn"), opponent_players.get(f"{slot}flag"),
                opponent_players.get(f"{slot}faction"), opponent_players.get(f"{slot}role1"),
            ),
        )
    return placement_row_id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--titles", help="comma-separated title ids (default: all is_active titles with tournaments_lpdb data)")
    parser.add_argument("--tiers", default=",".join(DEFAULT_TIERS), help=f"comma-separated liquipediatier values to pull, server-side filtered (default {','.join(DEFAULT_TIERS)})")
    parser.add_argument("--max-requests", type=int, default=MAX_REQUESTS_PER_RUN, help=f"per-run safety cap (default {MAX_REQUESTS_PER_RUN})")
    parser.add_argument("--status", action="store_true", help="report shared rolling-window request usage and exit -- no API calls")
    parser.add_argument("--refresh", action="store_true", help="ignore persisted per-wiki/title pagination offsets and re-pull from offset 0")
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

    tiers = [t.strip() for t in args.tiers.split(",") if t.strip()]

    all_titles = load_titles(REPO_ROOT / "config" / "titles.yaml")
    if args.titles:
        wanted = set(args.titles.split(","))
        titles = [t for t in all_titles if t["id"] in wanted]
    else:
        titles = [t for t in all_titles if t.get("is_active")]

    conn = get_connection()
    seed_titles_and_aliases(conn, all_titles)

    if args.refresh:
        offset_state = _load_offset_state()
        for t in titles:
            offset_state.pop(f"placement:{t.get('liquipedia_wiki')}:{t['id']}", None)
        _save_offset_state(offset_state)

    headers = {
        "Authorization": f"Apikey {api_key}",
        "User-Agent": f"FandomDataPuller/1.0 (research; contact: {contact})",
        "Accept-Encoding": "gzip",
    }
    budget = RequestBudget(args.max_requests)
    started_at = utcnow_iso()
    placements_written = 0
    participants_written = 0
    errors: list[str] = []

    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0) as client:
        for t in titles:
            wiki = t.get("liquipedia_wiki")
            if not wiki:
                continue
            if not budget.check():
                errors.append(f"{t['id']}: skipped, request budget exhausted for this run")
                continue

            game_codes = GAME_CODES_BY_TITLE.get(t["id"]) if t["id"] in FIGHTERS_WIKI_TITLES else None
            conditions = build_conditions(tiers, game_codes)
            resume_key = f"placement:{wiki}:{t['id']}"

            rows = fetch_placements(client, budget, wiki, conditions, resume_key)
            title_placements = 0
            title_participants = 0
            for row in rows:
                placement_row_id = upsert_placement(conn, t["id"], wiki, row)
                if placement_row_id is None:
                    continue
                title_placements += 1
                opponent_players = row.get("opponentplayers") or {}
                title_participants += sum(1 for k in opponent_players if _SLOT_RE.match(k))
            conn.commit()
            placements_written += title_placements
            participants_written += title_participants
            print(
                f"[info] {t['id']}: {title_placements} placement rows, {title_participants} participant slots "
                f"from wiki '{wiki}' (tiers={','.join(tiers)}) — {budget.count}/{budget.max_requests} requests used",
                flush=True,
            )

    finished_at = utcnow_iso()
    status = "ok" if not errors else "partial"
    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('liquipedia_lpdb_placements', NULL, ?, ?, ?, ?, ?)
        """,
        (started_at, finished_at, status, placements_written + participants_written, "; ".join(errors[:20]) or None),
    )
    conn.commit()
    conn.close()

    print(f"wrote {placements_written} placement rows, {participants_written} participant slots (status={status}, requests_used={budget.count}/{budget.max_requests})")
    if errors:
        print(f"errors: {'; '.join(errors[:5])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
