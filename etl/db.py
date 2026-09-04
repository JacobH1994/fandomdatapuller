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


def _seed_reference_value(conn: sqlite3.Connection, table: str, name: str) -> int:
    """INSERT OR IGNORE a genres/platforms row by name, return its id.
    genres/platforms are reference tables (PRD §6) — a table you add rows
    to as the Phase 3 taxonomy is populated, not a hardcoded enum, so new
    names showing up in config/titles.yaml just get appended here."""
    conn.execute(f"INSERT OR IGNORE INTO {table} (name) VALUES (?)", (name,))
    row = conn.execute(f"SELECT id FROM {table} WHERE name = ?", (name,)).fetchone()
    return row[0]


def seed_titles_and_aliases(conn: sqlite3.Connection, titles: list[dict]) -> None:
    """Idempotently seeds `titles` and `title_aliases` from config/titles.yaml.
    Safe to call on every run: does nothing for a title/alias already
    present. Does not handle a category ID *changing* under an existing
    title (that would need the old alias's valid_to set) — out of scope
    until title_aliases actually needs to track a real rename.

    Also seeds genre_id/platform_id (Phase 3 classification, PRD §18) from
    the same config's genre/platform fields, populating the genres/platforms
    reference tables as a side effect. Config is the source of truth here
    (CLAUDE.md's config-driven convention), so every call re-applies it —
    a title whose genre/platform is edited in config gets re-classified on
    the next run, same as canonical_name/is_active above. Always written as
    ('ai_assisted', 'ai_assisted_unreviewed') per CLAUDE.md's provenance
    rule; this function never promotes to 'verified' — that's a human-review
    step, done directly against research.db, not something a config re-seed
    should silently overwrite. To avoid clobbering a reviewed row, this only
    writes genre_id/platform_id when the title's current genre_confidence
    (or platform_confidence) is NOT already 'verified'."""
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

        genre = t.get("genre")
        if genre:
            genre_id = _seed_reference_value(conn, "genres", genre)
            conn.execute(
                """
                UPDATE titles SET genre_id = ?, genre_source = 'ai_assisted',
                    genre_confidence = 'ai_assisted_unreviewed'
                WHERE id = ? AND (genre_confidence IS NULL OR genre_confidence != 'verified')
                """,
                (genre_id, t["id"]),
            )

        platform = t.get("platform")
        if platform:
            platform_id = _seed_reference_value(conn, "platforms", platform)
            conn.execute(
                """
                UPDATE titles SET platform_id = ?, platform_source = 'ai_assisted',
                    platform_confidence = 'ai_assisted_unreviewed'
                WHERE id = ? AND (platform_confidence IS NULL OR platform_confidence != 'verified')
                """,
                (platform_id, t["id"]),
            )
    conn.commit()
