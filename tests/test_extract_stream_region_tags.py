"""Fixture-based tests for etl/extract_stream_region_tags.py.
Small, fixed fixtures — no live data, no network."""

from etl.extract_stream_region_tags import classify_row


def test_single_region_tag_wins():
    assert classify_row("some stream", "English,NA,Competitive") == "NA"


def test_tag_aliases_fold_to_canonical_region():
    assert classify_row(None, "EUW") == "EU"
    assert classify_row(None, "EUNE") == "EU"
    assert classify_row(None, "LAN") == "LATAM"
    assert classify_row(None, "ANZ") == "OCE"


def test_br_tag_never_classified_ambiguous_by_design():
    assert classify_row(None, "BR,Competitive") is None


def test_conflicting_regions_return_none():
    assert classify_row(None, "NA,EU") is None


def test_no_signal_returns_none():
    assert classify_row("just a normal stream title", "English,Competitive") is None


def test_title_long_substring_match():
    assert classify_row("Grinding ranked - North America server", None) == "NA"
    assert classify_row("Oceania qualifiers today!", None) == "OCE"


def test_title_short_codes_not_matched_to_avoid_false_positives():
    # "na" appearing inside ordinary prose (not a tag) should not trigger
    # a region match — only the long-substring patterns apply to titles.
    assert classify_row("gonna smurf on ranked today", None) is None
