#!/usr/bin/env python3
"""YouTube live-viewership collector (PRD §9.7).

Checks each curated official YouTube channel (config/channels_youtube.yaml)
for live status and, if live, its current concurrent-viewer count, writing
the result as a timestamped gzipped JSON file under data/raw/youtube/ — the
same git-scraping pattern collectors/twitch_poll.py uses, for the same
reason (this workflow's runner is ephemeral; the committed raw file is the
permanent record).

**Quota, not access, is the real constraint** (confirmed live, matches the
PRD): a plain API key against a Google Cloud project is enough auth, no
OAuth. But `search.list` — the only way to discover which video (if any) a
channel is CURRENTLY live on — costs 100 units against a 10,000/day default
quota, while `videos.list` — checking a KNOWN video's current viewer count —
costs just 1 unit and batches up to 50 IDs per call. That asymmetry drives
this script's whole design:

  - **Discovery** (search.list, expensive): only run for a channel when
    either (a) this is a "sweep" run (--sweep, or the baseline cadence —
    see --sweep-interval-hours, default 6h/day = ~4 sweeps/day, matching
    the PRD's "a few times a day" baseline) and the channel wasn't already
    known live last run, or (b) the channel has never been checked before
    (first run). A channel already known live from the PREVIOUS run's
    snapshot is deliberately NOT re-discovered — see refresh, below.
  - **Refresh** (videos.list, cheap): every run, for every channel that
    was live in the LAST committed snapshot (read back from
    data/raw/youtube/ — no separate state file, reusing the same
    "raw files are the permanent record" pattern rather than inventing a
    second persistence mechanism), batched up to 50 IDs per call. If a
    previously-live video's response no longer carries
    `liveStreamingDetails.concurrentViewers`, it's ended — that channel
    reverts to "not live" and won't be rechecked until the next sweep.
  - **Known video ID short-circuit** (PRD §9.7, "a free efficiency gain
    when convenient, not a dependency"): a channel entry in
    config/channels_youtube.yaml may include a `video_id` directly (e.g.
    a tournament's published stream URL) — skips discovery for that
    channel entirely in favor of a straight refresh check.

A quota safety cap (--max-quota, default 8000 — leaving headroom under the
10,000/day default since this script can run more than once a day) aborts
remaining DISCOVERY calls gracefully mid-run if hit, logged as a partial
status, not a crash; already-known-live channels still get their cheap
refresh regardless; matches collectors/twitch_poll.py's own
max-platform-pages safety-valve pattern.

**Deliberately a completely separate file from config/channels.yaml and
.github/workflows/poll.yml** — CLAUDE.md's "one rule" (never risk the
Twitch collector, even briefly) rules out reshaping either of those files'
structure to make room for a second platform.

**No new dependency**: raw REST calls via httpx (already a dependency),
not the google-api-python-client SDK — same reasoning
requirements.txt already documents for keeping `anthropic` out of the
shared install: this file is installed as-is for other collectors' CI
jobs too, so avoiding an unnecessary new dependency here is a deliberate
choice, not an oversight.

Every channel in config/channels_youtube.yaml is by construction official
(there's no community-costream-discovery equivalent for YouTube in this
design, per the PRD's own "populates the official-channel tier only")  —
every row this writes has is_official_broadcast=1.

Usage:
    python collectors/youtube_poll.py                    # normal run
    python collectors/youtube_poll.py --sweep             # force a discovery sweep this run
    python collectors/youtube_poll.py --titles valorant,dota2
    python collectors/youtube_poll.py --sweep-interval-hours 4
    python collectors/youtube_poll.py --max-quota 5000

Requires YOUTUBE_API_KEY — either exported in the environment, or set in a
.env file at the repo root (auto-loaded; see .env.example). Real
environment variables always take precedence.
"""

from __future__ import annotations

import argparse
import glob
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
TITLES_CONFIG = REPO_ROOT / "config" / "titles.yaml"
CHANNELS_CONFIG = REPO_ROOT / "config" / "channels_youtube.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw" / "youtube"
DOTENV_PATH = REPO_ROOT / ".env"

