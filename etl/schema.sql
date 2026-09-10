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
-- series_key groups tournaments belonging to the same recurring series
-- (e.g. every "VCT/<year>/Champions" edition) — a Liquipedia-naming-
-- convention judgment call, not a native field, derived rule-based by
-- etl/generate_tournament_aliases.py from liquipedia_page (stripping
-- years and, for a small set of bare-organizer-acronym prefixes like
-- "ESL"/"PGL"/"MPL", folding in the next segment too so distinct branded
-- sub-events don't collapse together — see that script's docstring for
-- the full derivation and the real cases it was calibrated against).
-- Only ever populated for tier-1/tier-2 tournaments (co-streaming is a
-- top-tier phenomenon) — NULL here means "not aliased," not "unknown."
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
    series_key TEXT,
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'liquipedia',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (liquipedia_wiki, liquipedia_page)
);

-- Populated by etl/generate_tournament_aliases.py, keyed on (title_id,
-- series_key) rather than a specific tournament_id: an alias identifies a
-- recurring SERIES ("The International", "TI"), not one edition — the
-- temporal join in etl/classify_broadcast_tier.py (condition 2, against
-- tournaments.start_date/end_date) is what disambiguates which edition a
-- stream actually refers to, so the alias set itself doesn't need to be
-- edition-specific. title_id is part of the key (not derivable from
-- series_key alone) because the same organizer/series name recurs across
-- unrelated games (e.g. "ESL/Snapdragon Pro Series" exists separately for
-- pubg_mobile, free_fire, mobile_legends_bb, wild_rift, brawl_stars).
--
-- case_sensitive: aliases under 4 characters (e.g. "TI", "MSI") collide
-- with unrelated text even under word-boundary matching if matched
-- case-insensitively, so those rows carry case_sensitive=1 and
-- etl/classify_broadcast_tier.py's compile_alias_pattern() honors it.
--
-- Two provenance shapes, per row: rule-based extraction (source=
-- 'rule_based', confidence='verified' — a deterministic transform of
-- already-verified tournament data, same reasoning as tier/prize_pool)
-- and LLM-derived colloquial nicknames (source='ai_assisted',
-- confidence='ai_assisted_unreviewed' per PRD §14/CLAUDE.md's provenance
-- rule — never promoted without human review).
CREATE TABLE IF NOT EXISTS tournament_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    series_key TEXT NOT NULL,
    alias TEXT NOT NULL,
    case_sensitive INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'rule_based',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (title_id, series_key, alias)
);

-- Marks a series as "the LLM nickname pass has been attempted," separate
-- from tournament_aliases itself — a genuinely-empty LLM result (no
-- well-known nickname exists) writes zero alias rows, so checking
-- tournament_aliases alone for "already done" would retry that series
-- forever, burning API budget on the same negative answer every run.
-- Rule-based-only series (no ANTHROPIC_API_KEY, or --skip-llm) correctly
-- have NO row here, so a later run with the LLM enabled still checks them.
CREATE TABLE IF NOT EXISTS tournament_alias_llm_checked (
    title_id TEXT NOT NULL REFERENCES titles(id),
    series_key TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    nickname_count INTEGER NOT NULL,
    PRIMARY KEY (title_id, series_key)
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
-- platform: added 2026-09-08 for collectors/youtube_poll.py (PRD §9.7).
-- The PRD's own §9.7 note says this table needs "no schema change" —
-- that undersold it: without an explicit discriminator, a query summing
-- viewer_count across this table (analysis/metrics.py's
-- _viewership_trend does exactly this) would silently blend Twitch and
-- YouTube viewer counts together the moment YouTube rows exist, which is
-- sometimes the right question (total cross-platform attention) and
-- sometimes badly wrong (a per-platform trend), and nothing would flag
-- which. channel_id's format alone (YouTube's "UC..." vs. Twitch's
-- numeric user_id) is not a reason to skip an explicit column just
-- because it happens to be inferable — DEFAULT 'twitch' backfills every
-- existing row correctly with no guessing.
CREATE TABLE IF NOT EXISTS viewership_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    platform TEXT NOT NULL DEFAULT 'twitch',
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
    -- Not (platform, channel_id, captured_at): channel_id formats don't
    -- collide across platforms in practice (YouTube's "UC..." vs.
    -- Twitch's numeric user_id) — adding platform to the key would need
    -- an invasive recreate-and-copy migration on a live table with no
    -- real safety benefit, so left as-is deliberately, not overlooked.
    UNIQUE (channel_id, captured_at)
);

