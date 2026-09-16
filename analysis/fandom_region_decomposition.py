"""English-language fandom region decomposition (PRD §9.17, added
2026-09-12). Built after `research/inter_esports_dynamics/notebooks/niche_membership.ipynb` found Apex
Legends and PUBG: BATTLEGROUNDS sharing a Japanese-speaking audience, but
could say nothing about their `en`-tagged viewers — English spans the US,
UK, India, the Philippines, Canada, Australia and more with no finer tag
from Twitch (or Steam, or Wikipedia) to tell them apart.

**Core idea — timezone deconvolution.** Twitch's `language` field can't
split English, but *when* an English-speaking population is active can:
people are systematically more active in their own local daytime/evening
hours than at 4am local time, regardless of language. So:

1. Calibrate a canonical "local-hour activity shape" from languages this
   project can already map to a single, low-variance timezone with real
   confidence — deliberately a narrower, stricter bar than
   `niche_membership.ipynb`'s own `LANGUAGE_TO_REGION` proxy (which maps
   `ru` to the whole "Europe" continent, and `ru`-speaking Twitch alone
   spans Russia's 11 timezones — not a single-offset anchor, even though
   it's a perfectly good coarse *region* signal elsewhere in this
   project). See CALIBRATION_LANGUAGES below for exactly which languages
   qualify and why.
2. Fit any subject's observed English-hour-of-day curve as a
   non-negative mixture of that calibrated shape, rotated to each
   candidate English-speaking country's own UTC offset.

This is deliberately signal-agnostic: `decompose_by_timezone` takes a
plain 24-bucket hourly series and doesn't know or care whether it came
from Twitch viewer-time or Steam review-posting-time — see
`get_twitch_english_hourly_series` and (in
`collectors/steam_review_history_pull.py`'s companion loader)
`get_steam_review_hourly_series` for the two real inputs this project
feeds it.

**DST is handled properly, via real IANA timezones — not fixed nominal
offsets — fixed 2026-09-14 after a user question exposed how wrong the
earlier "fixed offset" design actually was.** `CANDIDATE_ENGLISH_COUNTRIES`/
`CANDIDATE_GLOBAL_COUNTRIES` map each candidate to an IANA zone name
(e.g. `"Europe/London"`), and `decompose_by_timezone` resolves each
candidate's real UTC offset at a caller-supplied `reference_datetime`
via `zoneinfo` — the actual offset for that specific moment, not a
year-round approximation. Checked directly what the old fixed-offset
scheme got wrong for this project's own Twitch collection window
(2026-08-31 to 2026-09-12, deep in Northern Hemisphere DST season):
`UK_Ireland`, `US_Canada_East`, `US_Pacific`, and `Western_Europe` were
ALL silently using their winter (standard-time) offset for a window that
was actually in summer (daylight-time) — every one of them off by
exactly the DST hour, not "smeared," genuinely wrong.

**Fixing DST correctly surfaces a real, structural, un-fixable ambiguity
that a caller must understand, not something a smarter offset choice can
resolve.** South Africa observes no DST (fixed UTC+2 year-round); Central
Europe is UTC+2 for roughly seven months a year (CEST, late March to late
October). During that window, a South African viewer/reviewer and a
German one are, by clock time alone, **genuinely indistinguishable** —
not approximately similar, identically so. This isn't a gap in this
function's offset table (Europe isn't even in `CANDIDATE_ENGLISH_COUNTRIES`
today) — it's what timezone deconvolution fundamentally cannot do,
confirmed by working through this exact case 2026-09-14. `South_Africa`'s
estimated share in any result should be read as "this share of the
clock-time signal," which may include real Central European (or any
other UTC+2-at-that-moment) activity this method has no way to strip out.
Distinguishing them for real needs a different signal (language,
self-declared region tags) — not a further-tuned timezone offset.

**Because seasonal ambiguity is now a live, dynamic thing (not a fixed
property of the candidate list), `decompose_by_timezone` auto-merges any
two candidates that resolve to the identical offset at the given
`reference_datetime`** — into one combined output entry (e.g.
`"Nigeria+UK_Ireland"`, labels sorted alphabetically, which happens for about seven months a year once
`UK_Ireland` correctly shifts to BST/+1) — rather than either crashing on
a rank-deficient regression or silently splitting an unidentifiable
weight between them the way the old static design did (the bug that
first surfaced this whole area, `US_East`/`Canada_East`, both permanently
UTC-5 — now just two names that always resolve to the same offset and
always auto-merge, no manual pre-merging of the candidate dict required
any more).

**Steam reviews specifically are not a random sample of anything, in
either dimension — checked directly 2026-09-13, not assumed.**
- **Time**: `collectors/steam_review_history_pull.py`'s crawl is a
  deterministic, most-recent-first walk that stops at a hard wall (a
  real, community-documented Steam cursor-pagination bug — see that
  collector's own docstring), not a sample spread across a title's whole
  history. Confirmed the reached window itself has zero gap days for
  both crawled subjects (PUBG: 994/994 days, Apex Legends: 1,450/1,450
  days) — a complete census of that period, then a hard cliff to
  nothing before it, not sparse coverage that happens to reach back
  that far.
- **Population**: reviewers are self-selected, not a random draw from
  the playerbase. More-engaged players review more; sentiment is
  bimodal (people write reviews when they feel strongly, not as a
  neutral cross-section); Steam's own review-prompt UI and
  regional review-writing norms can skew which languages/countries show
  up, independent of actual playerbase share. Every notebook consuming
  `steam_review_history` should treat it as "who chose to review, day by
  day, within the reached window" — not "a random sample of who plays
  this game."
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import yaml
from scipy.optimize import nnls

REPO_ROOT = Path(__file__).resolve().parent.parent
SUBJECTS_CONFIG_PATH = REPO_ROOT / "config" / "fandom_decomposition_subjects.yaml"

# Languages confidently anchored to ONE low-variance UTC offset, for
# calibrating the canonical local-hour curve. Deliberately a short list:
# `ja`/`ko` (Japan/Korea, UTC+9, no DST, each a large single-country
# Twitch audience in this project's own data) are the only two languages
# checked and kept. Excluded on purpose, not overlooked: `ru` (Russia
# alone spans 11 timezones), `de`/`fr` (DST-observing, and each spans
# more than one country), `pt` (Brazil vs. Portugal — different offsets
# entirely, same ambiguity niche_membership.ipynb's LANGUAGE_TO_REGION
# already flags for `en`/`es`).
CALIBRATION_LANGUAGES: dict[str, float] = {
    "ja": 9.0,
    "ko": 9.0,
}

# Candidate English-speaking countries/regions for decomposition, each an
# IANA timezone name (see module docstring's DST section) -- resolved to
# a real, DST-aware UTC offset at call time by decompose_by_timezone, not
# a fixed nominal value. "US_Canada_East" uses America/New_York as the
# representative zone for both countries' eastern time -- they've shared
# identical DST rules since the US's 2007 Energy Policy Act change, so
# this loses no real distinction, unlike merging two genuinely different
# things. UK and Ireland are combined the same way (Europe/London) --
# both on identical clocks year-round.
#
# **Bug found 2026-09-13, not caught until real (non-smoke-test) Steam
# review data existed, originally "fixed" by manually merging colliding
# pairs into the dict itself**: the original version listed "US_East" and
# "Canada_East" as separate candidates at the same fixed offset --
# genuinely identical, so nnls arbitrarily split weight between them.
# **That manual-merge approach itself turned out to be the wrong fix,
# found 2026-09-14 while adding real DST support**: it can't handle a
# collision that only exists part of the year (UK_Ireland and Nigeria
# both land on UTC+1 for the ~7 months UK observes BST, but not the other
# ~5). decompose_by_timezone now detects and merges same-offset
# candidates automatically, at call time, against whatever
# reference_datetime it's given -- so this dict lists every candidate
# separately and lets the function handle any collision, permanent or
# seasonal, rather than requiring this list to be pre-merged by hand.
CANDIDATE_ENGLISH_COUNTRIES: dict[str, str] = {
    "US_Canada_East": "America/New_York",
    "US_Pacific": "America/Los_Angeles",
    "UK_Ireland": "Europe/London",
    "India": "Asia/Kolkata",
    "Philippines": "Asia/Manila",
    "Australia_East": "Australia/Sydney",
    "Nigeria": "Africa/Lagos",
    "South_Africa": "Africa/Johannesburg",
}

# General-purpose (not English-specific) candidate set for the
# whole-playerbase pooled decomposition (language=None) -- built from the
# top review-languages actually observed across this project's real Steam
# review crawls (PUBG, Apex Legends, Counter-Strike) rather than guessed
# in the abstract. Japan/South_Korea and Russia/Turkey are listed
# separately, not pre-merged -- both pairs happen to always resolve to
# the same offset (neither Japan, Korea, Russia, nor Turkey observes DST),
# so decompose_by_timezone's auto-merge will combine them on every call
# without this dict needing to know that in advance, the same reasoning
# CANDIDATE_ENGLISH_COUNTRIES' own comment gives.
CANDIDATE_GLOBAL_COUNTRIES: dict[str, str] = {
    "China": "Asia/Shanghai",
    "Japan": "Asia/Tokyo",
    "South_Korea": "Asia/Seoul",
    "Russia": "Europe/Moscow",
    "Turkey": "Europe/Istanbul",
    "Brazil": "America/Sao_Paulo",
    "Western_Europe": "Europe/Berlin",
    "North_America": "America/Chicago",
}


def load_subjects() -> dict[str, dict]:
    """Reads config/fandom_decomposition_subjects.yaml, keyed by subject
    id. The single place every other function/notebook in this subsystem
    looks up a subject's source table / filter -- adding a new subject is
    a config edit there, never a code change here."""
    with open(SUBJECTS_CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    return {s["id"]: s for s in data["subjects"]}


def _hour_bucket(captured_at: str) -> int:
    # captured_at is ISO 8601 UTC text (CLAUDE.md convention) -- the hour
    # digits sit at a fixed offset, no datetime parsing needed.
    return int(captured_at[11:13])


def _hourly_utc_curve_from_rows(rows: list[tuple[str, float]]) -> np.ndarray:
    """rows: (captured_at, viewer_count) pairs -> a 24-length array, index
    = UTC hour of day, summed across whatever date range the rows span.
    Collapses the whole window into one 'typical day' shape -- reasonable
    for a short window, and consistent with every other notebook in this
    project treating a short snapshot as directional, not a seasonally-
    averaged baseline."""
    buckets = np.zeros(24)
    for captured_at, viewer_count in rows:
        buckets[_hour_bucket(captured_at)] += viewer_count
    return buckets


def get_twitch_english_hourly_series(conn: sqlite3.Connection, subject: dict) -> np.ndarray:
    """The English-viewer-time input to decompose_by_timezone, for either
    subject shape (see config/fandom_decomposition_subjects.yaml):
    title_id-keyed subjects read language_mix_snapshots (already
    aggregated per title/hour/language); game_id-keyed subjects read
    platform_viewership_snapshots directly (per-stream, not pre-
    aggregated by language -- summed here instead), optionally narrowed
    to one content_segment."""
    if subject["source_table"] == "viewership_snapshots":
        rows = conn.execute(
            "SELECT captured_at, viewer_count FROM language_mix_snapshots "
            "WHERE title_id = ? AND language_code = 'en'",
            (subject["title_id"],),
        ).fetchall()
    elif subject["source_table"] == "platform_viewership_snapshots":
        query = "SELECT captured_at, viewer_count FROM platform_viewership_snapshots WHERE game_id = ? AND language = 'en'"
        params: tuple = (subject["game_id"],)
        if subject.get("content_segment"):
            query += " AND content_segment = ?"
            params += (subject["content_segment"],)
        rows = conn.execute(query, params).fetchall()
    else:
        raise ValueError(f"unknown source_table {subject['source_table']!r} for subject {subject['id']!r}")
    return _hourly_utc_curve_from_rows(rows)


def get_steam_review_hourly_series(
    conn: sqlite3.Connection, subject: dict, *,
    language: str | None = "english", year: int | None = None,
    since: int | None = None, until: int | None = None,
) -> np.ndarray:
    """The Steam-review-posting-time input to decompose_by_timezone -- an
    entirely independent population from get_twitch_english_hourly_series
    (owners who write reviews, not people watching streams), same
    signal-agnostic decompose_by_timezone function underneath.

    `timestamp_created` is Unix epoch UTC (collectors/
    steam_review_history_pull.py's own docstring) -- bucketed by UTC hour
    the same way _hour_bucket does for ISO text, just via
    datetime.utcfromtimestamp instead of a string slice.

    `language` defaults to 'english' (Steam's own language string, not
    Twitch's `en` code -- the two vocabularies are never joined directly,
    see steam_review_history's schema comment) for the main English-
    decomposition use case. Pass `language=None` to pool every language
    together -- this is what a language-INDEPENDENT playerbase-location
    check needs (e.g. research/inter_esports_dynamics/notebooks/english_fandom_decomposition.ipynb's
    Counter-Strike cross-validation against Russia/CIS grassroots-
    tournament growth, which is about the whole playerbase's timing, not
    the English-speaking slice of it).

    Pass `year` to compute one calendar year's bucket only, or `since`/
    `until` (Unix epoch, inclusive) directly for a finer window (a
    quarter, a month) -- `year` is convenience sugar for the common case,
    computed into the same since/until bounds internally; pass at most
    one of `year` or `since`/`until`. This is what makes the time-series
    decomposition described in the PRD possible: steam_review_history can
    span a title's whole crawled window, unlike Twitch's ~2-week
    language_mix_snapshots coverage, so decomposing one period at a time
    (rather than the whole history collapsed into one 'typical day') is
    what lets estimated regional share be compared against time-varying
    signals like research/esports_lifecycle_and_maturity/notebooks/fastest_growing_cs_regions.ipynb's grassroots-
    tournament growth findings.

    **`steam_review_history`'s actual coverage window varies by subject
    and is often NOT since a title's release** -- confirmed live 2026-09-13
    that Steam's own `filter=recent` cursor pagination has an undocumented
    depth cap for very-high-review-count titles (PUBG: BATTLEGROUNDS'
    crawl reached only 536,953 of 2,753,749 total reviews, back to
    2023-12-25, not its 2017-12-21 release -- see `collectors/
    steam_review_history_pull.py`'s own docstring). Check
    `MIN(timestamp_created)` for a subject before treating any `year`/
    `since` earlier than that as meaningful -- it will just return an
    empty (all-zero) series, not an error."""
    from datetime import timezone as _tz
    from datetime import datetime as _dt

    if year is not None and (since is not None or until is not None):
        raise ValueError("pass at most one of year or since/until")
    if year is not None:
        since = int(_dt(year, 1, 1, tzinfo=_tz.utc).timestamp())
        until = int(_dt(year + 1, 1, 1, tzinfo=_tz.utc).timestamp()) - 1

    query = "SELECT timestamp_created FROM steam_review_history WHERE subject_id = ?"
    params: tuple = (subject["id"],)
    if language is not None:
        query += " AND language = ?"
        params += (language,)
    if since is not None:
        query += " AND timestamp_created >= ?"
        params += (since,)
    if until is not None:
        query += " AND timestamp_created <= ?"
        params += (until,)
    rows = conn.execute(query, params).fetchall()

    buckets = np.zeros(24)
    for (timestamp_created,) in rows:
        buckets[_dt.fromtimestamp(timestamp_created, tz=_tz.utc).hour] += 1
    return buckets


def calibrate_timezone_curve(conn: sqlite3.Connection) -> np.ndarray:
    """Builds the canonical local-hour activity shape (a 24-length array
    summing to 1, index = hour of local day) from CALIBRATION_LANGUAGES'
    pooled, normalized local-hour curves.

    Each calibration language contributes one curve, shifted from UTC to
    its own local hour (local_hour = (utc_hour + offset) % 24) and
    normalized to sum 1 BEFORE pooling -- an unweighted mean across
    languages, not a volume-weighted one, so a single very-large-audience
    calibration language can't dominate what's meant to be a generic
    human daily-activity rhythm.

    Returns a uniform (flat) curve if no calibration language has any
    data at all -- decompose_by_timezone still runs, it just can't
    distinguish any candidate country from another (every predicted
    curve is identical), which is the honest result of no real
    calibration signal, not a crash."""
    local_curves = []
    for language_code, utc_offset in CALIBRATION_LANGUAGES.items():
        rows = conn.execute(
            "SELECT captured_at, viewer_count FROM language_mix_snapshots WHERE language_code = ?",
            (language_code,),
        ).fetchall()
        utc_curve = _hourly_utc_curve_from_rows(rows)
        if utc_curve.sum() <= 0:
            continue
        shift = int(round(utc_offset))
        local_curve = np.roll(utc_curve, shift)
        local_curves.append(local_curve / local_curve.sum())

    if not local_curves:
        return np.full(24, 1.0 / 24)
    return np.mean(local_curves, axis=0)


def _offset_hours(zone_name: str, reference_datetime: datetime) -> float:
    """The real, DST-aware UTC offset (hours) for an IANA zone at a
    specific moment -- not a fixed nominal value. `reference_datetime`
    must be timezone-aware (callers in this project always pass UTC)."""
    local = reference_datetime.astimezone(ZoneInfo(zone_name))
    return local.utcoffset().total_seconds() / 3600.0


def _format_utc_offset(offset: int) -> str:
    """'UTC+2' / 'UTC-5' / 'UTC+0' -- the stable, permanent label for a
    resolved integer-hour offset. Never changes as candidates are added
    or removed, unlike a name built from candidate labels (see module
    docstring's 2026-09-15 section) -- this is what actually gets
    persisted as `english_fandom_region_estimates.region_or_country`."""
    return f"UTC{offset:+d}"


def _group_candidates_by_offset(
    candidate_countries: dict[str, str], reference_datetime: datetime,
) -> dict[int, list[str]]:
    """Groups candidate names by their resolved integer-hour UTC offset at
    `reference_datetime` -- the one place this grouping is computed, shared
    by decompose_by_timezone (which only needs the offsets) and
    reference_cities_for_offsets (which only needs the names)."""
    groups: dict[int, list[str]] = defaultdict(list)
    for name, zone_name in candidate_countries.items():
        offset = int(round(_offset_hours(zone_name, reference_datetime)))
        groups[offset].append(name)
    return groups


def reference_cities_for_offsets(
    candidate_countries: dict[str, str], reference_datetime: datetime,
) -> dict[str, str]:
    """Display-only lookup: {'UTC+2': 'Johannesburg/Berlin', ...} -- the
    illustrative reference cities currently sharing each resolved offset,
    derived straight from each candidate's own IANA zone name (the part
    after the '/'; no separate city field needed).

    Deliberately NOT part of decompose_by_timezone's own return value, and
    never persisted alongside it (2026-09-15, at the user's direct
    request): a share belongs with real, measured categories (self-
    declared tags, language codes) that decompose_by_timezone's caller is
    free to mix into the same table without a caveat; a reference-city
    annotation is illustrative rendering sugar for a timezone-inferred
    bucket and reads very differently -- keeping the two in genuinely
    separate outputs stops a future chart/table from silently blending
    'we measured this' and 'here's an example of what this offset might
    be' into one undifferentiated row. Call this only when actually
    building a display for timezone-deconvolution results specifically,
    never merged into a table of tag/language shares."""
    groups = _group_candidates_by_offset(candidate_countries, reference_datetime)
    result: dict[str, str] = {}
    for offset, names in groups.items():
        cities = [candidate_countries[name].rsplit("/", 1)[-1].replace("_", " ") for name in names]
        result[_format_utc_offset(offset)] = "/".join(cities)
    return result


def decompose_by_timezone(
    hourly_series: np.ndarray,
    candidate_countries: dict[str, str] = CANDIDATE_ENGLISH_COUNTRIES,
    calibration_curve: np.ndarray | None = None,
    conn: sqlite3.Connection | None = None,
    *,
    reference_datetime: datetime,
) -> dict[str, float]:
    """Fits `hourly_series` (any 24-length UTC-hour-of-day array -- Twitch
    viewer-time, Steam review-posting-time, doesn't matter which) as a
    non-negative mixture of `candidate_countries`, each an IANA timezone
    name resolved to its real UTC offset AT `reference_datetime` (see
    module docstring's DST section) -- represented by the calibrated
    local-hour curve rotated to that resolved offset.

    `reference_datetime` is required, not defaulted to "now" -- a caller
    analyzing a historical window (a past quarter, a past year) must say
    which moment's DST state applies, since silently using today's DST
    state for old data would just reintroduce the bug this parameter
    exists to fix. Pass the actual midpoint of the window `hourly_series`
    was drawn from, not an arbitrary date.

    Two or more candidates that resolve to the IDENTICAL offset at this
    reference_datetime -- permanently (Japan/South_Korea, Russia/Turkey)
    or only seasonally (UK_Ireland/Nigeria, for the months UK observes
    BST) -- are automatically merged, since nnls has no way to split
    weight between two indistinguishable columns.

    **Output is keyed by the resolved UTC offset itself (e.g. "UTC+2"),
    not by candidate name (changed 2026-09-15).** A candidate-name label
    like "South_Africa" claims more precision than clock-time-of-day
    activity can actually support -- see the module docstring's DST
    section, which found this exact bucket structurally indistinguishable
    from Central/Western Europe for roughly seven months a year. The
    offset is the actual thing being measured and is permanently stable
    regardless of which candidates get added or removed later, so it's
    safe to persist as a natural key. For a human-readable rendering of
    which candidates currently share a given offset (e.g. "Johannesburg/
    Berlin" for "UTC+2"), call reference_cities_for_offsets() separately
    -- deliberately not folded into this function's own return value, so
    a caller never accidentally mixes a real, measured category (a
    self-declared tag, a language code) with an inferred-and-illustrative
    one in the same table without choosing to.

    Pass `calibration_curve` directly (recommended when decomposing many
    subjects/windows against the same calibration) or `conn` to compute
    it fresh via calibrate_timezone_curve. Exactly one of the two must be
    given.

    Solved via non-negative least squares (scipy.optimize.nnls) against
    both series normalized to sum 1 first -- nnls has no way to enforce
    weights summing to exactly 1 as a hard constraint, so the raw result
    is renormalized afterward; documented here rather than silently
    assumed, since a caller inspecting raw nnls output before that last
    step would see weights that don't already sum to 1.

    Returns {} (not a divide-by-zero) if hourly_series has no signal at
    all (sums to zero) -- nothing to decompose, not an error.
    """
    if (calibration_curve is None) == (conn is None):
        raise ValueError("pass exactly one of calibration_curve or conn")
    if calibration_curve is None:
        calibration_curve = calibrate_timezone_curve(conn)

    total = hourly_series.sum()
    if total <= 0:
        return {}
    observed = hourly_series / total

    # Group candidates by resolved integer-hour offset first -- two names
    # landing on the same offset become one design-matrix column and one
    # output label, never two indistinguishable columns handed to nnls.
    groups = _group_candidates_by_offset(candidate_countries, reference_datetime)

    labels = [_format_utc_offset(offset) for offset in groups]
    design_matrix = np.column_stack([
        np.roll(calibration_curve, -offset) for offset in groups
    ])

    weights, _residual = nnls(design_matrix, observed)
    weight_total = weights.sum()
    if weight_total <= 0:
        return {label: 0.0 for label in labels}
    shares = weights / weight_total
    return dict(zip(labels, shares.tolist()))
