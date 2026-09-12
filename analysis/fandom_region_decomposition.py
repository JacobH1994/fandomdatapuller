"""English-language fandom region decomposition (PRD §9.17, added
2026-09-12). Built after `notebooks/niche_membership.ipynb` found Apex
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

**Known simplification, stated plainly, not silently assumed away**: UTC
offsets below are fixed nominal values, not DST-aware. A candidate
country whose clocks shift seasonally gets one offset year-round, which
can smear its predicted curve by up to an hour during part of the year.
Acceptable for this subsystem's purpose (a directional regional-share
estimate, explicitly not a settled finding — see every notebook this
feeds), not acceptable if this function's output were ever treated as
precise.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path

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

# Candidate English-speaking countries/regions for decomposition, with a
# fixed nominal UTC offset (see module docstring's DST caveat). UK and
# Ireland are combined — both UTC+0, no way to distinguish them from
# activity timing alone.
CANDIDATE_ENGLISH_COUNTRIES: dict[str, float] = {
    "US_East": -5.0,
    "US_Pacific": -8.0,
    "UK_Ireland": 0.0,
    "India": 5.5,
    "Philippines": 8.0,
    "Australia_East": 10.0,
    "Canada_East": -5.0,
    "Nigeria": 1.0,
    "South_Africa": 2.0,
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
    conn: sqlite3.Connection, subject: dict, *, language: str | None = "english", year: int | None = None
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
    check needs (e.g. notebooks/english_fandom_decomposition.ipynb's
    Counter-Strike cross-validation against Russia/CIS grassroots-
    tournament growth, which is about the whole playerbase's timing, not
    the English-speaking slice of it).

    Pass `year` to compute one calendar year's bucket only -- this is
    what makes the per-year/quarter time series described in the PRD
    possible: steam_review_history spans a title's whole lifetime, unlike
    Twitch's ~2-week language_mix_snapshots window, so decomposing one
    year at a time (rather than the whole history collapsed into one
    'typical day') is what lets estimated regional share be compared
    against year-over-year signals like
    notebooks/fastest_growing_cs_regions.ipynb's grassroots-tournament
    growth findings."""
    from datetime import timezone as _tz
    from datetime import datetime as _dt

    query = "SELECT timestamp_created FROM steam_review_history WHERE subject_id = ?"
    params: tuple = (subject["id"],)
    if language is not None:
        query += " AND language = ?"
        params += (language,)
    if year is not None:
        query += " AND timestamp_created BETWEEN ? AND ?"
        params += (
            int(_dt(year, 1, 1, tzinfo=_tz.utc).timestamp()),
            int(_dt(year + 1, 1, 1, tzinfo=_tz.utc).timestamp()) - 1,
        )
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


def decompose_by_timezone(
    hourly_series: np.ndarray,
    candidate_countries: dict[str, float] = CANDIDATE_ENGLISH_COUNTRIES,
    calibration_curve: np.ndarray | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, float]:
    """Fits `hourly_series` (any 24-length UTC-hour-of-day array -- Twitch
    viewer-time, Steam review-posting-time, doesn't matter which) as a
    non-negative mixture of `candidate_countries`, each represented by
    the calibrated local-hour curve rotated to that country's own UTC
    offset.

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

    country_names = list(candidate_countries)
    design_matrix = np.column_stack([
        np.roll(calibration_curve, -int(round(candidate_countries[name])))
        for name in country_names
    ])

    weights, _residual = nnls(design_matrix, observed)
    weight_total = weights.sum()
    if weight_total <= 0:
        return {name: 0.0 for name in country_names}
    shares = weights / weight_total
    return dict(zip(country_names, shares.tolist()))
