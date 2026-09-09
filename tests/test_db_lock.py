"""Tests etl/db.py's research.db.lock advisory-lock mechanism, added
2026-09-09 after --rebuild corrupted research.db by deleting it out from
under a still-running collector's open connection (see etl/db.py and
etl/load_snapshots.py for the incident and the fix). Uses a real temp
file for the lock (not the repo's actual data/research.db.lock) via
monkeypatch, since flock is real OS-level state, not something to fake."""

import fcntl

import pytest

import etl.db as db


@pytest.fixture
def isolated_lock_path(tmp_path, monkeypatch):
    """Points etl.db at a throwaway lock file and resets its cached fd
    before and after, so this process's own prior/later lock use (e.g. a
    real get_connection() call elsewhere) can't leak into this test."""
    monkeypatch.setattr(db, "LOCK_PATH", tmp_path / "research.db.lock")
    monkeypatch.setattr(db, "_lock_file", None)
    yield
    if db._lock_file is not None:
        db._lock_file.close()
    monkeypatch.setattr(db, "_lock_file", None)


def test_rebuild_lock_succeeds_when_nothing_else_holds_it(isolated_lock_path):
    assert db.try_acquire_rebuild_lock() is True


def test_rebuild_lock_fails_when_another_fd_holds_a_shared_lock(isolated_lock_path):
    # Simulates a second process's get_connection() call: a genuinely
    # separate open file description to the same path. flock() treats two
    # fds to the same file as independent lock holders even within one
    # process, which is exactly the property this whole mechanism relies
    # on (see etl/db.py's module docstring for why that matters here).
    other_fd = open(db.LOCK_PATH, "w")
    fcntl.flock(other_fd, fcntl.LOCK_SH)
    try:
        assert db.try_acquire_rebuild_lock() is False
    finally:
        other_fd.close()


def test_rebuild_lock_succeeds_again_after_the_other_holder_releases(isolated_lock_path):
    other_fd = open(db.LOCK_PATH, "w")
    fcntl.flock(other_fd, fcntl.LOCK_SH)
    assert db.try_acquire_rebuild_lock() is False
    other_fd.close()  # releases the shared lock (OS-level, on fd close)

    assert db.try_acquire_rebuild_lock() is True
