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

-- LPDB v3 API staging table (docs/liquipedia_lpdb_transition_plan.md Phase
-- 1), deliberately SEPARATE from `tournaments` above rather than sharing
-- it: `tournaments`'s own UNIQUE (liquipedia_wiki, liquipedia_page)
-- constraint does not include `source`, so an LPDB-sourced row for a
-- tournament the MediaWiki-sourced collector already has would silently
-- collide (or require a schema change to the live table) rather than
-- landing as a clearly source-flagged, side-by-side row the way the
-- transition plan's Phase 1 explicitly calls for ("a staging area... not
-- a blind merge into the live table"). Reconciled against `tournaments` in
-- Phase 2; only Phase 3 (cutover, not yet done) decides what happens to
-- this table and the live one long-term.
CREATE TABLE IF NOT EXISTS tournaments_lpdb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    liquipedia_wiki TEXT NOT NULL,
    liquipedia_page TEXT NOT NULL, -- LPDB's own `pagename` field
    name TEXT,
    tier TEXT, -- raw liquipediatier, e.g. "1" — confirmed live as a clean, uniform digit string across every wiki tested (2026-09-30), unlike the per-wiki label variance `_normalize_tier()` exists to handle for the MediaWiki-sourced table
    game TEXT, -- LPDB's own `game` sub-field (e.g. "cs2", "t8") — not present on the MediaWiki-sourced table; the structured replacement for category-name-based generational-continuity filtering on shared wikis
    status TEXT, -- LPDB's own `status` field (e.g. "unconfirmed") — lets a forecast/reporting query distinguish a confirmed event from a projected/rumored one; not present on the MediaWiki-sourced table
    prize_pool REAL,
    currency TEXT, -- always NULL — LPDB v3 has no currency field anywhere in the tournament or placement schema (confirmed live 2026-09-30). UPGRADED FROM INFERENCE TO CONFIRMED (2026-10-02): cross-checked `prize_pool` against `tournaments.prize_pool`/`currency` for every non-USD MediaWiki-sourced row that also exists in this table (GBP, EUR, CNY, KRW, RUB so far) -- the implied conversion rates are real, plausible, date-varying market rates (CNY ~6.8-6.9/USD, KRW ~1,100-1,300/USD, EUR ~0.82-0.92/USD, GBP ~0.64/USD, RUB ~82.7/USD for a 2026 BetBoom event), not a coincidence or a single fixed rate. `prize_pool` here is genuinely pre-converted to USD by Liquipedia's own display convention -- treat it as USD, not as an unknown-currency nominal figure, though this is still a cross-source inference, not something LPDB's own API documentation states
    start_date TEXT,
    end_date TEXT,
    country TEXT, -- LPDB's own `locations.country1`, a lowercase ISO-2 code (e.g. "es") — NOT the same convention as `tournaments.country`'s full country names; left as-is rather than silently normalized, a Phase 2 reconciliation item
    region TEXT, -- LPDB's own `locations.region1` (e.g. "Europe", "Middle East", "World") — LPDB's own region scheme, NOT this project's COUNTRY_TO_REGION taxonomy (which has no "World"/"Middle East" categories) — also left as-is, also a Phase 2 item
    region_confidence TEXT DEFAULT 'liquipedia_lpdb_native', -- distinct from `tournaments.region_confidence`'s 'proxy_estimate'/'manual_judgment_call' values on purpose: this is LPDB's own direct claim, not this project's inference — just on a scheme not yet reconciled with the rest of the project
    team_number INTEGER,
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'liquipedia_lpdb',
    confidence TEXT NOT NULL DEFAULT 'verified',
    special_tier_category TEXT, -- NULL for every normal-tiered row; populated only for tier='-1' rows by etl/classify_special_tiers.py (built 2026-10-02) as one of 'season_wrapper' / 'recurring_series' / 'special_mode_circuit' / 'showmatch_exhibition' / 'informal' / 'likely_real_mistiered' / 'unclassified' -- see that script's own module docstring for what each means and real examples. Confirmed live that tier=-1 is NOT one thing -- StarCraft II's $400K "2017 DreamHack Season" and Overwatch's official $225K OWL All-Stars sit in the same raw bucket as Age of Empires II's zero-prize 1v1 community pickup games. This column is a DIFFERENT provenance tier than the row's own `confidence` above, always -- it's a keyword/threshold heuristic classification, ai_assisted_unreviewed regardless of what `confidence` says, not an LPDB-native field.
    special_tier_category_confidence TEXT DEFAULT 'ai_assisted_unreviewed',
    UNIQUE (liquipedia_wiki, liquipedia_page)
);

