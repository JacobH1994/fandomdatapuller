#!/usr/bin/env python3
"""Classifies each platform_viewership_snapshots row's content_segment --
the nested GTA-RP taxonomy requested directly by the user (2026-09-10):
NoPixel is a subdivision of GTA RP, GTA RP is a subdivision of GTA V, all
three levels tracked at real granularity going forward, not just
NoPixel-vs-everything-else.

Segments (checked in this order, most specific first):
  - nopixel: title or tags mention "nopixel"/"no pixel" (the same test
    already used ad hoc in notebooks/gta_v_deep_dive.ipynb and
    notebooks/mlbb_russia_deep_dive.ipynb-adjacent investigation, now
    persisted instead of re-derived per-notebook).
  - gta_rp_other: roleplay-indicating, but not NoPixel specifically --
    the hundreds of other named GTA RP servers (LegacyRP, MajesticRP,
    CapitalRP, the TARP family, ...).
  - non_rp: everything else in the game (free roam, story mode, stunts,
    heists content, ...).

**Why tags need different matching logic than the title, confirmed
against real data before writing this, not assumed**: pulled every
distinct GTA V tag seen so far (761 of 7,262 looked RP-related) and
found the overwhelming majority are smashed-together compound words with
no internal separator ("LegacyRP", "GTAVFiveM", "nopixelrp") -- the
word-boundary regex etl/classify_broadcast_tier.py uses for tournament
aliases would silently miss nearly all of them, since `\\b`-style
matching needs a non-word character at the match edge that these tags
don't have.

A naive substring-anywhere match on bare "rp" has the opposite problem
-- confirmed real false positives in the same tag pull: "CareerProgress",
"BurpsAndFarts", "Sharpness", "ContentCreatorProgram", "controllerplayer",
and (in stream titles) "Cyberpunk2077" all contain "rp" mid-word with no
roleplay connection at all.

The fix, validated against both sets of real examples before shipping:
  - Long, distinctive substrings ("roleplay", "fivem", "gtarp") match
    anywhere in a tag -- effectively zero collision risk at that length.
  - Bare "rp" is only trusted as a tag *suffix* ("...rp"), which is the
    real convention (every false positive above fails this test; every
    real RP tag found passes it, including the standalone "RP" tag).
  - "tarp" is a real, repeatedly-observed community-name family (TARP,
    TarpAmbassador, TARPPartnered, ...) that doesn't fit the suffix
    pattern -- special-cased as a tag *prefix*, a deliberate, documented
    judgment call, not a general rule.
  - The stream title (free-text prose, not a curated tag) keeps
    word-boundary matching instead -- "rp" as an isolated word in a
    sentence is a real signal; "rp" as a substring of an unrelated word
    in prose is not.

**Incremental by default** (`content_segment IS NULL` only, same
convention as classify_broadcast_tier.py). `--full-reclassify`
reclassifies every row -- needed if this ruleset itself improves later.
Currently only game_id='32982' (Grand Theft Auto V) has a ruleset; rows
for every other game are left with content_segment=NULL (not
applicable, not "unclassified").

Usage:
    python etl/classify_gta_content_segment.py
    python etl/classify_gta_content_segment.py --full-reclassify
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

GTA_V_GAME_ID = "32982"

NOPIXEL_SUBSTRINGS = ("nopixel", "no pixel")
RP_SAFE_SUBSTRINGS = ("roleplay", "fivem", "gtarp")
RP_TAG_PREFIXES = ("tarp",)

# Word-boundary patterns for the free-text title -- same (?<!\w)/(?!\w)
# convention as classify_broadcast_tier.py's compile_alias_pattern, for
# the same reason (plain \b breaks at non-word match edges).
TITLE_NOPIXEL_PATTERN = re.compile(r"(?<!\w)no\s?pixel(?!\w)", re.IGNORECASE)
TITLE_RP_PATTERN = re.compile(
    r"(?<!\w)(roleplay|fivem|gtarp|rp)(?!\w)", re.IGNORECASE
)


def classify_tag(tag: str) -> str | None:
    """Returns 'nopixel', 'gta_rp_other', or None (not RP-indicating) for
    one tag, using substring/suffix/prefix rules validated against real
    observed tags (see module docstring)."""
    t = tag.strip().lower()
    if not t:
        return None
    if any(s in t for s in NOPIXEL_SUBSTRINGS):
        return "nopixel"
    if any(s in t for s in RP_SAFE_SUBSTRINGS):
        return "gta_rp_other"
    if t.endswith("rp"):
        return "gta_rp_other"
    if t.startswith(RP_TAG_PREFIXES):
        return "gta_rp_other"
    return None


def classify_row(stream_title: str | None, tags: str | None) -> str:
    """nopixel > gta_rp_other > non_rp, most specific match wins."""
    tag_list = [t for t in (tags or "").split(",") if t.strip()]
    tag_segments = {classify_tag(t) for t in tag_list}
    tag_segments.discard(None)
    if "nopixel" in tag_segments:
        return "nopixel"

    title = stream_title or ""
    if TITLE_NOPIXEL_PATTERN.search(title):
        return "nopixel"

    if "gta_rp_other" in tag_segments:
        return "gta_rp_other"
    if TITLE_RP_PATTERN.search(title):
        return "gta_rp_other"

    return "non_rp"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--full-reclassify", action="store_true",
        help="reclassify every GTA V row, not just content_segment IS NULL ones",
    )
    args = parser.parse_args()

    conn = get_connection()
    started_at = utcnow_iso()

    scope_clause = "" if args.full_reclassify else "AND content_segment IS NULL"
    rows = conn.execute(
        f"""
        SELECT id, stream_title, tags
        FROM platform_viewership_snapshots
        WHERE game_id = ? {scope_clause}
        """,
        (GTA_V_GAME_ID,),
    ).fetchall()

    print(f"{len(rows)} GTA V row(s) to classify ({'full reclassify' if args.full_reclassify else 'incremental, unclassified only'})")
    if not rows:
        conn.close()
        return 0

    counts: dict[str, int] = defaultdict(int)
    for row_id, stream_title, tags in rows:
        segment = classify_row(stream_title, tags)
        counts[segment] += 1
        conn.execute(
            "UPDATE platform_viewership_snapshots SET content_segment = ?, content_segment_confidence = 'proxy_estimate' WHERE id = ?",
            (segment, row_id),
        )

    conn.commit()

    finished_at = utcnow_iso()
    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('classify_gta_content_segment', NULL, ?, ?, 'ok', ?, NULL)
        """,
        (started_at, finished_at, len(rows)),
    )
    conn.commit()
    conn.close()

    print(f"classified {len(rows)} row(s): " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
