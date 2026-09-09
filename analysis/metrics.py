"""Reusable metric functions over research.db (PRD §12).

Only `get_success_milestone` is implemented this phase (PRD §18 Phase 2
needs it for the milestone-table backfill/reconciliation). The rest —
`get_niche_share`, `get_concentration` (HHI), `get_official_broadcast_share`,
`get_primary_region` — is Phase 4 and deliberately not here yet.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict

# The brief's definition (§4): "minimum 2-year history of A-tier-or-better
# competition across at least 2 continents, with viewership flat or growing
# over that period."
#
# collectors/liquipedia.py's docstring previously claimed the infobox's raw
# `liquipediatier` value is always a plain number ("1"/"2"), with S-Tier/
# A-Tier vs. Tier 1/Tier 2 being purely a *display*-category difference over
# the same underlying number. That claim was verified against exactly one
# wiki (teamfight_tactics) and is false more broadly — confirmed live
# 2026-09-05 directly against cached wikitext: counter_strike, valorant,
# and (for some pages) age_of_empires_ii genuinely author
# `|liquipediatier=S-Tier` / `A-Tier` / `A` as the literal field value, not
# a number. Left unhandled, this silently zeroed out (or drastically
# undercounted) qualifying tournaments for those titles — counter_strike
# and valorant are not edge cases, they're two of this project's largest
# tracked titles.
#
# _normalize_tier maps those label values onto the same "1"/"2" scale
# rather than expanding DEFAULT_QUALIFYING_TIERS with letter variants, so
# there's exactly one canonical "qualifying" definition to reason about.
# The mapping (S~1, A~2) is not a fresh guess: it mirrors
# collectors/liquipedia.py's own TIER_CONVENTIONS list, which already
# treats "S-Tier Tournaments"/"A-Tier Tournaments" as equivalent to
# "Tier 1 Tournaments"/"Tier 2 Tournaments" for tournament *discovery* — a
# precedent already established elsewhere in this codebase, not invented
# here. B-Tier/C-Tier and anything else pass through unchanged (i.e. don't
# qualify), matching "A-tier-or-better."
TIER_LABEL_NORMALIZATION: dict[str, str] = {
    "S": "1", "S-Tier": "1",
    "A": "2", "A-Tier": "2",
}


def _normalize_tier(raw: str | None) -> str | None:
    if raw is None:
        return None
    return TIER_LABEL_NORMALIZATION.get(raw, raw)


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

    Evaluates the "viewership flat or growing" clause when a data source
    has coverage for the qualifying window — see `_viewership_trend`.
    `viewership_check` is explicitly None when no source covers the
    window, rather than silently treated as passed, so callers can't
    mistake an unevaluated condition for a satisfied one. In practice this
    stays None for any title whose window predates real viewership
    coverage (Twitch collection started 2026-08-31; the Kaggle import in
    `monthly_category_history`, if loaded, only reaches back to 2016) —
    that's an honest gap, not something to paper over by lowering the bar.

    Also returns `qualifying_window_scale`: the absolute prize-pool/team
    scale of the qualifying window's tournaments, alongside (not gating)
    the milestone flag. PRD §6: Liquipedia's tier label is era-relative,
    not an absolute production bar, so two titles can both "meet the
    milestone" at wildly different absolute scales — this is the permanent
    companion figure that keeps that distinction visible rather than
    collapsing "successful" (institutional durability) into "scale."
    """
    rows = conn.execute(
        """
        SELECT start_date, region, tier, prize_pool, currency, team_number
        FROM tournaments WHERE title_id = ? AND start_date IS NOT NULL
        """,
        (title_id,),
    ).fetchall()

    year_regions: dict[int, set[str]] = {}
    year_tournaments: dict[int, list[tuple]] = defaultdict(list)
    for start_date, region, tier, prize_pool, currency, team_number in rows:
        if _normalize_tier(tier) not in qualifying_tiers:
            continue
        try:
            year = int(str(start_date)[:4])
        except (TypeError, ValueError):
            continue
        year_regions.setdefault(year, set())
        if region:
            year_regions[year].add(region)
        year_tournaments[year].append((prize_pool, currency, team_number))

    years_with_qualifying_competition = sorted(year_regions)
    milestone_year = None
    window_start_year = None
    for start_year in years_with_qualifying_competition:
        window = range(start_year, start_year + min_consecutive_years)
        if not all(y in year_regions for y in window):
            continue
        regions_in_window: set[str] = set()
        for y in window:
            regions_in_window |= year_regions[y]
        if len(regions_in_window) >= min_continents:
            window_start_year = start_year
            milestone_year = start_year + min_consecutive_years - 1
            break

    qualifying_window_scale = None
    viewership_check = None
    if milestone_year is not None:
        qualifying_window_scale = _qualifying_window_scale(
            year_tournaments, range(window_start_year, milestone_year + 1)
        )
        viewership_check = _viewership_trend(conn, title_id, window_start_year, milestone_year)

    return {
        "title_id": title_id,
        "milestone_year": milestone_year,
        "window_start_year": window_start_year,
        "meets_tier_and_region_criteria": milestone_year is not None,
        "years_with_qualifying_competition": years_with_qualifying_competition,
        "qualifying_window_scale": qualifying_window_scale,
        "viewership_check": viewership_check,
        "qualifying_tiers": sorted(qualifying_tiers),
        "min_consecutive_years": min_consecutive_years,
        "min_continents": min_continents,
    }