-- The settled default for "is this a real competitive tournament" across
-- tournaments_lpdb, closing out the tier=-1 investigation above (2026-10-02)
-- so this question doesn't get re-litigated by every future notebook that
-- touches this table. Decision, by special_tier_category (checked against
-- real per-title dollar and row-count materiality, not guessed):
--   - Always included: tier IN ('1','2','3','4') (normal tiers, unaffected
--     by any of this), recurring_series (real organized, often-paid
--     content, just high-frequency/minor -- Rocket League's Hoops League,
--     R6's FACEIT Pro League), special_mode_circuit (real, officially-
--     branded, well-resourced tournaments in an alternate game mode, not
--     the flagship ladder -- confirmed real, just never tiered),
--     likely_real_mistiered (cleared a real-tournament scale threshold
--     with no exhibition/informal signal -- the more defensible read is
--     "real event, missing a tier," not "ambiguous").
--   - Always excluded: season_wrapper (an aggregate season/tour record,
--     not a discrete tournament -- risks double-counting prize money
--     against sub-events already captured separately elsewhere, a risk
--     checked but not resolved either way), informal (by construction,
--     the fallback for small-stakes 1-2-player pickup-game-scale
--     content), unclassified (the heuristic found no confident signal --
--     defaulting to exclude is the safer failure mode, undercounting
--     rather than risking contamination; after three rounds of
--     classifier refinement this is down to 289 rows / 0.79% of the
--     combined normal-tier baseline across the 5 affected titles --
--     genuinely negligible combined, though AoE2 at 2.13% and Overwatch
--     at 3.12% specifically carry more of it than the others and are
--     worth remembering if a finding there looks sensitive to a few
--     percent of missing tournaments).
--   - Title-dependent: showmatch_exhibition is included everywhere EXCEPT
--     age_of_empires_ii, where it's ~1,600 rows of overwhelmingly casual,
--     near-zero-prize community 1v1s ("Fox vs Taiwan Aoe Gamer") that
--     would otherwise roughly double that title's grassroots-tier
--     tournament count if counted as real tournaments. Everywhere else
--     (Overwatch's $225K OWL All-Stars, Rocket League's Twitch Rivals)
--     the same category skews toward real official content.
CREATE VIEW IF NOT EXISTS tournaments_lpdb_competitive AS
SELECT *
FROM tournaments_lpdb
WHERE tier IN ('1', '2', '3', '4')
   OR (tier = '-1' AND special_tier_category IN ('recurring_series', 'special_mode_circuit', 'likely_real_mistiered'))
   OR (tier = '-1' AND special_tier_category = 'showmatch_exhibition' AND title_id != 'age_of_empires_ii');

-- Pro player bio/career data (docs/liquipedia_lpdb_transition_plan.md
-- Phase 4, built 2026-10-01 following a direct user request for a player
-- database and cohort analysis). LPDB's `player` resource, confirmed live
-- 2026-09-30 to carry real `birthdate`, `nationality`/`region`, team
-- affiliation, `status` (Active/Retired/Inactive), and `earnings`/
-- `earningsbyyear` -- no equivalent data exists anywhere else in this
-- project (no roster/player connector was built before this). `role`
-- varies by game (e.g. "rifle" for Counter-Strike) and is kept as raw
-- JSON text in `extradata_json` rather than a dedicated column, since its
-- shape isn't uniform across titles.
CREATE TABLE IF NOT EXISTS players_lpdb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    liquipedia_wiki TEXT NOT NULL,
    liquipedia_page TEXT NOT NULL, -- LPDB's own `pagename`
    player_id TEXT, -- LPDB's own `id` field -- the in-game handle (e.g. "Sico"), distinct from `name` (real name)
    name TEXT,
    nationality TEXT,
    nationality2 TEXT,
    nationality3 TEXT,
    region TEXT, -- LPDB's own region scheme, same caveat as tournaments_lpdb.region -- not this project's COUNTRY_TO_REGION
    birthdate TEXT, -- normalized: LPDB's "0000-01-01" sentinel (confirmed live, same pattern as tournaments_lpdb dates) becomes NULL, not stored as a literal date
    deathdate TEXT, -- same normalization
    team_pagename TEXT, -- current team, if any -- LPDB's own `teampagename`
    status TEXT, -- 'Active' / 'Retired' / 'Inactive' -- the primary field for cohort/career-duration analysis
    total_earnings REAL,
    extradata_json TEXT, -- raw LPDB `extradata` (role, roles, banned, ...) -- shape varies by title, not normalized into columns
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'liquipedia_lpdb',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (liquipedia_wiki, liquipedia_page)
);

