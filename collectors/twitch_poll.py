#!/usr/bin/env python3
"""Twitch live-viewership collector (PRD §9.1).

Polls the Twitch Helix `Get Streams` endpoint for every actively-tracked
title in config/titles.yaml, plus a platform-wide total, and writes the
result as a single timestamped, gzipped JSON file under data/raw/twitch/.

This is the git-scraping landing zone: the file this script writes is the
permanent record (PRD §2). It intentionally does NOT dedupe or load
anything into a database — that's the ETL's job (Phase 2), reading these
files back out later.

It is NOT an unmodified dump of the API response, by design (see
config/capture.yaml for the full rationale): every stream is classified
into one of three tiers before being written —

  1. Official channel (config/channels.yaml) -> always full detail
  2. viewer_count >= full_detail_min_viewers  -> full detail
  3. below threshold, not official            -> no per-stream record;
     folded into that title's below_threshold aggregate (viewer_total,
     and viewer_total_by_language) for the poll

"Full detail" always keeps title and tags (needed later for co-stream
detection). thumbnail_url and type are dropped from every tier.

Usage:
    python collectors/twitch_poll.py
    python collectors/twitch_poll.py --titles valorant,dota2
    python collectors/twitch_poll.py --skip-platform-totals

Requires TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET — either exported in the
environment, or set in a .env file at the repo root (auto-loaded; see
.env.example). Real environment variables always take precedence.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import random
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TITLES_CONFIG = REPO_ROOT / "config" / "titles.yaml"
CHANNELS_CONFIG = REPO_ROOT / "config" / "channels.yaml"
CAPTURE_CONFIG = REPO_ROOT / "config" / "capture.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw" / "twitch"
DOTENV_PATH = REPO_ROOT / ".env"

# Fields kept for a "full detail" stream record. thumbnail_url and type are
# deliberately excluded — see config/capture.yaml.
FULL_DETAIL_FIELDS = (
    "id",
    "user_id",
    "user_login",
    "user_name",
    "game_id",
    "game_name",
    "title",
    "viewer_count",
    "started_at",
    "language",
    "tags",
    "is_mature",
)


def load_dotenv(path: Path) -> None:
    """Minimal .env loader for local dev — no new dependency for one file.
    Real env vars (e.g. set by CI) always win over .env; only fills gaps."""
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

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
STREAMS_URL = "https://api.twitch.tv/helix/streams"

PAGE_SIZE = 100
MAX_RETRIES = 5
# Safety valve on platform-wide pagination — Twitch has no single "total
# viewers" endpoint, so the platform total is computed by paginating
# through every live stream. Cap it so a bug (or Twitch never running out
# of pages) can't hang the job or blow through the rate limit budget.
DEFAULT_MAX_PLATFORM_PAGES = int(os.environ.get("TWITCH_MAX_PLATFORM_PAGES", "1000"))


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RunErrors:
    items: list[dict] = field(default_factory=list)

    def add(self, scope: str, message: str) -> None:
        self.items.append({"scope": scope, "message": message})
        print(f"[error] {scope}: {message}", file=sys.stderr)


def load_titles(path: Path) -> list[dict]:
    with open(path) as f:
        config = yaml.safe_load(f)
    return config.get("titles", [])


def load_official_channels(path: Path) -> dict[str, set[str]]:
    with open(path) as f:
        config = yaml.safe_load(f) or {}
    raw = config.get("channels") or {}
    return {title_id: {login.lower() for login in (logins or [])} for title_id, logins in raw.items()}


def load_capture_config(path: Path) -> dict:
    with open(path) as f:
        config = yaml.safe_load(f) or {}
    return config


def slim_stream(stream: dict) -> dict:
    return {field_name: stream.get(field_name) for field_name in FULL_DETAIL_FIELDS}


def tier_streams(streams: list[dict], official_logins: set[str], min_viewers: int) -> tuple[list[dict], dict]:
    """Classify streams per config/capture.yaml. Returns (full_detail_records,
    below_threshold_aggregate)."""
    full_detail: list[dict] = []
    below_stream_count = 0
    below_viewer_total = 0
    below_viewer_by_language: Counter[str] = Counter()

    for stream in streams:
        login = (stream.get("user_login") or "").lower()
        viewer_count = stream.get("viewer_count", 0)
        if login in official_logins or viewer_count >= min_viewers:
            full_detail.append(slim_stream(stream))
        else:
            below_stream_count += 1
            below_viewer_total += viewer_count
            language = stream.get("language") or "unknown"
            below_viewer_by_language[language] += viewer_count

    below_threshold = {
        "stream_count": below_stream_count,
        "viewer_total": below_viewer_total,
        "viewer_total_by_language": dict(below_viewer_by_language),
    }
    return full_detail, below_threshold


def get_access_token(client_id: str, client_secret: str) -> str:
    resp = httpx.post(
        TOKEN_URL,
        params={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def request_with_retry(
    client: httpx.Client, params: dict, errors: RunErrors, scope: str
) -> httpx.Response | None:
    """GET the streams endpoint with exponential backoff + jitter on 429/5xx,
    and pre-emptive throttling when the rate-limit bucket is nearly empty."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(STREAMS_URL, params=params, timeout=30)
        except httpx.RequestError as exc:
            if attempt == MAX_RETRIES:
                errors.add(scope, f"request failed after {MAX_RETRIES} attempts: {exc}")
                return None
            time.sleep(backoff_seconds(attempt))
            continue

        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == MAX_RETRIES:
                errors.add(
                    scope,
                    f"status {resp.status_code} after {MAX_RETRIES} attempts: {resp.text[:200]}",
                )
                return None
            retry_after = resp.headers.get("Retry-After")
            wait = float(retry_after) if retry_after else backoff_seconds(attempt)
            time.sleep(wait)
            continue

        resp.raise_for_status()
        throttle_if_needed(resp)
        return resp

    return None