-- Current Steam concurrent-player count per title (PRD §9.12), added
-- 2026-09-08. Deliberately NOT a row in viewership_snapshots — that
-- table is about STREAM viewership (a channel someone is watching);
-- this is about PLAYING the game, a fundamentally different signal, the
-- same reasoning monthly_category_history already documents for staying
-- separate from viewership_snapshots. Steam's own
-- GetNumberOfCurrentPlayers has no historical parameter — confirmed live
-- (2026-09-08) it's current-state-only, same unbackfillable property as
-- Twitch/YouTube's live APIs (CLAUDE.md's "one rule," extended again).
-- Only covers titles actually distributed on Steam (config/
-- steam_appids.yaml) — Riot's client-exclusive titles and every mobile
-- title have no Steam presence at all, not a gap in this table, a real
-- property of the platform.
CREATE TABLE IF NOT EXISTS steam_player_counts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    captured_at TEXT NOT NULL,
    player_count INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'steam_api',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (title_id, captured_at)
);

-- Steam catalog classification (PRD §9.12a), added 2026-09-08. One row
-- per app_id, covering EVERY Steam release (not just the 23 tracked
-- esports titles) — release metadata, not player counts, so it's fixed
-- historical fact and NOT subject to the "one rule"/§2 backfill
-- constraint the live-poll tables are. Written by two producers into the
-- same table: collectors/steam_catalog_backfill.py (Track A, one-time,
-- on-demand, walks the full historical catalog) and
-- collectors/steam_discovery_poll.py (Track B, ongoing, scheduled,
-- if_modified_since-driven) — same classification logic in both, see
-- collectors/steam_catalog_common.py.
--
-- app_id is the primary key directly (Steam's own ID, already globally
-- unique) rather than a separate autoincrement id — there's no reason
-- for a surrogate key when the natural one is already stable and simple.
--
-- VR and Indie are DERIVED, boolean columns, not left as "check the raw
-- categories/genres text every time" — confirmed live (2026-09-08)
-- against Half-Life: Alyx that VR support lives in `categories` (id 31 =
-- "VR Support", id 54 = "VR Only"), NOT `genres` (Alyx's own genres are
-- just ["Action", "Adventure"], no VR signal there at all). is_indie is
-- derived from "Indie" appearing in `genres` — note genres is a
-- multi-valued list, not a taxonomy: a title can carry "Indie" AND
-- "Action" simultaneously, and there is no positive "AAA" tag, only the
-- absence of "Indie".
--
-- low_relevance_flag (near-zero recommendations.total): flagged, never
-- used to DROP a row — volume/count analyses need the complete catalog
-- to stay honest, composition/lifecycle analyses can filter this flag
-- out when noise, not volume, is what matters.
CREATE TABLE IF NOT EXISTS steam_release_history (
    app_id INTEGER PRIMARY KEY,
    name TEXT,
    app_type TEXT, -- appdetails' own `type` field ("game", "dlc", ...) — a validation signal: GetAppList's default already excludes DLC, so a non-"game" value here would mean that assumption broke, not something to silently trust
    release_date_raw TEXT, -- as Steam gives it, e.g. "25 Mar, 2020" — not always a clean parseable date (can be "Coming soon" etc.)
    release_date TEXT, -- ISO 8601, NULL if release_date_raw wasn't parseable — same "malformed source data degrades gracefully, never guessed" discipline as tournaments.start_date
    is_released INTEGER NOT NULL DEFAULT 1, -- from release_date.coming_soon
    genres TEXT, -- comma-joined genre names, as given
    is_indie INTEGER NOT NULL DEFAULT 0,
    categories TEXT, -- comma-joined category descriptions, as given
    has_vr_support INTEGER NOT NULL DEFAULT 0, -- category id 31 present
    vr_only INTEGER NOT NULL DEFAULT 0, -- category id 54 present
    developers TEXT, -- comma-joined
    publishers TEXT, -- comma-joined
    recommendations_total INTEGER, -- NULL when appdetails omits the field entirely (not the same as a confirmed 0)
    low_relevance_flag INTEGER NOT NULL DEFAULT 0,
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'steam_store_api',
    confidence TEXT NOT NULL DEFAULT 'verified'
);

-- Which apps are inside their post-discovery lifecycle-tracking window
-- (PRD §9.12a Track B) — bookkeeping only, not the player-count data
-- itself (see steam_cohort_player_counts below). Populated when
-- collectors/steam_discovery_poll.py first sees a NEW app_id (one not
-- already in steam_release_history) via if_modified_since; existing
-- apps that merely got metadata updates are reclassified into
-- steam_release_history but do NOT re-enter the cohort.
--
-- Separate from steam_player_counts/steam_release_history deliberately:
-- app_id here is an arbitrary Steam catalog app, not one of the 23
-- tracked esports titles, so it can't reuse title_id-keyed tables (that
-- column is a REFERENCES titles(id) FK everywhere else in this schema).
CREATE TABLE IF NOT EXISTS steam_release_cohort (
    app_id INTEGER PRIMARY KEY REFERENCES steam_release_history(app_id),
    discovered_at TEXT NOT NULL,
    tracking_window_end TEXT NOT NULL, -- discovered_at + ~1 year
    last_polled_at TEXT,
    next_poll_due TEXT NOT NULL -- daily for the first ~90 days, weekly out to tracking_window_end — see collectors/steam_cohort_poll.py
);

