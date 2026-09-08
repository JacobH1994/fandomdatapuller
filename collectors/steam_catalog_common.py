"""Shared Steam-catalog classification logic (PRD §9.12a), used by both
collectors/steam_catalog_backfill.py (Track A, one-time historical sweep)
and collectors/steam_discovery_poll.py (Track B, ongoing go-forward
discovery) — one implementation to get right, not two to keep in sync.

Two Valve endpoints, neither the live-viewer-count APIs this project's
other Steam work already covers:

  - `IStoreService/GetAppList/v1` — confirmed live (2026-09-08) to work
    with an ordinary Web API key, no publisher account needed. Defaults
    to games-only: all four `include_dlc`/`include_software`/
    `include_videos`/`include_hardware` flags default false (confirmed:
    passing `include_dlc=true` at the same `max_results` reaches a much
    lower `last_appid` than the default call, proving DLC rows are
    genuinely excluded by default, not just rare). `if_modified_since`
    (a Unix timestamp) genuinely filters — confirmed: returned appids
    jump non-sequentially and every `last_modified` is past the cutoff,
    unlike the strictly-ascending default walk. Paginate by passing the
    previous response's `last_appid` back in as the next call's
    `last_appid`, until `have_more_results` is false. The OLD
    `ISteamApps/GetAppList/v2` is a confirmed hard 404 now — dead, not a
    fallback.
  - `store.steampowered.com/api/appdetails` — one app per call (no
    batching), no key needed. `{"<appid>": {"success": bool, "data":
    {...}}}` — `success=False` or a missing `data` key means this app has
    no store page (delisted, region-locked, etc.), not an error to abort
    a whole run over.

**VR lives in `categories`, not `genres`** — confirmed live against
Half-Life: Alyx (appid 546560): its `genres` is just ["Action",
"Adventure"], no VR signal there at all, while `categories` carries both
id 31 ("VR Support") and id 54 ("VR Only"). Checked by numeric id, not by
matching the description string, since ids are the stable part of the
contract. One real quirk found while doing this: `categories[].id` comes
back as a JSON int, but `genres[].id` comes back as a JSON STRING (e.g.
`"1"`) — inconsistent within the same response, handled defensively below
rather than assumed uniform.

**Indie**: `"Indie"` appearing as a genre description. Multi-valued, not
a taxonomy — a title can carry "Indie" and "Action" simultaneously, and
there is no positive "AAA" signal, only the absence of "Indie".

**recommendations.total**: the whole `recommendations` key can be absent
from a response entirely — treated as NULL (unknown), never coerced to 0,
since "no recommendations field" and "confirmed zero recommendations" are
different facts. `low_relevance_flag` fires when total is NULL or below
LOW_RELEVANCE_THRESHOLD (10, picked as a conservative "essentially nobody
has weighed in" cutoff, not a rigorous statistical threshold — documented
here as a judgment call, not asserted as principled). This is a FLAG,
never a filter: volume/count analyses need the complete catalog to stay
honest; composition/lifecycle analyses can exclude flagged rows when
noise, not volume, is what matters.
"""

from __future__ import annotations

import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx

APPLIST_URL = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"

APPLIST_PAGE_SIZE = 5000  # well within a single call; Valve accepts up to 50000, but a moderate page keeps memory/retry blast-radius small
MAX_RETRIES = 5
LOW_RELEVANCE_THRESHOLD = 10

# appdetails has no batching (one app per call, unlike GetAppList) and no
# officially-published rate limit the way Liquipedia's API terms document
# one — unlike collectors/liquipedia.py's RateLimiter(min_interval=2.0),
# this interval is a conservative, community-informed estimate, not a
# confirmed published term. Applied proactively (paced before every call,
# not just backed off after a 429) for the same reason liquipedia.py
# paces its own requests: a long, unbatched sweep (Track A walks the
# entire catalog; Track B's first run alone was measured live at ~10,300
# apps for a naive 7-day if_modified_since window) hammering an endpoint
# as fast as network round-trips allow is inconsiderate regardless of
# whether Valve happens to tolerate it, and reactive-only backoff is also
# slower in practice once 429s start compounding.
APPDETAILS_MIN_INTERVAL = 1.5


@dataclass
class RateLimiter:
    min_interval: float
    _last_call: float = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last_call
        remaining = self.min_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_call = time.monotonic()


_appdetails_limiter = RateLimiter(APPDETAILS_MIN_INTERVAL)

VR_SUPPORT_CATEGORY_ID = 31
VR_ONLY_CATEGORY_ID = 54

# Observed real formats for appdetails' release_date.date — "Coming soon",
# "TBD", and "" are all real observed values that intentionally fail every
# format below, producing release_date=NULL rather than a guess.
_DATE_FORMATS = ("%d %b, %Y", "%b %d, %Y", "%B %d, %Y", "%d %B, %Y", "%b %Y", "%B %Y", "%Y")


