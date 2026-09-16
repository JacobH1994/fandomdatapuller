"""Fixture-based tests for analysis/fandom_region_decomposition.py.
Small, fixed fixtures — no live data, no network."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from analysis.fandom_region_decomposition import (
    CANDIDATE_ENGLISH_COUNTRIES,
    CANDIDATE_GLOBAL_COUNTRIES,
    _offset_hours,
    calibrate_timezone_curve,
    decompose_by_timezone,
    get_steam_review_hourly_series,
    get_twitch_english_hourly_series,
    load_subjects,
)

WINTER = datetime(2026, 1, 15, tzinfo=timezone.utc)  # Northern Hemisphere standard time
SUMMER = datetime(2026, 7, 15, tzinfo=timezone.utc)  # Northern Hemisphere daylight time

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "etl" / "schema.sql"


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA_PATH.read_text())
    connection.execute("INSERT INTO titles (id, canonical_name) VALUES ('test_title', 'Test Title')")
    yield connection
    connection.close()


def insert_lang_row(conn, title_id, hour, language_code, viewer_count):
    conn.execute(
        "INSERT INTO language_mix_snapshots (title_id, captured_at, language_code, viewer_count) VALUES (?, ?, ?, ?)",
        (title_id, f"2026-01-01T{hour:02d}:00:00Z", language_code, viewer_count),
    )
    conn.commit()


def test_calibrate_timezone_curve_shifts_ja_utc_peak_to_local_hour(conn):
    # Japan is UTC+9 — a Japanese-language viewership spike recorded at
    # UTC hour 3 reflects local hour 12 (3 + 9). All other calibration
    # languages (just 'ko' besides 'ja') have zero data, so the pooled
    # curve should be exactly ja's own shifted curve.
    insert_lang_row(conn, "test_title", 3, "ja", 1000)
    curve = calibrate_timezone_curve(conn)
    assert curve.shape == (24,)
    assert np.isclose(curve.sum(), 1.0)
    assert curve.argmax() == 12


def test_calibrate_timezone_curve_flat_when_no_calibration_data(conn):
    curve = calibrate_timezone_curve(conn)
    assert np.allclose(curve, np.full(24, 1.0 / 24))


def test_decompose_by_timezone_recovers_known_mixture():
    # A one-hot calibration curve (all activity at local hour 12) makes
    # the recovered mixture exact and easy to reason about: America/
    # New_York in January (EST, UTC-5) predicts a UTC peak at hour 17;
    # Africa/Lagos (UTC+1 year-round) predicts a UTC peak at hour 11.
    calibration_curve = np.zeros(24)
    calibration_curve[12] = 1.0
    candidates = {"US_East": "America/New_York", "Nigeria": "Africa/Lagos"}

    observed = np.zeros(24)
    observed[17] = 0.7  # US_East's predicted peak (EST, winter)
    observed[11] = 0.3  # Nigeria's predicted peak

    shares = decompose_by_timezone(observed, candidates, calibration_curve=calibration_curve, reference_datetime=WINTER)
    # Labels are the resolved UTC offset itself since 2026-09-15, not the
    # candidate name -- US_East (America/New_York) is UTC-5 in January,
    # Nigeria (Africa/Lagos) is UTC+1 year-round.
    assert shares["UTC-5"] == pytest.approx(0.7, abs=1e-6)
    assert shares["UTC+1"] == pytest.approx(0.3, abs=1e-6)


def test_decompose_by_timezone_no_signal_returns_empty():
    assert decompose_by_timezone(np.zeros(24), calibration_curve=np.full(24, 1.0 / 24), reference_datetime=WINTER) == {}


def test_decompose_by_timezone_requires_exactly_one_of_calibration_curve_or_conn():
    with pytest.raises(ValueError):
        decompose_by_timezone(np.ones(24), reference_datetime=WINTER)


def test_decompose_by_timezone_requires_reference_datetime():
    with pytest.raises(TypeError):
        decompose_by_timezone(np.ones(24), calibration_curve=np.full(24, 1.0 / 24))


def test_decompose_by_timezone_merges_permanent_same_offset_candidates():
    # Japan and South Korea are both UTC+9 year-round -- neither observes
    # DST -- so they must merge regardless of reference_datetime.
    calibration_curve = np.zeros(24)
    calibration_curve[12] = 1.0
    candidates = {"Japan": "Asia/Tokyo", "South_Korea": "Asia/Seoul"}
    observed = np.zeros(24)
    observed[3] = 1.0  # both predict a UTC peak at hour 3 (12 - 9)

    shares = decompose_by_timezone(observed, candidates, calibration_curve=calibration_curve, reference_datetime=WINTER)
    # Merged candidates still collapse to one column/label, but the label
    # is the resolved offset itself now, not a "Name+Name" join.
    assert set(shares) == {"UTC+9"}
    assert shares["UTC+9"] == pytest.approx(1.0, abs=1e-6)


def test_decompose_by_timezone_merges_seasonal_same_offset_candidates():
    # UK_Ireland (Europe/London) and Nigeria (Africa/Lagos, no DST) both
    # land on UTC+1 only during British Summer Time -- found live
    # 2026-09-14 while fixing the fixed-offset design's DST bug.
    calibration_curve = np.zeros(24)
    calibration_curve[12] = 1.0
    candidates = {"UK_Ireland": "Europe/London", "Nigeria": "Africa/Lagos"}
    observed = np.zeros(24)
    observed[11] = 1.0

    winter_shares = decompose_by_timezone(observed, candidates, calibration_curve=calibration_curve, reference_datetime=WINTER)
    assert set(winter_shares) == {"UTC+0", "UTC+1"}  # GMT (+0) vs +1 -- distinguishable in winter

    summer_shares = decompose_by_timezone(observed, candidates, calibration_curve=calibration_curve, reference_datetime=SUMMER)
    assert set(summer_shares) == {"UTC+1"}  # BST (+1) vs +1 -- indistinguishable in summer, merge to one offset label


def test_offset_hours_is_dst_aware():
    # Confirms the actual bug: America/New_York is -5 in January (EST)
    # but -4 in July (EDT) -- a fixed nominal offset can't represent both.
    assert _offset_hours("America/New_York", WINTER) == pytest.approx(-5.0)
    assert _offset_hours("America/New_York", SUMMER) == pytest.approx(-4.0)
    # South Africa never observes DST -- same offset year-round.
    assert _offset_hours("Africa/Johannesburg", WINTER) == pytest.approx(2.0)
    assert _offset_hours("Africa/Johannesburg", SUMMER) == pytest.approx(2.0)


def test_get_twitch_english_hourly_series_title_id_subject(conn):
    insert_lang_row(conn, "test_title", 5, "en", 100)
    insert_lang_row(conn, "test_title", 5, "ja", 999)  # different language, must not leak in
    subject = {"id": "test_title", "source_table": "viewership_snapshots", "title_id": "test_title"}
    series = get_twitch_english_hourly_series(conn, subject)
    assert series[5] == 100
    assert series.sum() == 100


def test_get_twitch_english_hourly_series_game_id_subject_with_content_segment(conn):
    conn.execute(
        """
        INSERT INTO platform_viewership_snapshots
            (game_id, channel_id, captured_at, viewer_count, language, content_segment)
        VALUES ('32982', 'chan1', '2026-01-01T08:00:00Z', 50, 'en', 'nopixel')
        """
    )
    conn.execute(
        """
        INSERT INTO platform_viewership_snapshots
            (game_id, channel_id, captured_at, viewer_count, language, content_segment)
        VALUES ('32982', 'chan2', '2026-01-01T08:00:00Z', 200, 'en', 'non_rp')
        """
    )
    conn.commit()
    subject = {
        "id": "gta_v_nopixel", "source_table": "platform_viewership_snapshots",
        "game_id": "32982", "content_segment": "nopixel",
    }
    series = get_twitch_english_hourly_series(conn, subject)
    assert series[8] == 50  # only the nopixel-segment row, not the non_rp one


def test_get_steam_review_hourly_series_filters_language_and_year(conn):
    def ts(year: int) -> int:
        return int(datetime(year, 6, 1, 14, tzinfo=timezone.utc).timestamp())

    conn.execute(
        "INSERT INTO steam_review_history (subject_id, app_id, review_id, language, timestamp_created, fetched_at) "
        "VALUES ('apex_legends', 1, 'r1', 'english', ?, '2026-01-01T00:00:00Z')",
        (ts(2024),),
    )
    conn.execute(
        "INSERT INTO steam_review_history (subject_id, app_id, review_id, language, timestamp_created, fetched_at) "
        "VALUES ('apex_legends', 1, 'r2', 'schinese', ?, '2026-01-01T00:00:00Z')",
        (ts(2024),),
    )
    conn.execute(
        "INSERT INTO steam_review_history (subject_id, app_id, review_id, language, timestamp_created, fetched_at) "
        "VALUES ('apex_legends', 1, 'r3', 'english', ?, '2026-01-01T00:00:00Z')",
        (ts(2023),),
    )
    conn.commit()
    subject = {"id": "apex_legends"}
    series_2024 = get_steam_review_hourly_series(conn, subject, year=2024)
    assert series_2024[14] == 1  # only r1 — r2 is non-English, r3 is a different year
    series_all = get_steam_review_hourly_series(conn, subject)
    assert series_all[14] == 2  # r1 and r3, both English
    series_pooled = get_steam_review_hourly_series(conn, subject, language=None)
    assert series_pooled[14] == 3  # r1, r2, r3 — every language pooled


def test_get_steam_review_hourly_series_since_until(conn):
    def ts(y, m, d):
        return int(datetime(y, m, d, 14, tzinfo=timezone.utc).timestamp())

    conn.execute(
        "INSERT INTO steam_review_history (subject_id, app_id, review_id, language, timestamp_created, fetched_at) "
        "VALUES ('pubg', 1, 'r1', 'english', ?, '2026-01-01T00:00:00Z')",
        (ts(2024, 3, 1),),
    )
    conn.execute(
        "INSERT INTO steam_review_history (subject_id, app_id, review_id, language, timestamp_created, fetched_at) "
        "VALUES ('pubg', 1, 'r2', 'english', ?, '2026-01-01T00:00:00Z')",
        (ts(2024, 7, 1),),
    )
    conn.commit()
    subject = {"id": "pubg"}
    q1 = get_steam_review_hourly_series(conn, subject, since=ts(2024, 1, 1), until=ts(2024, 4, 1))
    assert q1[14] == 1  # only r1
    q_error = None
    try:
        get_steam_review_hourly_series(conn, subject, year=2024, since=ts(2024, 1, 1))
    except ValueError as e:
        q_error = e
    assert q_error is not None


def test_candidate_dicts_resolve_to_valid_offsets_in_both_seasons():
    # Not a "no collisions allowed" check any more -- decompose_by_timezone
    # merges collisions automatically now (see the merge tests above), and
    # some (UK_Ireland/Nigeria) are only real part of the year. This just
    # confirms every candidate's IANA zone name is valid and resolves to a
    # sane offset in both DST states, so a typo'd zone name fails loudly
    # here rather than silently in a notebook.
    for candidates in (CANDIDATE_ENGLISH_COUNTRIES, CANDIDATE_GLOBAL_COUNTRIES):
        for name, zone_name in candidates.items():
            for reference_datetime in (WINTER, SUMMER):
                offset = _offset_hours(zone_name, reference_datetime)
                assert -12.0 <= offset <= 14.0, f"{name} ({zone_name}) resolved to an implausible offset {offset} at {reference_datetime}"


def test_load_subjects_has_expected_keys():
    subjects = load_subjects()
    assert "apex_legends" in subjects
    assert "gta_v" in subjects
    assert subjects["gta_v"]["source_table"] == "platform_viewership_snapshots"
    assert subjects["apex_legends"]["source_table"] == "viewership_snapshots"
