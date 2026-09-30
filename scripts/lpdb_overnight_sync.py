#!/usr/bin/env python3
"""Unattended LPDB sync loop, built 2026-10-01 following a direct request to
"acquire tournament data from the other titles automatically overnight,
resuming as the [rate limit] count resets."

Runs for up to WALL_CLOCK_BUDGET_HOURS (default 23, leaving an hour of
margin under a 24h ask), working through a fixed-priority queue:

  1. Tournament pulls (collectors/liquipedia_lpdb.py) for every active
     title not yet marked complete in the shared pagination-offset state
     (data/cache/liquipedia_lpdb/tournament_offsets.json).
  2. Player/roster pulls (collectors/liquipedia_lpdb_players.py) for every
     active, non-fighters-wiki title not yet complete in the same state
     file.
  3. Broadcast/match-stream sampling (collectors/liquipedia_lpdb_broadcasts.py)
     for every active title whose tournament pull (1) is done -- tracked
     in this script's own small state file, OVERNIGHT_STATE_PATH, since
     that collector samples a fixed N tournaments rather than paginating
     to completion the way (1)/(2) do.

Every invocation goes through the SAME shared, cross-process request
budget (collectors/liquipedia_lpdb.py's RequestBudget /
data/cache/liquipedia_lpdb/request_log.json) -- this script never tracks
its own separate request count, so it can't accidentally double the
effective rate against LPDB's real 60/hour ceiling. When a collector
subprocess reports its run was cut short by that shared budget, this
script sleeps until the reported reset ETA (plus a small buffer) rather
than busy-polling, and deliberately runs collectors below the hard 60/hour
line (MAX_REQUESTS_PER_INVOCATION, see below) rather than constantly
saturating it -- explicitly requested ("let's not piss off our friends at
LPDB"), not just a rate-limit technicality.

This script does NOT touch collectors/twitch_poll.py, poll.yml, or any
other live-viewership collector -- CLAUDE.md's absolute rule. It only
calls LPDB-facing scripts.

Usage:
    python scripts/lpdb_overnight_sync.py                      # default 23h budget
    python scripts/lpdb_overnight_sync.py --hours 4             # shorter test run
    nohup python scripts/lpdb_overnight_sync.py > /tmp/lpdb_sync.log 2>&1 &   # actual overnight usage
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from collectors.liquipedia_lpdb import (  # noqa: E402
    OFFSET_STATE_PATH, RATE_WINDOW_SECONDS, REQUEST_LOG_PATH, SERVER_RATE_LIMIT,
    _load_request_log, _reset_eta,
)
from collectors.liquipedia_lpdb import GAME_CODES_BY_TITLE  # noqa: E402
from collectors.liquipedia_lpdb import load_titles  # noqa: E402

TITLES_CONFIG = REPO_ROOT / "config" / "titles.yaml"
OVERNIGHT_STATE_PATH = REPO_ROOT / "data" / "cache" / "liquipedia_lpdb" / "overnight_sync_state.json"
LOG_PREFIX_FMT = "%Y-%m-%d %H:%M:%S UTC"

# Deliberately under the confirmed 60/hour ceiling, per invocation -- see
# module docstring. A single collector call self-limits further via its
# own RequestBudget against the real shared rolling window regardless.
MAX_REQUESTS_PER_INVOCATION = 45

FIGHTERS_WIKI_TITLES = set(GAME_CODES_BY_TITLE.keys())


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime(LOG_PREFIX_FMT)
    print(f"[{ts}] {msg}", flush=True)


def load_overnight_state() -> dict:
    if not OVERNIGHT_STATE_PATH.is_file():
        return {"broadcasts_done": []}
    try:
        return json.loads(OVERNIGHT_STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {"broadcasts_done": []}


def save_overnight_state(state: dict) -> None:
    OVERNIGHT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERNIGHT_STATE_PATH.write_text(json.dumps(state, indent=2))


def load_tournament_offset_state() -> dict:
    if not OFFSET_STATE_PATH.is_file():
        return {}
    try:
        return json.loads(OFFSET_STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def tournaments_done(title: dict, offset_state: dict) -> bool:
    wiki = title.get("liquipedia_wiki")
    game_codes = GAME_CODES_BY_TITLE.get(title["id"])
    key = f"{wiki}|{','.join(game_codes) if game_codes else ''}"
    return offset_state.get(key) == "done"


def players_done(title: dict, offset_state: dict) -> bool:
    wiki = title.get("liquipedia_wiki")
    return offset_state.get(f"player:{wiki}") == "done" and offset_state.get(f"squadplayer:{wiki}") == "done"


def run_collector(args: list[str]) -> tuple[bool, str]:
    """Runs a collector subprocess, returns (fully_completed, combined_output).
    fully_completed is False if the output shows the run was cut short by
    the shared request budget (status=partial)."""
    result = subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=600,
    )
    output = (result.stdout or "") + (result.stderr or "")
    completed = result.returncode == 0 and "status=partial" not in output
    return completed, output


def budget_remaining() -> int:
    timestamps = _load_request_log(REQUEST_LOG_PATH)
    return max(0, SERVER_RATE_LIMIT - len(timestamps))


def sleep_until_reset() -> None:
    timestamps = _load_request_log(REQUEST_LOG_PATH)
    eta_str = _reset_eta(timestamps)
    if not eta_str:
        log("budget exhausted but no timestamps found to compute an ETA from -- sleeping 5 min as a fallback")
        time.sleep(300)
        return
    eta = datetime.strptime(eta_str, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    sleep_s = max(30, (eta - now).total_seconds() + 60)  # +60s buffer past the reported reset
    log(f"shared budget exhausted -- sleeping {sleep_s/60:.1f} min until ~{eta_str} (+ buffer)")
    time.sleep(sleep_s)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hours", type=float, default=23.0, help="wall-clock budget in hours (default 23)")
    args = parser.parse_args()

    deadline = datetime.now(timezone.utc) + timedelta(hours=args.hours)
    log(f"lpdb_overnight_sync starting -- wall-clock deadline {deadline.strftime(LOG_PREFIX_FMT)}")

    all_titles = load_titles(TITLES_CONFIG)
    active_titles = [t for t in all_titles if t.get("is_active") and t.get("liquipedia_wiki")]
    overnight_state = load_overnight_state()

    cycles = 0
    while datetime.now(timezone.utc) < deadline:
        cycles += 1
        offset_state = load_tournament_offset_state()

        pending_tournaments = [t for t in active_titles if not tournaments_done(t, offset_state)]
        pending_players = [t for t in active_titles if t["id"] not in FIGHTERS_WIKI_TITLES and not players_done(t, offset_state)]
        pending_broadcasts = [
            t for t in active_titles
            if t["id"] not in overnight_state.get("broadcasts_done", []) and tournaments_done(t, offset_state)
        ]

        if not pending_tournaments and not pending_players and not pending_broadcasts:
            log("ALL WORK COMPLETE -- tournaments, players, and broadcast sampling done for every active title. Exiting.")
            return 0

        remaining = budget_remaining()
        log(f"cycle {cycles}: budget={remaining}/{SERVER_RATE_LIMIT} | pending: tournaments={len(pending_tournaments)} players={len(pending_players)} broadcasts={len(pending_broadcasts)}")

        if remaining < 2:
            sleep_until_reset()
            continue

        if pending_tournaments:
            title = pending_tournaments[0]
            log(f"tournaments: {title['id']}")
            _, output = run_collector([
                "collectors/liquipedia_lpdb.py", "--titles", title["id"],
                "--max-requests", str(MAX_REQUESTS_PER_INVOCATION),
            ])
            for line in output.strip().splitlines()[-4:]:
                log(f"  {line}")
            still_pending = not tournaments_done(title, load_tournament_offset_state())
            log(f"  -> {'partial, will resume next cycle (offset persisted)' if still_pending else 'complete'}")
        elif pending_players:
            title = pending_players[0]
            log(f"players: {title['id']}")
            _, output = run_collector([
                "collectors/liquipedia_lpdb_players.py", "--titles", title["id"],
                "--max-requests", str(MAX_REQUESTS_PER_INVOCATION),
            ])
            for line in output.strip().splitlines()[-4:]:
                log(f"  {line}")
            still_pending = not players_done(title, load_tournament_offset_state())
            log(f"  -> {'partial, will resume next cycle (offset persisted)' if still_pending else 'complete'}")
        else:
            title = pending_broadcasts[0]
            log(f"broadcasts: {title['id']}")
            completed, output = run_collector([
                "collectors/liquipedia_lpdb_broadcasts.py", "--titles", title["id"],
                "--max-requests", str(MAX_REQUESTS_PER_INVOCATION),
            ])
            for line in output.strip().splitlines()[-4:]:
                log(f"  {line}")
            if completed:
                overnight_state.setdefault("broadcasts_done", []).append(title["id"])
                save_overnight_state(overnight_state)
            log(f"  -> {'complete' if completed else 'partial, will retry next cycle'}")

    log(f"wall-clock budget ({args.hours}h) reached -- stopping. Re-run this script to continue where it left off (all progress is persisted).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