-- Per-year earnings, normalized out of players_lpdb's `earningsbyyear`
-- object into its own table so a cohort query (e.g. "median career
-- earnings trajectory by debut-year cohort") doesn't have to parse JSON
-- per row.
CREATE TABLE IF NOT EXISTS player_earnings_by_year_lpdb (
    player_row_id INTEGER NOT NULL REFERENCES players_lpdb(id),
    year INTEGER NOT NULL,
    earnings REAL NOT NULL,
    PRIMARY KEY (player_row_id, year)
);

-- Roster tenure history -- LPDB's `squadplayer` resource, confirmed live
-- 2026-09-30 to carry real `joindate`/`leavedate` per team stint, which
-- `players_lpdb` alone (current team only) can't reconstruct. This is the
-- actual source for career-duration and team-hopping/regionalization
-- cohort analysis, not `players_lpdb.status` alone. Keyed on LPDB's own
-- `objectname` (e.g. "100044_Allu_2012-12-04__former"), which is already
-- unique per roster stint -- confirmed live, not assumed.
CREATE TABLE IF NOT EXISTS squadplayers_lpdb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    liquipedia_wiki TEXT NOT NULL,
    objectname TEXT NOT NULL, -- LPDB's own unique row identifier for this roster stint
    team_pagename TEXT NOT NULL, -- LPDB's own `pagename` on this resource -- the TEAM's page, not the player's
    player_id TEXT, -- LPDB's own `id` -- matches players_lpdb.player_id, not a hard FK (squadplayer can reference a player never separately pulled)
    player_link TEXT, -- LPDB's own `link` -- the player's actual wiki page, when it differs from `id`
    nationality TEXT,
    position TEXT,
    role TEXT,
    new_team_pagename TEXT, -- where the player went next, if known
    status TEXT, -- 'active' / 'former'
    join_date TEXT, -- normalized 0000-01-01 -> NULL, same as elsewhere
    leave_date TEXT,
    inactive_date TEXT,
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'liquipedia_lpdb',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (liquipedia_wiki, objectname)
);

-- Structured per-match broadcast channel data -- LPDB's `match` resource's
-- `stream` field, confirmed live 2026-09-30 to return real Twitch channel
-- identifiers per match (e.g. {"twitch_en_1": "Fragbite", "twitch":
-- "Fragbite"} on a real Svenska Cupen 2026 match) -- a Phase 0 "bonus
-- finding" (docs/liquipedia_lpdb_transition_plan.md), built out here
-- following a direct user request to evaluate it as a structured
-- alternative/supplement to config/channels.yaml's manually-curated list
-- and classify_broadcast_tier.py's text-matching `detected_costream`
-- heuristic. One row per (match, stream key) -- a match with
-- language-specific feeds produces multiple rows.
--
-- IMPORTANT, stated here so it isn't lost: `channel_name` is LPDB's own
-- Liquipedia-template value (e.g. "Fragbite") -- there is NO confirmation
-- yet that this is the exact lowercase Twitch LOGIN config/channels.yaml's
-- own header comment requires as its match key (display name and login
-- can differ). Treat every row here as `ai_assisted_unreviewed` candidate
-- data requiring the same live Twitch Helix verification step already
-- used to curate the 5 titles currently in config/channels.yaml -- do NOT
-- promote straight into that file's 'verified' entries without it.
CREATE TABLE IF NOT EXISTS match_streams_lpdb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    liquipedia_wiki TEXT NOT NULL,
    match_objectname TEXT NOT NULL, -- LPDB's own unique match identifier
    tournament_pagename TEXT, -- LPDB's own `tournament` field (a display name, not necessarily `tournaments_lpdb.liquipedia_page` -- not joined automatically, a Phase where-this-goes-next item)
    match_date TEXT,
    stream_key TEXT NOT NULL, -- e.g. "twitch", "twitch_en_1", "twitch_ru_1" -- LPDB's own key naming, not normalized
    channel_name TEXT NOT NULL, -- see the caveat above -- NOT confirmed to be a Twitch login
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'liquipedia_lpdb',
    confidence TEXT NOT NULL DEFAULT 'ai_assisted_unreviewed', -- deliberately NOT 'verified', unlike this project's other LPDB tables -- see the table comment above
    UNIQUE (liquipedia_wiki, match_objectname, stream_key)
);

