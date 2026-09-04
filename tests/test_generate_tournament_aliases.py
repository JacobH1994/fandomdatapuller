"""Fixture-based tests for etl/generate_tournament_aliases.py's pure
rule-based logic (no network, no LLM)."""

from etl.generate_tournament_aliases import rule_based_aliases, series_key


def test_series_key_is_first_path_segment():
    assert series_key("VCT/2024/Masters/Madrid") == "VCT"
    assert series_key("Six Invitational/2027/Global Standings") == "Six Invitational"


def test_series_key_handles_no_slash():
    assert series_key("All-In Cup") == "All-In Cup"


def test_rule_based_aliases_includes_series_and_readable_name():
    aliases = rule_based_aliases("VCT", "VCT/2024/Masters/Madrid")
    assert "VCT" in aliases
    assert "VCT 2024 Masters Madrid" in aliases


def test_rule_based_aliases_dedupes_when_name_equals_series():
    aliases = rule_based_aliases("All-In Cup", "All-In Cup")
    assert aliases == {"All-In Cup"}
