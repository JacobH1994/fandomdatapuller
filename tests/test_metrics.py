"""Fixture-based tests for analysis/metrics.py:get_success_milestone.
Small, fixed fixtures — no live data, no network."""

import sqlite3
from pathlib import Path

import pytest

from analysis.metrics import get_championship_windows, get_concentration, get_success_milestone

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


def insert_tournament_with_prize(conn, page, tier, start_date, prize_pool, title_id="test_title", currency="USD"):
    conn.execute(
        """
        INSERT INTO tournaments
            (title_id, liquipedia_wiki, liquipedia_page, name, tier, start_date, prize_pool, currency, fetched_at)
        VALUES (?, 'test', ?, ?, ?, ?, ?, ?, '2026-01-01T00:00:00Z')
        """,
        (title_id, page, page, tier, start_date, prize_pool, currency),
    )


def test_championship_window_picks_highest_prize_pool_tier1(conn):
    insert_tournament_with_prize(conn, "TI 2019", "1", "2019-08-15", 34_000_000)
    insert_tournament_with_prize(conn, "Major A 2019", "1", "2019-01-01", 1_000_000)

    windows = get_championship_windows(conn, "test_title")

    assert len(windows) == 1
    assert windows[0]["year"] == 2019
    assert windows[0]["liquipedia_page"] == "TI 2019"
    assert windows[0]["prize_pool"] == 34_000_000


def test_championship_window_non_usd_currency_excluded_even_if_numerically_larger(conn):
    # Real bug, found 2026-09-09: a raw prize_pool number with no currency
    # normalization means a foreign-currency figure can be numerically
    # bigger than a much larger real-USD prize without being worth more --
    # confirmed live this affected 95 of 291 windows across the full
    # 23-title dataset (every league_of_legends year, among others) before
    # this fix. A 275,000,000 KRW regional league (~$200K) must NOT beat a
    # $2,500,000 USD World Championship just because the raw number is
    # bigger.
    insert_tournament_with_prize(conn, "Regional League KRW", "1", "2020-06-01", 275_000_000, currency="krw")
    insert_tournament_with_prize(conn, "World Championship USD", "1", "2020-08-15", 2_500_000, currency="USD")

    windows = get_championship_windows(conn, "test_title")

    assert len(windows) == 1
    assert windows[0]["liquipedia_page"] == "World Championship USD"
    assert windows[0]["prize_pool"] == 2_500_000


def test_championship_window_only_non_usd_candidate_produces_no_window(conn):
    # A title-year whose ONLY prize_pool data is non-USD must get no
    # window that year, not a wrong one -- same "no guessed fallback"
    # principle as the NULL-prize_pool case already tested.
    insert_tournament_with_prize(conn, "Only KRW Event", "1", "2021-01-01", 300_000_000, currency="krw")

    windows = get_championship_windows(conn, "test_title")

    assert windows == []


def test_championship_window_null_currency_treated_as_usd(conn):
    # parse_infobox's own convention: currency is NULL when the plain
    # `prizepool` field was used with no `localcurrency` specified --
    # presumptively USD (not verified per-row, but the conservative,
    # documented assumption), so a NULL-currency candidate must still be
    # eligible, not silently excluded alongside real non-USD ones.
    insert_tournament_with_prize(conn, "Unlabeled Currency", "1", "2022-01-01", 1_000_000, currency=None)

    windows = get_championship_windows(conn, "test_title")

    assert len(windows) == 1
    assert windows[0]["liquipedia_page"] == "Unlabeled Currency"


def test_championship_window_tier1_only_not_tier2(conn):
    # A tier-2 event with a much larger prize pool must NOT win over a
    # smaller tier-1 event -- "tier-1 only", not "highest prize pool
    # regardless of tier".
    insert_tournament_with_prize(conn, "Big Tier 2", "2", "2021-01-01", 5_000_000)
    insert_tournament_with_prize(conn, "Small Tier 1", "1", "2021-05-01", 200_000)

    windows = get_championship_windows(conn, "test_title")

    assert len(windows) == 1
    assert windows[0]["liquipedia_page"] == "Small Tier 1"


def test_championship_window_null_prize_pool_excluded_from_candidacy(conn):
    # The only tier-1 event that year has no prize_pool at all -- must
    # produce NO window for that year, not a guessed/fallback one.
    insert_tournament_with_prize(conn, "No Prize Tier 1", "1", "2022-01-01", None)

    windows = get_championship_windows(conn, "test_title")

    assert windows == []


def test_championship_window_tie_broken_by_earliest_start_date(conn):
    insert_tournament_with_prize(conn, "Tie Late", "1", "2020-06-01", 500_000)
    insert_tournament_with_prize(conn, "Tie Early", "1", "2020-03-01", 500_000)

    windows = get_championship_windows(conn, "test_title")

    assert len(windows) == 1
    assert windows[0]["liquipedia_page"] == "Tie Early"


def test_championship_window_letter_tier_normalized(conn):
    insert_tournament_with_prize(conn, "S-Tier Event", "S-Tier", "2023-01-01", 2_000_000)

    windows = get_championship_windows(conn, "test_title")

    assert len(windows) == 1
    assert windows[0]["liquipedia_page"] == "S-Tier Event"


def test_championship_window_across_multiple_titles(conn):
    conn.execute("INSERT INTO titles (id, canonical_name) VALUES ('other_title', 'Other Title')")
    insert_tournament_with_prize(conn, "Test Title Event", "1", "2020-01-01", 1_000_000, title_id="test_title")
    insert_tournament_with_prize(conn, "Other Title Event", "1", "2020-01-01", 2_000_000, title_id="other_title")

    all_windows = get_championship_windows(conn)  # no title_id filter -> all titles

    assert {w["title_id"] for w in all_windows} == {"test_title", "other_title"}
    only_test = get_championship_windows(conn, "test_title")
    assert len(only_test) == 1 and only_test[0]["title_id"] == "test_title"


def test_concentration_hhi_and_top3_share():
    result = get_concentration([50.0, 30.0, 10.0, 10.0])

    assert result["n"] == 4
    # shares: 0.5, 0.3, 0.1, 0.1 -> HHI = 0.25 + 0.09 + 0.01 + 0.01 = 0.36
    assert result["hhi"] == pytest.approx(0.36)
    assert result["top3_share"] == pytest.approx(0.9)


def test_concentration_single_value_is_maximally_concentrated():
    result = get_concentration([100.0])

    assert result["hhi"] == pytest.approx(1.0)
    assert result["top3_share"] == pytest.approx(1.0)


def test_concentration_empty_input_returns_none_not_zero():
    result = get_concentration([])

    assert result["hhi"] is None
    assert result["top3_share"] is None
    assert result["n"] == 0


def test_concentration_all_zero_values_returns_none():
    result = get_concentration([0.0, 0.0])

    assert result["hhi"] is None
