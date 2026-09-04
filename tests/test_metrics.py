"""Fixture-based tests for analysis/metrics.py:get_success_milestone.
Small, fixed fixtures — no live data, no network."""

import sqlite3
from pathlib import Path

import pytest

from analysis.metrics import get_success_milestone

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "etl" / "schema.sql"


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA_PATH.read_text())
    connection.execute("INSERT INTO titles (id, canonical_name) VALUES ('test_title', 'Test Title')")
    yield connection
    connection.close()


def insert_tournament(conn, page, tier, start_date, region):
    conn.execute(
        """
        INSERT INTO tournaments
            (title_id, liquipedia_wiki, liquipedia_page, tier, start_date, region, fetched_at)
        VALUES ('test_title', 'test', ?, ?, ?, ?, '2026-01-01T00:00:00Z')
        """,
        (page, tier, start_date, region),
    )
    conn.commit()


def test_two_consecutive_years_two_continents_meets_milestone(conn):
    insert_tournament(conn, "Event 2019 NA", "1", "2019-06-01", "North America")
    insert_tournament(conn, "Event 2020 EU", "1", "2020-06-01", "Europe")

    result = get_success_milestone(conn, "test_title")

    assert result["meets_tier_and_region_criteria"] is True
    assert result["milestone_year"] == 2020


def test_single_continent_never_meets_milestone(conn):
    insert_tournament(conn, "Event 2019 NA", "1", "2019-06-01", "North America")
    insert_tournament(conn, "Event 2020 NA", "1", "2020-06-01", "North America")

    result = get_success_milestone(conn, "test_title")

    assert result["meets_tier_and_region_criteria"] is False
    assert result["milestone_year"] is None


def test_non_consecutive_years_never_meets_milestone(conn):
    insert_tournament(conn, "Event 2019 NA", "1", "2019-06-01", "North America")
    insert_tournament(conn, "Event 2021 EU", "1", "2021-06-01", "Europe")

    result = get_success_milestone(conn, "test_title")

    assert result["meets_tier_and_region_criteria"] is False
    assert result["years_with_qualifying_competition"] == [2019, 2021]


def test_below_qualifying_tier_is_excluded(conn):
    insert_tournament(conn, "Event 2019 NA", "3", "2019-06-01", "North America")
    insert_tournament(conn, "Event 2020 EU", "3", "2020-06-01", "Europe")

    result = get_success_milestone(conn, "test_title")

    assert result["years_with_qualifying_competition"] == []
    assert result["milestone_year"] is None


def test_no_tournaments_returns_none(conn):
    result = get_success_milestone(conn, "test_title")

    assert result["milestone_year"] is None
    assert result["years_with_qualifying_competition"] == []


def test_viewership_check_is_explicitly_unevaluated(conn):
    insert_tournament(conn, "Event 2019 NA", "1", "2019-06-01", "North America")
    insert_tournament(conn, "Event 2020 EU", "1", "2020-06-01", "Europe")

    result = get_success_milestone(conn, "test_title")

    assert result["viewership_check"] is None


def test_qualifying_window_scale_breaks_prize_pool_out_by_currency(conn):
    conn.execute(
        """
        INSERT INTO tournaments
            (title_id, liquipedia_wiki, liquipedia_page, tier, start_date, region,
             prize_pool, currency, team_number, fetched_at)
        VALUES ('test_title', 'test', 'Event 2019 NA', '1', '2019-06-01', 'North America',
                10000, 'USD', 8, '2026-01-01T00:00:00Z')
        """
    )
    conn.execute(
        """
        INSERT INTO tournaments
            (title_id, liquipedia_wiki, liquipedia_page, tier, start_date, region,
             prize_pool, currency, team_number, fetched_at)
        VALUES ('test_title', 'test', 'Event 2020 EU', '1', '2020-06-01', 'Europe',
                500000000, 'KRW', 16, '2026-01-01T00:00:00Z')
        """
    )
    conn.commit()

    result = get_success_milestone(conn, "test_title")

    scale = result["qualifying_window_scale"]
    assert scale["tournament_count"] == 2
    assert scale["avg_team_number"] == 12.0
    assert scale["prize_pool_by_currency"] == {
        "USD": {"count": 1, "total": 10000, "avg": 10000},
        "KRW": {"count": 1, "total": 500000000, "avg": 500000000},
    }


def test_qualifying_window_scale_is_none_without_a_milestone(conn):
    insert_tournament(conn, "Event 2019 NA", "1", "2019-06-01", "North America")

    result = get_success_milestone(conn, "test_title")

    assert result["qualifying_window_scale"] is None


