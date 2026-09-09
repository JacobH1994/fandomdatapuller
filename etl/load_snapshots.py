#!/usr/bin/env python3
"""Idempotent ETL: data/raw/{twitch,youtube,steam}/*.json.gz ->
research.db (PRD §9, §18, §9.7, §9.12).

research.db is derived and disposable — re-running this over the full raw
history from scratch always produces the same result. Each raw file is
loaded in its own transaction and only recorded in collector_runs once
fully loaded, so a file is either "not loaded yet" or "fully loaded," never
partially. Already-loaded files (by relative path) are skipped on rerun.

Also loads data/reference/{tournaments,tournament_aliases,
tournament_alias_llm_checked,steam_release_history,
monthly_category_history}.jsonl on every run (see
etl/export_reference_data.py) — this is what makes `--rebuild` actually
rebuild a *working* database rather than one with an empty tournaments
table: collectors/liquipedia.py writes tournament data directly into
research.db with no raw-file backup, so without this, --rebuild would
silently discard it (and, for the LLM-checked marker, silently re-spend
already-spent API budget re-asking questions already answered).
monthly_category_history (added 2026-09-09) closes the same gap a third
time — it had regressed to 0 rows after a --rebuild ran while this table
was still uncovered here. Cheap and idempotent (natural-key upserts), so
it runs unconditionally, not just under --rebuild.

`--rebuild` refuses to run if anything else currently holds research.db
open (etl/db.py's try_acquire_rebuild_lock — an OS-level advisory lock,
not a guess) — added 2026-09-09 after a real incident where --rebuild
deleted the file out from under a still-running Steam catalog backfill
and the replacement came up corrupted. No data was lost that time
(recovered via /proc/<pid>/fd), but this closes the gap properly instead
of relying on being able to do that again.

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
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from etl.db import DB_PATH, get_connection, seed_titles_and_aliases, try_acquire_rebuild_lock  # noqa: E402

TITLES_CONFIG = REPO_ROOT / "config" / "titles.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw" / "twitch"
RAW_DIR_YOUTUBE = REPO_ROOT / "data" / "raw" / "youtube"
RAW_DIR_STEAM = REPO_ROOT / "data" / "raw" / "steam"
RAW_DIR_STEAM_DISCOVERY = REPO_ROOT / "data" / "raw" / "steam_discovery"
RAW_DIR_STEAM_COHORT = REPO_ROOT / "data" / "raw" / "steam_cohort"
STEAM_COHORT_DAILY_PHASE_DAYS = 90
STEAM_COHORT_TRACKING_WINDOW_DAYS = 365
REFERENCE_DIR = REPO_ROOT / "data" / "reference"


def load_reference_data(conn) -> tuple[int, int, int, int, int]:
    """Loads data/reference/{tournaments,tournament_aliases,
    steam_release_history,monthly_category_history}.jsonl (see
    etl/export_reference_data.py) into research.db. All files are
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

    llm_checked_written = 0
    llm_checked_path = REFERENCE_DIR / "tournament_alias_llm_checked.jsonl"
    if llm_checked_path.is_file():
        with open(llm_checked_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                c = json.loads(line)
                conn.execute(
                    """
                    INSERT INTO tournament_alias_llm_checked (title_id, series_key, checked_at, nickname_count)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (title_id, series_key) DO UPDATE SET
                        checked_at=excluded.checked_at, nickname_count=excluded.nickname_count
                    """,
                    (c["title_id"], c["series_key"], c["checked_at"], c["nickname_count"]),
                )
                llm_checked_written += 1
        conn.commit()

    steam_release_written = 0
    steam_release_path = REFERENCE_DIR / "steam_release_history.jsonl"
    if steam_release_path.is_file():
        with open(steam_release_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                conn.execute(
                    """
                    INSERT INTO steam_release_history
                        (app_id, name, app_type, release_date_raw, release_date, is_released,
                         genres, is_indie, categories, has_vr_support, vr_only,
                         developers, publishers, recommendations_total, low_relevance_flag,
                         fetched_at, source, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (app_id) DO UPDATE SET
                        name=excluded.name, app_type=excluded.app_type,
                        release_date_raw=excluded.release_date_raw, release_date=excluded.release_date,
                        is_released=excluded.is_released, genres=excluded.genres,
                        is_indie=excluded.is_indie, categories=excluded.categories,
                        has_vr_support=excluded.has_vr_support, vr_only=excluded.vr_only,
                        developers=excluded.developers, publishers=excluded.publishers,
                        recommendations_total=excluded.recommendations_total,
                        low_relevance_flag=excluded.low_relevance_flag,
                        fetched_at=excluded.fetched_at, source=excluded.source, confidence=excluded.confidence
                    """,
                    (
                        r["app_id"], r["name"], r["app_type"], r["release_date_raw"], r["release_date"],
                        r["is_released"], r["genres"], r["is_indie"], r["categories"], r["has_vr_support"],
                        r["vr_only"], r["developers"], r["publishers"], r["recommendations_total"],
                        r["low_relevance_flag"], r["fetched_at"], r["source"], r["confidence"],
                    ),
                )
                steam_release_written += 1
        conn.commit()

    monthly_category_written = 0
    monthly_category_path = REFERENCE_DIR / "monthly_category_history.jsonl"
    if monthly_category_path.is_file():
        with open(monthly_category_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                m = json.loads(line)
                conn.execute(
                    """
                    INSERT INTO monthly_category_history
                        (title_id, year_month, hours_watched, avg_viewers, peak_viewers, source, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (title_id, year_month) DO UPDATE SET
                        hours_watched=excluded.hours_watched, avg_viewers=excluded.avg_viewers,
                        peak_viewers=excluded.peak_viewers, source=excluded.source,
                        confidence=excluded.confidence
                    """,
                    (
                        m["title_id"], m["year_month"], m["hours_watched"], m["avg_viewers"],
                        m["peak_viewers"], m["source"], m["confidence"],
                    ),
                )
                monthly_category_written += 1
        conn.commit()

    return (
        tournaments_written, aliases_written, llm_checked_written, steam_release_written,
        monthly_category_written,
    )


def load_titles_config() -> list[dict]:
    import yaml

    with open(TITLES_CONFIG) as f:
        return yaml.safe_load(f).get("titles", [])


def already_loaded_files(conn, collector: str = "twitch_poll") -> set[str]:
    rows = conn.execute(
        "SELECT raw_file FROM collector_runs WHERE collector = ? AND raw_file IS NOT NULL",
        (collector,),
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


def load_one_youtube_file(conn, path: Path) -> int:
    """Loads one collectors/youtube_poll.py raw snapshot (PRD §9.7).

    Every row is is_official_broadcast=1 by construction — a YouTube
    channel only appears here because it's in config/channels_youtube.yaml
    in the first place, unlike Twitch's tiered capture. Only channels
    that were actually LIVE this check get a viewership_snapshots row —
    a not-live check isn't "zero viewers," it's "nothing was broadcasting,"
    so it's correctly not represented as a row at all, matching how
    below-threshold Twitch streams are excluded from individual rows too.

    Also upserts `channels` (platform='youtube') from whatever channels
    this snapshot actually checked — the first thing in this codebase to
    ever write to that table (config/channels.yaml's Twitch channels are
    read directly by collectors/twitch_poll.py at capture time and never
    synced into it, a separate, pre-existing gap this doesn't attempt to
    close)."""
    rel_path = str(path.relative_to(REPO_ROOT))
    with gzip.open(path, "rt") as f:
        snapshot = json.load(f)

    rows_written = 0

    with conn:
        for ch in snapshot.get("channels", []):
            conn.execute(
                """
                INSERT INTO channels (title_id, platform, external_channel_id, login, name, is_official, source, confidence)
                VALUES (?, 'youtube', ?, ?, ?, 1, 'youtube_api', 'verified')
                ON CONFLICT (title_id, platform, login) DO UPDATE SET
                    external_channel_id=excluded.external_channel_id, name=excluded.name
                """,
                (ch["title_id"], ch["channel_id"], ch["channel_id"], ch.get("channel_name")),
            )

            if not ch.get("is_live"):
                continue

            conn.execute(
                """
                INSERT INTO viewership_snapshots
                    (title_id, platform, channel_id, channel_login, captured_at, viewer_count,
                     is_official_broadcast, stream_title, source, confidence)
                VALUES (?, 'youtube', ?, ?, ?, ?, 1, ?, 'youtube_api', 'verified')
                ON CONFLICT (channel_id, captured_at) DO NOTHING
                """,
                (
                    ch["title_id"], ch["channel_id"], ch["channel_id"], ch["checked_at"],
                    ch.get("viewer_count") or 0, ch.get("video_title"),
                ),
            )
            rows_written += 1

        errors = snapshot.get("errors") or []
        conn.execute(
            """
            INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
            VALUES ('youtube_poll', ?, ?, ?, ?, ?, ?)
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


def load_one_steam_file(conn, path: Path) -> int:
    """Loads one collectors/steam_poll.py raw snapshot (PRD §9.12).

    A title with player_count=None (Steam's API itself reported failure
    for that appid this poll — see parse_player_count_response's own
    docstring) gets no row at all, not a fabricated 0 — the same
    "absence means unknown, not zero" discipline already used for
    below-threshold Twitch streams and not-live YouTube channels."""
    rel_path = str(path.relative_to(REPO_ROOT))
    with gzip.open(path, "rt") as f:
        snapshot = json.load(f)

    rows_written = 0

    with conn:
        for t in snapshot.get("titles", []):
            if t.get("player_count") is None:
                continue
            conn.execute(
                """
                INSERT INTO steam_player_counts (title_id, captured_at, player_count, source, confidence)
                VALUES (?, ?, ?, 'steam_api', 'verified')
                ON CONFLICT (title_id, captured_at) DO NOTHING
                """,
                (t["title_id"], t["checked_at"], t["player_count"]),
            )
            rows_written += 1

        errors = snapshot.get("errors") or []
        conn.execute(
            """
            INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
            VALUES ('steam_poll', ?, ?, ?, ?, ?, ?)
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


def load_one_steam_discovery_file(conn, path: Path) -> int:
    """Loads one collectors/steam_discovery_poll.py raw snapshot (PRD
    §9.12a, Track B part 1). Upserts every classified app into
    steam_release_history regardless of whether it's new or a metadata
    update. Separately: any app_id NOT already in steam_release_cohort at
    load time gets a fresh cohort row inserted (discovered_at = this
    snapshot's captured_at, tracking_window_end = +365 days, next_poll_due
    = immediately) -- the collector script itself doesn't decide "is this
    new," only the loader does, since only the loader has a real,
    already-rebuilt research.db to check against."""
    rel_path = str(path.relative_to(REPO_ROOT))
    with gzip.open(path, "rt") as f:
        snapshot = json.load(f)

    rows_written = 0
    captured_at = snapshot["captured_at"]

    with conn:
        for a in snapshot.get("apps", []):
            app_id = a["app_id"]
            conn.execute(
                """
                INSERT INTO steam_release_history
                    (app_id, name, app_type, release_date_raw, release_date, is_released,
                     genres, is_indie, categories, has_vr_support, vr_only,
                     developers, publishers, recommendations_total, low_relevance_flag,
                     fetched_at, source, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'steam_store_api', 'verified')
                ON CONFLICT (app_id) DO UPDATE SET
                    name=excluded.name, app_type=excluded.app_type,
                    release_date_raw=excluded.release_date_raw, release_date=excluded.release_date,
                    is_released=excluded.is_released, genres=excluded.genres, is_indie=excluded.is_indie,
                    categories=excluded.categories, has_vr_support=excluded.has_vr_support,
                    vr_only=excluded.vr_only, developers=excluded.developers, publishers=excluded.publishers,
                    recommendations_total=excluded.recommendations_total,
                    low_relevance_flag=excluded.low_relevance_flag, fetched_at=excluded.fetched_at
                """,
                (
                    app_id, a["name"], a["app_type"], a["release_date_raw"], a["release_date"],
                    a["is_released"], a["genres"], a["is_indie"], a["categories"],
                    a["has_vr_support"], a["vr_only"], a["developers"], a["publishers"],
                    a["recommendations_total"], a["low_relevance_flag"], captured_at,
                ),
            )
            rows_written += 1

            already_cohort = conn.execute(
                "SELECT 1 FROM steam_release_cohort WHERE app_id = ?", (app_id,)
            ).fetchone()
            if already_cohort is None:
                discovered = datetime.strptime(captured_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                window_end = discovered + timedelta(days=STEAM_COHORT_TRACKING_WINDOW_DAYS)
                conn.execute(
                    """
                    INSERT INTO steam_release_cohort (app_id, discovered_at, tracking_window_end, last_polled_at, next_poll_due)
                    VALUES (?, ?, ?, NULL, ?)
                    """,
                    (
                        app_id, captured_at,
                        window_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        captured_at,  # due immediately
                    ),
                )

        errors = snapshot.get("errors") or []
        conn.execute(
            """
            INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
            VALUES ('steam_discovery_poll', ?, ?, ?, ?, ?, ?)
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


def load_one_steam_cohort_file(conn, path: Path) -> int:
    """Loads one collectors/steam_cohort_poll.py raw snapshot (PRD
    §9.12a, Track B part 2) into steam_cohort_player_counts. Recomputes
    next_poll_due from steam_release_cohort.discovered_at at LOAD time
    (daily for the first 90 days, weekly after) rather than trusting a
    value baked into the raw file -- discovered_at in the DB is the
    source of truth for "how old is this cohort entry," and the
    collector script itself already updates next_poll_due directly when
    run locally, so this is primarily what makes the schedule correct
    when reconstructing research.db from raw files alone (--rebuild)."""
    rel_path = str(path.relative_to(REPO_ROOT))
    with gzip.open(path, "rt") as f:
        snapshot = json.load(f)

    rows_written = 0

    with conn:
        for a in snapshot.get("apps", []):
            if a.get("player_count") is None:
                continue
            app_id = a["app_id"]
            checked_at = a["checked_at"]
            conn.execute(
                """
                INSERT INTO steam_cohort_player_counts (app_id, captured_at, player_count, source, confidence)
                VALUES (?, ?, ?, 'steam_api', 'verified')
                ON CONFLICT (app_id, captured_at) DO NOTHING
                """,
                (app_id, checked_at, a["player_count"]),
            )
            rows_written += 1

            cohort_row = conn.execute(
                "SELECT discovered_at FROM steam_release_cohort WHERE app_id = ?", (app_id,)
            ).fetchone()
            if cohort_row is not None:
                discovered_at = datetime.strptime(cohort_row[0], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                checked = datetime.strptime(checked_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                age_days = (checked - discovered_at).days
                interval = timedelta(days=1) if age_days < STEAM_COHORT_DAILY_PHASE_DAYS else timedelta(days=7)
                next_due = (checked + interval).strftime("%Y-%m-%dT%H:%M:%SZ")
                conn.execute(
                    "UPDATE steam_release_cohort SET last_polled_at = ?, next_poll_due = ? WHERE app_id = ?",
                    (checked_at, next_due, app_id),
                )

        errors = snapshot.get("errors") or []
        conn.execute(
            """
            INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
            VALUES ('steam_cohort_poll', ?, ?, ?, ?, ?, ?)
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

    if args.rebuild:
        if not try_acquire_rebuild_lock():
            print(
                "[error] research.db appears to be in use by another process right now "
                "(a running collector, or collectors/steam_catalog_backfill.py, which can "
                "stay connected for hours/days) -- refusing to --rebuild while that's true, "
                "since deleting the file out from under an open connection can corrupt it. "
                "Stop that process first, then retry.",
                file=sys.stderr,
            )
            return 1
        if DB_PATH.exists():
            DB_PATH.unlink()
            print(f"deleted {DB_PATH}")

    conn = get_connection()
    seed_titles_and_aliases(conn, load_titles_config())

    n_tournaments, n_aliases, n_llm_checked, n_steam_releases, n_monthly_category = load_reference_data(conn)
    print(f"loaded {n_tournaments} tournament(s), {n_aliases} tournament alias(es), "
          f"{n_llm_checked} LLM-checked series marker(s), {n_steam_releases} Steam release(s), "
          f"{n_monthly_category} monthly category history row(s) from data/reference/")

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

    loaded_yt = already_loaded_files(conn, collector="youtube_poll")
    all_files_yt = sorted(RAW_DIR_YOUTUBE.glob("**/*.json.gz"))
    to_load_yt = [p for p in all_files_yt if str(p.relative_to(REPO_ROOT)) not in loaded_yt]

    print(f"{len(all_files_yt)} YouTube raw files found, {len(loaded_yt)} already loaded, {len(to_load_yt)} to load")

    total_rows_yt = 0
    failures_yt = 0
    for path in to_load_yt:
        try:
            rows = load_one_youtube_file(conn, path)
            total_rows_yt += rows
        except Exception as exc:
            failures_yt += 1
            print(f"[error] failed to load {path}: {exc}", file=sys.stderr)

    loaded_steam = already_loaded_files(conn, collector="steam_poll")
    all_files_steam = sorted(RAW_DIR_STEAM.glob("**/*.json.gz"))
    to_load_steam = [p for p in all_files_steam if str(p.relative_to(REPO_ROOT)) not in loaded_steam]

    print(f"{len(all_files_steam)} Steam raw files found, {len(loaded_steam)} already loaded, {len(to_load_steam)} to load")

    total_rows_steam = 0
    failures_steam = 0
    for path in to_load_steam:
        try:
            rows = load_one_steam_file(conn, path)
            total_rows_steam += rows
        except Exception as exc:
            failures_steam += 1
            print(f"[error] failed to load {path}: {exc}", file=sys.stderr)

    loaded_disc = already_loaded_files(conn, collector="steam_discovery_poll")
    all_files_disc = sorted(RAW_DIR_STEAM_DISCOVERY.glob("**/*.json.gz"))
    to_load_disc = [p for p in all_files_disc if str(p.relative_to(REPO_ROOT)) not in loaded_disc]

    print(f"{len(all_files_disc)} Steam discovery raw files found, {len(loaded_disc)} already loaded, {len(to_load_disc)} to load")

    total_rows_disc = 0
    failures_disc = 0
    for path in to_load_disc:
        try:
            rows = load_one_steam_discovery_file(conn, path)
            total_rows_disc += rows
        except Exception as exc:
            failures_disc += 1
            print(f"[error] failed to load {path}: {exc}", file=sys.stderr)

    loaded_cohort = already_loaded_files(conn, collector="steam_cohort_poll")
    all_files_cohort = sorted(RAW_DIR_STEAM_COHORT.glob("**/*.json.gz"))
    to_load_cohort = [p for p in all_files_cohort if str(p.relative_to(REPO_ROOT)) not in loaded_cohort]

    print(f"{len(all_files_cohort)} Steam cohort raw files found, {len(loaded_cohort)} already loaded, {len(to_load_cohort)} to load")

    total_rows_cohort = 0
    failures_cohort = 0
    for path in to_load_cohort:
        try:
            rows = load_one_steam_cohort_file(conn, path)
            total_rows_cohort += rows
        except Exception as exc:
            failures_cohort += 1
            print(f"[error] failed to load {path}: {exc}", file=sys.stderr)

    conn.close()
    print(f"loaded {len(to_load) - failures}/{len(to_load)} Twitch file(s), {total_rows} row(s) written")
    print(f"loaded {len(to_load_yt) - failures_yt}/{len(to_load_yt)} YouTube file(s), {total_rows_yt} row(s) written")
    print(f"loaded {len(to_load_steam) - failures_steam}/{len(to_load_steam)} Steam file(s), {total_rows_steam} row(s) written")
    print(f"loaded {len(to_load_disc) - failures_disc}/{len(to_load_disc)} Steam discovery file(s), {total_rows_disc} row(s) written")
    print(f"loaded {len(to_load_cohort) - failures_cohort}/{len(to_load_cohort)} Steam cohort file(s), {total_rows_cohort} row(s) written")
    return 1 if (failures or failures_yt or failures_steam or failures_disc or failures_cohort) else 0


if __name__ == "__main__":
    sys.exit(main())
