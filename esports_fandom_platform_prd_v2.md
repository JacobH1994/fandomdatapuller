# Esports Fandom Research Platform — PRD v2 (for Claude Code)

Companion document: `esports_gauses_law_brief.md` (the Post 2 research brief). The brief defines *what is being researched and why*; this PRD defines *what to build*. Where the brief specifies a definition (success milestone, niche, esports vs. game fandom), the brief is authoritative and this document implements it.

## 1. Purpose

Post 2's research brief (Gause's Law / competitive exclusion) is the first real workload on this platform, not the only one. The underlying research program — digital fandom, with esports as one instance — will keep generating new questions, and each one shouldn't require rebuilding data infrastructure. This PRD specifies a build where Post 2 is fully served *and* the next question is mostly a new query rather than a new pipeline.

## 2. The one hard constraint

**Live viewership data cannot be backfilled.** Twitch's API exposes only current state; there is no historical endpoint. Every hour the collector is not running is an hour of data that can never be recovered, by any means, at any price. Third-party trackers appear to have deep history only because they have been archiving continuously for years.

Three consequences that shape the whole build:

1. The Twitch collector is **Phase 1**, not Phase 2. Stand it up before the schema is finished, before the analysis layer exists, before anything is polished. It accrues value from the moment it runs.
2. Silent collector failure is the single worst failure mode in the system. It is unrecoverable, and without monitoring it is invisible. §10 is therefore a requirement, not a nice-to-have.
3. Raw snapshots must be preserved in their original form, permanently, separate from any derived database. If the schema changes or the ETL has a bug, the raw record must still exist to re-derive from.

Historical depth prior to collector start-up comes from Esports Charts and Liquipedia only, and is bounded by what they publish.

## 3. Goals & non-goals

**Goals (V1)**
- Serve the Post 2 research brief end to end: ingested data → niche-cell metrics → charts and CSV.
- Replace hand-built collection (the milestone table; the seat-cap, prize-pool and viewership comparisons) with pipelines covering the full title list rather than six hand-picked examples.
- Carry provenance and confidence as queryable fields, not prose caveats.
- Begin accumulating an irreplaceable longitudinal viewership record immediately.
- Stay cheap and low-maintenance. This is a personal research tool, not a production service.

**Non-goals (V1)**
- Creator/streamer platforms (YouTube, TikTok). The schema shouldn't preclude adding them; V1 doesn't ingest them.
- A hosted, multi-user, always-on application. Local-first.
- Automated discovery of failed or non-surviving esports attempts. V1 stores qualitative notes on these; it doesn't research them.
- **Scraping SullyGnome or any comparable tracker.** SullyGnome's operator explicitly asks people not to scrape the site, and this project respects that. This is a standing constraint, not a V1 deferral: if a historical gap looks fillable by scraping a tracker, the answer is still no. Approach operators directly instead.
- **Any ingestion that violates a source's published terms.** Liquipedia's API terms, Twitch's Developer Agreement, and Reddit's API terms are to be read and respected, including data-retention and attribution clauses.

## 4. Users

One researcher: technical enough to run Python and review generated code, not a professional engineer. Optimize for low maintenance burden over configurability. Single local user for V1 — the schema shouldn't hard-code that, but access design can.

## 5. Repo layout

```
esports-research/
  CLAUDE.md                  # agent context, see §15
  README.md
  .env.example               # credential template, never real values
  .gitignore                 # must include .env, *.db
  config/
    titles.yaml              # tracked-title registry, see §7
    channels.yaml            # official broadcast channels per title
  collectors/
    twitch_poll.py           # runs in CI, writes raw snapshots
    liquipedia.py            # on-demand
    esports_charts.py        # on-demand
    reddit.py                # optional
  data/
    raw/                     # append-only snapshot files, committed
    research.db              # SQLite, gitignored, rebuildable from raw/
  etl/
    load_snapshots.py        # raw/ -> SQLite, idempotent
    schema.sql
  analysis/
    metrics.py               # reusable metric functions
    export.py                # CSV/Sheets export
  notebooks/
  tests/
  .github/workflows/
    poll.yml                 # scheduled Twitch collection
    healthcheck.yml          # gap detection, see §10
```