@dataclass
class RunErrors:
    items: list[dict] = field(default_factory=list)

    def add(self, scope: str, message: str) -> None:
        self.items.append({"scope": scope, "message": message})
        print(f"[error] {scope}: {message}", file=sys.stderr)


def backoff_seconds(attempt: int) -> float:
    base = min(2**attempt, 60)
    return base + random.uniform(0, 1)


def _parse_release_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def classify_app(data: dict) -> dict:
    """Pure function, no network I/O — takes one app's already-unwrapped
    appdetails `data` dict, returns a dict matching steam_release_history's
    columns (minus app_id/fetched_at/source/confidence, which callers add)."""
    release_date = data.get("release_date") or {}
    release_date_raw = release_date.get("date")

    genres = data.get("genres") or []
    genre_names = [g.get("description") for g in genres if g.get("description")]
    is_indie = "Indie" in genre_names

    categories = data.get("categories") or []
    category_names = [c.get("description") for c in categories if c.get("description")]
    # id inconsistently comes back as int (categories) vs string (genres)
    # in the live API — compare as strings on both sides to be safe.
    category_ids = {str(c.get("id")) for c in categories if c.get("id") is not None}
    has_vr_support = str(VR_SUPPORT_CATEGORY_ID) in category_ids
    vr_only = str(VR_ONLY_CATEGORY_ID) in category_ids

    developers = data.get("developers") or []
    publishers = data.get("publishers") or []

    recommendations = data.get("recommendations")
    recommendations_total = recommendations.get("total") if isinstance(recommendations, dict) else None
    low_relevance_flag = recommendations_total is None or recommendations_total < LOW_RELEVANCE_THRESHOLD

    return {
        "name": data.get("name"),
        "app_type": data.get("type"),
        "release_date_raw": release_date_raw,
        "release_date": _parse_release_date(release_date_raw),
        "is_released": 0 if release_date.get("coming_soon") else 1,
        "genres": ",".join(genre_names) if genre_names else None,
        "is_indie": 1 if is_indie else 0,
        "categories": ",".join(category_names) if category_names else None,
        "has_vr_support": 1 if has_vr_support else 0,
        "vr_only": 1 if vr_only else 0,
        "developers": ",".join(developers) if developers else None,
        "publishers": ",".join(publishers) if publishers else None,
        "recommendations_total": recommendations_total,
        "low_relevance_flag": 1 if low_relevance_flag else 0,
    }


def _request_with_retry(client: httpx.Client, url: str, params: dict, errors: RunErrors, scope: str) -> httpx.Response | None:
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

        if resp.status_code >= 400:
            errors.add(scope, f"status {resp.status_code}: {resp.text[:200]}")
            return None

        return resp

    return None


def fetch_app_list_page(
    client: httpx.Client, api_key: str, errors: RunErrors, *,
    if_modified_since: int | None = None, last_appid: int | None = None,
) -> dict | None:
    """One GetAppList page. Returns the raw {"apps", "have_more_results",
    "last_appid"} dict, or None on failure."""
    params: dict = {"key": api_key, "max_results": APPLIST_PAGE_SIZE}
    if if_modified_since is not None:
        params["if_modified_since"] = if_modified_since
    if last_appid is not None:
        params["last_appid"] = last_appid

    resp = _request_with_retry(client, APPLIST_URL, params, errors, "GetAppList")
    if resp is None:
        return None
    return resp.json().get("response", {})


def paginate_app_list(client: httpx.Client, api_key: str, errors: RunErrors, *, if_modified_since: int | None = None):
    """Yields one page (list of {"appid","name","last_modified",...} dicts)
    at a time until GetAppList reports have_more_results=False or a page
    fetch fails outright."""
    last_appid = None
    while True:
        page = fetch_app_list_page(client, api_key, errors, if_modified_since=if_modified_since, last_appid=last_appid)
        if page is None:
            return
        apps = page.get("apps", [])
        if apps:
            yield apps
        if not page.get("have_more_results"):
            return
        last_appid = page.get("last_appid")
        if last_appid is None:
            return


def fetch_appdetails(client: httpx.Client, appid: int, errors: RunErrors, scope: str) -> dict | None:
    """One appdetails call. Returns the unwrapped `data` dict, or None when
    the app has no store data (success=False/missing) or the request
    itself failed — both logged, both treated as "couldn't classify,"
    not something to crash a long-running sweep over.

    Proactively paced via _appdetails_limiter (see its own comment) —
    every caller of this function gets the same considerate pacing for
    free, rather than each of Track A/B needing to remember to apply it."""
    _appdetails_limiter.wait()
    resp = _request_with_retry(client, APPDETAILS_URL, {"appids": appid}, errors, scope)
    if resp is None:
        return None
    body = resp.json()
    entry = body.get(str(appid)) or {}
    if not entry.get("success") or not entry.get("data"):
        return None
    return entry["data"]
