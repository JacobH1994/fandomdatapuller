"""Reusable metric functions over research.db (PRD §12).

Only `get_success_milestone` is implemented this phase (PRD §18 Phase 2
needs it for the milestone-table backfill/reconciliation). The rest —
`get_niche_share`, `get_concentration` (HHI), `get_official_broadcast_share`,
`get_primary_region` — is Phase 4 and deliberately not here yet.
"""

from __future__ import annotations

import sqlite3

# The brief's definition (§4): "minimum 2-year history of A-tier-or-better
# competition across at least 2 continents, with viewership flat or growing
# over that period." tournaments.tier stores Liquipedia's raw numeric
# `liquipediatier` infobox value ("1" = top tier, "2" = second, ...) —
# confirmed empirically that this numbering is consistent across wikis even
# though the *display* category labels aren't (S-Tier/A-Tier vs. Tier 1/
# Tier 2 vs. others; see collectors/liquipedia.py). "A-tier-or-better" is
# therefore tier 1 or 2, uniformly, with no per-wiki label mapping needed.
DEFAULT_QUALIFYING_TIERS = frozenset({"1", "2"})


def get_success_milestone(
    conn: sqlite3.Connection,
    title_id: str,
    *,
    qualifying_tiers: frozenset[str] = DEFAULT_QUALIFYING_TIERS,
    min_consecutive_years: int = 2,
    min_continents: int = 2,
) -> dict:
    """Computes the brief's success-milestone definition from `tournaments`.

    Finds the earliest window of `min_consecutive_years` consecutive
    calendar years, each containing at least one qualifying-tier
    tournament, whose combined `region` coverage across the whole window
    reaches `min_continents` distinct regions. milestone_year is the last
    year of that window (the year the milestone was met), or None if no
    such window exists in the data.

    Interpretation note: the brief doesn't specify whether "across at least
    2 continents" applies within each individual year or cumulatively
    across the window — this implementation uses the cumulative reading
    (regions can appear in different years of the window), which is the
    more permissive and, we think, more natural reading of "history...
    across at least 2 continents" as a property of the whole window rather
    than every year in it.

    Does NOT evaluate the "viewership flat or growing" clause — no
    viewership-trend data source is wired in yet (that's Esports Charts,
    Phase 5, deferred per PRD §18). `viewership_check` is explicitly None
    rather than silently treated as passed, so callers can't mistake an
    unevaluated condition for a satisfied one.
    """
    rows = conn.execute(
        "SELECT start_date, region, tier FROM tournaments WHERE title_id = ? AND start_date IS NOT NULL",
        (title_id,),
    ).fetchall()

    year_regions: dict[int, set[str]] = {}
    for start_date, region, tier in rows:
        if tier not in qualifying_tiers:
            continue
        try:
            year = int(str(start_date)[:4])
        except (TypeError, ValueError):
            continue
        year_regions.setdefault(year, set())
        if region:
            year_regions[year].add(region)

    years_with_qualifying_competition = sorted(year_regions)
    milestone_year = None
    for start_year in years_with_qualifying_competition:
        window = range(start_year, start_year + min_consecutive_years)
        if not all(y in year_regions for y in window):
            continue
        regions_in_window: set[str] = set()
        for y in window:
            regions_in_window |= year_regions[y]
        if len(regions_in_window) >= min_continents:
            milestone_year = start_year + min_consecutive_years - 1
            break

    return {
        "title_id": title_id,
        "milestone_year": milestone_year,
        "meets_tier_and_region_criteria": milestone_year is not None,
        "years_with_qualifying_competition": years_with_qualifying_competition,
        "viewership_check": None,
        "qualifying_tiers": sorted(qualifying_tiers),
        "min_consecutive_years": min_consecutive_years,
        "min_continents": min_continents,
    }
