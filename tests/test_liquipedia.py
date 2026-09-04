"""Fixture-based tests for collectors/liquipedia.py:parse_infobox."""

from collectors.liquipedia import parse_infobox


def test_tier_with_trailing_html_comment_is_stripped():
    wikitext = """
    {{Infobox league
    |name=Test Tournament
    |liquipediatier=2<!-- discussed on Discord: https://discord.com/channels/x -->
    |sdate=2020-06-01
    |edate=2020-06-05
    }}
    """
    fields = parse_infobox(wikitext)

    assert fields["tier"] == "2"


def test_tier_without_comment_is_unaffected():
    wikitext = """
    {{Infobox league
    |name=Test Tournament
    |liquipediatier=S-Tier
    |sdate=2020-06-01
    |edate=2020-06-05
    }}
    """
    fields = parse_infobox(wikitext)

    assert fields["tier"] == "S-Tier"


def test_missing_infobox_returns_none():
    assert parse_infobox("no template here") is None
