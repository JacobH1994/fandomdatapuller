# fandomdatapuller

A personal research platform tracking digital-fandom metrics, built to serve
three active research questions and designed so future ones mostly need new
queries, not new pipelines:
`docs/esports_gauses_law_brief.md` (does competitive exclusion sort esports
titles *within* a niche, across titles?), `docs/counter_strike_lifecycle_brief.md`
(added 2026-09-09 — has a *single* title's own growth trajectory reached a
ceiling, independent of its competitors — see that brief's §3 for why it's
kept separate rather than folded into the first), and
`docs/wider_game_fandom_brief.md` (added 2026-09-09 — how do non-esports
game fandoms behave on Twitch, starting from an esports-vs-general creator-
insularity comparison and an anticipated GTA 6 launch as a live case study;
the first brief whose subject isn't esports at all — see its §3 for how it
relates to the other two). Full spec: `docs/esports_fandom_platform_prd_v2.md`.

`docs/system_reference.md` describes present state (what's actually
built, wired up, populated, or broken, read straight from the code and
data) — the PRD describes intent and decisions. When it drifts,
regenerate it rather than hand-editing it.

**The PRD and both research briefs are edited directly, the same as code**
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

**GitHub's own `schedule` trigger cannot be trusted to actually deliver
hourly cadence — confirmed directly, not assumed (2026-09-10).** A week of
`poll.yml` run history showed a real average gap of **3.8 hours** against
the configured 1-hour cron, present well before this repo had many
concurrently-scheduled workflows (ruling out our own concurrency as the
cause — this is GitHub deprioritizing `schedule`-triggered runs for this
repo at the platform level). Fixed by triggering externally instead:
`.github/workflows/dispatch_hourly.yml`/`dispatch_daily.yml` accept
`workflow_dispatch` (API-triggered, not subject to the same delay) and fan
out to every real collector plus the healthcheck. See `docs/
external_scheduler_setup.md` for the (external, account-gated) setup this
still needs, and re-run the same gap analysis periodically — if actual
cadence ever drifts back toward the old ~4h pattern, the external cron
service is the first thing to check, not this repo's own config.

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

**And to `collectors/steam_cohort_poll.py` / `steam_cohort_poll.yml`
(PRD §9.12a Track B, built 2026-09-08)** — a newly-discovered release's
daily player-count during its ~90-day launch window has the same
unbackfillable property, once it's in `steam_release_cohort`. **Not**
`collectors/steam_catalog_backfill.py` (Track A) or
`collectors/steam_discovery_poll.py`'s own classification pass, though —
release *metadata* (genres, VR flags, developer, ...) is fixed historical
fact, re-fetchable from Valve at any time, so Track A is deliberately
on-demand/local (mirrors `collectors/liquipedia.py`'s pattern) with no
schedule to protect.

**And to `collectors/twitch_platform_poll.py` / `twitch_platform_poll.yml`
(PRD §9.16, built 2026-09-09)** — the platform-wide, non-esports Twitch
collector feeding `docs/wider_game_fandom_brief.md`. Same unbackfillable
property as `collectors/twitch_poll.py` (it's the same API), and the same
fully-separate-file discipline as YouTube/Steam before it — imports
`twitch_poll.py`'s auth/retry helpers but never modifies that file, and
writes to its own `data/raw/twitch_platform/` subtree so a bug here can
never touch the 23-title collector. Deliberately NOT a full,
unthresholded capture of every live Twitch channel — discussed directly
with the user (2026-09-09): permanently committing channel logins and
freeform stream titles for every ordinary streamer platform-wide, to
this project's *public* repo, is a materially different thing than the
23-tracked-titles collection, and doesn't serve any research question
here. Uses `config/twitch_platform_capture.yaml`'s own tiered threshold
instead (re-derived from a real poll, not copied from `config/
capture.yaml` — the two populations' viewer-count distributions turned
out similarly shaped but not identical).

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
repo secret before the scheduled workflow can run; the platform-wide,
non-esports Twitch collector (PRD §9.16, `collectors/
twitch_platform_poll.py`, built 2026-09-09 for `docs/
wider_game_fandom_brief.md`) — built and tested locally, one real
snapshot loaded, not yet run on its own GitHub Actions schedule. See
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

Run the platform-wide, non-esports Twitch collector locally (PRD §9.16,
`docs/wider_game_fandom_brief.md` — same `TWITCH_CLIENT_ID`/
`TWITCH_CLIENT_SECRET` as above; a completely separate script/config/
workflow from `twitch_poll.py`, by design — see `collectors/
twitch_platform_poll.py`'s own docstring):

```
python collectors/twitch_platform_poll.py
```

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

Run the Steam catalog backfill (PRD §9.12a Track A — one-time,
patient, on-demand like `collectors/liquipedia.py`; safe to interrupt
and resume, skips app_ids already in `steam_release_history` unless
`--refresh`). Expected to take 1-2 weeks of intermittent runs across
the full catalog — don't expect this to finish in one sitting:

```
python collectors/steam_catalog_backfill.py
```

Track B (ongoing go-forward discovery + lifecycle player-count
polling of newly-discovered releases) is fully automated —
`steam_discovery_poll.yml` (daily, 03:00 UTC) and
`steam_cohort_poll.yml` (daily, 04:00 UTC) — nothing to run manually
unless testing locally (`python collectors/steam_discovery_poll.py`,
`python collectors/steam_cohort_poll.py`; the latter needs
`etl/load_snapshots.py` run first so it has a `steam_release_cohort`
to query).

Load raw Twitch, YouTube, Steam, and platform-wide-Twitch snapshots into
`research.db` (incremental; add `--rebuild` to wipe and reload everything):

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
python etl/classify_gta_content_segment.py    # platform_viewership_snapshots.content_segment (GTA V only); --full-reclassify to redo everything
```

Export a full-detail (code stripped, everything else kept) PDF of any notebook, for your own record — not for sharing externally:

```
scripts/export_notebook_pdfs.sh notebooks/<name>.ipynb
```

Build an external-facing "Boudica" branded report PDF (`pdf_outputs/`) — turquoise
accent, repeating watermark, clean prose only, no file paths/code/column names.
Write the report body by hand first (`reports/<name>/report.md` + `reports/<name>/figs/`,
not auto-derived from a notebook — see `docs/system_reference.md`'s Scripts section
for why), then:

```
python scripts/build_client_report.py \
  --title "Report Title" --meta "10 September 2026 · Research Note" \
  --body reports/<name>/report.md --output pdf_outputs/<name>.pdf
```

Run tests:

```
pytest
```
