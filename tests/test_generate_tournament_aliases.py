"""Fixture-based tests for etl/generate_tournament_aliases.py's pure
rule-based logic (no network, no LLM)."""

from etl.generate_tournament_aliases import (
    rule_based_aliases,
    series_key_and_depth,
    sub_event_name,
)


def test_series_key_strips_embedded_year():
    assert series_key_and_depth("Masters Tour 2020 Indonesia/Qualifiers/16") == ("Masters Tour Indonesia", 1)


def test_series_key_strips_year_segment():
    assert series_key_and_depth("The International/2023") == ("The International", 1)


def test_series_key_handles_no_slash():
    assert series_key_and_depth("All-In Cup") == ("All-In Cup", 1)


def test_series_key_folds_in_second_segment_for_bare_acronym():
    # "PGL" alone is a bare organizer acronym — the second segment names a
    # genuinely distinct branded event (a specific Major), so it's folded
    # in rather than left to collapse every PGL Major into one series.
    assert series_key_and_depth("PGL/Bucharest Major/2018") == ("PGL/Bucharest Major", 2)
    assert series_key_and_depth("PGL/Arlington Major/2022") == ("PGL/Arlington Major", 2)


def test_series_key_does_not_fold_in_bare_year_or_number_second_segment():
    # CS:GO's PGL Majors are named "PGL/<year>/<city>" — folding in would
    # just re-fragment by host city, so it falls back to "PGL" alone.
    assert series_key_and_depth("PGL/2024/Copenhagen") == ("PGL", 1)


def test_series_key_does_not_fold_in_for_non_acronym_first_segment():
    assert series_key_and_depth("DreamLeague/27/China") == ("DreamLeague", 1)


def test_sub_event_name_is_segment_after_series_key():
    key, depth = series_key_and_depth("VCT/2026/China League/Kickoff")
    assert key == "VCT"
    assert sub_event_name("VCT/2026/China League/Kickoff", depth) == "China League"


def test_sub_event_name_skips_past_a_bare_year():
    key, depth = series_key_and_depth("The International/2017/North America")
    assert key == "The International"
    assert sub_event_name("The International/2017/North America", depth) == "North America"


def test_sub_event_name_none_when_nothing_but_numbers_remain():
    key, depth = series_key_and_depth("DreamLeague/27/China")
    assert sub_event_name("DreamLeague/27", depth) is None


def test_rule_based_aliases_includes_name_minus_year_full_name_and_acronym():
    aliases = rule_based_aliases("The International", "The International/2011")
    assert "The International" in aliases
    assert "The International 2011" in aliases
    assert "TI" in aliases


def test_rule_based_aliases_dedupes_when_full_name_equals_name_minus_year():
    aliases = rule_based_aliases("DreamLeague", "DreamLeague")
    assert aliases == {"DreamLeague"}


def test_rule_based_aliases_skips_acronym_for_single_word_series():
    aliases = rule_based_aliases("DreamLeague", "DreamLeague/27")
    assert "DreamLeague" in aliases
    assert "DreamLeague 27" in aliases
    assert not any(len(a) <= 2 and a.isupper() for a in aliases)