The important structural property: `data/research.db` is **derived and disposable**, rebuildable at any time from `data/raw/`. Raw snapshots are the asset; the database is a convenience.

## 6. Data model

SQLite. All timestamps stored in **UTC, ISO 8601**, without exception — the data spans global events and will be aggregated to daily and monthly buckets, where naive local times silently corrupt boundaries.

| Table | Key fields | Populated by |
|---|---|---|
| `titles` | id, canonical_name, publisher, launch_date, is_active | Manual seed + Liquipedia/IGDB |
| `title_aliases` | id, title_id, alias, platform, external_ids (Twitch category, Liquipedia page, IGDB id), valid_from, valid_to | Manual + connector mapping |
| `tournaments` | id, title_id, tier, prize_pool, currency, start_date, end_date, region | Liquipedia |
| `viewership_snapshots` | id, title_id, channel_id, captured_at, viewer_count, is_official_broadcast | Twitch (live), Esports Charts (event) |
| `platform_totals` | id, captured_at, platform, total_viewers, total_channels | Twitch |
| `channels` | id, title_id, platform, external_channel_id, is_official, name | Manual + Twitch |
| `community_signals` | id, title_id, subreddit_type (main/esports), subscriber_count, captured_at | Reddit (optional) |
| `demographic_snapshots` | id, title_id, age_bucket, gender, share, captured_at | Esports Charts enterprise (if pursued) |
| `failed_challengers` | id, name, genre, platform, region, notes, source | Manual, qualitative |
| `collector_runs` | id, collector, started_at, finished_at, status, rows_written, error | All collectors |

Genre and platform are reference tables rather than hardcoded enums — close to fixed facts about a product, sourced once and rarely revisited.

**Region is measured, not configured.** Unlike genre and platform, regional audience concentration is a behavior of the audience over time, not a fact about the game, and it can shift over a title's life the way Post 1 describes happening industry-wide. It shouldn't live in a static reference table set once in config. Two structured sources feed it, layered by confidence rather than treated as equally solid:

1. **Tournament region** (`tournaments.region`, from Liquipedia) — authoritative where it exists, since competitive circuits are organized by region (LCK is Korea, LEC is Europe). Covers the esports-specific side precisely, but only that side.
2. **Broadcast language mix** — the standard proxy where direct geography isn't available. `Get Streams`, the same endpoint the collector already polls hourly for §9.1, returns each stream's language on every call at no extra cost. Rather than storing every individual stream's language indefinitely, the poller aggregates it into a per-title, per-poll breakdown before discarding the per-stream detail — consistent with the earlier storage design, and only a modest addition to that estimate rather than a new category of cost.

| Table | Key fields | Populated by |
|---|---|---|
| `language_mix_snapshots` | id, title_id, captured_at, language_code, viewer_count | Twitch (derived from the same poll as §9.1, aggregated at capture time) |

Language is an imperfect proxy and should be treated as one: Korean or Japanese imply a region with reasonable confidence; English spans North America, the UK, India and the Philippines; Spanish spans Spain and most of Latin America. `analysis/metrics.py` should expose `get_primary_region(title, start, end)`, combining both sources — Liquipedia region where available, language mix as fallback or corroboration — and returning its answer tagged with which tier of evidence it rests on, never a bare label. A region inferred purely from language gets its own confidence tier (`proxy_estimate`, §14) rather than being folded into `manual_judgment_call` — it's a principled inference, not a human decision, and conflating the two overstates or understates the wrong thing depending on which way you'd round it.

If regional precision matters enough for a specific analysis, an Esports Charts enterprise conversation is worth having (§8) — but their public marketing copy attaches geo/demo granularity to a Twitch Extension product, not clearly to the historical API, and doesn't confirm third-party access to past events. Treat it as a question to ask, not a source to plan around, until confirmed directly.

