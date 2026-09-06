#!/usr/bin/env python3
"""Idempotent ETL: data/raw/twitch/*.json.gz -> research.db (PRD §9, §18).

research.db is derived and disposable — re-running this over the full raw
history from scratch always produces the same result. Each raw file is
loaded in its own transaction and only recorded in collector_runs once
fully loaded, so a file is either "not loaded yet" or "fully loaded," never
partially. Already-loaded files (by relative path) are skipped on rerun.

Also loads data/reference/{tournaments,tournament_aliases}.jsonl on every
run (see etl/export_reference_data.py) — this is what makes `--rebuild`
actually rebuild a *working* database rather than one with an empty
tournaments table: collectors/liquipedia.py writes tournament data
directly into research.db with no raw-file backup, so without this,
--rebuild would silently discard it. Cheap and idempotent (natural-key
upserts), so it runs unconditionally, not just under --rebuild.

Usage:
    python etl/load_snapshots.py                 # incremental: only new files
    python etl/load_snapshots.py --rebuild        # delete research.db and reload everything
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from etl.db import DB_PATH, get_connection, seed_titles_and_aliases  # noqa: E402

TITLES_CONFIG = REPO_ROOT / "config" / "titles.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw" / "twitch"
REFERENCE_DIR = REPO_ROOT / "data" / "reference"


def load_reference_data(conn) -> tuple[int, int]:
    """Loads data/reference/{tournaments,tournament_aliases}.jsonl (see
    etl/export_reference_data.py) into research.db. Both files are
    optional — a repo checkout that predates this mechanism, or one where
    export hasn't been run yet, just skips silently (nothing to load is
    not an error). Natural-key upserts throughout, so safe to call on
    every run, not just --rebuild.

    tournament_aliases rows are keyed on (title_id, series_key) in the
    export, not a raw numeric tournament_id — series_key is itself a
    stable string (etl/generate_tournament_aliases.py), so this is a
    direct natural-key upsert, no id resolution needed."""
    tournaments_written = 0
    tournaments_path = REFERENCE_DIR / "tournaments.jsonl"
    if tournaments_path.is_file():
        with open(tournaments_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                t = json.loads(line)
                conn.execute(
                    """
                    INSERT INTO tournaments
                        (title_id, liquipedia_wiki, liquipedia_page, name, tier, prize_pool,
                         currency, start_date, end_date, country, region, region_confidence,
                         team_number, series_key, fetched_at, source, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (liquipedia_wiki, liquipedia_page) DO UPDATE SET
                        title_id=excluded.title_id, name=excluded.name, tier=excluded.tier,
                        prize_pool=excluded.prize_pool, currency=excluded.currency,
                        start_date=excluded.start_date, end_date=excluded.end_date,
                        country=excluded.country, region=excluded.region,
                        region_confidence=excluded.region_confidence,
                        team_number=excluded.team_number, series_key=excluded.series_key,
                        fetched_at=excluded.fetched_at,
                        source=excluded.source, confidence=excluded.confidence
                    """,
                    (
                        t["title_id"], t["liquipedia_wiki"], t["liquipedia_page"], t["name"], t["tier"],
                        t["prize_pool"], t["currency"], t["start_date"], t["end_date"], t["country"],
                        t["region"], t["region_confidence"], t["team_number"], t.get("series_key"),
                        t["fetched_at"], t["source"], t["confidence"],
                    ),
                )
                tournaments_written += 1
        conn.commit()

    aliases_written = 0
    aliases_path = REFERENCE_DIR / "tournament_aliases.jsonl"
    if aliases_path.is_file():
        with open(aliases_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                a = json.loads(line)
                conn.execute(
                    """
                    INSERT INTO tournament_aliases (title_id, series_key, alias, case_sensitive, source, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT (title_id, series_key, alias) DO UPDATE SET
                        case_sensitive=excluded.case_sensitive, source=excluded.source,
                        confidence=excluded.confidence
                    """,
                    (a["title_id"], a["series_key"], a["alias"], a["case_sensitive"], a["source"], a["confidence"]),
                )
                aliases_written += 1
        conn.commit()

    return tournaments_written, aliases_written


def load_titles_config() -> list[dict]:
    import yaml

    with open(TITLES_CONFIG) as f:
        return yaml.safe_load(f).get("titles", [])


def already_loaded_files(conn) -> set[str]:
    rows = conn.execute(
        "SELECT raw_file FROM collector_runs WHERE collector = 'twitch_poll' AND raw_file IS NOT NULL"
    ).fetchall()
    return {r[0] for r in rows}


def load_one_file(conn, path: Path) -> int:
    rel_path = str(path.relative_to(REPO_ROOT))
    with gzip.open(path, "rt") as f:
        snapshot = json.load(f)

    rows_written = 0
    captured_at = snapshot["captured_at"]

    with conn:  # one transaction per file: fully loaded or not at all
        for title_id, title_data in snapshot.get("titles", {}).items():
            streams = title_data.get("streams", [])
            lang_totals: Counter[str] = Counter()

            for stream in streams:
                language = stream.get("language") or "unknown"
                lang_totals[language] += stream.get("viewer_count", 0)
                tags = stream.get("tags") or []
                conn.execute(
                    """
                    INSERT INTO viewership_snapshots
                        (title_id, channel_id, channel_login, captured_at, viewer_count,
                         is_official_broadcast, stream_title, tags, language, source, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'twitch_api', 'verified')
                    ON CONFLICT (channel_id, captured_at) DO NOTHING
                    """,
                    (
                        title_id,
                        stream.get("user_id"),
                        stream.get("user_login"),
                        captured_at,
                        stream.get("viewer_count", 0),
                        1 if stream.get("is_official_broadcast") else 0,
                        stream.get("title"),
                        ",".join(tags) if tags else None,
                        stream.get("language"),
                    ),
                )
                rows_written += 1

            below = title_data.get("below_threshold") or {}
            for language, viewer_total in (below.get("viewer_total_by_language") or {}).items():
                lang_totals[language] += viewer_total

            for language, viewer_count in lang_totals.items():
                conn.execute(
                    """
                    INSERT INTO language_mix_snapshots
                        (title_id, captured_at, language_code, viewer_count, source, confidence)
                    VALUES (?, ?, ?, ?, 'twitch_api', 'verified')
                    ON CONFLICT (title_id, captured_at, language_code) DO NOTHING
                    """,
                    (title_id, captured_at, language, viewer_count),
                )
                rows_written += 1

        platform_totals = snapshot.get("platform_totals")
        if platform_totals:
            conn.execute(
                """
                INSERT INTO platform_totals
                    (captured_at, platform, total_viewers, total_channels, hit_page_cap, source, confidence)
                VALUES (?, 'twitch', ?, ?, ?, 'twitch_api', 'verified')
                ON CONFLICT (captured_at, platform) DO NOTHING
                """,
                (
                    captured_at,
                    platform_totals.get("total_viewers", 0),
                    platform_totals.get("total_channels", 0),
                    1 if platform_totals.get("hit_page_cap") else 0,
                ),
            )
            rows_written += 1

        errors = snapshot.get("errors") or []
        conn.execute(
            """
            INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
            VALUES ('twitch_poll', ?, ?, ?, ?, ?, ?)
            ON CONFLICT (collector, raw_file) DO NOTHING
            """,
            (
                rel_path,
                snapshot.get("run_started_at"),
                snapshot.get("run_finished_at"),
                snapshot.get("status", "unknown"),
                rows_written,
                json.dumps(errors) if errors else None,
            ),
        )

    return rows_written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="delete research.db and reload everything from data/raw/")
    args = parser.parse_args()

    if args.rebuild and DB_PATH.exists():
        DB_PATH.unlink()
        print(f"deleted {DB_PATH}")

    conn = get_connection()
    seed_titles_and_aliases(conn, load_titles_config())

    n_tournaments, n_aliases = load_reference_data(conn)
    print(f"loaded {n_tournaments} tournament(s), {n_aliases} tournament alias(es) from data/reference/")

    loaded = already_loaded_files(conn)
    all_files = sorted(RAW_DIR.glob("**/*.json.gz"))
    to_load = [p for p in all_files if str(p.relative_to(REPO_ROOT)) not in loaded]

    print(f"{len(all_files)} raw files found, {len(loaded)} already loaded, {len(to_load)} to load")

    total_rows = 0
    failures = 0
    for path in to_load:
        try:
            rows = load_one_file(conn, path)
            total_rows += rows
        except Exception as exc:  # one bad file shouldn't abort the whole run
            failures += 1
            print(f"[error] failed to load {path}: {exc}", file=sys.stderr)

    conn.close()
    print(f"loaded {len(to_load) - failures}/{len(to_load)} files, {total_rows} rows written")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
