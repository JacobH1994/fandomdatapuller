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
    Europe: October 2020", "CEA Spring 2021"). Distinct from
    season_wrapper (not an aggregate) and informal (these are organized,
    recurring, often real-money content, not pickup games).
  - special_mode_circuit: organized, officially-branded tournaments in an
    ALTERNATE competitive mode, not the main ladder (Rocket League's
    "Champions Road"/"Offseason Open" Hoops/Rumble/Jump Jam series,
    Overwatch's "Flash Ops:" experimental-mode series) -- real
    tournaments, well-resourced (up to 582 teams, $54K), just not the
    flagship format, which is likely exactly why they never got a
    standard tier.
  - showmatch_exhibition: explicit exhibition/special-format signals
    (Showmatch, All-Star, Invitational, Rivals, Charity, Showdown,
    Takedown, Celebration) or an explicit "X vs Y" 1v1/2v2 naming
    pattern.
  - informal: fallback for small-stakes 1-2-player content that matched
    nothing above -- genuine pickup-game-scale records.
  - likely_real_mistiered: no keyword matched, but prize_pool/team_number
    are at real-tournament scale (>= $1,000, >= 8 teams) -- e.g.
    StarCraft II's "DreamHack EIZO Open 2012" at $211K. Separated from
    'unclassified' so that bucket stays honestly small rather than padded
    with events that are almost certainly real.
  - unclassified: matched nothing above with confidence, and doesn't
    clear the likely_real_mistiered scale threshold either. Treat as
    "needs a manual look," not a sixth real category.

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

# A brand name + "Season N" + a sub-event word (e.g. "RHL Season 3 - Qualifier 1",
# "RHL Season 10 - Finals") is NOT a season-wrapper (it's excluded by SUBEVENT_WORDS
# above) -- it's one real installment of an ongoing numbered-season ladder. Found
# 2026-10-02 digging into Rocket League's 'unclassified' remainder: ~25 "RHL Season
# N - ..." rows this exact pattern was falling through to unclassified for lack of
# a positive rule, not just correctly failing the wrapper check.
SEASONED_SUBEVENT_RE = re.compile(r"\bSeason\s*\d+\b.{0,20}\b(Finals?|Playoffs?|Qualifiers?|Round|Stage)\b", re.I)

RECURRING_SERIES_RE = re.compile(
    r"\bWeek\s*\d+\b"
    r"|\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b"
    r"|\bBi-Weekly\b"
    r"|\bHUB\b"
    # Broadened after a direct request to dig further into 'unclassified' rather than
    # leave it as a dead end: named series recurring with a bare YYYY or 'Spring/Fall
    # YYYY' suffix across multiple editions (e.g. StarCraft II's "CEA Spring 2019" /
    # "CEA Spring 2021" / "CEA Fall 2019", "High School Starleague 2014-2015") --
    # confirmed live these are real dated installments of an ongoing league, same
    # structural category as the Week-N/month-year patterns above, not a one-off.
    r"|\b(Spring|Summer|Fall|Autumn|Winter)\s+\d{4}\b"
    r"|\b\d{4}\s*-\s*(Spring|Summer|Fall|Autumn|Winter)\b"  # year-then-season order, e.g. "Ant League 2023 - Autumn Edition"
    r"|\b\d{4}-\d{4}\b"
    # Numeric M-D-YY / MM-DD-YYYY dates -- found 2026-10-02: Rocket League's "Ranked
    # Hoops 1v1 M-D-YY" / "Ranked Hoops 2v2 MM-DD-YY" pattern alone accounts for
    # several hundred rows, almost all of which were falling through to
    # unclassified because the existing rule only recognized month NAMES, not
    # numeric dates.
    r"|\b\d{1,2}-\d{1,2}-\d{2,4}\b"
    # Bare "#N" numbered installment of an otherwise-named series (e.g. Overwatch's
    # "Duck Squad Widow 1v1 #7", "LA3EB Overwatch 2 1V1 Cup #14", "Crazy Raccoon Cup
    # #3") -- found 2026-10-02 as Overwatch's single largest unclassified pattern.
    # Checked AFTER the showmatch/vs-pattern checks below in rule order (not here in
    # regex order) specifically so a numbered EXHIBITION ("FishStix Invitational #1")
    # still classifies as showmatch_exhibition, not recurring_series -- a bare
    # number is a weaker signal than an explicit exhibition keyword.
    r"|#\d+\b"
    # "CGL" (a known amateur ladder platform) numbered regional divisions --
    # "CGL GOATs - EU 6", "CGL Lucioball - NA", "CGL Stadium - SA 1" -- found
    # 2026-10-02 as Overwatch's last remaining extractable pattern (~16 rows).
    r"|\bCGL\s+(GOATs|Lucioball|Stadium)\b",
    re.I,
)

# Real, identifiable official special-GAME-MODE circuits -- found 2026-10-02 by
# digging into the 'unclassified' bucket specifically (the thing this pass exists
# to fix): Rocket League's "Champions Road"/"Offseason Open" regional series
# ($16K-$54K, 26-347 teams per edition) and Overwatch's "Flash Ops:" experimental-
# mode series ($7K-$25K, up to 582 teams) are organized, well-resourced, officially
# branded tournaments in an ALTERNATE competitive mode (Rocket League's Hoops/
# Rumble/Jump Jam party modes; Overwatch's experimental/arcade modes) -- not
# exhibitions, not informal, not the main ladder. Real tournaments, just not the
# flagship competitive format, which is exactly why they likely never got a
# standard tier. Kept as their own category rather than folded into
# showmatch_exhibition specifically so a "real tournament, alternate mode" question
# can be answered separately from a "real exhibition/showmatch" one.
SPECIAL_MODE_CIRCUIT_RE = re.compile(
    r"\bChampions\s*Road\b"
    r"|\bOffseason\s*Open\b"
    r"|\bRumble\s*Open\b"
    r"|\bJump\s*Jam\b"
    r"|\bHoops\s*League\b"
    r"|\bFlash\s*Ops\b"
    r"|\bFreestyle\s*(Tournament|Invitational)\b",
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
# Broadened 2026-10-02: the original anchored ^...$ form required the ENTIRE name
# to be just "X vs Y", so any trailing suffix broke the match -- found live that
# AoE2's "GamerLegion vs White Wolf Palace (2)", "coRe vs LaSh #2", and "komtan vs
# kei - Who is No. 2 in Japan?" were all falling through to unclassified for
# exactly this reason. A bare "search" for the vs-pattern anywhere in the name is
# a strong enough signal on its own; no need to anchor it.
VS_PATTERN_RE = re.compile(r"\b[\w'.]+(?:\s+[&,]\s*[\w'.]+)*\s+vs\.?\s+[\w'.]+", re.I)

INFORMAL_PRIZE_CEILING = 500.0
INFORMAL_TEAM_CEILING = 2

# A second fallback threshold, checked only after every keyword rule above has
# already failed to match -- added 2026-10-02 after finding that several
# high-prize unclassified rows (StarCraft II's "DreamHack EIZO Open 2012" at
# $211K, "NetEase Starcraft2 League 2012: Race Challenge" at $24K) have no
# distinguishing keyword at all, just the scale of a genuinely real tournament.
# Separate from 'unclassified' specifically so the remaining true fallback is
# smaller and more honestly "needs a human," not padded with events that are
# almost certainly real.
LIKELY_REAL_PRIZE_FLOOR = 1000.0
LIKELY_REAL_TEAM_FLOOR = 8


def classify(name: str, prize_pool: float | None, team_number: int | None) -> str:
    name = name or ""

    if SEASON_WRAPPER_RE.search(name) and not SUBEVENT_WORDS.search(name):
        return "season_wrapper"

    # Explicit keyword/semantic checks run BEFORE the structural recurring_series
    # check below, specifically because that check's broadened "#N" pattern
    # (added 2026-10-02) would otherwise swallow a numbered EXHIBITION like
    # "FishStix Invitational #1" before its "Invitational" keyword ever gets
    # checked. A named keyword match is a stronger, more specific signal than a
    # bare trailing number.
    if SHOWMATCH_RE.search(name) or VS_PATTERN_RE.search(name):
        return "showmatch_exhibition"

    if SPECIAL_MODE_CIRCUIT_RE.search(name):
        return "special_mode_circuit"

    if SEASONED_SUBEVENT_RE.search(name) or RECURRING_SERIES_RE.search(name):
        return "recurring_series"

    prize = prize_pool or 0.0
    teams = team_number if (team_number is not None and team_number >= 0) else None
    if prize <= INFORMAL_PRIZE_CEILING and (teams is None or teams <= INFORMAL_TEAM_CEILING):
        return "informal"

    if prize >= LIKELY_REAL_PRIZE_FLOOR and (teams is None or teams >= LIKELY_REAL_TEAM_FLOOR):
        return "likely_real_mistiered"

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