def _qualifying_window_scale(year_tournaments: dict[int, list[tuple]], window_years: range) -> dict:
    """Absolute prize-pool/team-scale figures for the milestone's qualifying
    window (see get_success_milestone's docstring). team_number is
    currency-independent and safe to average directly; prize_pool is not —
    `tournaments.currency` is never converted (no FX-rate source in this
    project), so blending pools across currencies into one number would be
    actively misleading (confirmed live: some titles' raw prize_pool values
    span currencies differing by orders of magnitude). Broken out per
    currency instead of forcing a single figure."""
    team_numbers = []
    prize_by_currency: dict[str, list[float]] = defaultdict(list)
    tournament_count = 0
    for year in window_years:
        for prize_pool, currency, team_number in year_tournaments.get(year, []):
            tournament_count += 1
            if team_number is not None:
                team_numbers.append(team_number)
            if prize_pool is not None:
                prize_by_currency[currency or "unknown"].append(prize_pool)

    return {
        "tournament_count": tournament_count,
        "avg_team_number": sum(team_numbers) / len(team_numbers) if team_numbers else None,
        "prize_pool_by_currency": {
            cur: {"count": len(vals), "total": sum(vals), "avg": sum(vals) / len(vals)}
            for cur, vals in prize_by_currency.items()
        },
    }


def _viewership_trend(conn: sqlite3.Connection, title_id: str, start_year: int, end_year: int) -> dict | None:
    """Evaluates "viewership flat or growing" over [start_year, end_year],
    from whichever data source has coverage.

    Deliberately source-agnostic against `viewership_snapshots`: it reads
    every row regardless of `source`, so a future Esports Charts connector
    (PRD §9.3, which is specified to land in this same table with
    source='esportscharts') is picked up automatically — swapping in a
    better historical source later means writing that connector, not
    changing this function. Only official-broadcast rows
    (`is_official_broadcast=1`) count, to stay esports-specific rather than
    pulling in general game-fandom category traffic (PRD §4).

    Falls back to `monthly_category_history` (Kaggle import, PRD §9.6) only
    when viewership_snapshots has no coverage for the window. That source
    is category-wide, not esports-specific, and proxy_estimate confidence
    (unverified provenance) — both are labelled explicitly in the result
    (`esports_specific`, `confidence`) rather than presenting Kaggle-derived
    evidence as equivalent in strength to a real broadcast measurement.

    Returns None if neither source covers the window at all — an
    unevaluated clause, not a silent pass.

    "Flat or growing" is read here as: the window's last-year aggregate
    viewership is not below its first-year aggregate — no tolerance band
    for a marginal decline. A judgment call, documented rather than silent,
    same spirit as the region-window interpretation note above.
    """
    official_rows = conn.execute(
        """
        SELECT captured_at, viewer_count FROM viewership_snapshots
        WHERE title_id = ? AND is_official_broadcast = 1
          AND substr(captured_at, 1, 4) BETWEEN ? AND ?
        """,
        (title_id, str(start_year), str(end_year)),
    ).fetchall()

    by_year: dict[int, list[float]] = defaultdict(list)
    for captured_at, viewer_count in official_rows:
        by_year[int(captured_at[:4])].append(viewer_count)

    if by_year:
        return _trend_result(by_year, source="viewership_snapshots", confidence="verified", esports_specific=True)

    monthly_rows = conn.execute(
        """
        SELECT year_month, avg_viewers, peak_viewers FROM monthly_category_history
        WHERE title_id = ? AND substr(year_month, 1, 4) BETWEEN ? AND ?
        """,
        (title_id, str(start_year), str(end_year)),
    ).fetchall()

    for year_month, avg_viewers, peak_viewers in monthly_rows:
        metric = peak_viewers if peak_viewers is not None else avg_viewers
        if metric is not None:
            by_year[int(year_month[:4])].append(metric)

    if not by_year:
        return None
    return _trend_result(
        by_year, source="monthly_category_history", confidence="proxy_estimate", esports_specific=False
    )


