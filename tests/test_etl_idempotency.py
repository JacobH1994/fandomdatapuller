"""Confirms loading the same raw snapshot file twice produces no duplicate
rows (PRD §13, §9). load_one_file() takes a real path under data/raw/twitch/
because it derives the file's collector_runs key relative to REPO_ROOT —
the fixture here writes into (and cleans up) a dedicated subfolder there
rather than mocking that away, since the real relative-path behavior is
exactly what's under test."""

import gzip
import json
import sqlite3
from pathlib import Path

import pytest

from etl.load_snapshots import REPO_ROOT, load_one_file, load_one_youtube_file

SCHEMA_PATH = REPO_ROOT / "etl" / "schema.sql"
FIXTURE_DIR = REPO_ROOT / "data" / "raw" / "twitch" / "_test_fixtures"
FIXTURE_DIR_YOUTUBE = REPO_ROOT / "data" / "raw" / "youtube" / "_test_fixtures"


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA_PATH.read_text())
    connection.execute("INSERT INTO titles (id, canonical_name) VALUES ('dota2', 'Dota 2')")
    yield connection
    connection.close()


@pytest.fixture
def fixture_snapshot():
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIXTURE_DIR / "20260101T000000Z.json.gz"
    snapshot = {
        "captured_at": "2026-01-01T00:00:00Z",
        "run_started_at": "2026-01-01T00:00:00Z",
        "run_finished_at": "2026-01-01T00:00:05Z",
        "status": "ok",
        "titles": {
            "dota2": {
                "streams": [
                    {
                        "user_id": "123",
                        "user_login": "somestreamer",
                        "viewer_count": 500,
                        "language": "en",
                        "title": "Dota 2 tournament",
                        "is_official_broadcast": True,
                    }
                ],
                "below_threshold": {
                    "stream_count": 10,
                    "viewer_total": 20,
                    "viewer_total_by_language": {"en": 15, "pt": 5},
                },
            }
        },
        "platform_totals": {"total_viewers": 100000, "total_channels": 5000, "hit_page_cap": False},
        "errors": [],
    }
    with gzip.open(path, "wt") as f:
        json.dump(snapshot, f)
    yield path
    path.unlink()
    FIXTURE_DIR.rmdir()


def test_loading_twice_produces_no_duplicate_rows(conn, fixture_snapshot):
    first_rows = load_one_file(conn, fixture_snapshot)
    assert first_rows > 0

    viewership_1 = conn.execute("SELECT COUNT(*) FROM viewership_snapshots").fetchone()[0]
    language_1 = conn.execute("SELECT COUNT(*) FROM language_mix_snapshots").fetchone()[0]
    platform_1 = conn.execute("SELECT COUNT(*) FROM platform_totals").fetchone()[0]
    runs_1 = conn.execute("SELECT COUNT(*) FROM collector_runs").fetchone()[0]

    # load_one_file must be safe to call twice on its own (every insert uses
    # ON CONFLICT DO NOTHING against a natural key), independent of the
    # caller-side already-loaded check in main().
    load_one_file(conn, fixture_snapshot)

    assert conn.execute("SELECT COUNT(*) FROM viewership_snapshots").fetchone()[0] == viewership_1
    assert conn.execute("SELECT COUNT(*) FROM language_mix_snapshots").fetchone()[0] == language_1
    assert conn.execute("SELECT COUNT(*) FROM platform_totals").fetchone()[0] == platform_1
    assert conn.execute("SELECT COUNT(*) FROM collector_runs").fetchone()[0] == runs_1


def test_viewership_row_fields(conn, fixture_snapshot):
    load_one_file(conn, fixture_snapshot)

    row = conn.execute(
        "SELECT title_id, channel_id, viewer_count, is_official_broadcast FROM viewership_snapshots"
    ).fetchone()

    assert row == ("dota2", "123", 500, 1)


def test_language_mix_combines_full_detail_and_below_threshold(conn, fixture_snapshot):
    load_one_file(conn, fixture_snapshot)

    rows = dict(
        conn.execute(
            "SELECT language_code, viewer_count FROM language_mix_snapshots WHERE title_id = 'dota2'"
        ).fetchall()
    )

    # full-detail stream contributes en=500; below_threshold adds en=15, pt=5
    assert rows["en"] == 515
    assert rows["pt"] == 5


