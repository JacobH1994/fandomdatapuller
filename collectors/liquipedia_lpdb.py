#!/usr/bin/env python3
"""Liquipedia LPDB v3 connector (Phase 1, docs/liquipedia_lpdb_transition_plan.md).

Built following formal LPDB access approval (2026-09-30) and a 9-request
Phase 0 probe against the live API that confirmed the access mechanics and
answered the plan's open questions with real data — see that doc for the
full writeup. Summary of what that means for this script specifically:

  - Auth: `Authorization: Apikey <key>` header, not a query param. Base URL
    `https://api.liquipedia.net/api/v3/`. Every request needs a `wiki`
    param. GET only, gzip required (per Liquipedia's own API terms).
  - Rate limit: 60 requests/hour on this project's tier, confirmed live.
    This script tracks its own request count and hard-stops well under
    that (MAX_REQUESTS_PER_RUN) rather than trusting the server's own
    429 handling alone -- leaves headroom for anything else using the
    same key concurrently, and makes a ban structurally difficult to
    trigger by accident.
  - Pagination (limit=1000/page) makes a full-history pull cheap: a wiki
    with a few thousand tournaments costs single-digit requests, not one
    request per tournament the way the old wikitext-per-page approach did.
  - `liquipediatier` comes back as a clean, uniform digit STRING on every
    wiki tested -- no per-wiki S-Tier/A-Tier label to normalize the way
    `_normalize_tier()` (collectors/liquipedia.py) has to.
  - Per-team prize payouts ARE available as structured data via the
    `placement` resource (confirmed against a real completed tournament),
    but this script does NOT pull placements for every tournament --
    that's O(tournaments) requests, impractical within the rate budget
    for a full backfill. Left for a separate, deliberately-scoped pass
    (see docs/liquipedia_lpdb_transition_plan.md Phase 2).
  - No currency field exists anywhere in the schema -- confirmed by
    inspecting full field lists on real records, not assumed. `currency`
    stays NULL on every row this script writes.
  - The shared `fighters` wiki's `game` field cleanly separates
    sub-games -- GAME_CODES_BY_TITLE below was derived from a live
    `groupby=game` query (2026-09-30), not guessed, and deliberately
    excludes `sfxt` (Street Fighter X Tekken) from street_fighter's list,
    carrying forward the existing crossover-exclusion policy.
  - Tournament records include BOTH historical and future/projected
    events (a real 2028 Major with status="unconfirmed" showed up in
    testing) -- this script does not filter those out. That's what makes
    etl/forecast_event_windows.py possible: the forward-looking data is
    just... in here, once this collector has run.

Writes to `tournaments_lpdb`, NOT `tournaments` -- a deliberately separate
staging table (see schema.sql's own comment on why: the live table's
UNIQUE constraint doesn't include `source`, so a blind insert would
either collide with or require changing the MediaWiki-sourced table).
collectors/liquipedia.py is untouched by this script, still the source
for the live `tournaments` table, per the transition plan's own Phase 1
scope ("build alongside the current one").

Usage:
    python collectors/liquipedia_lpdb.py                       # all active titles
    python collectors/liquipedia_lpdb.py --titles dota2,valorant
    python collectors/liquipedia_lpdb.py --max-requests 40      # override the per-run safety cap
    python collectors/liquipedia_lpdb.py --status               # no API calls -- just reports rolling-window usage and reset ETA

Rate-limit tracking: `data/cache/liquipedia_lpdb/request_log.json` (gitignored,
disposable) persists the timestamp of every real request made, across runs --
not just within one process. Without this, two runs of this script minutes
apart could each individually respect MAX_REQUESTS_PER_RUN while still
together blowing through the server's real 60/hour ceiling, since a fresh
process has no memory of what a previous run already spent. RequestBudget
loads this log on startup, drops entries older than the 60-minute window, and
computes the real remaining budget from that -- not just this run's own
counter. `--status` reads the same log read-only to answer "how much budget
is left, and when does more free up" without spending any of it.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from etl.db import get_connection, seed_titles_and_aliases, utcnow_iso  # noqa: E402

TITLES_CONFIG = REPO_ROOT / "config" / "titles.yaml"
DOTENV_PATH = REPO_ROOT / ".env"
REQUEST_LOG_PATH = REPO_ROOT / "data" / "cache" / "liquipedia_lpdb" / "request_log.json"

BASE_URL = "https://api.liquipedia.net/api/v3/"
PAGE_LIMIT = 1000  # documented max; makes a full-history pull cost ~1 request per ~1000 tournaments
MIN_INTERVAL = 2.0  # seconds between requests -- well under the 60/hour cap even on a long run
SERVER_RATE_LIMIT = 60  # confirmed live (2026-09-30): 60 requests/hour on this project's tier
RATE_WINDOW_SECONDS = 3600
MAX_REQUESTS_PER_RUN = 50  # per-run cap; ALSO bounded by real rolling-window usage -- see RequestBudget

# Derived live via `GET tournament?wiki=fighters&query=game&groupby=game ASC&limit=1000`
# (2026-09-30), cross-checked against config/titles.yaml's own liquipedia_category
# generation lists -- not guessed. `sfxt` (Street Fighter X Tekken) is deliberately
# excluded from street_fighter: a genuine crossover product, not a generation, per
# the same policy collectors/liquipedia.py's docstring already documents.
GAME_CODES_BY_TITLE: dict[str, list[str]] = {
    "tekken": ["t4", "t5", "t6", "t7", "t8", "ttt", "ttt2"],
    "street_fighter": ["sfii", "sfa2", "sfa3", "sfiii", "sfiv", "sfv", "sf6"],
    "mortal_kombat": ["mk3", "mk9", "mkx", "mk11", "mk1"],
    "guilty_gear": ["ggxx", "ggxrd", "ggst"],
}

# Same list this project already uses for the MediaWiki-sourced table
# (collectors/liquipedia.py) -- kept identical on purpose so the two
# tables' region values are at least comparable where both use it. LPDB's
# OWN region1 field uses a different scheme entirely (see schema.sql's
# comment on tournaments_lpdb.region) and is stored separately/as-is,
# not run through this dict -- this dict exists only as a fallback for
# constructing `region` in case that's useful downstream, but as shipped
# this script just stores LPDB's own region1 value directly (see below).


def load_dotenv(path: Path) -> None:
    """Minimal .env loader, matching collectors/twitch_poll.py's own helper."""
    import os

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


