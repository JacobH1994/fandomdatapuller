#!/usr/bin/env python3
"""Extracts a self-declared region marker from each viewership_snapshots/
platform_viewership_snapshots row's own `tags`/`title` text (PRD §9.17,
one of the fandom-region-decomposition signals — see
analysis/fandom_region_decomposition.py's module docstring for the
subsystem this feeds).

**Region-tag whitelist checked against real observed tags before
shipping, not assumed** (same discipline etl/classify_gta_content_segment.py
already applies to its own tag rules): pulled every distinct tag matching
a region-code-shaped pattern across `viewership_snapshots.tags` and
confirmed each candidate below actually behaves as a real region marker
at scale — NA (1,567), UK (1,626), EU (1,238), EUW (1,506), EUNE (105),
OCE (2,312), SEA (372), LATAM (2,134), LAN (543), LAS (388), APAC (111),
ANZ (32), KR (43), JP (837), EMEA (36), MENA (69), NAE (61), NAW (13).

**"BR" deliberately excluded, not overlooked**: it's genuinely ambiguous
at scale — heavily used as a Battle Royale *game-mode* tag in Fortnite/
PUBG/Apex Legends as well as a Brazil *region* tag in League of Legends/
VALORANT (both real, confirmed by title-by-title breakdown), and this
extractor has no per-title disambiguation logic. A wrong region label is
worse than a missing one, so "BR" is skipped entirely rather than guessed
from title context.

Only TAGS are checked against the whitelist directly (a comma-joined
list of short, already-curated tokens, so an exact case-insensitive tag
match is low-risk). Stream TITLES (free prose) additionally get a
narrower, longer-substring-only pattern — the short 2-3 letter codes are
too collision-prone in free text (a casual "na" mid-sentence isn't a
region declaration) to trust there.

A stream tagged with more than one DISTINCT canonical region (e.g. both
NA and EU tags on the same stream — seen in practice from co-stream/
multi-region event coverage) gets NULL, not a guess at which one "wins" —
conflicting self-declaration is a real signal that this stream doesn't
cleanly belong to one region, not noise to resolve.

Incremental by default (self_declared_region_tag IS NULL only, same
convention as classify_broadcast_tier.py/classify_gta_content_segment.py).
`--full-reclassify` reclassifies every row.

Usage:
    python etl/extract_stream_region_tags.py
    python etl/extract_stream_region_tags.py --full-reclassify
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

# Raw tag token (case-insensitive, exact match) -> canonical region.
# Several raw codes fold into one canonical region (EUW/EUNE/EU -> "EU",
# NAE/NAW/NA -> "NA", LAN/LAS/LATAM -> "LATAM", OCE/ANZ -> "OCE") since
# they're the same real-world region at a finer server-shard granularity
# this project has no other use for. SEA and APAC are kept distinct
# (Southeast Asia is a strict subset of the broader Asia-Pacific label,
# and collapsing them would overstate agreement between two streams that
# only share the broader claim).
TAG_TO_REGION: dict[str, str] = {
    "na": "NA", "nae": "NA", "naw": "NA",
    "eu": "EU", "euw": "EU", "eune": "EU", "emea": "EU",
    "uk": "UK",
    "oce": "OCE", "anz": "OCE",
    "sea": "SEA",
    "apac": "APAC",
    "latam": "LATAM", "lan": "LATAM", "las": "LATAM",
    "kr": "KR",
    "jp": "JP",
    "mena": "MENA",
}

# Free-text title patterns -- long, distinctive substrings only (see
# module docstring for why the short tag codes above aren't reused here).
TITLE_REGION_PATTERNS: dict[str, re.Pattern] = {
    "NA": re.compile(r"(?<!\w)north\s?america(?!\w)", re.IGNORECASE),
    "EU": re.compile(r"(?<!\w)europe(?!\w)", re.IGNORECASE),
    "OCE": re.compile(r"(?<!\w)oceania(?!\w)", re.IGNORECASE),
    "SEA": re.compile(r"(?<!\w)south\s?east\s?asia(?!\w)", re.IGNORECASE),
    "LATAM": re.compile(r"(?<!\w)latin\s?america(?!\w)", re.IGNORECASE),
}


def classify_tags(tags: str | None) -> set[str]:
    regions = set()
    for tag in (tags or "").split(","):
        canonical = TAG_TO_REGION.get(tag.strip().lower())
        if canonical:
            regions.add(canonical)
    return regions


def classify_title(title: str | None) -> set[str]:
    text = title or ""
    return {region for region, pattern in TITLE_REGION_PATTERNS.items() if pattern.search(text)}


def classify_row(title: str | None, tags: str | None) -> str | None:
    """None if no region signal found, or if the tag/title signals
    disagree on more than one distinct region (see module docstring)."""
    regions = classify_tags(tags) | classify_title(title)
    if len(regions) == 1:
        return next(iter(regions))
    return None


def _classify_table(conn, *, table: str, title_column: str, full_reclassify: bool) -> tuple[int, dict[str, int]]:
    scope_clause = "" if full_reclassify else "AND self_declared_region_tag IS NULL"
    rows = conn.execute(
        f"SELECT id, {title_column}, tags FROM {table} WHERE tags IS NOT NULL {scope_clause}"
    ).fetchall()

    counts: dict[str, int] = defaultdict(int)
    for row_id, title, tags in rows:
        region = classify_row(title, tags)
        counts[region or "none"] += 1
        conn.execute(
            f"UPDATE {table} SET self_declared_region_tag = ?, self_declared_region_tag_confidence = 'ai_assisted_unreviewed' WHERE id = ?",
            (region, row_id),
        )
    conn.commit()
    return len(rows), counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--full-reclassify", action="store_true",
        help="reclassify every row with a non-NULL tags value, not just self_declared_region_tag IS NULL ones",
    )
    args = parser.parse_args()

    conn = get_connection()
    started_at = utcnow_iso()

    total_rows = 0
    for table, title_column in (
        ("viewership_snapshots", "stream_title"),
        ("platform_viewership_snapshots", "stream_title"),
    ):
        n, counts = _classify_table(conn, table=table, title_column=title_column, full_reclassify=args.full_reclassify)
        total_rows += n
        print(f"{table}: classified {n} row(s): " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    finished_at = utcnow_iso()
    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('extract_stream_region_tags', NULL, ?, ?, 'ok', ?, NULL)
        """,
        (started_at, finished_at, total_rows),
    )
    conn.commit()
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
