"""Fixture-based tests for collectors/steam_poll.py's pure logic — no
network calls, no live API key needed."""

from collectors.steam_poll import parse_player_count_response


def test_parse_player_count_response_success():
    body = {"response": {"player_count": 493865, "result": 1}}
    assert parse_player_count_response(body) == 493865


def test_parse_player_count_response_zero_is_a_real_value_when_result_is_1():
    # A niche title can legitimately have zero concurrent players — that's
    # a real 0, distinct from result != 1 (an API-level failure).
    body = {"response": {"player_count": 0, "result": 1}}
    assert parse_player_count_response(body) == 0


def test_parse_player_count_response_missing_result_returns_none_not_zero():
    # Confirmed live (2026-09-08): the "no key" gotcha this project hit
    # returns result=1 with player_count=0 for some titles — that case is
    # handled above as a real 0. This test is the OTHER failure shape:
    # result != 1 (or absent), which must be distinguishable as "the call
    # itself didn't work," never silently coerced into 0.
    body = {"response": {"error": "Bad Request"}}
    assert parse_player_count_response(body) is None


def test_parse_player_count_response_result_not_one():
    body = {"response": {"result": 42}}
    assert parse_player_count_response(body) is None


def test_parse_player_count_response_empty_body():
    assert parse_player_count_response({}) is None
