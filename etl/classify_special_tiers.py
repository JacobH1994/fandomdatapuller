#!/usr/bin/env python3
"""Classifies `tournaments_lpdb` rows with `tier='-1'` into sub-categories,
built 2026-10-02 following a direct request to resolve what '-1' means
before trusting any tier-based query. Confirmed live that it is NOT one
thing: StarCraft II's $400K "2017 DreamHack Season" and Overwatch's
official $225K OWL All-Stars sit in the same raw bucket as Age of
Empires II's zero-prize 1v1 community pickup games, weekly "Ranked
Hoops" ladder installments, and at least some plain qualifiers that look
like ordinary real events Liquipedia editors just never tiered (e.g.
Rocket League's "MADNESS: West Qualifier").

Five categories, keyword/structure rules applied in order (first match
wins) -- NOT a prestige axis. A 'showmatch_exhibition' row can be a
$250K official Twitch Rivals special or a $5 AoE2 community 1v1; the
category captures FORMAT (exhibition/non-ladder), not value. Cross-
reference `prize_pool`/`team_number` separately for that.

  - season_wrapper: a single record standing in for an entire season/
    tour/circuit in aggregate, not a granular sub-event (e.g. "2017
    DreamHack Season"). Deliberately narrow -- excludes anything with a
    sub-event qualifier word (Week/Qualifier/Stage/Round/Finals), since
    "Season" appearing in a name does NOT by itself mean the record is a
    wrapper (e.g. "Heatseeker League - Season 4 - Last-Chance Qualifier"
    is one real qualifier, not a season in aggregate).
  - recurring_series: numbered/dated installments of an ongoing minor
    ladder (e.g. "Ranked Hoops 2v2: Week 127", "FACEIT Pro League -
    Europe: October 2020"). Distinct from season_wrapper (not an
    aggregate) and informal (these are organized, recurring, often
    real-money content, not pickup games).
  - showmatch_exhibition: explicit exhibition/special-format signals
    (Showmatch, All-Star, Invitational, Rivals, Charity, Showdown,
    Takedown, Celebration) or an explicit "X vs Y" 1v1/2v2 naming
    pattern.
  - informal: fallback for small-stakes 1-2-player content that matched
    nothing above -- genuine pickup-game-scale records.
  - unclassified: matched nothing above with confidence -- includes
    likely-real, plainly-under-tiered events (e.g. a bare "X Qualifier"
    with no other signal). Treat as "needs a manual look," not a fifth
    real category.

Writes `special_tier_category` + `special_tier_category_confidence`
('ai_assisted_unreviewed', always, regardless of the row's own
`confidence`) -- see etl/schema.sql's comment on the column for why this
is a different provenance tier than the rest of the row.

Usage:
    python etl/classify_special_tiers.py                 # all titles, tier=-1 rows only
    python etl/classify_special_tiers.py --titles age_of_empires_ii
    python etl/classify_special_tiers.py --sample 5       # print N examples per category for a sanity check
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from etl.db import get_connection  # noqa: E402

SUBEVENT_WORDS = re.compile(r"\b(Week|Qualifier|Stage|Round|Finals?|Playoffs?|Group\s*Stage|Last-Chance)\b", re.I)
SEASON_WRAPPER_RE = re.compile(r"\b(Season|Tour|Circuit)\b", re.I)

RECURRING_SERIES_RE = re.compile(
    r"\bWeek\s*\d+\b"
    r"|\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b"
    r"|\bBi-Weekly\b"
    r"|\bHUB\b",
    re.I,
)

SHOWMATCH_RE = re.compile(
    r"\bShow\s*[Mm]atch(es)?\b"
    r"|\bAll[\s-]?Stars?\b"
    r"|\bInvitational\b"
    r"|\bRivals\b"
    r"|\bCharity\b"
    r"|\bShowdown\b"
    r"|\bTakedown\b"
    r"|\bCelebration\b"
    r"|\bStreamer\b"
    r"|\bExhibition\b",
    re.I,
)
VS_PATTERN_RE = re.compile(r"^[\w'.\s]{2,40}\s+vs\.?\s+[\w'.\s]{2,40}$", re.I)

INFORMAL_PRIZE_CEILING = 500.0
INFORMAL_TEAM_CEILING = 2


def classify(name: str, prize_pool: float | None, team_number: int | None) -> str:
    name = name or ""

    if SEASON_WRAPPER_RE.search(name) and not SUBEVENT_WORDS.search(name):
        return "season_wrapper"

    if RECURRING_SERIES_RE.search(name):
        return "recurring_series"

    if SHOWMATCH_RE.search(name) or VS_PATTERN_RE.match(name.strip()):
        return "showmatch_exhibition"

    prize = prize_pool or 0.0
    teams = team_number if (team_number is not None and team_number >= 0) else None
    if prize <= INFORMAL_PRIZE_CEILING and (teams is None or teams <= INFORMAL_TEAM_CEILING):
        return "informal"

    return "unclassified"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--titles", help="comma-separated title ids (default: all titles with tier=-1 rows)")
    parser.add_argument("--sample", type=int, default=3, help="examples to print per category per title (default 3)")
    args = parser.parse_args()

    conn = get_connection()
    if args.titles:
        title_ids = args.titles.split(",")
    else:
        title_ids = [r[0] for r in conn.execute("SELECT DISTINCT title_id FROM tournaments_lpdb WHERE tier='-1'")]

    overall_counts: dict[str, int] = {}
    for title_id in title_ids:
        rows = conn.execute(
            "SELECT id, name, prize_pool, team_number FROM tournaments_lpdb WHERE title_id=? AND tier='-1'",
            (title_id,),
        ).fetchall()
        by_category: dict[str, list] = {}
        for row_id, name, prize_pool, team_number in rows:
            category = classify(name, prize_pool, team_number)
            conn.execute(
                "UPDATE tournaments_lpdb SET special_tier_category=?, special_tier_category_confidence='ai_assisted_unreviewed' WHERE id=?",
                (category, row_id),
            )
            by_category.setdefault(category, []).append(name)
            overall_counts[category] = overall_counts.get(category, 0) + 1
        conn.commit()

        print(f"=== {title_id}: {len(rows)} tier=-1 rows classified ===")
        for category, names in sorted(by_category.items(), key=lambda kv: -len(kv[1])):
            print(f"  {category:22} {len(names):5}  e.g. {names[:args.sample]}")
        print()

    print("=== totals across all titles processed ===")
    for category, n in sorted(overall_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {category:22} {n}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