A *niche* is a query across genre, platform and region, so refining any of the three later requires no migration.

**`title_aliases` is load-bearing, not bookkeeping.** The existing dataset already contains CS:GO/CS2 under one banner, PUBG PC and PUBG Mobile as separate entries, and Wild Rift distinct from League of Legends. Titles get renamed, sequels absorb their predecessor's scene, and one title can span several Twitch categories across platforms. Deciding case by case at query time produces results that quietly change depending on who wrote the query. Model it once, explicitly, with validity dates.

**`platform_totals` answers a question the per-title tables can't.** "Esports' share of total platform attention over time" needs a denominator. Twitch has no single esports category — League, CS2, VALORANT and the rest are separate — so the whole-platform total has to be collected alongside the tracked titles, at the same cadence, or the share metric is not computable retrospectively.

**Derived, not stored raw:** `success_milestone_year` per title, computed from `tournaments` against the brief's definition (2+ years of A-tier-or-better competition across 2+ continents, viewership flat or growing). Implement it as a documented function with the definition's thresholds as named parameters, so a change to the definition re-derives rather than requiring re-entry. This is the centrepiece of Post 1 and the basis of the title list, so it needs to be reproducible rather than hand-maintained.

**Uniqueness constraints** on every ingested table (e.g. `viewership_snapshots` unique on `(channel_id, captured_at)`), so re-running a load cannot duplicate rows. See §9.

## 7. Tracked-title configuration

`config/titles.yaml` is the collector's single source of truth: which titles to poll, their Twitch category IDs, their Liquipedia identifiers, genre/platform/region tags, and whether each is actively tracked. `config/channels.yaml` maps official broadcast channels per title.

Two properties matter:
- Adding a title to the research is a config edit, not a code change.
- The config is version-controlled, so "what were we tracking in March?" is answerable from git history. This matters for a longitudinal dataset where coverage changes over time.

The official-channel list is what makes the esports-vs-game-fandom distinction (brief §7, limitation 4) computable rather than rhetorical. It requires manual curation and periodic review, since channels change between seasons.

## 8. Prerequisites & dependencies ("predicates")

| Dependency | Needed for | Cost | Notes |
|---|---|---|---|
| Twitch developer app | Live polling | Free | Client ID/secret via dev.twitch.tv; client-credentials flow |
| Liquipedia API registration | Tournament, tier, prize-pool data | Free | Registration required; confirm current terms and rate limits at liquipedia.net/api |
| GitHub account + repo | Version control, scheduled ingestion, raw-data durability | Free (private: 2,000 Actions min/month) | See §11 on repo visibility |
| Python 3.11+ | Everything | Free | `httpx`, `pandas`, `pyyaml`, `sqlite3` (stdlib), `plotly`/`matplotlib`, `jupyter`, `pytest` |
| Esports Charts enterprise contact | Demographic data (H1) and country-level geography (§6, non-proxied region) — **capability unconfirmed, not just cost** | Paid; capability *and* cost both unconfirmed | Public marketing copy attributes geo/demo granularity to a "Twitch Extension" product, distinct from the real-time-viewer-count "Private API" — unclear whether either covers historical, per-event data, or is available to anyone other than the channel/event owner. Confirm what's actually queryable before assuming access. |
| IGDB API key | Genre cross-reference | Free | Optional |
| Reddit API access | Community signals | Free tier | Optional; confirm current terms |
| Supabase account | Alternative landing zone (§9.3) | Free tier sufficient | Not the default |

## 9. Ingestion components

All connectors share the same contract: write to `collector_runs`; be idempotent; tag every row with `source` and `confidence`; back off and retry on rate limits rather than failing the run.

**Idempotency is a hard requirement.** Scheduled jobs re-run, ETL scripts get run twice, a laptop loses power mid-load. Every load must use `INSERT ... ON CONFLICT DO NOTHING` (or equivalent) against the natural key. A research dataset that has silently double-counted an event is worse than one with a visible gap, because the gap is detectable and the duplication is not.

