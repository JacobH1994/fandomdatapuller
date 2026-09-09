#!/usr/bin/env python3
"""Twitch platform-wide (non-esports) viewership collector.

Deliberately a SEPARATE script/config/workflow from collectors/twitch_poll.py
-- the same discipline CLAUDE.md already documents for collectors/
youtube_poll.py and collectors/steam_poll.py: a change here can never put
at risk the 23-title collector CLAUDE.md protects as the "one rule."

Captures the platform-wide "everything else" -- every live stream NOT
under one of the 23 tracked titles' Twitch category IDs -- grouped by
game, using the same tiered full-detail/aggregate-below-threshold policy
config/capture.yaml already proved out for the tracked titles, just
re-derived for this much larger, much more power-law-skewed population
(see config/twitch_platform_capture.yaml for that derivation). Feeds
docs/wider_game_fandom_brief.md (added 2026-09-09) -- first use case:
comparing esports creator insularity against the wider Twitch creator
population, and tracking non-esports blockbuster launches (GTA 6 being
the motivating case) the same way collectors/twitch_poll.py tracks
tracked-title lifecycles.

Reuses (imports only, never modifies) collectors/twitch_poll.py's auth,
retry, dotenv, and title-loading helpers. Deliberately does NOT call
that module's fetch_platform_totals() -- that function discards
per-stream detail by design (it only needs a sum), and changing what a
protected function returns is a bigger risk than duplicating its ~15
line pagination loop here.

There is no "official broadcast" concept for games this project doesn't
track (that requires config/channels.yaml, which is title-specific), so
tiering here is viewer_count >= threshold only, no official-channel
override.

Usage:
    python collectors/twitch_platform_poll.py
    python collectors/twitch_platform_poll.py --max-pages 50       # local testing, bounded
    python collectors/twitch_platform_poll.py --min-viewers 1      # threshold-derivation runs

Requires TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET -- same as
collectors/twitch_poll.py (either exported, or in .env at the repo root).
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from collectors.twitch_poll import (  # noqa: E402 -- import after sys.path setup, same pattern as this repo's other collectors
    PAGE_SIZE,
    RunErrors,
    get_access_token,
    load_dotenv,
    load_titles,
    request_with_retry,
    utcnow_iso,
)
from collectors.twitch_poll import DOTENV_PATH as TWITCH_DOTENV_PATH  # noqa: E402

TITLES_CONFIG = REPO_ROOT / "config" / "titles.yaml"
CAPTURE_CONFIG = REPO_ROOT / "config" / "twitch_platform_capture.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw" / "twitch_platform"

DEFAULT_MAX_PAGES = int(os.environ.get("TWITCH_PLATFORM_MAX_PAGES", "1000"))


def load_capture_config(path: Path) -> dict:
    if not path.is_file():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def tracked_game_ids(titles: list[dict]) -> set[str]:
    return {t["twitch_category_id"] for t in titles if t.get("twitch_category_id")}


def fetch_all_streams(
    client: httpx.Client, errors: RunErrors, max_pages: int
) -> tuple[list[dict], bool]:
    """Paginate /helix/streams with NO game_id filter -- the same call
    twitch_poll.py's fetch_platform_totals() makes, but keeping every
    stream record instead of discarding it after summing."""
    streams: list[dict] = []
    cursor: str | None = None
    pages_fetched = 0
    hit_page_cap = False

    while True:
        if pages_fetched >= max_pages:
            hit_page_cap = True
            break
        params = {"first": PAGE_SIZE}
        if cursor:
            params["after"] = cursor
        resp = request_with_retry(client, params, errors, "platform_poll")
        if resp is None:
            break
        body = resp.json()
        page = body.get("data", [])
        pages_fetched += 1
        streams.extend(page)
        cursor = body.get("pagination", {}).get("cursor")
        if not cursor or not page:
            break

    if hit_page_cap:
        errors.add(
            "platform_poll",
            f"hit max_pages={max_pages} before pagination exhausted; "
            "this poll's results are a partial sample, not a full sweep",
        )
    return streams, hit_page_cap


def slim_stream(stream: dict) -> dict:
    tags = stream.get("tags") or []
    return {
        "user_id": stream.get("user_id"),
        "user_login": stream.get("user_login"),
        "viewer_count": stream.get("viewer_count", 0),
        "started_at": stream.get("started_at"),
        "language": stream.get("language"),
        "tags": tags,
        "title": stream.get("title"),
    }


def tier_and_group_by_game(
    streams: list[dict], excluded_game_ids: set[str], min_viewers: int
) -> dict:
    """Groups every non-tracked-title stream by game_id, applying the
    full-detail/aggregate-below-threshold split -- see module docstring
    for why there's no official-channel override here."""
    by_game: dict[str, dict] = {}

    for stream in streams:
        game_id = stream.get("game_id") or ""
        if not game_id or game_id in excluded_game_ids:
            continue
        bucket = by_game.setdefault(
            game_id,
            {
                "game_name": stream.get("game_name") or "(unknown)",
                "streams": [],
                "below_threshold": {"stream_count": 0, "viewer_total": 0},
            },
        )
        viewer_count = stream.get("viewer_count", 0)
        if viewer_count >= min_viewers:
            bucket["streams"].append(slim_stream(stream))
        else:
            bucket["below_threshold"]["stream_count"] += 1
            bucket["below_threshold"]["viewer_total"] += viewer_count

    return by_game


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument(
        "--min-viewers",
        type=int,
        default=None,
        help="override config/twitch_platform_capture.yaml's full_detail_min_viewers",
    )
    args = parser.parse_args()

    load_dotenv(TWITCH_DOTENV_PATH)
    client_id = os.environ.get("TWITCH_CLIENT_ID")
    client_secret = os.environ.get("TWITCH_CLIENT_SECRET")
    if not client_id or not client_secret:
        print(
            "TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET must be set in the environment",
            file=sys.stderr,
        )
        return 1

    run_started_at = utcnow_iso()
    errors = RunErrors()

    all_titles = load_titles(TITLES_CONFIG)
    excluded_game_ids = tracked_game_ids(all_titles)
    capture_config = load_capture_config(CAPTURE_CONFIG)
    min_viewers = (
        args.min_viewers
        if args.min_viewers is not None
        else int(capture_config.get("full_detail_min_viewers", 5))
    )

    try:
        token = get_access_token(client_id, client_secret)
    except httpx.HTTPError as exc:
        print(f"failed to obtain access token: {exc}", file=sys.stderr)
        return 1

    headers = {"Client-Id": client_id, "Authorization": f"Bearer {token}"}
    with httpx.Client(headers=headers) as client:
        streams, hit_page_cap = fetch_all_streams(client, errors, args.max_pages)

    by_game = tier_and_group_by_game(streams, excluded_game_ids, min_viewers)

    run_finished_at = utcnow_iso()
    status = "ok" if not errors.items else ("partial" if by_game else "failed")
    total_full_detail = sum(len(g["streams"]) for g in by_game.values())

    snapshot = {
        "captured_at": run_finished_at,
        "run_started_at": run_started_at,
        "run_finished_at": run_finished_at,
        "status": status,
        "capture_policy": {"full_detail_min_viewers": min_viewers},
        "excluded_tracked_game_ids": sorted(excluded_game_ids),
        "raw_stream_count": len(streams),
        "distinct_games": len(by_game),
        "full_detail_stream_count": total_full_detail,
        "hit_page_cap": hit_page_cap,
        "games": by_game,
        "errors": errors.items,
    }

    now = datetime.now(timezone.utc)
    out_dir = RAW_DIR / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{now.strftime('%Y%m%dT%H%M%SZ')}.json.gz"
    with gzip.open(out_path, "wt") as f:
        json.dump(snapshot, f, separators=(",", ":"), sort_keys=True)

    print(
        f"wrote {out_path.relative_to(REPO_ROOT)}: {len(streams)} raw streams, "
        f"{len(by_game)} distinct non-tracked games, {total_full_detail} full-detail records, "
        f"status={status}"
    )
    return 0 if status != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
