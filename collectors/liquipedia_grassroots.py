#!/usr/bin/env python3
"""One-time, on-demand crawl of the lower-tier ("grassroots"/community)
tournament tiers Liquipedia tracks below the tier-1/2 scope `collectors/
liquipedia.py` deliberately restricts itself to (that file's own
docstring: TIER_CONVENTIONS only tries S/A-Tier or Tier-1/2 categories).

Built 2026-09-08 for `docs/counter_strike_lifecycle_brief.md`'s grassroots-
scene question (is the base of the competitive pyramid narrowing too, not
just tier-1/2) — the notebook's own §15 proxy (extracting a year from each
page's title, no per-page fetch) undercounts 44-47% of pages and was
explicitly flagged there as suggestive, not conclusive. This script gets
the real thing: each page's actual `start_date` from its own Infobox
league template, same as the tier-1/2 crawl.

Liquipedia's tier taxonomy is NOT standardized across wikis (confirmed
already in collectors/liquipedia.py's own docstring) — checked directly
here too: counterstrike uses "B-Tier Tournaments"/"C-Tier Tournaments",
dota2 uses "Tier 3 Tournaments"/"Tier 4 Tournaments". LOWER_TIER_CATEGORIES
below is therefore an explicit per-wiki mapping, not a guessed convention
list — deliberately scoped to just the two titles this was built for
(counter_strike, dota2), not generalized to all 23 tracked titles.

Scale, measured live before running (2026-09-09): counterstrike B-Tier
2,711 + C-Tier 15,448 = 18,159 pages; dota2 Tier 3 1,978 + Tier 4 1,050 =
3,028 pages. ~21,187 pages total, ~11-12 hours at the project's 2s/request
Liquipedia rate limit (liquipedia.net/api-terms-of-use) for the wikitext
fetches alone. A real multi-hour commitment, same category as
collectors/steam_catalog_backfill.py's Track A — patient, resumable
(skips pages already in `tournaments`, same idempotent-skip pattern as
collectors/liquipedia.py), safe to interrupt and rerun.

Writes into the SAME `tournaments` table as the tier-1/2 crawl (natural
key `(liquipedia_wiki, liquipedia_page)`, no schema change needed — `tier`
is already a free-text column). Every existing downstream reader
(`analysis/metrics.py`, `etl/generate_tournament_aliases.py`,
`etl/classify_broadcast_tier.py`) already filters explicitly by tier
('1'/'2'/'S-Tier'/'A-Tier'), so adding B/C-Tier and Tier-3/4 rows to the
same table doesn't silently change any existing tier-1/2 result --
checked, not assumed, before running this.

Usage:
    python collectors/liquipedia_grassroots.py                    # counter_strike, dota2 (default)
    python collectors/liquipedia_grassroots.py --titles counter_strike
    python collectors/liquipedia_grassroots.py --refresh           # also re-fetch/re-parse known pages
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import httpx  # noqa: E402

from etl.db import get_connection  # noqa: E402
from collectors.liquipedia import (  # noqa: E402
    USER_AGENT,
    GENERAL_MIN_INTERVAL,
    RateLimiter,
    Cache,
    CACHE_DIR,
    category_members,
    fetch_wikitext,
    parse_infobox,
    upsert_tournament,
    utcnow_iso,
)

LOWER_TIER_CATEGORIES: dict[str, tuple[str, list[str]]] = {
    # title_id -> (liquipedia_wiki, [lower-tier category names])
    "counter_strike": ("counterstrike", ["B-Tier Tournaments", "C-Tier Tournaments"]),
    "dota2": ("dota2", ["Tier 3 Tournaments", "Tier 4 Tournaments"]),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--titles",
        default="counter_strike,dota2",
        help="comma-separated title ids (default: counter_strike,dota2 -- the only ones LOWER_TIER_CATEGORIES maps)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="force re-fetch and re-parse of pages already in research.db (default: skip them, resumable)",
    )
    args = parser.parse_args()

    wanted = args.titles.split(",")
    unknown = [t for t in wanted if t not in LOWER_TIER_CATEGORIES]
    if unknown:
        print(f"[error] no LOWER_TIER_CATEGORIES mapping for: {', '.join(unknown)} -- add one before running", file=sys.stderr)
        return 1

    conn = get_connection()
    cache = Cache(CACHE_DIR, refresh=args.refresh)
    limiter = RateLimiter(GENERAL_MIN_INTERVAL)
    started_at = utcnow_iso()
    rows_written = 0
    errors: list[str] = []

    known_pages_by_wiki: dict[str, set[str]] = {}
    if not args.refresh:
        for wiki, page in conn.execute("SELECT liquipedia_wiki, liquipedia_page FROM tournaments"):
            known_pages_by_wiki.setdefault(wiki, set()).add(page)

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for title_id in wanted:
            wiki, categories = LOWER_TIER_CATEGORIES[title_id]
            print(f"[info] {title_id}: discovering pages in {categories} on wiki '{wiki}'...", flush=True)
            all_pages: set[str] = set()
            for category in categories:
                pages = category_members(client, wiki, category, limiter)
                print(f"[info]   {category}: {len(pages)} pages", flush=True)
                all_pages |= set(pages)

            known = known_pages_by_wiki.get(wiki, set())
            to_fetch = sorted(p for p in all_pages if p not in known)
            print(
                f"[info] {title_id}: {len(all_pages)} candidate pages total, "
                f"{len(to_fetch)} new (skipping {len(all_pages) - len(to_fetch)} already in research.db)",
                flush=True,
            )

            for i, page_title in enumerate(to_fetch, 1):
                if i % 100 == 0:
                    print(f"[info] {title_id}: {i}/{len(to_fetch)} new pages processed ({rows_written} written so far)", flush=True)
                wikitext = fetch_wikitext(client, wiki, page_title, limiter, cache)
                if wikitext is None:
                    errors.append(f"{title_id}/{page_title}: page fetch failed or missing")
                    continue
                fields = parse_infobox(wikitext)
                if fields is None:
                    errors.append(f"{title_id}/{page_title}: no Infobox league template found")
                    continue
                upsert_tournament(conn, title_id, wiki, page_title, fields)
                conn.commit()
                rows_written += 1

    finished_at = utcnow_iso()
    status = "ok" if not errors else "partial"
    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('liquipedia_grassroots', NULL, ?, ?, ?, ?, ?)
        """,
        (started_at, finished_at, status, rows_written, "; ".join(errors[:20]) or None),
    )
    conn.commit()
    conn.close()

    print(f"wrote {rows_written} tournament rows (status={status}, page_errors={len(errors)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