**Rate limiting and etiquette.** Twitch enforces a token-bucket limit; exceeding it returns 429 until the bucket refills, so exponential backoff with jitter is required. Liquipedia is a volunteer-run project: cache aggressively, never re-request unchanged historical data, and send a descriptive user-agent identifying the project and a contact address. The standard applied to SullyGnome in §3 applies here too — being a good citizen of the sources is a project value, not an afterthought.

### 9.1 Twitch live collector (scheduled — Phase 1)
GitHub Actions cron workflow polling `Get Streams` for every tracked title plus the platform-wide totals, appending each poll to `data/raw/` as a timestamped file committed back to the repo (the "git scraping" pattern). A separate local ETL (`etl/load_snapshots.py`) lands committed snapshots into SQLite on demand.

- **Default cadence:** hourly, for tracked titles and platform totals. The research questions resolve at monthly and yearly granularity, so hourly loses little.
- **Event mode:** manually-triggered 5–15 minute polling for specific titles during specific broadcast windows, where an accurate peak-viewer figure matters.
- **Cost:** free on a public repo; on a private repo the 2,000 free Actions minutes/month comfortably cover hourly polling, with a few dollars of overage at heavy event-mode use.
- **Bonus property:** because raw snapshots are committed to git, the collection history is automatically versioned, backed up off-machine, and independently auditable. This is a large part of why this pattern is preferred over a VPS.

### 9.2 Liquipedia connector (on-demand)
Pulls tournament tier, prize pool, dates and region per title into `tournaments`. Historical data doesn't change on a clock; re-run when the title list changes or periodically to catch corrections. Cache responses locally and re-request only what's missing or stale.

### 9.3 Esports Charts connector (on-demand)
Event and peak viewership per title. Populates `viewership_snapshots` with `source=esportscharts`, `is_official_broadcast=true`, since event data is esports-specific by construction.

**Alternative landing zone (both 9.1 and 9.3):** the scheduled job could write directly to hosted Postgres (Supabase free tier) instead of committing files. Free-tier projects pause after a week of inactivity, which is a non-issue given hourly writes. This buys remote queryability at the cost of an external dependency and the loss of git's automatic versioning of raw data. Recommend git-scraping as the default; revisit only if multi-device access becomes necessary.

### 9.4 Manual and curated data
`failed_challengers`, cause-of-death annotations (the Overwatch case), and official-channel curation are entered directly with `source=manual`. No automation planned. Flagged as directional rather than exhaustive, per the brief's survivorship-bias limitation.

### 9.5 Optional
Reddit main-vs-esports subreddit snapshots; IGDB genre cross-reference. Both on-demand, both deferrable past V1.

## 10. Collector reliability & monitoring

Because collector downtime is unrecoverable (§2), reliability requirements are non-negotiable:

- **Heartbeat check.** A second scheduled workflow (`healthcheck.yml`, daily) queries the most recent snapshot timestamp and fails loudly if it is older than a threshold (suggest 3 hours against an hourly cadence). A failing GitHub Actions workflow emails the repo owner by default, which is sufficient alerting for this project.
- **Gap ledger.** The ETL records detected gaps in collection into a table, so analysis can distinguish "viewership was zero" from "we weren't looking." An unlogged gap becomes an invisible artefact in a chart two years from now.
- **Run logging.** Every collector writes to `collector_runs` — start, finish, status, rows written, error. Cheap, and makes "when did this break" answerable.
- **Retry semantics.** Transient failures retry with backoff inside the run. A wholly failed run is logged and surfaced by the heartbeat rather than silently skipped.
- **Token refresh.** App access tokens expire; the collector must handle refresh automatically rather than failing after weeks of clean operation.

## 11. Secrets & repository visibility

- Credentials live in `.env` locally (gitignored, with a committed `.env.example` template) and in GitHub Actions repository secrets for CI. Never in code, never in config YAML, never in committed snapshots.
- `.gitignore` must cover `.env` and `*.db` from the first commit.
- **A decision is required on repo visibility, and it is not purely a cost question.** A public repo makes Actions minutes free and unlimited, but also makes every committed snapshot, the tracked-title config, and any accidentally-committed secret public. A private repo keeps the dataset private within a 2,000 minute/month free allowance. Given the research is intended for publication anyway, public is defensible and cheaper. Recommend deciding deliberately and, if public, enabling secret scanning and doing a review pass before the first push.