API_BASE = "https://www.googleapis.com/youtube/v3"
SEARCH_COST = 100
VIDEOS_COST = 1
VIDEOS_BATCH_SIZE = 50
MAX_RETRIES = 5
DEFAULT_MAX_QUOTA = 8000
DEFAULT_SWEEP_INTERVAL_HOURS = 6


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_dotenv(path: Path) -> None:
    """Minimal .env loader, same approach as collectors/twitch_poll.py —
    real environment variables always win."""
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


def load_titles(path: Path) -> list[dict]:
    with open(path) as f:
        config = yaml.safe_load(f)
    return config.get("titles", [])


def load_youtube_channels(path: Path) -> dict[str, list[dict]]:
    """Returns {title_id: [{"channel_id", "name", "video_id"(optional)}]}."""
    with open(path) as f:
        config = yaml.safe_load(f) or {}
    return config.get("channels") or {}


def find_last_snapshot(raw_dir: Path) -> dict | None:
    """Reads back the most recent committed raw file to recover prior
    per-channel live state — no separate state file, same "raw files ARE
    the permanent record" pattern collectors/twitch_poll.py's own
    git-scraping design already relies on."""
    files = sorted(glob.glob(str(raw_dir / "**" / "*.json.gz"), recursive=True))
    if not files:
        return None
    with gzip.open(files[-1], "rt") as f:
        return json.load(f)


def prior_live_state(last_snapshot: dict | None) -> dict[str, dict]:
    """Returns {channel_id: {"video_id", "viewer_count", ...}} for channels
    that were live as of the last snapshot. Missing/malformed snapshot
    just means "no known prior state" — not an error, since a channel
    never checked before is exactly what a sweep is for."""
    if not last_snapshot:
        return {}
    state = {}
    for row in last_snapshot.get("channels", []):
        if row.get("is_live") and row.get("video_id"):
            state[row["channel_id"]] = row
    return state


def request_with_retry(client: httpx.Client, url: str, params: dict, errors: RunErrors, scope: str) -> dict | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(url, params=params, timeout=30)
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

        if resp.status_code == 403 and "quotaExceeded" in resp.text:
            errors.add(scope, "YouTube API quota exceeded — stopping remaining calls this run")
            return None

        if resp.status_code >= 400:
            errors.add(scope, f"status {resp.status_code}: {resp.text[:200]}")
            return None

        return resp.json()

    return None


def backoff_seconds(attempt: int) -> float:
    base = min(2**attempt, 60)
    return base + random.uniform(0, 1)


def discover_live_video(client: httpx.Client, api_key: str, channel_id: str, errors: RunErrors) -> str | None:
    """search.list with eventType=live — the only way to find which video
    (if any) a channel is currently live on. Costs SEARCH_COST regardless
    of whether anything is found (not found is a normal, common result,
    not an error)."""
    body = request_with_retry(
        client,
        f"{API_BASE}/search",
        {"part": "snippet", "channelId": channel_id, "eventType": "live", "type": "video", "key": api_key},
        errors,
        f"discover/{channel_id}",
    )
    if body is None:
        return None
    items = body.get("items", [])
    if not items:
        return None
    return items[0]["id"]["videoId"]


def parse_videos_response(body: dict, requested_ids: list[str]) -> dict[str, dict]:
    """Pure parsing of one videos.list response body — no network I/O, so
    directly unit-testable against fixture JSON. Returns
    {video_id: {"is_live", "viewer_count", "title"}}.

    A video is only truly live if BOTH `snippet.liveBroadcastContent`
    says "live" AND `liveStreamingDetails.concurrentViewers` is present —
    confirmed against the API's documented behavior that the latter field
    is only populated while a broadcast is actually live (it's absent
    once a stream ends, even if the video object itself still exists as
    a VOD). A requested id absent from `items` entirely (deleted,
    privated, or simply ended and dropped) is explicitly reported
    is_live=False, not silently omitted — the caller needs to know it
    ended, not just get silence for it."""
    results: dict[str, dict] = {}
    for item in body.get("items", []):
        vid = item["id"]
        live_details = item.get("liveStreamingDetails") or {}
        concurrent = live_details.get("concurrentViewers")
        is_live = item.get("snippet", {}).get("liveBroadcastContent") == "live" and concurrent is not None
        results[vid] = {
            "is_live": is_live,
            "viewer_count": int(concurrent) if concurrent is not None else None,
            "title": item.get("snippet", {}).get("title"),
        }
    for vid in requested_ids:
        if vid not in results:
            results[vid] = {"is_live": False, "viewer_count": None, "title": None}
    return results


