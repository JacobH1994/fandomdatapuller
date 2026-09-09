#!/usr/bin/env python3
"""Steam current-player-count collector (PRD §9.12).

Polls Valve's official `ISteamUserStats/GetNumberOfCurrentPlayers` for
every title in config/steam_appids.yaml, writing the result as a
timestamped gzipped JSON file under data/raw/steam/ — the same
git-scraping pattern collectors/twitch_poll.py and collectors/
youtube_poll.py use, for the same reason (no historical parameter exists
on this endpoint — confirmed live, current-state-only — so a missed poll
is permanently lost, same urgency as CLAUDE.md's "one rule").

**Much simpler than the YouTube collector, deliberately**: no discovery
step, no live/not-live state, no per-title quota asymmetry to design
around. Every configured title gets one direct GetNumberOfCurrentPlayers
call, every run. Valve's general Web API rate limit (~100,000 calls/day
per key) isn't remotely close to being exercised at this project's scale
(a dozen titles, hourly) — no safety-cap logic needed the way YouTube's
10,000/day search-heavy budget required one.

**A real gotcha, confirmed live (2026-09-08), not documented in Valve's
own API reference**: without a `key` parameter, this endpoint silently
returns `player_count: 0` (not an error — `result: 1`, i.e. "success")
for several high-traffic titles specifically (confirmed: Counter-Strike 2,
PUBG, Apex Legends, Tekken 8 all did this) while working correctly
without a key for others (Dota 2, Rainbow Six Siege, Rocket League, Age
of Empires II, Street Fighter 6, Mortal Kombat 1, Guilty Gear -Strive-).
Adding ANY `key` value — even an invalid one, confirmed live — made
those same "zero" titles return real, plausible numbers instead. This
script always sends a real key regardless (required, not optional, for
legitimate sustained use), but the gotcha is documented here because it
means a future "quick test without a key" will misleadingly look like
several of this project's biggest titles have zero players, not like a
missing-parameter issue.

No new dependency: raw REST via httpx (already a dependency), matching
collectors/liquipedia.py's and collectors/youtube_poll.py's own reasoning
for avoiding an SDK in a file installed as-is for other collectors' CI
jobs too.

Usage:
    python collectors/steam_poll.py
    python collectors/steam_poll.py --titles dota2,counter_strike

Requires STEAM_API_KEY — either exported in the environment, or set in a
.env file at the repo root (auto-loaded; see .env.example). Free to
register at https://steamcommunity.com/dev/apikey. Real environment
variables always take precedence.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
APPIDS_CONFIG = REPO_ROOT / "config" / "steam_appids.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw" / "steam"
DOTENV_PATH = REPO_ROOT / ".env"

API_URL = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
MAX_RETRIES = 5


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


@dataclass
class RunErrors:
    items: list[dict] = field(default_factory=list)

    def add(self, scope: str, message: str) -> None:
        self.items.append({"scope": scope, "message": message})
        print(f"[error] {scope}: {message}", file=sys.stderr)


def load_appids(path: Path) -> dict[str, int]:
    with open(path) as f:
        config = yaml.safe_load(f) or {}
    return config.get("titles") or {}


def backoff_seconds(attempt: int) -> float:
    base = min(2**attempt, 60)
    return base + random.uniform(0, 1)


def parse_player_count_response(body: dict) -> int | None:
    """Pure parsing of one GetNumberOfCurrentPlayers response body — no
    network I/O, directly unit-testable. Returns None (not 0) for a
    malformed/unsuccessful response — result != 1 means Valve's API
    itself is saying this call didn't work as expected (an unrecognized
    appid, most likely), which is a different, worse thing than "this
    game really does have zero current players" and must not be silently
    coerced into the same value."""
    response = body.get("response") or {}
    if response.get("result") != 1:
        return None
    return response.get("player_count")


def fetch_player_count(client: httpx.Client, appid: int, api_key: str, errors: RunErrors, scope: str) -> int | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(API_URL, params={"appid": appid, "key": api_key}, timeout=30)
        except httpx.RequestError as exc:
            if attempt == MAX_RETRIES:
                errors.add(scope, f"request failed after {MAX_RETRIES} attempts: {exc}")
                return None
            time.sleep(backoff_seconds(attempt))
            continue

        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == MAX_RETRIES:
                errors.add(scope, f"status {resp.status_code} after {MAX_RETRIES} attempts: {resp.text[:200]}")
                return None
            time.sleep(backoff_seconds(attempt))
            continue

        if resp.status_code == 404:
            # Confirmed live 2026-09-09: Steam returns a genuine HTTP 404
            # (body `{"response":{"result":42}}`) for an appid it doesn't
            # recognize yet — routine and expected for a title that
            # hasn't released, not an anomaly. Logging this via errors.add
            # made every steam_cohort_poll.py run whose newly-discovered
            # titles are all still pre-release report status="failed" and
            # page — a false alarm for exactly the case
            # collectors/steam_cohort_poll.py's own docstring already
            # said was expected and handled. Silently return None (the
            # existing "unknown, not zero" semantics), no errors.add.
            return None

        if resp.status_code >= 400:
            errors.add(scope, f"status {resp.status_code}: {resp.text[:200]}")
            return None

        body = resp.json()
        count = parse_player_count_response(body)
        if count is None:
            errors.add(scope, f"unexpected response (result != 1): {body}")
        return count

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--titles", help="comma-separated title ids to check (default: all in config/steam_appids.yaml)")
    args = parser.parse_args()

    load_dotenv(DOTENV_PATH)
    api_key = os.environ.get("STEAM_API_KEY")
    if not api_key:
        print("STEAM_API_KEY must be set in the environment", file=sys.stderr)
        return 1

    run_started_at = utcnow_iso()
    errors = RunErrors()

    appids = load_appids(APPIDS_CONFIG)
    if not appids:
        print("[info] config/steam_appids.yaml has no titles configured — nothing to check, exiting cleanly")
        return 0

    if args.titles:
        wanted = set(args.titles.split(","))
        appids = {t: a for t, a in appids.items() if t in wanted}

    checked_at = utcnow_iso()
    results: list[dict] = []

    with httpx.Client() as client:
        for title_id, appid in appids.items():
            count = fetch_player_count(client, appid, api_key, errors, title_id)
            results.append({
                "title_id": title_id,
                "appid": appid,
                "player_count": count,
                "checked_at": checked_at,
            })

    run_finished_at = utcnow_iso()
    succeeded = sum(1 for r in results if r["player_count"] is not None)
    status = "ok" if not errors.items else ("partial" if succeeded else "failed")

    snapshot = {
        "captured_at": run_finished_at,
        "run_started_at": run_started_at,
        "run_finished_at": run_finished_at,
        "status": status,
        "titles": results,
        "errors": errors.items,
    }

    now = datetime.now(timezone.utc)
    out_dir = RAW_DIR / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{now.strftime('%Y%m%dT%H%M%SZ')}.json.gz"
    with gzip.open(out_path, "wt") as f:
        json.dump(snapshot, f, separators=(",", ":"), sort_keys=True)

    print(f"wrote {out_path} (status={status}, titles_checked={len(results)}, succeeded={succeeded})")

    return 0 if status != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