## 12. Analysis & output layer

**Notebooks, not a dashboard, for V1.** A dashboard is a fixed set of pre-built views: well suited to questions asked repeatedly, poorly suited to a research process that keeps generating new ones. `analysis/metrics.py` sits between raw SQL and notebooks so new questions become function calls rather than new plumbing:

- `get_niche_share(genre, platform, region, start, end)`
- `get_concentration(niche, start, end)` — default to HHI (Herfindahl-Hirschman Index), the standard concentration measure and a direct fit for the coexistence-vs-exclusion question. Keep the measure swappable.
- `get_official_broadcast_share(title, start, end)` — the esports-vs-game-fandom metric.
- `get_success_milestone(title)` — the brief's definition, computed.
- `get_primary_region(title, start, end)` — Liquipedia tournament region where available, language mix (§6) as fallback/corroboration, tagged with which tier it rests on.

**CSV export is a first-class output, not an afterthought.** `analysis/export.py` writes any metric result to CSV for manual work in Google Sheets. The platform removes the drudgery of *compiling* tables; it doesn't dictate where the thinking happens. Every chart produced should have a one-line path to the underlying CSV.

A lightweight dashboard for genuinely recurring checks is a plausible V2.

## 13. Validation & testing

- **Reconciliation against the hand-built figures.** The existing six-title comparisons (seat caps, prize pools, peak viewers) and the milestone table are the best available test fixture: known-good numbers produced independently of this pipeline. Phase 2 is not complete until pipeline output reconciles against them, with every discrepancy either explained or corrected. This is the single strongest check that the automation is trustworthy, and it exists only because the manual work was done first.
- **Unit tests** on `metrics.py`, particularly the milestone and concentration functions, using small fixed fixtures. Derived-metric bugs are the kind that produce a plausible-looking chart and a wrong conclusion.
- **Schema constraint tests** confirming that double-loading a snapshot file produces no duplicate rows.
- **A confidence audit query** — `SELECT * WHERE confidence != 'verified'` — run before anything is published, per §14.

## 14. Provenance & confidence

Every row in every table carries:
- `source` (`liquipedia`, `twitch_api`, `esportscharts`, `manual`, `ai_assisted`)
- `confidence` (`verified` / `ai_assisted_unreviewed` / `manual_judgment_call` / `proxy_estimate`)

`proxy_estimate` marks values inferred from an imperfect but principled signal — language standing in for region (§6) is the clearest example — rather than a human decision or unreviewed model output. It is neither of the other two and shouldn't be filtered by either one's rule.

This is the engineering translation of the brief's limitations. "AI-assisted and unchecked" or "this was a judgment call" becomes a filterable property rather than something to remember and caveat by hand. Before publication the question is a query, not a memory exercise.

The practice is grounded in something already observed: the existing milestone sheet's own validation column caught at least one suspect AI-generated figure. That instinct is correct and this schema formalises it. **Anything Claude Code generates or infers — genre tags, region assignments, milestone calculations from ambiguous sources — defaults to `ai_assisted_unreviewed` and is promoted to `verified` only by explicit human review.**

## 15. CLAUDE.md

Create `CLAUDE.md` at the repo root, since Claude Code reads it automatically as standing context for every session. It should carry:

- One-paragraph project summary and a pointer to this PRD and the research brief.
- The §2 constraint, stated plainly: live data cannot be backfilled, so never disable, pause, or "temporarily" break the collector while refactoring.
- The §3 ethical non-goals: no scraping SullyGnome or comparable trackers; respect all source terms.
- The provenance rule from §14: generated or inferred data is always `ai_assisted_unreviewed`.
- Conventions: UTC everywhere, idempotent loads, config-driven title list, `research.db` is disposable and rebuildable from `data/raw/`.
- Commands for common tasks (run ETL, run tests, trigger event-mode polling).

