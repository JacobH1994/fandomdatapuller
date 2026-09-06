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

## The one rule that overrides everything else

**Live Twitch viewership data cannot be backfilled.** Twitch's API only
exposes current state — there is no historical endpoint. An hour the
collector isn't running is an hour of data lost permanently, at any price.

Never disable, pause, or "temporarily" break `collectors/twitch_poll.py` or
the `poll.yml` workflow while refactoring something else, even briefly. If a
change risks the collector, make it in a way that keeps polling running, or
don't make it yet.

## Ethical non-goals — do not build these

- No scraping SullyGnome or any comparable tracker, ever, even to fill a gap
  that looks otherwise unfillable. Approach operators directly instead.
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
(`etl/classify_broadcast_tier.py`); `data/reference/` exports. See
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

Load raw Twitch snapshots into `research.db` (incremental; add `--rebuild`
to wipe and reload everything):

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
