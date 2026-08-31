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
  attribution clauses.

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
- **`data/research.db` is derived and disposable** (once it exists — not
  built yet, see below). It's gitignored and rebuildable at any time from
  `data/raw/`, which is the permanent, original-form record and is never
  edited after the fact.

## Current state

Only Phase 1 (collector) is built: the Twitch live-viewership collector,
tracked-title config, raw snapshot landing zone, and heartbeat monitoring.
The SQLite schema, ETL, and every other connector (Liquipedia, Esports
Charts, Reddit) are not built yet — don't assume `data/research.db`,
`etl/`, or `analysis/` exist.

## Common tasks

Run the collector locally (needs `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET`
in `.env`, or exported in the shell):

```
pip install -r requirements.txt
python collectors/twitch_poll.py
```

Trigger event-mode polling (tighter interval during a specific broadcast
window) from the GitHub Actions UI: run the "Twitch live-viewership poll"
workflow manually with `duration_minutes` / `interval_minutes` set.

ETL and test commands will be added here once Phase 2 exists.
