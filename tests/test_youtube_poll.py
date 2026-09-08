"""Fixture-based tests for collectors/youtube_poll.py's pure logic — no
network calls, no live API key needed."""

from collectors.youtube_poll import parse_videos_response, prior_live_state


def test_parse_videos_response_live_video():
    body = {
        "items": [
            {
                "id": "abc123",
                "snippet": {"liveBroadcastContent": "live", "title": "Grand Final"},
                "liveStreamingDetails": {"concurrentViewers": "45231"},
            }
        ]
    }
    result = parse_videos_response(body, ["abc123"])
    assert result["abc123"] == {"is_live": True, "viewer_count": 45231, "title": "Grand Final"}


def test_parse_videos_response_ended_stream_missing_concurrent_viewers():
    # liveBroadcastContent can still say "live" briefly after a stream
    # ends, but concurrentViewers disappears the moment it's not truly
    # live — is_live must key off both, not liveBroadcastContent alone.
    body = {
        "items": [
            {
                "id": "abc123",
                "snippet": {"liveBroadcastContent": "live", "title": "Grand Final (ended)"},
                "liveStreamingDetails": {"actualEndTime": "2026-09-08T12:00:00Z"},
            }
        ]
    }
    result = parse_videos_response(body, ["abc123"])
    assert result["abc123"]["is_live"] is False
    assert result["abc123"]["viewer_count"] is None


def test_parse_videos_response_missing_id_reported_not_live():
    # Requested a video that's deleted/privated/dropped — must be reported
    # explicitly, not silently omitted from the result.
    body = {"items": []}
    result = parse_videos_response(body, ["gone123"])
    assert result == {"gone123": {"is_live": False, "viewer_count": None, "title": None}}


def test_parse_videos_response_upcoming_not_live():
    body = {
        "items": [
            {
                "id": "xyz789",
                "snippet": {"liveBroadcastContent": "upcoming", "title": "Starts soon"},
                "liveStreamingDetails": {"scheduledStartTime": "2026-09-09T00:00:00Z"},
            }
        ]
    }
    result = parse_videos_response(body, ["xyz789"])
    assert result["xyz789"]["is_live"] is False


def test_parse_videos_response_batch_mixed_results():
    body = {
        "items": [
            {
                "id": "live1",
                "snippet": {"liveBroadcastContent": "live", "title": "Live now"},
                "liveStreamingDetails": {"concurrentViewers": "100"},
            }
        ]
    }
    result = parse_videos_response(body, ["live1", "notfound2"])
    assert result["live1"]["is_live"] is True
    assert result["notfound2"]["is_live"] is False


def test_prior_live_state_extracts_only_live_channels():
    snapshot = {
        "channels": [
            {"channel_id": "UC1", "is_live": True, "video_id": "v1", "viewer_count": 500},
            {"channel_id": "UC2", "is_live": False, "video_id": None, "viewer_count": None},
            {"channel_id": "UC3", "is_live": True, "video_id": None, "viewer_count": None},  # malformed: no video_id
        ]
    }
    state = prior_live_state(snapshot)
    assert set(state) == {"UC1"}
    assert state["UC1"]["video_id"] == "v1"


def test_prior_live_state_handles_no_snapshot():
    assert prior_live_state(None) == {}


def test_prior_live_state_handles_empty_channels():
    assert prior_live_state({"channels": []}) == {}