def refresh_video_batch(client: httpx.Client, api_key: str, video_ids: list[str], errors: RunErrors) -> dict[str, dict]:
    """videos.list, up to VIDEOS_BATCH_SIZE ids per call — see
    parse_videos_response for the actual response interpretation."""
    results: dict[str, dict] = {}
    for i in range(0, len(video_ids), VIDEOS_BATCH_SIZE):
        batch = video_ids[i : i + VIDEOS_BATCH_SIZE]
        body = request_with_retry(
            client,
            f"{API_BASE}/videos",
            {"part": "snippet,liveStreamingDetails", "id": ",".join(batch), "key": api_key},
            errors,
            "refresh",
        )
        if body is None:
            continue
        results.update(parse_videos_response(body, batch))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--titles", help="comma-separated title ids to check (default: all with configured channels)")
    parser.add_argument("--sweep", action="store_true", help="force a full discovery sweep this run")
    parser.add_argument(
        "--sweep-interval-hours", type=float, default=DEFAULT_SWEEP_INTERVAL_HOURS,
        help=f"baseline: do a discovery sweep if this many hours have passed since the last one (default {DEFAULT_SWEEP_INTERVAL_HOURS})",
    )
    parser.add_argument("--max-quota", type=int, default=DEFAULT_MAX_QUOTA, help=f"safety cap on quota units spent this run (default {DEFAULT_MAX_QUOTA})")
    args = parser.parse_args()

    load_dotenv(DOTENV_PATH)
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("YOUTUBE_API_KEY must be set in the environment", file=sys.stderr)
        return 1

    run_started_at = utcnow_iso()
    errors = RunErrors()

    all_titles = {t["id"] for t in load_titles(TITLES_CONFIG)}
    channels_by_title = load_youtube_channels(CHANNELS_CONFIG)
    if not channels_by_title:
        print("[info] config/channels_youtube.yaml has no channels curated yet — nothing to check, exiting cleanly")
        return 0

    if args.titles:
        wanted = set(args.titles.split(","))
        channels_by_title = {t: v for t, v in channels_by_title.items() if t in wanted}

    unknown_titles = set(channels_by_title) - all_titles
    if unknown_titles:
        errors.add("config", f"channels_youtube.yaml references unknown title_id(s): {sorted(unknown_titles)}")
        channels_by_title = {t: v for t, v in channels_by_title.items() if t in all_titles}

    channels: list[dict] = [
        {"title_id": title_id, **entry}
        for title_id, entries in channels_by_title.items()
        for entry in entries
    ]

    last_snapshot = find_last_snapshot(RAW_DIR)
    prior_state = prior_live_state(last_snapshot)

    is_sweep = args.sweep or last_snapshot is None
    if not is_sweep and last_snapshot is not None:
        last_captured = datetime.strptime(last_snapshot["captured_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        hours_since = (datetime.now(timezone.utc) - last_captured).total_seconds() / 3600
        is_sweep = hours_since >= args.sweep_interval_hours

    quota_used = 0
    quota_exhausted = False
    results: list[dict] = []
    checked_at = utcnow_iso()

    with httpx.Client() as client:
        # Refresh, cheap: every channel known live as of the last snapshot.
        known_live_ids = [row["video_id"] for row in prior_state.values()]
        refreshed: dict[str, dict] = {}
        if known_live_ids:
            refreshed = refresh_video_batch(client, api_key, known_live_ids, errors)
            quota_used += VIDEOS_COST * ((len(known_live_ids) + VIDEOS_BATCH_SIZE - 1) // VIDEOS_BATCH_SIZE)

        for ch in channels:
            channel_id = ch["channel_id"]
            prior = prior_state.get(channel_id)
            video_id = None
            source_note = None

            if prior and prior["video_id"] in refreshed:
                r = refreshed[prior["video_id"]]
                if r["is_live"]:
                    video_id, viewer_count, video_title = prior["video_id"], r["viewer_count"], r["title"]
                    results.append({
                        "title_id": ch["title_id"], "channel_id": channel_id, "channel_name": ch.get("name"),
                        "is_live": True, "video_id": video_id, "viewer_count": viewer_count,
                        "video_title": video_title, "checked_at": checked_at, "discovery_method": "refresh",
                    })
                    continue
                # else: fell offline since last check — falls through to
                # discovery below (only actually fetched if is_sweep).

            if ch.get("video_id"):
                # Known video_id short-circuit (PRD §9.7) — skip discovery,
                # go straight to a refresh check for this one video.
                r = refresh_video_batch(client, api_key, [ch["video_id"]], errors)
                quota_used += VIDEOS_COST
                info = r.get(ch["video_id"], {"is_live": False, "viewer_count": None, "title": None})
                results.append({
                    "title_id": ch["title_id"], "channel_id": channel_id, "channel_name": ch.get("name"),
                    "is_live": info["is_live"], "video_id": ch["video_id"] if info["is_live"] else None,
                    "viewer_count": info["viewer_count"], "video_title": info["title"],
                    "checked_at": checked_at, "discovery_method": "configured_video_id",
                })
                continue

            if not is_sweep:
                # Not live last check, not a sweep run — deliberately not
                # re-discovered this run (see module docstring).
                results.append({
                    "title_id": ch["title_id"], "channel_id": channel_id, "channel_name": ch.get("name"),
                    "is_live": False, "video_id": None, "viewer_count": None, "video_title": None,
                    "checked_at": checked_at, "discovery_method": "skipped_not_sweep",
                })
                continue

            if quota_used + SEARCH_COST > args.max_quota:
                quota_exhausted = True
                results.append({
                    "title_id": ch["title_id"], "channel_id": channel_id, "channel_name": ch.get("name"),
                    "is_live": None, "video_id": None, "viewer_count": None, "video_title": None,
                    "checked_at": checked_at, "discovery_method": "skipped_quota_cap",
                })
                continue

            discovered = discover_live_video(client, api_key, channel_id, errors)
            quota_used += SEARCH_COST
            if discovered is None:
                results.append({
                    "title_id": ch["title_id"], "channel_id": channel_id, "channel_name": ch.get("name"),
                    "is_live": False, "video_id": None, "viewer_count": None, "video_title": None,
                    "checked_at": checked_at, "discovery_method": "sweep_not_live",
                })
                continue

            r = refresh_video_batch(client, api_key, [discovered], errors)
            quota_used += VIDEOS_COST
            info = r.get(discovered, {"is_live": True, "viewer_count": None, "title": None})
            results.append({
                "title_id": ch["title_id"], "channel_id": channel_id, "channel_name": ch.get("name"),
                "is_live": info["is_live"], "video_id": discovered if info["is_live"] else None,
                "viewer_count": info["viewer_count"], "video_title": info["title"],
                "checked_at": checked_at, "discovery_method": "sweep_discovered",
            })

    run_finished_at = utcnow_iso()
    if quota_exhausted:
        errors.add("quota", f"max_quota={args.max_quota} reached mid-sweep — some channels not checked this run")
    status = "ok" if not errors.items else ("partial" if results else "failed")

    snapshot = {
        "captured_at": run_finished_at,
        "run_started_at": run_started_at,
        "run_finished_at": run_finished_at,
        "status": status,
        "sweep_mode": is_sweep,
        "quota_used": quota_used,
        "channels": results,
        "errors": errors.items,
    }

    now = datetime.now(timezone.utc)
    out_dir = RAW_DIR / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{now.strftime('%Y%m%dT%H%M%SZ')}.json.gz"
    with gzip.open(out_path, "wt") as f:
        json.dump(snapshot, f, separators=(",", ":"), sort_keys=True)

    live_count = sum(1 for r in results if r.get("is_live"))
    print(
        f"wrote {out_path} (status={status}, sweep={is_sweep}, quota_used={quota_used}, "
        f"channels_checked={len(results)}, live={live_count})"
    )

    return 0 if status != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
