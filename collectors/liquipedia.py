#!/usr/bin/env python3
"""Liquipedia tournament connector (PRD §9.2, revised per user instruction).

The PRD originally specified this against the LPDB API. LPDB requires an
approved registration the user doesn't have. Confirmed live against
Liquipedia's own terms (liquipedia.net/api-terms-of-use) that the standard
MediaWiki API needs no registration at all, so this connector uses that
instead: `action=query&list=categorymembers` to discover tournament pages,
`action=query&prop=revisions` to fetch their wikitext, and mwparserfromhell
to parse the `Infobox league` template out of it. `action=parse` is never
used — it's rate-limited to 1 req/30s vs. the general endpoint's 1 req/2s,
and raw wikitext plus a template parser gets the same data faster.

Tier taxonomy is NOT standardized across Liquipedia's per-game wikis —
confirmed live during design: Counter-Strike uses S-Tier/A-Tier, Dota 2 uses
Tier 1/Tier 2, VALORANT has A-Tier as its top rung (no S-Tier exists), and
the shared fighting-games wiki has no tier categories at all (competitions
are grouped as "<Game> <Version> Competitions" instead). This connector
tries known conventions in order and uses whichever one actually has
members on a given wiki; a title whose wiki matches neither is logged and
skipped rather than guessed. As of this connector's initial build, that
means the four fighting-game titles (tekken, street_fighter, mortal_kombat,
guilty_gear) get no tournament data yet — a known gap, not a silent one.

That category-naming variance turns out to be cosmetic, not structural:
confirmed empirically (a real teamfight_tactics pull) that the infobox's own
`liquipediatier` field is a plain number ("1", "2", ...) — the S-Tier/A-Tier
and Tier 1/Tier 2 category labels are just display names generated from that
same number. `tournaments.tier` stores that raw number, so "A-tier-or-better"
downstream (analysis/metrics.py) is `tier in {"1", "2"}` uniformly, with no
per-wiki label mapping needed despite the discovery-category variance above.

On-demand, not scheduled: historical tournament data doesn't change on a
clock (PRD §9.2). Responses are cached locally under data/cache/liquipedia/
(gitignored — unlike Twitch, this is re-fetchable at any time, so the cache
is disposable, not a permanent record) and re-requested only with --refresh.

Usage:
    python collectors/liquipedia.py
    python collectors/liquipedia.py --titles counter_strike,dota2
    python collectors/liquipedia.py --refresh
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
import mwparserfromhell
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from etl.db import get_connection, seed_titles_and_aliases  # noqa: E402

TITLES_CONFIG = REPO_ROOT / "config" / "titles.yaml"
CACHE_DIR = REPO_ROOT / "data" / "cache" / "liquipedia"

USER_AGENT = (
    "FandomDataPuller/1.0 "
    "(https://github.com/JacobH1994/fandomdatapuller; jacob.harrison1994@gmail.com)"
)

# Tried in order per wiki; first convention with any non-empty category wins.
# See module docstring — this is an empirically-derived list, not a spec.
TIER_CONVENTIONS: list[tuple[str, str]] = [
    ("S-Tier Tournaments", "A-Tier Tournaments"),
    ("Tier 1 Tournaments", "Tier 2 Tournaments"),
]

GENERAL_MIN_INTERVAL = 2.0  # seconds, per liquipedia.net/api-terms-of-use
MAX_RETRIES = 3

# Deliberately incomplete — covers countries actually seen in this project's
# tracked titles' major tournament history. Unmapped countries get
# region=None (logged), never guessed.
COUNTRY_TO_REGION: dict[str, str] = {
    "USA": "North America", "United States": "North America", "Canada": "North America",
    "Mexico": "North America",
    "Brazil": "South America", "Argentina": "South America", "Chile": "South America",
    "Peru": "South America", "Colombia": "South America",
    "United Kingdom": "Europe", "Germany": "Europe", "France": "Europe", "Sweden": "Europe",
    "Poland": "Europe", "Denmark": "Europe", "Finland": "Europe", "Spain": "Europe",
    "Netherlands": "Europe", "Ukraine": "Europe", "Russia": "Europe", "Belgium": "Europe",
    "Portugal": "Europe", "Italy": "Europe", "Czech Republic": "Europe", "Romania": "Europe",
    "Austria": "Europe", "Switzerland": "Europe", "Norway": "Europe", "Turkey": "Europe",
    "South Korea": "Asia", "China": "Asia", "Japan": "Asia", "Singapore": "Asia",
    "Philippines": "Asia", "Malaysia": "Asia", "Indonesia": "Asia", "Vietnam": "Asia",
    "Thailand": "Asia", "India": "Asia", "Taiwan": "Asia", "Saudi Arabia": "Asia",
    "United Arab Emirates": "Asia",
    "Australia": "Oceania", "New Zealand": "Oceania",
    "South Africa": "Africa",
}


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_titles(path: Path) -> list[dict]:
    with open(path) as f:
        config = yaml.safe_load(f)
    return config.get("titles", [])


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


class Cache:
    """Local, disposable, permanent-record-exempt (see module docstring)."""

    def __init__(self, root: Path, refresh: bool):
        self.root = root
        self.refresh = refresh

    def _path(self, wiki: str, kind: str, key: str) -> Path:
        digest = hashlib.sha256(key.encode()).hexdigest()[:20]
        return self.root / wiki / kind / f"{digest}.json"

    def get(self, wiki: str, kind: str, key: str):
        if self.refresh:
            return None
        path = self._path(wiki, kind, key)
        if not path.is_file():
            return None
        return json.loads(path.read_text())

    def set(self, wiki: str, kind: str, key: str, value) -> None:
        path = self._path(wiki, kind, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))


def api_get(client: httpx.Client, wiki: str, params: dict, limiter: RateLimiter) -> dict | None:
    url = f"https://liquipedia.net/{wiki}/api.php"
    params = {**params, "format": "json"}
    for attempt in range(1, MAX_RETRIES + 1):
        limiter.wait()
        try:
            resp = client.get(url, params=params, timeout=30)
        except httpx.RequestError as exc:
            if attempt == MAX_RETRIES:
                print(f"[error] {wiki}: request failed: {exc}", file=sys.stderr)
                return None
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == MAX_RETRIES:
                print(f"[error] {wiki}: status {resp.status_code}", file=sys.stderr)
                return None
            time.sleep(5 * attempt)
            continue
        resp.raise_for_status()
        return resp.json()
    return None


def category_members(
    client: httpx.Client, wiki: str, category: str, limiter: RateLimiter, cache: Cache
) -> list[str]:
    cache_key = f"categorymembers:{category}"
    cached = cache.get(wiki, "categorymembers", cache_key)
    if cached is not None:
        return cached

    titles: list[str] = []
    cmcontinue = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": "500",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
        body = api_get(client, wiki, params, limiter)
        if body is None:
            break
        members = body.get("query", {}).get("categorymembers", [])
        titles.extend(m["title"] for m in members if m.get("ns") == 0)  # ns=0: articles only
        cmcontinue = body.get("continue", {}).get("cmcontinue")
        if not cmcontinue:
            break

    cache.set(wiki, "categorymembers", cache_key, titles)
    return titles


def discover_tournament_pages(
    client: httpx.Client, wiki: str, limiter: RateLimiter, cache: Cache
) -> tuple[list[str], str | None]:
    """Returns (page_titles, convention_used). convention_used is None if no
    known tier convention had any members on this wiki."""
    for top, second in TIER_CONVENTIONS:
        top_pages = category_members(client, wiki, top, limiter, cache)
        second_pages = category_members(client, wiki, second, limiter, cache)
        if top_pages or second_pages:
            combined = sorted(set(top_pages) | set(second_pages))
            return combined, f"{top} + {second}"
    return [], None


def fetch_wikitext(
    client: httpx.Client, wiki: str, page_title: str, limiter: RateLimiter, cache: Cache
) -> str | None:
    cached = cache.get(wiki, "wikitext", page_title)
    if cached is not None:
        return cached.get("wikitext")

    params = {
        "action": "query",
        "titles": page_title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
    }
    body = api_get(client, wiki, params, limiter)
    if body is None:
        return None
    pages = body.get("query", {}).get("pages", {})
    for page in pages.values():
        if "missing" in page:
            cache.set(wiki, "wikitext", page_title, {"wikitext": None})
            return None
        revisions = page.get("revisions", [])
        if revisions:
            wikitext = revisions[0]["slots"]["main"]["*"]
            cache.set(wiki, "wikitext", page_title, {"wikitext": wikitext})
            return wikitext
    return None


NUMERIC_RE = re.compile(r"[\d.]+")


def _clean_number(value: str) -> float | None:
    if not value:
        return None
    match = NUMERIC_RE.search(value.replace(",", ""))
    return float(match.group()) if match else None


def parse_infobox(wikitext: str) -> dict | None:
    """Extracts fields from the `Infobox league` template. Returns None if
    no such template is found (logged by the caller, not guessed)."""
    parsed = mwparserfromhell.parse(wikitext)
    for template in parsed.filter_templates():
        name = template.name.strip().lower()
        if name != "infobox league":
            continue

        def get(param: str) -> str | None:
            if template.has(param):
                return str(template.get(param).value).strip() or None
            return None

        prize_pool = _clean_number(get("prizepoolusd") or get("prizepool") or "")
        return {
            "tier": get("liquipediatier"),
            "prize_pool": prize_pool,
            "currency": "USD" if get("prizepoolusd") else get("localcurrency"),
            "start_date": get("sdate"),
            "end_date": get("edate"),
            "country": get("country"),
            "team_number": int(m.group()) if get("team_number") and (m := NUMERIC_RE.search(get("team_number"))) else None,
        }
    return None


def upsert_tournament(conn: sqlite3.Connection, title_id: str, wiki: str, page_title: str, fields: dict) -> None:
    country = fields.get("country")
    region = COUNTRY_TO_REGION.get(country) if country else None
    conn.execute(
        """
        INSERT INTO tournaments
            (title_id, liquipedia_wiki, liquipedia_page, name, tier, prize_pool,
             currency, start_date, end_date, country, region, region_confidence,
             team_number, fetched_at, source, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'liquipedia', 'verified')
        ON CONFLICT (liquipedia_wiki, liquipedia_page) DO UPDATE SET
            title_id=excluded.title_id, name=excluded.name, tier=excluded.tier,
            prize_pool=excluded.prize_pool, currency=excluded.currency,
            start_date=excluded.start_date, end_date=excluded.end_date,
            country=excluded.country, region=excluded.region,
            region_confidence=excluded.region_confidence,
            team_number=excluded.team_number, fetched_at=excluded.fetched_at
        """,
        (
            title_id, wiki, page_title, page_title, fields.get("tier"),
            fields.get("prize_pool"), fields.get("currency"), fields.get("start_date"),
            fields.get("end_date"), country, region,
            "proxy_estimate" if region else None,
            fields.get("team_number"), utcnow_iso(),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--titles", help="comma-separated title ids (default: all is_active titles)")
    parser.add_argument("--refresh", action="store_true", help="bypass the local cache")
    args = parser.parse_args()

    all_titles = load_titles(TITLES_CONFIG)
    if args.titles:
        wanted = set(args.titles.split(","))
        titles = [t for t in all_titles if t["id"] in wanted]
    else:
        titles = [t for t in all_titles if t.get("is_active")]

    conn = get_connection()
    seed_titles_and_aliases(conn, all_titles)

    cache = Cache(CACHE_DIR, refresh=args.refresh)
    limiter = RateLimiter(GENERAL_MIN_INTERVAL)
    started_at = utcnow_iso()
    rows_written = 0
    skipped_titles: list[str] = []
    errors: list[str] = []

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for t in titles:
            wiki = t["liquipedia_wiki"]
            pages, convention = discover_tournament_pages(client, wiki, limiter, cache)
            if convention is None:
                msg = f"{t['id']}: no recognized tier-category convention on wiki '{wiki}' — skipped"
                print(f"[warn] {msg}", file=sys.stderr)
                skipped_titles.append(t["id"])
                continue

            print(f"[info] {t['id']}: using '{convention}' on wiki '{wiki}' — {len(pages)} candidate pages", flush=True)
            for i, page_title in enumerate(pages, 1):
                if i % 25 == 0:
                    print(f"[info] {t['id']}: {i}/{len(pages)} pages processed", flush=True)
                wikitext = fetch_wikitext(client, wiki, page_title, limiter, cache)
                if wikitext is None:
                    errors.append(f"{t['id']}/{page_title}: page fetch failed or missing")
                    continue
                fields = parse_infobox(wikitext)
                if fields is None:
                    errors.append(f"{t['id']}/{page_title}: no Infobox league template found")
                    continue
                upsert_tournament(conn, t["id"], wiki, page_title, fields)
                conn.commit()  # short-lived transaction per page, not one lock for the whole run
                rows_written += 1

    finished_at = utcnow_iso()
    status = "ok" if not errors and not skipped_titles else "partial"
    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('liquipedia', NULL, ?, ?, ?, ?, ?)
        """,
        (started_at, finished_at, status, rows_written, "; ".join(errors[:20]) or None),
    )
    conn.commit()
    conn.close()

    print(
        f"wrote {rows_written} tournament rows "
        f"(status={status}, skipped_titles={len(skipped_titles)}, page_errors={len(errors)})"
    )
    if skipped_titles:
        print(f"skipped (no tier-category match): {', '.join(skipped_titles)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
