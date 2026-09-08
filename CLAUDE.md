# fandomdatapuller

A personal research platform tracking digital-fandom metrics, built to serve
`docs/esports_gauses_law_brief.md` (the current research question — does
competitive exclusion sort esports titles within a niche?) and designed so
future questions mostly need new queries, not new pipelines. Full spec:
`docs/esports_fandom_platform_prd_v2.md`.

`docs/system_reference.md` describes present state (what's actually
built, wired up, populated, or broken, read straight from the code and
data) — the PRD describes intent and decisions. When it drifts,
regenerate it rather than hand-editing it.

**The PRD and the research brief are edited directly, the same as code**
(PRD §15, added 2026-09-08) — they aren't maintained elsewhere and copied
in. When a research decision, data-source design, or connection to an
existing hypothesis comes up in conversation, write it into these
documents as part of doing the work, not as a separate step to remember
later. If a request doesn't obviously connect to what's currently
written, that's the documents lagging the conversation (scope has grown
several times this way already) — ask what's missing rather than
assuming the request belongs to a different project.

## The one rule that overrides everything else

**Live Twitch viewership data cannot be backfilled.** Twitch's API only
exposes current state — there is no historical endpoint. An hour the
collector isn't running is an hour of data lost permanently, at any price.

Never disable, pause, or "temporarily" break `collectors/twitch_poll.py` or
the `poll.yml` workflow while refactoring something else, even briefly. If a
change risks the collector, make it in a way that keeps polling running, or
don't make it yet.

**The same applies to `collectors/youtube_poll.py` / `youtube_poll.yml`
(PRD §9.7, built 2026-09-08)** — YouTube's live-viewer-count API is exactly
as unbackfillable as Twitch's. Deliberately a fully separate script, config
file (`config/channels_youtube.yaml`, not a reshaped `config/channels.yaml`),
and workflow from Twitch's, specifically so a change to one can never risk
the other — keep it that way; don't merge them for "consistency" later.

**And to `collectors/steam_poll.py` / `steam_poll.yml` (PRD §9.12, built
2026-09-08)** — Steam's `GetNumberOfCurrentPlayers` has no historical
parameter either, confirmed live. No legitimate backfill path exists if
this stops running: SteamDB explicitly prohibits scraping in their own
FAQ, and SteamCharts' own displayed data only covers ~30 days — both
checked directly, neither is a fallback. Same fully-separate-file
discipline as YouTube (`config/steam_appids.yaml`, `steam_poll.yml`).

## Ethical non-goals — do not build these

- No scraping SullyGnome, SteamDB, or any comparable tracker, ever, even to
  fill a gap that looks otherwise unfillable. Approach operators directly
  instead. SteamDB specifically: checked their own FAQ directly (2026-09-07)
  — they explicitly prohibit scraping/crawling and warn of a ban for
  automated access. Confirmed, not assumed.
- Respect every source's published terms: Twitch's Developer Agreement,
  Liquipedia's API terms, Reddit's API terms — including retention and
  attribution clauses. For Liquipedia specifically: 1 request/2s general,
  never `action=parse` (1 request/30s, and the connector doesn't need it —
  see `collectors/liquipedia.py`), always the descriptive User-Agent, cache
  everything locally and don't re-request unchanged historical data.

## Provenance

Anything Claude Code generates or infers — genre tags, region assignments,
milestone calculations from ambiguous sources — is `ai_assisted_unreviewed`
by default, promoted to `verified` only by explicit human review. This
applies to config values too: an unverified Twitch category ID in
`config/titles.yaml` is a config-level version of the same rule.

## Conventions

- **UTC, ISO 8601, everywhere.** No naive local timestamps — this data gets
  aggregated to daily/monthly buckets across global events.
- **Idempotent loads.** Anything that writes into the eventual SQLite layer
  uses `INSERT ... ON CONFLICT DO NOTHING` against a natural key. A silent
  duplicate is worse than a visible gap.
- **Config-driven title list.** Adding a tracked title is an edit to
  `config/titles.yaml`, not a code change. It's version-controlled on
  purpose — "what were we tracking in March?" should be answerable from git
  history.
- **`data/research.db` is derived and disposable, rebuildable from
  committed repo contents alone** — `data/raw/` (Twitch snapshots) *and*
  `data/reference/` (`tournaments`/`tournament_aliases`, exported by
  `etl/export_reference_data.py`). `python etl/load_snapshots.py
  --rebuild` replays both. This closes a real gap: `collectors/
  liquipedia.py` writes tournament data straight into `research.db` with
  no raw-file backup, so before `data/reference/` existed, `--rebuild`
  silently discarded it with no way to recover except a full re-crawl.
  **The safety net only covers what's actually been exported and
  committed** — run `etl/export_reference_data.py` (part of
  `scripts/local_refresh.sh`) after any Liquipedia crawl or alias
  generation, or a `--rebuild` right after new crawling and before the
  next export still loses that gap. Never run `--rebuild` without
  confirming `data/reference/` is current. A schema change (a new/renamed
  column) also does not retroactively apply to an existing `research.db`
  — `get_connection()` only runs `CREATE TABLE IF NOT EXISTS`, a no-op
  against a table that already exists — so after editing
  `etl/schema.sql`, apply the matching `ALTER TABLE` to the live database
  directly rather than reaching for `--rebuild` to "pick up" the change.
