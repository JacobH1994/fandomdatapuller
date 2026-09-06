#!/usr/bin/env python3
"""Classify each viewership_snapshots row's broadcast_tier — the
annotation pass, per PRD §9.1's three-condition detection:

  - primary_official: `is_official_broadcast=1` (already determined at
    capture time against config/channels.yaml — collectors/twitch_poll.py
    — not recomputed here against today's config, same "as of capture
    time" convention that column already follows).
  - detected_costream: ALL THREE of (a) the stream's title_id equals a
    tournament's title_id, (b) `captured_at` falls within that
    tournament's [start_date, end_date], (c) the stream's title or tags
    contain one of that tournament's SERIES's `tournament_aliases`
    (looked up via `tournaments.series_key`, not `tournament_id` — an
    alias identifies a recurring series, not one edition; this condition
    is what disambiguates which edition it is), matched with word-boundary
    regex (e.g. `\\bmsi\\b`), case-insensitive unless the alias's
    `case_sensitive` flag is set (aliases under 4 characters, e.g. "TI" —
    see etl/generate_tournament_aliases.py). Matched against ANY
    qualifying tournament — several can run concurrently for one title
    (parallel regional splits).
  - general: everything else. Every row in viewership_snapshots is
    already tier-1/tier-2 by construction (tier-3 streams never get an
    individual row at all — collectors/twitch_poll.py), so no further
    tier filtering happens here.

**Stores WHY, not just the verdict**: `matched_tournament_id` and
`matched_alias` alongside `broadcast_tier`, so any detected_costream
classification is auditable — re-derivable from the stored evidence, not
a bare label to take on faith.

confidence per PRD §9.1: `primary_official`/`general` = 'verified' (a
deterministic check against an already-verified column); `detected_costream`
= 'proxy_estimate' — an imperfect text-match heuristic, explicitly no more
confident than that even when it fires (a streamer reacting to highlights
without showing the live feed can still match on text — an accepted,
priced-in tradeoff, not a bug to chase).

**Incremental by default** (`broadcast_tier IS NULL` only). `--full-reclassify`
reclassifies every row — needed because tournament_aliases or
config/channels.yaml can improve after earlier rows were already
classified against a worse ruleset; without an explicit full re-run,
those earlier rows silently stay wrong against an outdated rule set
forever, which is worse than the cost of redoing the classification work.

Usage:
    python etl/classify_broadcast_tier.py
    python etl/classify_broadcast_tier.py --full-reclassify
    python etl/classify_broadcast_tier.py --titles league_of_legends,dota2
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from etl.db import get_connection, utcnow_iso  # noqa: E402


def compile_alias_pattern(alias: str, case_sensitive: bool = False) -> re.Pattern:
    """Word-boundary match (PRD §9.1 condition 3) — but `\\b` itself breaks
    when the alias starts or ends with a non-word character, which real
    aliases do (e.g. the game's own name, "Guilty Gear -STRIVE-"): `\\b`
    requires a word/non-word transition exactly at the match edge, so a
    match ending in "-" immediately followed by a space has no such
    transition and `\\b` silently fails to match text it obviously should.
    `(?<!\\w)`/`(?!\\w)` check the character outside the match instead,
    which is what "word boundary" actually needs to mean here — confirmed
    by a failing test on exactly this alias before this fix.

    case_sensitive=True (tournament_aliases.case_sensitive, set for
    aliases under 4 characters — see etl/generate_tournament_aliases.py)
    drops the default IGNORECASE: "TI" or "MSI" matched case-insensitively
    would false-positive constantly against unrelated text even with word
    boundaries enforced."""
    escaped = re.escape(alias)
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(r"(?<!\w)" + escaped + r"(?!\w)", flags)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--titles", help="comma-separated title ids (default: all)")
    parser.add_argument(
        "--full-reclassify", action="store_true",
        help="reclassify every row, not just broadcast_tier IS NULL ones",
    )
    args = parser.parse_args()

    conn = get_connection()
    started_at = utcnow_iso()

    title_filter = ""
    params: tuple = ()
    if args.titles:
        title_ids = [t.strip() for t in args.titles.split(",")]
        title_filter = "AND vs_.title_id IN (" + ",".join("?" for _ in title_ids) + ")"
        params = tuple(title_ids)

    scope_clause = "" if args.full_reclassify else "AND vs_.broadcast_tier IS NULL"
    rows = conn.execute(
        f"""
        SELECT vs_.id, vs_.title_id, vs_.captured_at, vs_.is_official_broadcast,
               vs_.stream_title, vs_.tags
        FROM viewership_snapshots vs_
        WHERE 1=1 {scope_clause} {title_filter}
        """,
        params,
    ).fetchall()

    print(f"{len(rows)} row(s) to classify ({'full reclassify' if args.full_reclassify else 'incremental, unclassified only'})")
    if not rows:
        conn.close()
        return 0

    # Precompute candidate tournaments per (title_id, captured_at) once —
    # captured_at is shared by every stream in the same poll (one raw file
    # per timestamp), so this is a handful of combinations, not one lookup
    # per row. For each, find tournaments live at that moment for that
    # title and pre-compile their aliases' word-boundary patterns.
    distinct_keys = {(r[1], r[2]) for r in rows}
    print(f"{len(distinct_keys)} distinct (title_id, captured_at) combination(s) to resolve tournament candidates for")

    candidates_by_key: dict[tuple[str, str], list[tuple[int, list[tuple[str, re.Pattern]]]]] = {}
    alias_cache: dict[tuple[str, str], list[tuple[str, re.Pattern]]] = {}

    for title_id, captured_at in distinct_keys:
        date_ = captured_at[:10]
        tournament_rows = conn.execute(
            """
            SELECT id, series_key FROM tournaments
            WHERE title_id = ? AND start_date IS NOT NULL AND end_date IS NOT NULL
              AND date(start_date) <= date(?) AND date(end_date) >= date(?)
            """,
            (title_id, date_, date_),
        ).fetchall()

        candidates = []
        for tournament_id, series_key in tournament_rows:
            if series_key is None:
                continue  # not tier-1/2, or predates generate_tournament_aliases.py — no aliases possible
            cache_key = (title_id, series_key)
            if cache_key not in alias_cache:
                alias_rows = conn.execute(
                    "SELECT alias, case_sensitive FROM tournament_aliases WHERE title_id = ? AND series_key = ?",
                    (title_id, series_key),
                ).fetchall()
                alias_cache[cache_key] = [
                    (a, compile_alias_pattern(a, bool(cs))) for (a, cs) in alias_rows if a
                ]
            if alias_cache[cache_key]:
                candidates.append((tournament_id, alias_cache[cache_key]))
        candidates_by_key[(title_id, captured_at)] = candidates

    now = utcnow_iso()
    counts = defaultdict(int)

    for row_id, title_id, captured_at, is_official, stream_title, tags in rows:
        if is_official:
            broadcast_tier, confidence, matched_tournament_id, matched_alias = "primary_official", "verified", None, None
        else:
            search_text = " ".join(filter(None, [stream_title, (tags or "").replace(",", " ")]))
            match = None
            for tournament_id, patterns in candidates_by_key.get((title_id, captured_at), []):
                for alias, pattern in patterns:
                    if search_text and pattern.search(search_text):
                        match = (tournament_id, alias)
                        break
                if match:
                    break

            if match:
                broadcast_tier, confidence = "detected_costream", "proxy_estimate"
                matched_tournament_id, matched_alias = match
            else:
                broadcast_tier, confidence, matched_tournament_id, matched_alias = "general", "verified", None, None

        counts[broadcast_tier] += 1
        conn.execute(
            """
            UPDATE viewership_snapshots
            SET broadcast_tier = ?, broadcast_tier_confidence = ?,
                matched_tournament_id = ?, matched_alias = ?
            WHERE id = ?
            """,
            (broadcast_tier, confidence, matched_tournament_id, matched_alias, row_id),
        )

    conn.commit()

    finished_at = utcnow_iso()
    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('classify_broadcast_tier', NULL, ?, ?, 'ok', ?, NULL)
        """,
        (started_at, finished_at, len(rows)),
    )
    conn.commit()
    conn.close()

    print(f"classified {len(rows)} row(s): " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