def load_titles(path: Path) -> list[dict]:
    with open(path) as f:
        config = yaml.safe_load(f)
    return config.get("titles", [])


def _load_request_log(path: Path = REQUEST_LOG_PATH) -> list[float]:
    """Loads persisted request timestamps (UTC epoch seconds), pruned to the
    last RATE_WINDOW_SECONDS -- real cross-run history, not just this
    process's own count."""
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    now = time.time()
    return [t for t in raw if now - t < RATE_WINDOW_SECONDS]


def _reset_eta(timestamps: list[float]) -> str | None:
    """When the oldest request in the current rolling window will age out,
    freeing up a budget slot -- None if the window is empty."""
    if not timestamps:
        return None
    oldest = min(timestamps)
    return datetime.fromtimestamp(oldest + RATE_WINDOW_SECONDS, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def print_budget_status(path: Path = REQUEST_LOG_PATH) -> None:
    """Read-only report: how much of the real 60/hour window is already
    spent (across ALL runs, not just the current process), and when more
    frees up. Makes no API calls."""
    timestamps = _load_request_log(path)
    used = len(timestamps)
    remaining = max(0, SERVER_RATE_LIMIT - used)
    print(f"LPDB requests used in the trailing {RATE_WINDOW_SECONDS // 60} minutes: {used}/{SERVER_RATE_LIMIT}")
    print(f"Remaining in that window: {remaining}")
    eta = _reset_eta(timestamps)
    if eta:
        print(f"Oldest request in-window ages out at: {eta} (frees one slot)")
    else:
        print("No requests logged in the current window — full budget available.")


class RequestBudget:
    """Tracks request count against BOTH this run's own MAX_REQUESTS_PER_RUN
    cap AND the real server-side rolling 60/hour window (persisted across
    runs in REQUEST_LOG_PATH) -- a per-run counter alone can't stop two
    runs minutes apart from together exceeding the server's actual limit,
    since a fresh process has no memory of what a previous run already
    spent. A hard stop, not just a rate limiter, since a ban here is
    explicitly described as escalating from temporary to permanent."""

    def __init__(self, max_requests: int, log_path: Path = REQUEST_LOG_PATH) -> None:
        self.max_requests = max_requests
        self.log_path = log_path
        self.timestamps = _load_request_log(log_path)
        self.count = 0  # requests made by this process only, for the per-run cap
        self._last_call = 0.0

    def check(self) -> bool:
        if self.count >= self.max_requests:
            print(
                f"[warn] hit the {self.max_requests}-request safety cap for this run — "
                "stopping early. Re-run later (or pass --max-requests) to continue.",
                file=sys.stderr,
            )
            return False
        if len(self.timestamps) >= SERVER_RATE_LIMIT:
            eta = _reset_eta(self.timestamps)
            print(
                f"[warn] rolling-window usage is at the confirmed {SERVER_RATE_LIMIT}/hour limit "
                f"(tracked across all runs, not just this one) — stopping to avoid a ban. "
                f"Next slot frees at {eta}. Run with --status to check anytime.",
                file=sys.stderr,
            )
            return False
        return True

    def wait_and_count(self) -> None:
        elapsed = time.monotonic() - self._last_call
        remaining = MIN_INTERVAL - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_call = time.monotonic()
        self.count += 1
        now = time.time()
        self.timestamps.append(now)
        self.timestamps = [t for t in self.timestamps if now - t < RATE_WINDOW_SECONDS]
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text(json.dumps(self.timestamps))


OFFSET_STATE_PATH = REPO_ROOT / "data" / "cache" / "liquipedia_lpdb" / "tournament_offsets.json"
_OFFSET_DONE = "done"  # sentinel: this wiki+conditions key's pagination reached a natural end (page < PAGE_LIMIT), not a budget cutoff


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


def fetch_tournaments(
    client: httpx.Client, budget: RequestBudget, wiki: str, game_codes: list[str] | None,
    resume_key: str | None = None,
) -> list[dict]:
    """Paginates GET /v3/tournament for one wiki (optionally filtered to a
    set of `game` codes, for shared wikis), stopping when a page returns
    fewer than PAGE_LIMIT results or the request budget runs out.

    If `resume_key` is given, resumes from the last offset persisted in
    OFFSET_STATE_PATH for that key rather than always starting at 0 --
    added so the overnight sync orchestrator (scripts/lpdb_overnight_sync.py)
    doesn't re-pay for pages a prior, budget-cut-off run already fetched
    and upserted. A key already marked _OFFSET_DONE is skipped entirely
    (returns immediately) -- its pagination already reached a natural end,
    re-querying it would cost a request for zero new rows every time."""
    results: list[dict] = []
    offset_state = _load_offset_state() if resume_key else {}
    stored = offset_state.get(resume_key) if resume_key else None
    if stored == _OFFSET_DONE:
        return results
    offset = stored if isinstance(stored, int) else 0

    conditions = None
    if game_codes:
        conditions = " OR ".join(f"[[game::{g}]]" for g in game_codes)

    while True:
        if not budget.check():
            break
        params: dict = {"wiki": wiki, "limit": PAGE_LIMIT, "offset": offset}
        if conditions:
            params["conditions"] = conditions
        budget.wait_and_count()
        resp = client.get("tournament", params=params)
        if resp.status_code != 200:
            print(f"[warn] {wiki}: HTTP {resp.status_code} at offset={offset}: {resp.text[:200]}", file=sys.stderr)
            break
        body = resp.json()
        if body.get("error"):
            print(f"[warn] {wiki}: API error at offset={offset}: {body['error']}", file=sys.stderr)
            break
        page = body.get("result", [])
        results.extend(page)
        if len(page) < PAGE_LIMIT:
            if resume_key:
                offset_state[resume_key] = _OFFSET_DONE
                _save_offset_state(offset_state)
            break
        offset += PAGE_LIMIT
        if resume_key:
            offset_state[resume_key] = offset
            _save_offset_state(offset_state)
    return results


LPDB_NULL_DATE = "0000-01-01"  # LPDB's own sentinel for "date field never set on this page" -- confirmed live (2026-09-30) on ~1.9% of league_of_legends rows (e.g. "Oceanic Challenger Series 2016 Split 2 Promotion"). Not a real date; normalized to NULL on write so it can't silently poison a date-range query (see LPDB_NULL_DATE's use in etl/forecast_event_windows.py's own guard, belt-and-suspenders with this one).


def _normalize_lpdb_date(value: str | None) -> str | None:
    return None if value == LPDB_NULL_DATE else value


def upsert_tournament(conn, title_id: str, wiki: str, row: dict) -> bool:
    """Returns True if a row was actually written, False if this LPDB
    record had no pagename/name to key on and was skipped -- so callers
    can count real writes instead of attempted ones."""
    locations = row.get("locations") or {}
    pagename = row.get("pagename") or row.get("name")
    if not pagename:
        return False
    conn.execute(
        """
        INSERT INTO tournaments_lpdb
            (title_id, liquipedia_wiki, liquipedia_page, name, tier, game, status,
             prize_pool, currency, start_date, end_date, country, region,
             region_confidence, team_number, fetched_at, source, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, 'liquipedia_lpdb_native', ?, ?, 'liquipedia_lpdb', 'verified')
        ON CONFLICT (liquipedia_wiki, liquipedia_page) DO UPDATE SET
            title_id=excluded.title_id, name=excluded.name, tier=excluded.tier,
            game=excluded.game, status=excluded.status, prize_pool=excluded.prize_pool,
            start_date=excluded.start_date, end_date=excluded.end_date,
            country=excluded.country, region=excluded.region,
            team_number=excluded.team_number, fetched_at=excluded.fetched_at
        """,
        (
            title_id, wiki, pagename, row.get("name"), row.get("liquipediatier"),
            row.get("game"), row.get("status"), row.get("prizepool"),
            _normalize_lpdb_date(row.get("startdate")), _normalize_lpdb_date(row.get("enddate")),
            locations.get("country1"), locations.get("region1"),
            row.get("participantsnumber"), utcnow_iso(),
        ),
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--titles", help="comma-separated title ids (default: all is_active titles)")
    parser.add_argument("--max-requests", type=int, default=MAX_REQUESTS_PER_RUN, help=f"safety cap (default {MAX_REQUESTS_PER_RUN}, confirmed limit is 60/hour)")
    parser.add_argument("--status", action="store_true", help="report rolling-window request usage and reset ETA, then exit -- makes no API calls")
    parser.add_argument("--refresh", action="store_true", help="ignore persisted per-wiki pagination offsets (OFFSET_STATE_PATH) and re-pull from offset 0")
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

    all_titles = load_titles(TITLES_CONFIG)
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
    rows_written = 0
    errors: list[str] = []

    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0) as client:
        for t in titles:
            wiki = t.get("liquipedia_wiki")
            if not wiki:
                continue
            game_codes = GAME_CODES_BY_TITLE.get(t["id"])
            if not budget.check():
                errors.append(f"{t['id']}: skipped, request budget exhausted for this run")
                continue
            resume_key = None if args.refresh else f"{wiki}|{','.join(game_codes) if game_codes else ''}"
            rows = fetch_tournaments(client, budget, wiki, game_codes, resume_key=resume_key)
            written_for_title = 0
            for row in rows:
                if upsert_tournament(conn, t["id"], wiki, row):
                    written_for_title += 1
            rows_written += written_for_title
            conn.commit()
            skipped_for_title = len(rows) - written_for_title
            print(
                f"[info] {t['id']}: {written_for_title} tournaments written from wiki '{wiki}'"
                + (f" ({skipped_for_title} skipped, no pagename)" if skipped_for_title else "")
                + (f" (game filter: {','.join(game_codes)})" if game_codes else "")
                + f" — {budget.count}/{budget.max_requests} requests used",
                flush=True,
            )

    finished_at = utcnow_iso()
    status = "ok" if not errors else "partial"
    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('liquipedia_lpdb', NULL, ?, ?, ?, ?, ?)
        """,
        (started_at, finished_at, status, rows_written, "; ".join(errors[:20]) or None),
    )
    conn.commit()
    conn.close()

    print(f"wrote {rows_written} tournament rows (status={status}, requests_used={budget.count}/{budget.max_requests})")
    if errors:
        print(f"errors: {'; '.join(errors[:5])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