-- The actual lifecycle player-count time series for cohort apps (PRD
-- §9.12a Track B) — the cohort-app equivalent of steam_player_counts,
-- separate because cohort apps aren't in `titles` (see
-- steam_release_cohort's own comment). Same unbackfillable property as
-- every other live-poll table: a missed day during a title's tracked
-- window is permanent loss, which is exactly why Track B runs on a
-- schedule rather than on-demand (see PRD §9.12a).
CREATE TABLE IF NOT EXISTS steam_cohort_player_counts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER NOT NULL REFERENCES steam_release_cohort(app_id),
    captured_at TEXT NOT NULL,
    player_count INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'steam_api',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (app_id, captured_at)
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

-- Platform-wide, non-esports Twitch viewership (PRD §9.16, added
-- 2026-09-09) -- collectors/twitch_platform_poll.py's full-detail tier,
-- for docs/wider_game_fandom_brief.md. Deliberately NOT keyed on
-- title_id: these are arbitrary Twitch game categories this project
-- doesn't otherwise track (GTA V, Minecraft, Just Chatting, ...), so
-- game_id (Twitch's own id) is the natural key, same reasoning
-- steam_release_cohort documents for why app_id-keyed tables can't
-- reuse the title_id FK pattern. Streams under one of the 23 tracked
-- titles' twitch_category_id are excluded here by the collector itself
-- (see excluded_tracked_game_ids in its raw snapshot) -- that data
-- already lives in viewership_snapshots; duplicating it here would let
-- a future query silently double-count a title's own attention.
--
-- No is_official_broadcast column: that concept requires config/
-- channels.yaml, which is title-specific and doesn't exist for games
-- this project doesn't track.
CREATE TABLE IF NOT EXISTS platform_viewership_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    game_name TEXT,
    platform TEXT NOT NULL DEFAULT 'twitch',
    channel_id TEXT NOT NULL,
    channel_login TEXT,
    captured_at TEXT NOT NULL,
    viewer_count INTEGER NOT NULL,
    stream_title TEXT,
    tags TEXT, -- comma-joined, same convention as viewership_snapshots.tags
    language TEXT,
    source TEXT NOT NULL DEFAULT 'twitch_api',
    confidence TEXT NOT NULL DEFAULT 'verified',
    -- Nested content classification (added 2026-09-10, `etl/
    -- classify_gta_content_segment.py`) -- 'nopixel' / 'gta_rp_other' /
    -- 'non_rp', NULL until classified. Deliberately named generically
    -- (not gta_v_segment) since the column could carry a ruleset for a
    -- different game later, the same way viewership_snapshots.broadcast_tier
    -- is one column serving whichever title's rows it's applied to --
    -- today only game_id='32982' (Grand Theft Auto V) has a ruleset.
    content_segment TEXT,
    content_segment_confidence TEXT,
    UNIQUE (channel_id, captured_at)
);

-- The below-threshold aggregate counterpart to
-- platform_viewership_snapshots -- one row per (game, poll), mirroring
-- language_mix_snapshots' role for viewership_snapshots but keyed by
-- game_id and without the per-language breakdown (not needed for the
-- creator-insularity/lifecycle questions this table exists for; add a
-- language dimension later if a question actually needs it, rather
-- than building it speculatively now).
CREATE TABLE IF NOT EXISTS platform_viewership_below_threshold (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    game_name TEXT,
    captured_at TEXT NOT NULL,
    stream_count INTEGER NOT NULL,
    viewer_total INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'twitch_api',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (game_id, captured_at)
);

CREATE INDEX IF NOT EXISTS idx_viewership_title_captured ON viewership_snapshots (title_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_platform_viewership_game_captured ON platform_viewership_snapshots (game_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_language_mix_title_captured ON language_mix_snapshots (title_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_tournaments_title ON tournaments (title_id);
CREATE INDEX IF NOT EXISTS idx_tournament_aliases_series ON tournament_aliases (title_id, series_key);
CREATE INDEX IF NOT EXISTS idx_viewership_broadcast_tier ON viewership_snapshots (broadcast_tier);
CREATE INDEX IF NOT EXISTS idx_tournaments_title_dates ON tournaments (title_id, start_date, end_date);