- **Every ingested table carries `source`/`confidence`** (PRD §14). Twitch
  and successfully-parsed Liquipedia fields are `verified` (measured or
  deterministically extracted, not inferred); anything Claude Code
  generates or infers defaults to `ai_assisted_unreviewed`.

## Current state

Phase 1 (Twitch collector) and Phase 2 (schema/ETL/Liquipedia connector) are
built. `etl/schema.sql` has the full PRD §6 schema, though
`community_signals`, `demographic_snapshots`, `failed_challengers`, and the
`genres`/`platforms` reference tables are empty until their respective
phases. `analysis/metrics.py` has only `get_success_milestone` so far — the
rest (`get_niche_share`, `get_concentration`, `get_official_broadcast_share`,
`get_primary_region`) is Phase 4.

Also built: Phase 3 genre/platform classification; `get_success_milestone`'s
`qualifying_window_scale`/`viewership_check`; the Kaggle historical-viewership
import; several analysis notebooks (`notebooks/`); `tournament_aliases`
(rule-based + LLM-derived, `etl/generate_tournament_aliases.py`);
`viewership_snapshots.broadcast_tier` co-stream detection
(`etl/classify_broadcast_tier.py`); `data/reference/` exports; the
YouTube live collector (PRD §9.7, `collectors/youtube_poll.py`) — built
but not yet collecting anything real, since `config/channels_youtube.yaml`
still needs human curation (same bootstrap gap `config/channels.yaml`
has had from the start); the Steam current-player collector (PRD §9.12,
`collectors/steam_poll.py`, 11 titles pre-configured in
`config/steam_appids.yaml`) — built and already collecting real data
locally, blocked only on `STEAM_API_KEY` being added as a GitHub Actions
repo secret before the scheduled workflow can run. See
`docs/milestone_reconciliation.md` and the PRD's changelog-style sections
for the reasoning behind non-obvious calls in this area — not duplicated
here.

## Common tasks

Install dependencies:

```
pip install -r requirements.txt
```

Run the Twitch collector locally (needs `TWITCH_CLIENT_ID` /
`TWITCH_CLIENT_SECRET` in `.env`, or exported in the shell):

```
python collectors/twitch_poll.py
```

Trigger event-mode polling (tighter interval during a specific broadcast
window) from the GitHub Actions UI: run the "Twitch live-viewership poll"
workflow manually with `duration_minutes` / `interval_minutes` set.

Run the YouTube collector locally (PRD §9.7 — needs `YOUTUBE_API_KEY` in
`.env`, or exported in the shell; a completely separate script/config/
workflow from Twitch's, by design — see `collectors/youtube_poll.py`'s
own docstring):

```
python collectors/youtube_poll.py
```

Curating `config/channels_youtube.yaml` (empty until a human populates
it, same bootstrap state `config/channels.yaml` started in) is required
before this collects anything. Force a discovery sweep (otherwise
governed by `--sweep-interval-hours`, default every 6h) from the GitHub
Actions UI: run the "YouTube live-viewership poll" workflow manually with
`sweep=true` — worth doing once at the start of a specific tournament.

Run the Steam collector locally (PRD §9.12 — needs `STEAM_API_KEY` in
`.env`, or exported in the shell; free to register at
steamcommunity.com/dev/apikey). Simpler than the other two — no config
curation needed first, `config/steam_appids.yaml` ships pre-populated
with every tracked title's verified Steam AppID (an objective fact, not
a judgment call):

```
python collectors/steam_poll.py
```

Load raw Twitch, YouTube, and Steam snapshots into `research.db` (incremental;
add `--rebuild` to wipe and reload everything):

```
python etl/load_snapshots.py
```

Pull tournament data from Liquipedia (on-demand, not scheduled; add
`--titles a,b,c` to limit, `--refresh` to bypass the local cache):

```
python collectors/liquipedia.py
```

Run the full local refresh routine (fixed order, explicit — see the
script's own header comment for what each step does and why the order
matters):

```
scripts/local_refresh.sh                     # skips the Liquipedia crawl
scripts/local_refresh.sh --with-crawl        # also crawls Liquipedia first
scripts/local_refresh.sh --with-llm-aliases  # step 4 spends on ANTHROPIC_API_KEY
```

Its individual steps, runnable on their own too:

```
python etl/generate_tournament_aliases.py     # tournament_aliases; --skip-llm for rule-based only
python etl/export_reference_data.py           # data/reference/*.jsonl, for commit
python etl/classify_broadcast_tier.py         # viewership_snapshots.broadcast_tier; --full-reclassify to redo everything
```

Run tests:

```
pytest
```
