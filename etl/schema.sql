-- SQLite schema for research.db (PRD §6). This file is the source of truth
-- for the schema; research.db itself is derived/disposable and gitignored
-- (rebuild with `python etl/load_snapshots.py --rebuild`).
--
-- Every ingested table carries `source` and `confidence` per PRD §14.
-- confidence values: 'verified' | 'ai_assisted_unreviewed' |
-- 'manual_judgment_call' | 'proxy_estimate'. Anything Claude Code infers
-- defaults to 'ai_assisted_unreviewed' unless it's a deterministic
-- extraction of primary-source data (e.g. parsing a Liquipedia infobox),
-- which is 'verified'.
--
-- All timestamps are UTC, ISO 8601 text (PRD §6) — SQLite has no native
-- datetime type, and storing as ISO text keeps them sortable and readable.

PRAGMA foreign_keys = ON;

-- Reference tables (PRD §6: "close to fixed facts about a product, sourced
-- once and rarely revisited" — a table you add rows to, not a hardcoded
-- enum). Populated in Phase 3; empty for now.
CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS platforms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- One row per tracked title. id is the same slug used in
-- config/titles.yaml, so seeding this table from that config is a direct
-- key match. genre_id is nullable until Phase 3 classification.
-- success_milestone_year is NOT a column here — PRD §6 is explicit that
-- it's derived, not stored, so it stays reproducible if the definition's
-- thresholds change. See analysis/metrics.py:get_success_milestone.
CREATE TABLE IF NOT EXISTS titles (
    id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    publisher TEXT,
    launch_date TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    genre_id INTEGER REFERENCES genres(id),
    source TEXT NOT NULL DEFAULT 'manual',
    confidence TEXT NOT NULL DEFAULT 'manual_judgment_call'
);

-- Load-bearing, not bookkeeping (PRD §6): a title can span several Twitch
-- categories across platforms, get renamed, or absorb a predecessor's
-- scene. valid_to = NULL means still current. Seeded from
-- config/titles.yaml (twitch_category_id) and extended by the Liquipedia
-- connector (liquipedia_wiki/liquipedia_page).
CREATE TABLE IF NOT EXISTS title_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    alias TEXT NOT NULL,
    platform TEXT,
    twitch_category_id TEXT,
    liquipedia_wiki TEXT,
    liquipedia_page TEXT,
    igdb_id TEXT,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    confidence TEXT NOT NULL DEFAULT 'manual_judgment_call',
    UNIQUE (title_id, alias, valid_from)
);

-- Populated by collectors/liquipedia.py. region is derived from the
-- infobox's country field via a small country->region lookup — that
-- derivation is a judgment call, not a direct measurement, so it gets its
-- own confidence even though tier/prize_pool/dates are 'verified'.
-- Kept simple as one confidence value per row for now (the row-level
-- convention PRD §14 describes); region_confidence exists because region
-- specifically is a step removed from the source field.
CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    liquipedia_wiki TEXT NOT NULL,
    liquipedia_page TEXT NOT NULL,
    name TEXT,
    tier TEXT, -- raw liquipediatier value, e.g. "1", "2" — see analysis/metrics.py
    prize_pool REAL,
    currency TEXT,
    start_date TEXT,
    end_date TEXT,
    country TEXT,
    region TEXT,
    region_confidence TEXT DEFAULT 'manual_judgment_call',
    team_number INTEGER,
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'liquipedia',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (liquipedia_wiki, liquipedia_page)
);

-- One row per full-detail stream per poll (PRD §6). Below-capture-threshold
-- streams (config/capture.yaml) never appear here individually — their
-- viewer_count is folded into platform_totals/language_mix_snapshots
-- instead. is_official_broadcast reflects config/channels.yaml *as of
-- capture time* (persisted by the collector itself, not recomputed here
-- from today's config) — see collectors/twitch_poll.py.
CREATE TABLE IF NOT EXISTS viewership_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    channel_id TEXT NOT NULL,
    channel_login TEXT,
    captured_at TEXT NOT NULL,
    viewer_count INTEGER NOT NULL,
    is_official_broadcast INTEGER NOT NULL DEFAULT 0,
    stream_title TEXT,
    language TEXT,
    source TEXT NOT NULL DEFAULT 'twitch_api',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (channel_id, captured_at)
);

-- Denominator for "esports' share of total platform attention" (PRD §6/§9).
-- One row per poll, from the collector's platform_totals aggregate
-- (already bounded/approximate if hit_page_cap is true on that poll).
CREATE TABLE IF NOT EXISTS platform_totals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'twitch',
    total_viewers INTEGER NOT NULL,
    total_channels INTEGER NOT NULL,
    hit_page_cap INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'twitch_api',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (captured_at, platform)
);

-- Region proxy (PRD §6): broadcast-language mix, aggregated at capture time
-- from the same poll as viewership_snapshots. One row per
-- (title, poll, language) combining each full-detail stream's own
-- `language` field with the collector's own below_threshold
-- viewer_total_by_language aggregate — see etl/load_snapshots.py.
CREATE TABLE IF NOT EXISTS language_mix_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    captured_at TEXT NOT NULL,
    language_code TEXT NOT NULL,
    viewer_count INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'twitch_api',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (title_id, captured_at, language_code)
);

-- Official broadcast channels per title (PRD §6/§7), mirrors
-- config/channels.yaml. Feeds is_official_broadcast and the
-- esports-vs-game-fandom "% of category attention on official channels"
-- metric (Phase 4).
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    platform TEXT NOT NULL DEFAULT 'twitch',
    external_channel_id TEXT,
    login TEXT NOT NULL,
    name TEXT,
    is_official INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'manual',
    confidence TEXT NOT NULL DEFAULT 'manual_judgment_call',
    UNIQUE (title_id, platform, login)
);

-- Phase 5 (optional). Schema only, empty until that phase.
CREATE TABLE IF NOT EXISTS community_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    subreddit_type TEXT NOT NULL,
    subscriber_count INTEGER,
    captured_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    confidence TEXT NOT NULL DEFAULT 'manual_judgment_call',
    UNIQUE (title_id, subreddit_type, captured_at)
);

-- Phase 5 (Esports Charts enterprise, if pursued). Schema only, empty.
CREATE TABLE IF NOT EXISTS demographic_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    age_bucket TEXT,
    gender TEXT,
    share REAL,
    captured_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'esportscharts',
    confidence TEXT NOT NULL DEFAULT 'manual_judgment_call'
);

-- Phase 5 (qualitative, manual). Mitigates survivorship bias, brief
-- Limitation 2. Schema only, empty until curated.
CREATE TABLE IF NOT EXISTS failed_challengers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    genre_id INTEGER REFERENCES genres(id),
    platform TEXT,
    region TEXT,
    notes TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    confidence TEXT NOT NULL DEFAULT 'manual_judgment_call'
);

-- Every collector run, scheduled or on-demand (PRD §10). For
-- twitch_poll.py, raw_file is the data/raw path loaded and doubles as the
-- ETL's idempotency key — a file already present here is skipped on
-- re-run. On-demand connectors (liquipedia) have no raw_file.
CREATE TABLE IF NOT EXISTS collector_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collector TEXT NOT NULL,
    raw_file TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    rows_written INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    UNIQUE (collector, raw_file)
);

CREATE INDEX IF NOT EXISTS idx_viewership_title_captured ON viewership_snapshots (title_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_language_mix_title_captured ON language_mix_snapshots (title_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_tournaments_title ON tournaments (title_id);
