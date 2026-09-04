"""Tests for etl/classify_broadcast_tier.py's word-boundary alias matching
— the specific correctness requirement called out explicitly: a plain
substring check would false-positive on an alias appearing inside an
unrelated word."""

from etl.classify_broadcast_tier import compile_alias_pattern


def test_word_boundary_matches_whole_word():
    pattern = compile_alias_pattern("MSI")
    assert pattern.search("Watching MSI finals today!")


def test_word_boundary_rejects_substring_inside_another_word():
    pattern = compile_alias_pattern("MSI")
    assert not pattern.search("Chatting about MSIexpert builds tonight")


def test_word_boundary_is_case_insensitive():
    pattern = compile_alias_pattern("Worlds")
    assert pattern.search("hyped for worlds!!")


def test_word_boundary_matches_multi_word_alias_as_a_phrase():
    pattern = compile_alias_pattern("Six Invitational")
    assert pattern.search("Six Invitational Day 3 co-stream")
    assert not pattern.search("Sixth Invitational-adjacent stuff")


def test_alias_with_regex_special_characters_is_escaped():
    pattern = compile_alias_pattern("Guilty Gear -STRIVE-")
    assert pattern.search("watching Guilty Gear -STRIVE- ranked")