Keep it short. It is read every session; length dilutes it.

## 16. Success criteria

**Phase 1 (collector)** — the Twitch collector runs unattended for 30+ consecutive days, hourly, capturing tracked titles and platform totals, with the heartbeat check passing and any gaps logged.

**Phase 2 (backfill)** — the milestone table regenerates for all 25+ titles from Liquipedia rather than manual entry, and reconciles against the hand-built version.

**Phase 3 (classification)** — every tracked title carries genre, platform and region tags, with AI-assisted assignments marked as such.

**Phase 4 (metrics)** — niche-cell share and concentration are computable for any genre × platform × region combination and any date range; official-broadcast share is computable for every title with a curated channel list.

**Phase 5 (extensibility)** — a new research question (for example the H2 volatility test) is answerable by writing a query against existing tables. New ingestion code is required only for genuinely new data types.

**Throughout** — every row carries `source` and `confidence`; every chart has a CSV path; re-running any loader produces no duplicates.

## 17. Cost summary

| Component | Approach | Monthly |
|---|---|---|
| Twitch live polling | GitHub Actions, hourly, git-scraping | $0 (within free allowance; a few $ at heavy event-mode use) |
| Liquipedia | On-demand, local, cached | $0 |
| Esports Charts | Public site as currently used | $0 (private API optional, paid, TBD) |
| Core database | Local SQLite | $0 |
| Optional Supabase landing zone | Only if chosen over git-scraping | $0 free tier |
| Analysis | Local Jupyter | $0 |

**Realistic total: $0/month**, with a bounded path to a few dollars if polling frequency rises materially. The only meaningful cost decision in the project is whether to pursue Esports Charts' paid tier for demographic data.

## 18. Phased build plan

**Phase 1 — Collector first.** Twitch collector, tracked-title config, raw snapshot landing zone, heartbeat monitoring. Ship this before anything else; every day of delay is permanently lost data. The schema does not need to be finished for this phase, because raw snapshots are stored in original form and loaded later.

**Phase 2 — Foundation.** SQLite schema with provenance fields, `title_aliases`, idempotent ETL from raw snapshots, Liquipedia connector, milestone-table backfill, reconciliation against the hand-built figures.

**Phase 3 — Classification.** Genre, platform and region tagging (Claude-assisted first pass, human-reviewed, marked `ai_assisted_unreviewed` until reviewed); official-channel curation; IGDB cross-reference if pursued.

**Phase 4 — Metrics.** `metrics.py`, HHI concentration, niche-share, official-broadcast share, CSV export, unit tests.

**Phase 5 — Case-study data.** Esports Charts enterprise scoping if pursued; pre-2020 baseline pull; the cross-genre 2020 check (Fall Guys, Among Us, Rocket League); subreddit-pair snapshots; failed-challenger notes.

**Phase 6 — Analysis & output.** Notebooks and charts for Post 2.

Phases 2 through 4 can overlap; Phase 1 should not wait for any of them.

## 19. Open decisions

- **Repo visibility** (§11) — public (free unlimited Actions, public dataset) vs. private (private dataset, 2,000 free minutes). Recommend deciding before the first push rather than after.
- **Git-scraping vs. Supabase** landing zone — recommend git-scraping; revisit if remote access becomes necessary.
- **Esports Charts enterprise** — first confirm what's actually available (their public copy is ambiguous between a channel-owner-facing Twitch Extension and their historical API — see §8), then whether the demographic and geographic data justifies cost. It would be the only direct test of H1's cohort claim and the only non-proxied source for region, *if* it turns out to cover third-party historical queries at all.
- **Liquipedia terms** — confirm current API terms, rate limits and attribution requirements before building against it.
- **IGDB and Reddit connectors** — V1 or deferred past the Post 2 deadline.
- **Event-mode trigger list** — which broadcasts warrant 5–15 minute polling, and who maintains that calendar.
