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
-- key match. genre_id/platform_id are nullable until Phase 3
-- classification. success_milestone_year is NOT a column here — PRD §6 is
-- explicit that it's derived, not stored, so it stays reproducible if the
-- definition's thresholds change. See analysis/metrics.py:get_success_milestone.
--
-- genre_id/platform_id deliberately do NOT reuse the row-level
-- source/confidence above: that pair describes the manually-seeded
-- identity fields (canonical_name, is_active, ...), sourced from
-- config/titles.yaml at 'manual'/'manual_judgment_call'. Genre and platform
-- come from a different, later process (Claude's Phase 3 classification
-- pass, config-driven per CLAUDE.md's provenance rule) and need their own
-- source/confidence so reusing the row-level pair doesn't misrepresent
-- canonical_name etc. as ai_assisted — same reasoning as tournaments.
-- region_confidence below, extended to a full source+confidence pair
-- (rather than confidence alone) because unlike region, genre/platform's
-- *source* value ('ai_assisted') also differs from the row default, not
-- just its confidence. NULL until seeded; set to
-- ('ai_assisted', 'ai_assisted_unreviewed') by seed_titles_and_aliases
-- (etl/db.py) from config/titles.yaml's genre/platform fields, promoted to
-- 'verified' only by explicit human review (CLAUDE.md).
CREATE TABLE IF NOT EXISTS titles (
    id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    publisher TEXT,
    launch_date TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    genre_id INTEGER REFERENCES genres(id),
    genre_source TEXT,
    genre_confidence TEXT,
    platform_id INTEGER REFERENCES platforms(id),
    platform_source TEXT,
    platform_confidence TEXT,
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

-- Populated by etl/generate_tournament_aliases.py, per tournament (not per
-- series) even though generation happens once per series and fans out --
-- collectors/twitch_poll.py's/etl/classify_broadcast_tier.py's word-boundary
-- alias match (PRD §9.1 condition 3) needs a specific tournament_id to
-- attach a match to, so the same alias is inserted once per tournament
-- sharing that series rather than stored once at a series level that
-- doesn't otherwise exist as an entity in this schema.
-- Two provenance shapes, per row: rule-based extraction (source=
-- 'rule_based', confidence='verified' — a deterministic transform of
-- already-verified tournament data, same reasoning as tier/prize_pool)
-- and LLM-derived colloquial nicknames (source='ai_assisted',
-- confidence='ai_assisted_unreviewed' per PRD §14/CLAUDE.md's provenance
-- rule — never promoted without human review).
CREATE TABLE IF NOT EXISTS tournament_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id),
    alias TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'rule_based',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (tournament_id, alias)
);

-- One row per full-detail stream per poll (PRD §6). Below-capture-threshold
-- streams (config/capture.yaml) never appear here individually — their
-- viewer_count is folded into platform_totals/language_mix_snapshots
-- instead. is_official_broadcast reflects config/channels.yaml *as of
-- capture time* (persisted by the collector itself, not recomputed here
-- from today's config) — see collectors/twitch_poll.py.
--
-- broadcast_tier/matched_tournament_id/matched_alias: set by
-- etl/classify_broadcast_tier.py per PRD §9.1's three-condition detection.
-- Deliberately columns here, not PRD §6's originally-sketched separate
-- channel_broadcast_roles table (channel_id, tournament_id, valid_from/to)
-- — a per-snapshot annotation is the right grain: a single channel can be
-- primary_official during one event and general the rest of the time, and
-- several tournaments for the same title can run concurrently, so "which
-- tournament, if any, does THIS specific poll match" is a fact about the
-- snapshot, not a durable validity-dated role assignment on the channel.
-- matched_tournament_id/matched_alias store WHY a row was classified
-- detected_costream, not just the verdict, so any classification is
-- auditable rather than a bare label. NULL broadcast_tier means
-- unclassified (this pass hasn't run on that row yet), not "general" —
-- classify_broadcast_tier.py's incremental mode targets exactly these.
CREATE TABLE IF NOT EXISTS viewership_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    channel_id TEXT NOT NULL,
    channel_login TEXT,
    captured_at TEXT NOT NULL,
    viewer_count INTEGER NOT NULL,
    is_official_broadcast INTEGER NOT NULL DEFAULT 0,
    stream_title TEXT,
    tags TEXT, -- comma-joined, as captured (collectors/twitch_poll.py's raw JSON has a tags array per stream) — NULL for rows loaded before this column existed, not "no tags"; etl/classify_broadcast_tier.py's alias match treats a NULL here as "nothing to search," not a failure
    language TEXT,
    broadcast_tier TEXT, -- 'primary_official' | 'detected_costream' | 'general' | NULL (unclassified)
    broadcast_tier_confidence TEXT, -- 'verified' (primary_official/general) | 'proxy_estimate' (detected_costream, PRD §9.1)
    matched_tournament_id INTEGER REFERENCES tournaments(id),
    matched_alias TEXT,
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

-- One-time Kaggle historical import (PRD §9.6) — the only source in this
-- project reaching Twitch category-wide viewership before the collector's
-- own start date (2026-08-31). Deliberately separate from
-- viewership_snapshots, not merged into it: this is monthly
-- pre-aggregated data, not poll-derived, and merging them would leave a
-- future query silently comparing monthly averages against hourly polls.
-- Category-wide, not esports-specific — "game fandom, not esports
-- fandom" per §9.6, includes ranked play/guides/cosmetics content —
-- never fold directly into an esports-specific metric without labelling
-- (see analysis/metrics.py's use of it). Provenance is unverified (the
-- dataset doesn't document its own collection method), hence
-- confidence='proxy_estimate' by default rather than 'verified'. See
-- collectors/kaggle_import.py.
CREATE TABLE IF NOT EXISTS monthly_category_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    year_month TEXT NOT NULL, -- 'YYYY-MM'
    hours_watched REAL,
    avg_viewers REAL,
    peak_viewers REAL,
    source TEXT NOT NULL DEFAULT 'kaggle_import',
    confidence TEXT NOT NULL DEFAULT 'proxy_estimate',
    UNIQUE (title_id, year_month)
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
CREATE INDEX IF NOT EXISTS idx_tournament_aliases_tournament ON tournament_aliases (tournament_id);
CREATE INDEX IF NOT EXISTS idx_viewership_broadcast_tier ON viewership_snapshots (broadcast_tier);
CREATE INDEX IF NOT EXISTS idx_tournaments_title_dates ON tournaments (title_id, start_date, end_date);