def get_championship_windows(conn: sqlite3.Connection, title_id: str | None = None) -> list[dict]:
    """Brief H3's championship-concentration test (docs/esports_gauses_law_brief.md),
    added 2026-09-08: for each (title, calendar year), the tier-1
    tournament with the highest prize_pool — the "world championship
    window" for that title-year. Deliberately objective, no name-matching
    against "World Championship"/"Worlds"/"TI"/etc., since those vary per
    title and some tier-1 events that function as a de facto world
    championship don't literally carry that name — reuses exactly the
    same tier-normalization and year-grouping approach
    get_success_milestone/_qualifying_window_scale already depend on
    (_normalize_tier, start_date's year), not a new convention.

    **Tier-1 only, not tier-1-or-2** — deliberately narrower than
    get_success_milestone's DEFAULT_QUALIFYING_TIERS, since "the biggest
    event of the year" is a tier-1-specific claim; a title whose highest-
    prize-pool event that year is tier-2 gets no window that year, not a
    fallback to its tier-2 event.

    **A title-year needs a tier-1 tournament with a NON-NULL prize_pool
    to get a window at all** — prize_pool is frequently missing in this
    project's Liquipedia-sourced data (a known, pre-existing gap), and
    "highest prize_pool" is meaningless to compute over all-NULL
    candidates; silently falling back to some other criterion (e.g. team
    count) would misrepresent what was actually being ranked. A tie (two
    tier-1 tournaments the same year with equal prize_pool) is broken by
    earliest start_date, then by liquipedia_page for full determinism —
    documented here as a judgment call, not asserted as principled.

    Returns one dict per (title_id, year) with a qualifying window:
    title_id, year, liquipedia_page, name, prize_pool, currency,
    start_date, end_date. Rows with NULL/unparseable start_date are
    excluded (can't assign a year), same handling as
    get_success_milestone's own year parsing.

    **Currency bug, found and fixed 2026-09-09**: `prize_pool` is a raw
    number with no currency normalization (`etl/liquipedia.py`'s
    `parse_infobox` stores whatever the wiki's own `prizepool`/
    `prizepoolusd`/`localcurrency` fields say, verbatim). The original
    version of this function picked the numerically-largest `prize_pool`
    regardless of `currency`, which is comparing apples to oranges — a
    275,000,000 KRW regional league (~$200K USD) has a bigger raw number
    than a $2.5M USD World Championship, and would win. Confirmed live
    this wasn't a rare edge case: 95 of 291 windows across the full
    23-title dataset had a non-USD currency, including EVERY
    league_of_legends year 2012-2025 (LCK's KRW figures beating Worlds'
    USD ones every single time). Now restricted to `currency = 'USD'` or
    `currency IS NULL` (an unlabeled `prizepool` field, by
    `parse_infobox`'s own convention, means no `localcurrency` was found —
    treated as presumptively USD, consistent with how the plain
    `prizepool` field is conventionally used on these wikis, but NOT
    verified per-row) — a tournament with an explicitly-tagged non-USD
    currency is excluded from candidacy entirely rather than wrongly
    compared as if it were USD. A title-year whose only prize_pool data is
    non-USD now correctly gets no window that year, rather than a wrong
    one."""
    params: tuple = ()
    title_filter = ""
    if title_id is not None:
        title_filter = "AND title_id = ?"
        params = (title_id,)

    rows = conn.execute(
        f"""
        SELECT title_id, start_date, end_date, tier, prize_pool, currency,
               liquipedia_page, name
        FROM tournaments
        WHERE start_date IS NOT NULL AND prize_pool IS NOT NULL
              AND (currency = 'USD' OR currency IS NULL)
              {title_filter}
        """,
        params,
    ).fetchall()

    candidates_by_key: dict[tuple[str, int], list[tuple]] = defaultdict(list)
    for t_id, start_date, end_date, tier, prize_pool, currency, page, name in rows:
        if _normalize_tier(tier) != "1":
            continue
        try:
            year = int(str(start_date)[:4])
        except (TypeError, ValueError):
            continue
        candidates_by_key[(t_id, year)].append((prize_pool, start_date, page, end_date, currency, name))

    results = []
    for (t_id, year), candidates in sorted(candidates_by_key.items()):
        # Highest prize_pool wins; ties broken by earliest start_date
        # (ISO text, sorts correctly ascending), then liquipedia_page, for
        # full determinism.
        prize_pool, start_date, page, end_date, currency, name = max(
            candidates, key=lambda c: (c[0], _sort_key_desc(c[1]), _sort_key_desc(c[2]))
        )
        results.append({
            "title_id": t_id,
            "year": year,
            "liquipedia_page": page,
            "name": name,
            "prize_pool": prize_pool,
            "currency": currency,
            "start_date": start_date,
            "end_date": end_date,
        })
    return results