def backoff_seconds(attempt: int) -> float:
    base = min(2**attempt, 60)
    return base + random.uniform(0, 1)


def throttle_if_needed(resp: httpx.Response) -> None:
    """Pre-emptively slow down before we hit the bucket limit, rather than
    waiting to be told via a 429."""
    remaining = resp.headers.get("Ratelimit-Remaining")
    reset = resp.headers.get("Ratelimit-Reset")
    if remaining is None or reset is None:
        return
    try:
        remaining_n = int(remaining)
        reset_ts = int(reset)
    except ValueError:
        return
    if remaining_n <= 1:
        wait = max(0, reset_ts - time.time())
        if wait:
            time.sleep(wait)


def fetch_streams_for_game(
    client: httpx.Client, game_id: str, errors: RunErrors, scope: str
) -> list[dict]:
    streams: list[dict] = []
    cursor: str | None = None
    while True:
        params = {"game_id": game_id, "first": PAGE_SIZE}
        if cursor:
            params["after"] = cursor
        resp = request_with_retry(client, params, errors, scope)
        if resp is None:
            break
        body = resp.json()
        streams.extend(body.get("data", []))
        cursor = body.get("pagination", {}).get("cursor")
        if not cursor:
            break
    return streams


def fetch_platform_totals(
    client: httpx.Client, errors: RunErrors, max_pages: int
) -> dict:
    total_viewers = 0
    total_channels = 0
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
        resp = request_with_retry(client, params, errors, "platform_totals")
        if resp is None:
            break
        body = resp.json()
        page = body.get("data", [])
        pages_fetched += 1
        total_channels += len(page)
        total_viewers += sum(s.get("viewer_count", 0) for s in page)
        cursor = body.get("pagination", {}).get("cursor")
        if not cursor or not page:
            break

    if hit_page_cap:
        errors.add(
            "platform_totals",
            f"hit max_pages={max_pages} before pagination exhausted; "
            "total_viewers/total_channels are a partial lower bound for this poll",
        )

    return {
        "total_viewers": total_viewers,
        "total_channels": total_channels,
        "pages_fetched": pages_fetched,
        "hit_page_cap": hit_page_cap,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--titles",
        help="comma-separated title ids to poll (default: all is_active titles in config)",
    )
    parser.add_argument(
        "--skip-platform-totals",
        action="store_true",
        help="skip the platform-wide pagination (useful for short event-mode polls)",
    )
    parser.add_argument(
        "--max-platform-pages",
        type=int,
        default=DEFAULT_MAX_PLATFORM_PAGES,
        help="safety cap on platform-total pagination pages",
    )
    args = parser.parse_args()

    load_dotenv(DOTENV_PATH)
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
    official_channels = load_official_channels(CHANNELS_CONFIG)
    capture_config = load_capture_config(CAPTURE_CONFIG)
    min_viewers = int(capture_config.get("full_detail_min_viewers", 3))
    if args.titles:
        wanted = set(args.titles.split(","))
        titles = [t for t in all_titles if t["id"] in wanted]
    else:
        titles = [t for t in all_titles if t.get("is_active")]

    for t in titles:
        if not t.get("twitch_category_verified", False):
            print(
                f"[warn] {t['id']}: twitch_category_id is unverified "
                f"({t.get('twitch_category_id')!r}) — see config/titles.yaml",
                file=sys.stderr,
            )

    try:
        token = get_access_token(client_id, client_secret)
    except httpx.HTTPError as exc:
        print(f"failed to obtain access token: {exc}", file=sys.stderr)
        return 1

    headers = {"Client-Id": client_id, "Authorization": f"Bearer {token}"}
    result_titles: dict[str, dict] = {}

    with httpx.Client(headers=headers) as client:
        for t in titles:
            game_id = t.get("twitch_category_id")
            if not game_id:
                errors.add(t["id"], "no twitch_category_id configured, skipped")
                continue
            streams = fetch_streams_for_game(client, game_id, errors, t["id"])
            full_detail, below_threshold = tier_streams(
                streams, official_channels.get(t["id"], set()), min_viewers
            )
            result_titles[t["id"]] = {
                "twitch_category_id": game_id,
                "twitch_category_verified": t.get("twitch_category_verified", False),
                "total_stream_count": len(streams),
                "full_detail_stream_count": len(full_detail),
                "streams": full_detail,
                "below_threshold": below_threshold,
            }

        platform_totals = None
        if not args.skip_platform_totals:
            platform_totals = fetch_platform_totals(client, errors, args.max_platform_pages)

    run_finished_at = utcnow_iso()
    status = "ok" if not errors.items else ("partial" if result_titles else "failed")

    snapshot = {
        "captured_at": run_finished_at,
        "run_started_at": run_started_at,
        "run_finished_at": run_finished_at,
        "status": status,
        "capture_policy": {"full_detail_min_viewers": min_viewers},
        "titles": result_titles,
        "platform_totals": platform_totals,
        "errors": errors.items,
    }

    now = datetime.now(timezone.utc)
    out_dir = RAW_DIR / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{now.strftime('%Y%m%dT%H%M%SZ')}.json.gz"
    with gzip.open(out_path, "wt") as f:
        json.dump(snapshot, f, separators=(",", ":"), sort_keys=True)

    print(f"wrote {out_path} (status={status}, titles={len(result_titles)})")

    return 0 if status != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