def test_viewership_check_uses_official_broadcast_twitch_data_when_present(conn):
    insert_tournament(conn, "Event 2019 NA", "1", "2019-06-01", "North America")
    insert_tournament(conn, "Event 2020 EU", "1", "2020-06-01", "Europe")

    conn.execute(
        """
        INSERT INTO viewership_snapshots
            (title_id, channel_id, captured_at, viewer_count, is_official_broadcast)
        VALUES ('test_title', 'c1', '2019-06-01T00:00:00Z', 1000, 1)
        """
    )
    conn.execute(
        """
        INSERT INTO viewership_snapshots
            (title_id, channel_id, captured_at, viewer_count, is_official_broadcast)
        VALUES ('test_title', 'c1', '2020-06-01T00:00:00Z', 2000, 1)
        """
    )
    # A non-official stream in the window with a much higher count — must
    # NOT be picked up, or the check would stop being esports-specific.
    conn.execute(
        """
        INSERT INTO viewership_snapshots
            (title_id, channel_id, captured_at, viewer_count, is_official_broadcast)
        VALUES ('test_title', 'c2', '2019-06-02T00:00:00Z', 999999, 0)
        """
    )
    conn.commit()

    result = get_success_milestone(conn, "test_title")

    check = result["viewership_check"]
    assert check["flat_or_growing"] is True
    assert check["source"] == "viewership_snapshots"
    assert check["confidence"] == "verified"
    assert check["esports_specific"] is True
    assert check["first_year_avg_viewers"] == 1000
    assert check["last_year_avg_viewers"] == 2000


def test_viewership_check_falls_back_to_kaggle_when_no_twitch_data(conn):
    insert_tournament(conn, "Event 2019 NA", "1", "2019-06-01", "North America")
    insert_tournament(conn, "Event 2020 EU", "1", "2020-06-01", "Europe")

    conn.execute(
        """
        INSERT INTO monthly_category_history (title_id, year_month, peak_viewers)
        VALUES ('test_title', '2019-06', 5000)
        """
    )
    conn.execute(
        """
        INSERT INTO monthly_category_history (title_id, year_month, peak_viewers)
        VALUES ('test_title', '2020-06', 3000)
        """
    )
    conn.commit()

    result = get_success_milestone(conn, "test_title")

    check = result["viewership_check"]
    assert check["flat_or_growing"] is False
    assert check["source"] == "monthly_category_history"
    assert check["confidence"] == "proxy_estimate"
    assert check["esports_specific"] is False


def test_viewership_check_prefers_twitch_over_kaggle_when_both_present(conn):
    insert_tournament(conn, "Event 2019 NA", "1", "2019-06-01", "North America")
    insert_tournament(conn, "Event 2020 EU", "1", "2020-06-01", "Europe")

    conn.execute(
        """
        INSERT INTO viewership_snapshots
            (title_id, channel_id, captured_at, viewer_count, is_official_broadcast)
        VALUES ('test_title', 'c1', '2019-06-01T00:00:00Z', 100, 1)
        """
    )
    conn.execute(
        """
        INSERT INTO monthly_category_history (title_id, year_month, peak_viewers)
        VALUES ('test_title', '2019-06', 999999)
        """
    )
    conn.commit()

    result = get_success_milestone(conn, "test_title")

    assert result["viewership_check"]["source"] == "viewership_snapshots"


def test_letter_tier_labels_are_normalized_to_qualifying(conn):
    insert_tournament(conn, "Event 2019 NA", "S-Tier", "2019-06-01", "North America")
    insert_tournament(conn, "Event 2020 EU", "A-Tier", "2020-06-01", "Europe")

    result = get_success_milestone(conn, "test_title")

    assert result["meets_tier_and_region_criteria"] is True
    assert result["milestone_year"] == 2020


def test_letter_tier_below_a_still_excluded(conn):
    insert_tournament(conn, "Event 2019 NA", "B-Tier", "2019-06-01", "North America")
    insert_tournament(conn, "Event 2020 EU", "C-Tier", "2020-06-01", "Europe")

    result = get_success_milestone(conn, "test_title")

    assert result["years_with_qualifying_competition"] == []
    assert result["milestone_year"] is None


def test_custom_thresholds_are_respected(conn):
    insert_tournament(conn, "Event 2019 NA", "1", "2019-06-01", "North America")
    insert_tournament(conn, "Event 2020 EU", "1", "2020-06-01", "Europe")
    insert_tournament(conn, "Event 2021 AS", "1", "2021-06-01", "Asia")

    result = get_success_milestone(conn, "test_title", min_consecutive_years=3, min_continents=3)

    assert result["meets_tier_and_region_criteria"] is True
    assert result["milestone_year"] == 2021