def _sort_key_desc(value: str | None) -> tuple:
    """Ties in get_championship_windows are broken by EARLIEST start_date/
    lowest liquipedia_page, but the overall comparison is `max(...)` (for
    "highest prize_pool") — this flips a plain ascending string comparison
    so that "earliest wins" reads as "greatest" under max(), without
    needing a second, opposite-direction comparison pass."""
    if value is None:
        return (1,)  # sorts after any real string, so a real value always "wins" a tie against None
    return (0, tuple(-ord(c) for c in value))


def get_concentration(shares: list[float]) -> dict:
    """HHI (Herfindahl-Hirschman Index) and top-3 share over a set of
    values already expressed as a pool (e.g. each title's championship
    peak viewers in a given year) — PRD §12's originally-planned
    get_concentration, built now for the championship-concentration
    notebook rather than earlier, since nothing needed it until this.

    Takes raw values, not pre-computed shares — computing the shares
    internally (each value / sum of all values) means a caller can't
    accidentally pass in shares that don't actually sum to 1 (e.g. from
    a subset) and get a silently-wrong HHI. HHI is computed on the
    0-1 share scale (max 1.0, a single-title pool), not the 0-10,000
    scale some finance contexts use — documented here since both
    conventions are common and silently picking one is a real ambiguity.

    Returns {"hhi", "top3_share", "n", "shares"} — `shares` (title-share
    pairs aren't tracked here, just the sorted share values themselves)
    is returned so a caller can audit the computation, not just trust
    the summary numbers."""
    total = sum(shares)
    if total <= 0 or not shares:
        return {"hhi": None, "top3_share": None, "n": len(shares), "shares": []}
    normalized = sorted((s / total for s in shares), reverse=True)
    hhi = sum(s**2 for s in normalized)
    top3_share = sum(normalized[:3])
    return {"hhi": hhi, "top3_share": top3_share, "n": len(shares), "shares": normalized}


def _trend_result(by_year: dict[int, list[float]], *, source: str, confidence: str, esports_specific: bool) -> dict:
    years_present = sorted(by_year)
    first_year_avg = sum(by_year[years_present[0]]) / len(by_year[years_present[0]])
    last_year_avg = sum(by_year[years_present[-1]]) / len(by_year[years_present[-1]])
    return {
        "flat_or_growing": last_year_avg >= first_year_avg,
        "source": source,
        "confidence": confidence,
        "esports_specific": esports_specific,
        "years_with_data": years_present,
        "first_year_avg_viewers": first_year_avg,
        "last_year_avg_viewers": last_year_avg,
    }