@pytest.fixture
def youtube_fixture_snapshot():
    FIXTURE_DIR_YOUTUBE.mkdir(parents=True, exist_ok=True)
    path = FIXTURE_DIR_YOUTUBE / "20260101T000000Z.json.gz"
    snapshot = {
        "captured_at": "2026-01-01T00:00:00Z",
        "run_started_at": "2026-01-01T00:00:00Z",
        "run_finished_at": "2026-01-01T00:00:05Z",
        "status": "ok",
        "sweep_mode": True,
        "quota_used": 101,
        "channels": [
            {
                "title_id": "dota2", "channel_id": "UCabc123", "channel_name": "Dota 2 Official",
                "is_live": True, "video_id": "vid1", "viewer_count": 12000,
                "video_title": "The International Grand Final", "checked_at": "2026-01-01T00:00:00Z",
                "discovery_method": "sweep_discovered",
            },
            {
                "title_id": "dota2", "channel_id": "UCdef456", "channel_name": "Dota 2 Backup",
                "is_live": False, "video_id": None, "viewer_count": None,
                "video_title": None, "checked_at": "2026-01-01T00:00:00Z",
                "discovery_method": "sweep_not_live",
            },
        ],
        "errors": [],
    }
    with gzip.open(path, "wt") as f:
        json.dump(snapshot, f)
    yield path
    path.unlink()
    FIXTURE_DIR_YOUTUBE.rmdir()


def test_youtube_loading_twice_produces_no_duplicate_rows(conn, youtube_fixture_snapshot):
    first_rows = load_one_youtube_file(conn, youtube_fixture_snapshot)
    assert first_rows == 1  # only the live channel gets a viewership_snapshots row

    viewership_1 = conn.execute("SELECT COUNT(*) FROM viewership_snapshots").fetchone()[0]
    channels_1 = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
    runs_1 = conn.execute("SELECT COUNT(*) FROM collector_runs").fetchone()[0]

    load_one_youtube_file(conn, youtube_fixture_snapshot)

    assert conn.execute("SELECT COUNT(*) FROM viewership_snapshots").fetchone()[0] == viewership_1
    assert conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0] == channels_1
    assert conn.execute("SELECT COUNT(*) FROM collector_runs").fetchone()[0] == runs_1


def test_youtube_not_live_channel_gets_no_viewership_row(conn, youtube_fixture_snapshot):
    load_one_youtube_file(conn, youtube_fixture_snapshot)

    row_count = conn.execute(
        "SELECT COUNT(*) FROM viewership_snapshots WHERE channel_id = 'UCdef456'"
    ).fetchone()[0]
    assert row_count == 0


def test_youtube_live_row_fields_and_platform_tag(conn, youtube_fixture_snapshot):
    load_one_youtube_file(conn, youtube_fixture_snapshot)

    row = conn.execute(
        "SELECT title_id, platform, channel_id, viewer_count, is_official_broadcast FROM viewership_snapshots"
    ).fetchone()
    assert row == ("dota2", "youtube", "UCabc123", 12000, 1)


def test_youtube_channels_table_upserted_for_both_live_and_not_live(conn, youtube_fixture_snapshot):
    load_one_youtube_file(conn, youtube_fixture_snapshot)

    rows = conn.execute(
        "SELECT title_id, platform, login, name FROM channels ORDER BY login"
    ).fetchall()
    assert rows == [
        ("dota2", "youtube", "UCabc123", "Dota 2 Official"),
        ("dota2", "youtube", "UCdef456", "Dota 2 Backup"),
    ]


def test_youtube_loading_does_not_affect_twitch_platform_default(conn, youtube_fixture_snapshot, fixture_snapshot):
    # A Twitch row loaded alongside a YouTube one must still default to
    # platform='twitch' (no explicit platform in the Twitch INSERT).
    load_one_file(conn, fixture_snapshot)
    load_one_youtube_file(conn, youtube_fixture_snapshot)

    platforms = {
        r[0] for r in conn.execute("SELECT DISTINCT platform FROM viewership_snapshots").fetchall()
    }
    assert platforms == {"twitch", "youtube"}