-- Broadcast TALENT (casters/analysts/hosts), not channels -- LPDB's
-- `broadcasters` resource, a different signal from match_streams_lpdb
-- above. Captured because the user asked to "capture stream channel
-- information from tournaments" broadly; kept as its own table since it
-- answers a genuinely different question (who casts, not which channel
-- airs it) and isn't part of the channel-tiering refit this Phase 4 work
-- is primarily scoped for.
CREATE TABLE IF NOT EXISTS broadcasters_lpdb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    liquipedia_wiki TEXT NOT NULL,
    objectname TEXT NOT NULL, -- LPDB's own unique row identifier
    tournament_pagename TEXT NOT NULL, -- LPDB's own `parent` field
    person_id TEXT, -- LPDB's own `id`
    person_name TEXT,
    position TEXT, -- e.g. "Analyst", "Host", "Caster"
    language TEXT,
    nationality TEXT, -- LPDB's own `flag`
    broadcast_date TEXT,
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'liquipedia_lpdb',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (liquipedia_wiki, objectname)
);

-- Per-tournament, per-team/-player final standings -- LPDB's `placement`
-- resource (docs/liquipedia_lpdb_transition_plan.md's own long-flagged gap,
-- "per-tournament participant lists", never pulled before
-- collectors/liquipedia_lpdb_placements.py, built 2026-10-03). This is the
-- actual link between a player/team's identity and WHICH tournaments they
-- competed in, at what tier -- players_lpdb/squadplayers_lpdb alone have no
-- such link, only a player's bio and current/past team, never a specific
-- event. Confirmed live 2026-10-03 against a real completed tournament
-- (StarLadder StarSeries Fall 2026, wiki=counterstrike): one row per
-- team/solo opponent's final standing, keyed on LPDB's own `objectname`
-- (e.g. "374646_ranking_aurora gaming"), same uniqueness convention as
-- match_streams_lpdb/broadcasters_lpdb.
--
-- Confirmed live, same `tournament`-vs-`parent` display-name trap
-- collectors/liquipedia_lpdb_broadcasts.py already documented for `match` --
-- `placement.tournament` is the human-readable display name ("StarLadder
-- StarSeries Fall 2026"), `placement.parent` is the page-slug
-- ("StarLadder/StarSeries/2026/Fall") matching tournaments_lpdb.liquipedia_page
-- exactly. tournament_pagename below stores `parent`; tournament_display_name
-- stores `tournament` for readability only -- never join on the latter.
--
-- Confirmed live: `liquipediatier` is present directly on this resource too
-- (not just on `tournament`), same clean digit-string format -- lets this
-- collector filter by tier at the API `conditions` level without a prior
-- tournaments_lpdb lookup. `game` is also present per-row (e.g. "cs2",
-- confirmed on both counterstrike and starcraft2 samples) -- unlike
-- `player`/`squadplayer` (players_lpdb's own docstring: no per-title game
-- field, only a multi-game extradata list), placement rows on the shared
-- `fighters` wiki should be splittable by title using the same
-- GAME_CODES_BY_TITLE `conditions` pattern collectors/liquipedia_lpdb.py's
-- tournament pull already uses -- NOT yet confirmed live against the
-- fighters wiki specifically (LPDB shared budget was at 0 for the rest of
-- this session before that check could run); treat as likely-true, verify
-- before the first real fighters-wiki placement pull.
--
-- `opponent_type` ('team' / 'solo', confirmed both live -- CS placements are
-- 'team', a StarCraft II 1v1 ranking is 'solo') is the reliable team-vs-solo
-- signal. `mode` (LPDB's own field, e.g. "team", "1v1") is NOT reliable for
-- this -- confirmed live a StarCraft II show-match row had
-- opponenttype='team' but mode='1v1' (mode describes match FORMAT, not this
-- row's opponent shape). Use opponent_type, not mode, for that distinction.
--
-- `placement` is TEXT, not INTEGER, on purpose -- confirmed live it holds
-- tie-ranges ("7-8", "5-6") and can be an empty string (seen on a
-- show-match-style row with no real standing). `prize_money` is this
-- opponent's total payout for this placement; `individual_prize_money` is
-- LPDB's own separate per-player share of it (confirmed live, both
-- populated on every real standings row sampled).
--
-- IMPORTANT date-format gotcha, confirmed live and DIFFERENT from every
-- other _lpdb table so far: this resource's own null-date sentinel is
-- "0000-01-01 00:00:00" (a full datetime), not tournaments_lpdb/players_lpdb's
-- plain "0000-01-01" -- collectors/liquipedia_lpdb.py's own
-- `_normalize_lpdb_date()` (exact-string-equality against LPDB_NULL_DATE)
-- would silently NOT catch this on `date`/`start_date` here, since the
-- strings differ by the trailing time component. This collector does its
-- own prefix-based normalization instead (`value.startswith("0000-01-01")`)
-- -- do not blindly reuse `_normalize_lpdb_date()` against this table's raw
-- API values without accounting for this.
CREATE TABLE IF NOT EXISTS placements_lpdb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title_id TEXT NOT NULL REFERENCES titles(id),
    liquipedia_wiki TEXT NOT NULL,
    objectname TEXT NOT NULL, -- LPDB's own unique row identifier for this placement entry
    tournament_pagename TEXT, -- LPDB's own `parent` -- the page slug, matches tournaments_lpdb.liquipedia_page; see table comment on the tournament/parent trap
    tournament_display_name TEXT, -- LPDB's own `tournament` -- human-readable only, never join on this
    tier TEXT, -- LPDB's own `liquipediatier` on this row, same clean digit-string format as tournaments_lpdb.tier
    game TEXT, -- LPDB's own per-row `game` sub-field -- see table comment on shared-wiki splitting
    placement TEXT, -- e.g. "1", "7-8", or "" -- see table comment on why this is TEXT
    opponent_type TEXT, -- 'team' / 'solo' -- the reliable signal for this, NOT `mode` (see table comment)
    opponent_name TEXT,
    opponent_template TEXT, -- LPDB's own `opponenttemplate` -- a roster-revision-qualified team identity (e.g. "aurora gaming 2025"), distinct from squadplayers_lpdb.team_pagename's plain page name; not reconciled with that table here
    prize_money REAL,
    individual_prize_money REAL, -- LPDB's own `individualprizemoney` -- per-player share of prize_money, confirmed live on every sampled row
    prize_pool_index INTEGER, -- LPDB's own `prizepoolindex` -- distinguishes concurrent prize pools/brackets within one tournament page
    mode TEXT, -- LPDB's own `mode` field (e.g. "team", "1v1") -- a match-format label, NOT a team/solo signal (see table comment)
    match_date TEXT, -- normalized: see table comment on the datetime-sentinel gotcha
    start_date TEXT, -- also normalized the same way
    extradata_json TEXT, -- raw LPDB `extradata` (playershare, prizepoints, opponentaliases, ...) -- shape varies, not normalized into columns, same treatment as players_lpdb.extradata_json
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'liquipedia_lpdb',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (liquipedia_wiki, objectname)
);

-- Normalized out of placements_lpdb's raw `opponentplayers` object -- one
-- row per player/coach SLOT within one placement row, so "which players
-- competed in tier-1/2 events" is a plain join, not JSON parsing per query
-- (same reasoning as player_earnings_by_year_lpdb's own table comment for
-- players_lpdb's `earningsbyyear`). No source/confidence/fetched_at of its
-- own -- inherits placements_lpdb's via placement_row_id, same convention
-- as player_earnings_by_year_lpdb.
--
-- THE key confirmed-live finding this whole collector was built to answer:
-- `player_page` below (LPDB's own opponentplayers "pN"/"cN" value, e.g.
-- "Yuurih") was checked directly against a real sample of players_lpdb rows
-- for the same title and MATCHES liquipedia_page exactly, case-sensitive
-- (e.g. "Yuurih" / "KSCERATO" / "ZywOo" / "Insani" / "B1t" all resolved to
-- real players_lpdb.liquipedia_page values from the same StarLadder
-- StarSeries Fall 2026 CS placement row). Players ARE individually
-- identifiable per placement row, not just teams -- elite-tier (tier IN
-- ('1','2')) *player* filtering, not only *team* filtering, is genuinely
-- possible from this data. `display_name` (LPDB's own "pNdn"/"cNdn") is
-- the as-rendered name and sometimes differs in case from `player_page` --
-- join on `player_page`, not `display_name`.
CREATE TABLE IF NOT EXISTS placement_participants_lpdb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    placement_row_id INTEGER NOT NULL REFERENCES placements_lpdb(id),
    slot TEXT NOT NULL, -- LPDB's own raw slot key, e.g. "p1", "c1" -- kept for traceability back to the source JSON
    kind TEXT NOT NULL, -- 'player' / 'coach', derived from the slot's p/c prefix
    player_page TEXT, -- see table comment -- matches players_lpdb.liquipedia_page / squadplayers_lpdb.player_link
    display_name TEXT,
    nationality TEXT, -- LPDB's own "pNflag"/"cNflag"
    faction TEXT, -- LPDB's own "pNfaction", when present (e.g. StarCraft II race) -- game-specific, NULL elsewhere
    role_label TEXT, -- LPDB's own "cNrole1" (e.g. "coach") -- only populated for coach slots
    UNIQUE (placement_row_id, slot)
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
    -- English-fandom region decomposition (PRD §9.17, added 2026-09-12):
    -- a self-declared region marker (e.g. 'NA'/'EU'/'OCE') found by
    -- etl/extract_stream_region_tags.py in this row's own tags/title text
    -- — NULL until classified, and NULL stays NULL forever for a stream
    -- whose text carries no such marker (most of them), not "not yet
    -- checked". A rule-based regex extraction, not a measured fact, so
    -- 'ai_assisted_unreviewed' per CLAUDE.md's provenance rule, same as
    -- genre/platform tags — never 'verified' by this step alone.
    self_declared_region_tag TEXT,
    self_declared_region_tag_confidence TEXT,
    -- Session-duration fields (added 2026-09-20) -- Twitch's own Get
    -- Streams response already carries both (collectors/twitch_poll.py's
    -- FULL_DETAIL_FIELDS has always kept them; they simply weren't loaded
    -- into this table until now). stream_id is Twitch's own identifier for
    -- THIS specific broadcast session -- changes every time a channel goes
    -- offline and comes back, which is what makes it possible to group
    -- polls into sessions cleanly rather than inferring session boundaries
    -- from gaps in polling. started_at is when that session began, per
    -- Twitch, not inferred from our own poll cadence. NULL for any row
    -- loaded before this column existed until the one-time backfill
    -- (etl/backfill_stream_session_fields.py) re-processes existing raw
    -- files -- NULL means "not backfilled yet," not "no session."
    stream_id TEXT,
    started_at TEXT,
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

-- Twitch account-creation dates (added 2026-09-20, ad-hoc rather than a
-- numbered PRD phase) -- a static, always-re-fetchable fact per channel
-- (Helix `Get Users`' own `created_at` field), NOT live/unbackfillable
-- data. Does NOT fall under CLAUDE.md's "one rule" schedule protection --
-- collectors/twitch_account_backfill.py is on-demand/resumable, same
-- category as collectors/steam_catalog_backfill.py's Track A, not a
-- scheduled poller. Built specifically to test whether a title community's
-- apparent "era" effect is really creator tenure (crossover channels
-- having existed longer) rather than conditions-of-formation -- the
-- collector's own first-seen date can't distinguish those (19 days of
-- polling history vs. years of real account age), this can.
CREATE TABLE IF NOT EXISTS twitch_account_metadata (
    channel_id TEXT PRIMARY KEY,
    login TEXT,
    display_name TEXT,
    broadcaster_type TEXT,
    account_created_at TEXT,
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'twitch_api',
    confidence TEXT NOT NULL DEFAULT 'verified'
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
-- for research/wider_game_fandoms/brief.md. Deliberately NOT keyed on
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
    -- Same self-declared-region extraction as viewership_snapshots (PRD
    -- §9.17) — kept as a separate column here rather than a shared table
    -- because this row's own game_id/channel_id shape differs from
    -- viewership_snapshots' title_id shape, same reasoning content_segment
    -- above already documents for staying a plain column, not a join.
    self_declared_region_tag TEXT,
    self_declared_region_tag_confidence TEXT,
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

-- Arabic-language stream snapshots (research/wider_game_fandoms/
-- arabic_gaming_scene/, collectors/twitch_arabic_snapshot.py, added
-- 2026-09-24). Deliberately NOT title_id-keyed and NOT excluding the 23
-- tracked titles' game IDs the way platform_viewership_snapshots does --
-- this table's whole purpose is to see Arabic-language activity across
-- every game at once, tracked or not, since that comparison is the point
-- (e.g. EA Sports FC 27 showing real Arabic volume despite not being a
-- tracked title at all). No viewer-count tiering either -- the
-- language='ar' population is small enough (325 concurrent streams at
-- first check) that full detail for every stream doesn't carry
-- platform_viewership_snapshots' "tens of thousands of ordinary
-- streamers" concern. `tags` is the main self-declared-geography signal
-- this table carries (e.g. "SaudiArabia"/"KSA"-family tags) -- extracted
-- into `self_declared_country_tag` at load time, same
-- inferred-until-reviewed discipline as every other derived column here.
CREATE TABLE IF NOT EXISTS arabic_language_stream_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream_id TEXT,
    channel_id TEXT NOT NULL,
    channel_login TEXT,
    game_id TEXT,
    game_name TEXT,
    stream_title TEXT,
    viewer_count INTEGER NOT NULL,
    started_at TEXT,
    language TEXT NOT NULL DEFAULT 'ar',
    tags TEXT, -- comma-joined, same convention as viewership_snapshots.tags
    self_declared_country_tag TEXT, -- extracted from tags via keyword match, NULL if no country-like tag found
    self_declared_country_tag_confidence TEXT,
    is_mature INTEGER,
    captured_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'twitch_api',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (channel_id, captured_at)
);

-- English-fandom region decomposition (PRD §9.17, added 2026-09-12).
-- `subject_id` keys against config/fandom_decomposition_subjects.yaml,
-- deliberately NOT title_id -- a subject can be a title_id-based esports
-- title (`viewership_snapshots`) or a game_id/content_segment-based
-- platform-wide subject like GTA V (`platform_viewership_snapshots`),
-- and this whole subsystem exists to treat both uniformly (see the PRD
-- section for why). None of the three tables below are unbackfillable --
-- Wikipedia pageviews and Steam reviews are both fixed historical fact,
-- re-fetchable at any time, so none of this needs CLAUDE.md's "one rule"
-- schedule protection the live Twitch/YouTube/Steam-player-count
-- collectors require.

-- Wikipedia article pageviews (collectors/wikipedia_pageviews_pull.py) --
-- an independent game-fandom signal (informational engagement, not
-- viewership), and a secondary input to decompose_by_timezone's diurnal-
-- pattern correlation. Official Wikimedia Pageviews REST API, confirmed
-- live 2026-09-12 to be documented and explicitly positioned for this
-- kind of research use -- same discipline as Liquipedia (descriptive
-- User-Agent, respect rate limits, cache locally).
CREATE TABLE IF NOT EXISTS wikipedia_pageview_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id TEXT NOT NULL,
    wiki_project TEXT NOT NULL, -- e.g. 'en.wikipedia' -- one edition per row, never blended across editions
    article_title TEXT NOT NULL,
    date TEXT NOT NULL, -- 'YYYY-MM-DD', the API's own daily granularity
    views INTEGER NOT NULL,
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'wikimedia_pageviews_api',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (subject_id, wiki_project, article_title, date)
);

-- Steam review-language history (collectors/steam_review_history_pull.py)
-- -- one row per individual review, not a periodic snapshot: confirmed
-- live 2026-09-12 that store.steampowered.com/appreviews/<appid> returns
-- `timestamp_created` per review alongside `language`, and a review's
-- creation date never changes -- genuinely backfillable historical fact,
-- named `_history` like steam_release_history for the same reason, not
-- `_snapshots`. Only language + timestamp_created + the review's own id
-- are stored -- no review text or vote counts, since nothing this
-- subsystem asks needs them (same "don't build speculatively" reasoning
-- platform_viewership_below_threshold's own header comment already
-- states for a different table). The endpoint itself is Valve's own
-- first-party server (powers their own store page) but UNDOCUMENTED --
-- not covered by the Steam Web API's official terms -- flagged here
-- explicitly so this is never mistaken for a documented guarantee the
-- way steam_release_history's `steam_store_api` source is.
CREATE TABLE IF NOT EXISTS steam_review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id TEXT NOT NULL,
    app_id INTEGER NOT NULL,
    review_id TEXT NOT NULL, -- Steam's own `recommendationid`
    language TEXT NOT NULL, -- Steam's own language code (e.g. 'english', 'schinese') -- NOT the same vocabulary as Twitch's language_code, never joined directly against it
    timestamp_created INTEGER NOT NULL, -- Unix epoch, UTC
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'steam_appreviews_undocumented',
    confidence TEXT NOT NULL DEFAULT 'verified',
    UNIQUE (app_id, review_id)
);

-- Synthesis output of the whole subsystem -- one row per (method,
-- signal_source) per region per window, deliberately NOT collapsed into
-- a single number per region. Matches this project's existing "three
-- metrics side by side, not one replacing another" convention
-- (research/foundations/fandom_and_niche_model/notebooks/niche_membership.ipynb's cosine_full/cosine_no_english/jsd
-- trio) -- disagreement between methods/sources is itself the finding,
-- not something to average away.
-- method: 'timezone_deconvolution' | 'tag_mining' | 'language_distribution'
-- signal_source: 'twitch_viewership' | 'steam_reviews' | 'wikipedia_pageviews'
-- (not every method applies to every signal_source -- e.g. tag_mining
-- only makes sense against twitch_viewership's own stream text).
-- window_start/window_end matter most for signal_source='steam_reviews',
-- where a title's whole review history supports a real per-year/quarter
-- time series, not just one current window the way Twitch's ~2-week
-- language_mix_snapshots coverage does.
CREATE TABLE IF NOT EXISTS english_fandom_region_estimates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id TEXT NOT NULL,
    region_or_country TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    method TEXT NOT NULL,
    signal_source TEXT NOT NULL,
    estimated_share REAL NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'ai_assisted_unreviewed', -- an inferred estimate, never 'verified' -- promoted only by explicit human review, per CLAUDE.md's provenance rule
    computed_at TEXT NOT NULL,
    UNIQUE (subject_id, region_or_country, window_start, window_end, method, signal_source)
);

CREATE INDEX IF NOT EXISTS idx_viewership_title_captured ON viewership_snapshots (title_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_platform_viewership_game_captured ON platform_viewership_snapshots (game_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_language_mix_title_captured ON language_mix_snapshots (title_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_tournaments_title ON tournaments (title_id);
CREATE INDEX IF NOT EXISTS idx_tournaments_lpdb_title ON tournaments_lpdb (title_id);
CREATE INDEX IF NOT EXISTS idx_tournaments_lpdb_title_dates ON tournaments_lpdb (title_id, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_tournaments_lpdb_tier_start ON tournaments_lpdb (tier, start_date);
CREATE INDEX IF NOT EXISTS idx_players_lpdb_title ON players_lpdb (title_id);
CREATE INDEX IF NOT EXISTS idx_players_lpdb_status ON players_lpdb (title_id, status);
CREATE INDEX IF NOT EXISTS idx_players_lpdb_birthdate ON players_lpdb (birthdate);
CREATE INDEX IF NOT EXISTS idx_player_earnings_year ON player_earnings_by_year_lpdb (year);
CREATE INDEX IF NOT EXISTS idx_squadplayers_lpdb_title ON squadplayers_lpdb (title_id);
CREATE INDEX IF NOT EXISTS idx_squadplayers_lpdb_player ON squadplayers_lpdb (title_id, player_id);
CREATE INDEX IF NOT EXISTS idx_squadplayers_lpdb_dates ON squadplayers_lpdb (join_date, leave_date);
CREATE INDEX IF NOT EXISTS idx_match_streams_lpdb_title ON match_streams_lpdb (title_id);
CREATE INDEX IF NOT EXISTS idx_match_streams_lpdb_channel ON match_streams_lpdb (channel_name);
CREATE INDEX IF NOT EXISTS idx_broadcasters_lpdb_title ON broadcasters_lpdb (title_id);
CREATE INDEX IF NOT EXISTS idx_placements_lpdb_title ON placements_lpdb (title_id);
CREATE INDEX IF NOT EXISTS idx_placements_lpdb_tournament ON placements_lpdb (title_id, tournament_pagename);
CREATE INDEX IF NOT EXISTS idx_placements_lpdb_tier ON placements_lpdb (tier);
CREATE INDEX IF NOT EXISTS idx_placement_participants_placement ON placement_participants_lpdb (placement_row_id);
CREATE INDEX IF NOT EXISTS idx_placement_participants_player ON placement_participants_lpdb (player_page);
CREATE INDEX IF NOT EXISTS idx_tournament_aliases_series ON tournament_aliases (title_id, series_key);
CREATE INDEX IF NOT EXISTS idx_viewership_broadcast_tier ON viewership_snapshots (broadcast_tier);
CREATE INDEX IF NOT EXISTS idx_tournaments_title_dates ON tournaments (title_id, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_arabic_stream_game_captured ON arabic_language_stream_snapshots (game_id, captured_at);
