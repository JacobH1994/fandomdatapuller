"""Fixture-based tests for collectors/steam_poll.py's pure logic — no
network calls, no live API key needed."""

import json

import httpx

from collectors.steam_poll import RunErrors, fetch_player_count, parse_player_count_response


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


def _mock_client(status_code: int, body: dict) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, content=json.dumps(body))

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_player_count_404_returns_none_without_logging_an_error():
    # Confirmed live 2026-09-09: Steam returns a genuine HTTP 404 (body
    # {"response":{"result":42}}) for an appid it doesn't recognize yet —
    # routine for a pre-release title, not an anomaly. This was
    # previously logged via errors.add and drove
    # collectors/steam_cohort_poll.py's status to "failed" (a false
    # alarm) whenever every currently-due cohort title happened to be
    # pre-release.
    errors = RunErrors()
    client = _mock_client(404, {"response": {"result": 42}})

    count = fetch_player_count(client, 12345, "fake-key", errors, "12345")

    assert count is None
    assert errors.items == []


def test_fetch_player_count_other_4xx_still_logs_an_error():
    # A genuine problem (e.g. bad key -> 403) must still be logged --
    # the 404 carve-out is specific to Steam's "unrecognized appid"
    # shape, not a blanket "ignore all 4xx" change.
    errors = RunErrors()
    client = _mock_client(403, {"response": {}})

    count = fetch_player_count(client, 12345, "fake-key", errors, "12345")

    assert count is None
    assert len(errors.items) == 1


def test_fetch_player_count_success_returns_count():
    errors = RunErrors()
    client = _mock_client(200, {"response": {"result": 1, "player_count": 500}})

    count = fetch_player_count(client, 12345, "fake-key", errors, "12345")

    assert count == 500
    assert errors.items == []
