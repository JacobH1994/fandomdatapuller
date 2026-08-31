"""Shared SQLite helpers for etl/load_snapshots.py and collectors/liquipedia.py.

research.db is derived and disposable (PRD §5) — get_connection() always
applies schema.sql, so there's no separate "init the db" step; any script
that opens a connection through here can assume the schema exists.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "etl" / "schema.sql"
DB_PATH = REPO_ROOT / "data" / "research.db"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    # WAL: readers (a notebook, another script) aren't blocked by a writer
    # mid-run, and a writer isn't blocked by a reader. Several scripts touch
    # this file independently (collector, ETL, connector, analysis) — this
    # is the standard fix for that access pattern, not a perf tweak.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def seed_titles_and_aliases(conn: sqlite3.Connection, titles: list[dict]) -> None:
    """Idempotently seeds `titles` and `title_aliases` from config/titles.yaml.
    Safe to call on every run: does nothing for a title/alias already
    present. Does not handle a category ID *changing* under an existing
    title (that would need the old alias's valid_to set) — out of scope
    until title_aliases actually needs to track a real rename."""
    today = utcnow_iso()[:10]
    for t in titles:
        conn.execute(
            """
            INSERT INTO titles (id, canonical_name, is_active, source, confidence)
            VALUES (?, ?, ?, 'manual', 'manual_judgment_call')
            ON CONFLICT (id) DO UPDATE SET
                canonical_name = excluded.canonical_name,
                is_active = excluded.is_active
            """,
            (t["id"], t["display_name"], 1 if t.get("is_active") else 0),
        )

        category_id = t.get("twitch_category_id")
        if category_id:
            existing = conn.execute(
                "SELECT 1 FROM title_aliases WHERE title_id = ? AND twitch_category_id = ?",
                (t["id"], category_id),
            ).fetchone()
            if not existing:
                conn.execute(
                    """
                    INSERT INTO title_aliases
                        (title_id, alias, platform, twitch_category_id, liquipedia_wiki,
                         valid_from, source, confidence)
                    VALUES (?, ?, NULL, ?, ?, ?, 'manual', 'manual_judgment_call')
                    """,
                    (t["id"], t["display_name"], category_id, t.get("liquipedia_wiki"), today),
                )
    conn.commit()
