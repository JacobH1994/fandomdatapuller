# fandomdatapuller

A personal research platform tracking digital-fandom metrics, built to serve
`docs/esports_gauses_law_brief.md` (the current research question — does
competitive exclusion sort esports titles within a niche?) and designed so
future questions mostly need new queries, not new pipelines. Full spec:
`docs/esports_fandom_platform_prd_v2.md`.

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
- **`data/research.db` is derived and disposable.** It's gitignored and
  rebuildable at any time via `python etl/load_snapshots.py --rebuild`,
  which replays the entire `data/raw/` history — that raw history is the
  permanent record and is never edited after the fact.
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

**Known gap:** the Liquipedia connector's tournament-tier categorization
varies by wiki (see `collectors/liquipedia.py`'s docstring) and doesn't yet
resolve for the four fighting-game titles (`tekken`, `street_fighter`,
`mortal_kombat`, `guilty_gear`) — they're logged and skipped, not guessed.
Needs follow-up research into that wiki's actual competition categorization
before they'll get tournament data.

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

Run tests:

```
pytest
```
