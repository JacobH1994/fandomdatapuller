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


def test_custom_thresholds_are_respected(conn):
    insert_tournament(conn, "Event 2019 NA", "1", "2019-06-01", "North America")
    insert_tournament(conn, "Event 2020 EU", "1", "2020-06-01", "Europe")
    insert_tournament(conn, "Event 2021 AS", "1", "2021-06-01", "Asia")

    result = get_success_milestone(conn, "test_title", min_consecutive_years=3, min_continents=3)

    assert result["meets_tier_and_region_criteria"] is True
    assert result["milestone_year"] == 2021
