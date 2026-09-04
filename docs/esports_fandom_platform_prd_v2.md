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
| `viewership_snapshots` | id, title_id, channel_id, captured_at, viewer_count, broadcast_tier | Twitch (live, curated channels only — see §9.1), Esports Charts (event) |
| `category_totals_snapshots` | id, title_id, captured_at, total_viewer_count, total_channel_count | Twitch, aggregated across *all* live streams in a title's category (official and non-official) at capture time — individual non-official stream records are not persisted |
| `platform_totals` | id, captured_at, platform, total_viewers, total_channels | Twitch |
| `monthly_category_history` | id, title_id, year_month, hours_watched, avg_viewers, peak_viewers, source, confidence | One-time Kaggle import (§9.6) — monthly pre-aggregated, **not** poll-derived; kept separate from `category_totals_snapshots` so the granularity difference stays explicit |
| `channels` | id, title_id, platform, external_channel_id, name | Manual + Twitch |
| `channel_broadcast_roles` | id, channel_id, tournament_id (nullable), broadcast_tier (`primary_official` / `detected_costream` / `general`), source, confidence, valid_from, valid_to | `primary_official` manually seeded once per title; `detected_costream` fully automated — see §9.1 |
| `tournament_aliases` | id, tournament_id, alias, source, confidence | Rule-based extraction from the tournament name + one LLM call per tournament *series* for colloquial nicknames ("Champs," "Worlds," "MSI") |
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

**Tier is era-relative, not an absolute bar — confirmed across 20 of 23 active titles from live reconciliation, not a bug.** Liquipedia's tier-1 label reflects a tournament's standing against its own title's contemporary competitive landscape, not a fixed dollar or prestige floor: the earliest tier-1 window for nearly every tracked title is dramatically smaller in prize pool and team scale than what tier-1 means once the scene matures. This is a plausible mechanism for Post 1's unexplained finding that newer successful titles run smaller in absolute scale than the classics — tier-1 only requires being the best version of a title's own scene, not the best thing in esports, so a small scene can sustain it indefinitely. `get_success_milestone` is not gated on an absolute production-scale threshold: doing so would collapse "successful" (institutional durability) back into "scale," the two axes Post 1 kept deliberately separate. It returns `qualifying_window_scale` as a permanent companion field instead — prize pool per currency (never blended across currencies) and team count for the qualifying window, alongside the milestone flag.

The viewership-flat-or-growing half of the original definition is now built (`viewership_check`): official-broadcast Twitch data first, falling back to the Kaggle category-wide import (floor 2016, `confidence=proxy_estimate`) where Twitch has no coverage; `None` — not a silent pass — where the qualifying window predates both. It is informational only, not a gate, precisely because the fallback source is a game-fandom signal, not an esports-specific one (§4) — a "declining" result can't yet distinguish a cooling competitive scene from a cooling general audience. Full findings, per-title reasoning, and two real data-quality bugs the reconciliation process surfaced (an HTML-comment leak corrupting `tournaments.tier`, and letter-tier wikis — including VALORANT — silently returning no milestone at all before the fix) live in `milestone_reconciliation.md`, not duplicated here.

**Title continuity is a live, only-partially-resolved question, not just a `title_aliases` lookup.** That table was built to solve "same entity, different name over time" (CS:GO/CS2). Reconciliation surfaced the inverse problem: Counter-Strike is tracked as one continuous entity across engine changes, while Tekken and Mortal Kombat are tracked per numbered installment, so the current pipeline's Tekken milestone has no relationship to the TWT-era scene the hand-built table actually described. Not necessarily wrong — fighting games may genuinely reset harder than CS did — but currently an artifact of how `config/titles.yaml` happened to get filled in, not a checked, stated policy. Matters beyond these two titles: it's a prerequisite for ever testing H2, since "years of accumulated narrative capital" depends on which clock a franchise gets measured against.

Two more open items from reconciliation: no systematic sweep for further shared-wiki tournament-discovery contamination beyond the two instances already found (fighting games; Age of Empires, where 62% of `age_of_empires_ii`'s rows turned out to belong to other AoE titles) — worth prioritizing given the hit rate so far. And a malformed `rocket_league` start_date (`"<s>2"`) remains flagged, not fixed.

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
| Liquipedia — no account needed | Tournament, tier, prize-pool, date data via the open MediaWiki API | Free | Confirmed free and unauthenticated; rate-limited (1 req/2s, 1 req/30s for `action=parse`), needs a descriptive User-Agent. LPDB (the structured endpoint) requires separate approval and isn't assumed available — see §9.2 |
| GitHub account + repo | Version control, scheduled ingestion, raw-data durability | Free (private: 2,000 Actions min/month) | See §11 on repo visibility |
| Python 3.11+ | Everything | Free | `httpx`, `pandas`, `pyyaml`, `sqlite3` (stdlib), `plotly`/`matplotlib`, `jupyter`, `pytest` |
| Esports Charts enterprise contact | Demographic data (H1) and country-level geography (§6, non-proxied region) — **capability unconfirmed, not just cost** | Paid; capability *and* cost both unconfirmed | Public marketing copy attributes geo/demo granularity to a "Twitch Extension" product, distinct from the real-time-viewer-count "Private API" — unclear whether either covers historical, per-event data, or is available to anyone other than the channel/event owner. Confirm what's actually queryable before assuming access. |
| IGDB API key | Genre cross-reference | Free | Optional |
| Reddit API access | Community signals | Free tier | Optional; confirm current terms |
| YouTube Data API key | Official-channel live viewership | Free | Google Cloud project, enable YouTube Data API v3, generate an API key — no OAuth for public reads. Quota (10,000 units/day) is the real constraint, not access — see §9.7 |
| Supabase account | Alternative landing zone (§9.3) | Free tier sufficient | Not the default |

## 9. Ingestion components

All connectors share the same contract: write to `collector_runs`; be idempotent; tag every row with `source` and `confidence`; back off and retry on rate limits rather than failing the run.

**Idempotency is a hard requirement.** Scheduled jobs re-run, ETL scripts get run twice, a laptop loses power mid-load. Every load must use `INSERT ... ON CONFLICT DO NOTHING` (or equivalent) against the natural key. A research dataset that has silently double-counted an event is worse than one with a visible gap, because the gap is detectable and the duplication is not.

**Rate limiting and etiquette.** Twitch enforces a token-bucket limit; exceeding it returns 429 until the bucket refills, so exponential backoff with jitter is required. Liquipedia's MediaWiki API (§9.2) is confirmed free but volunteer-run: hold to 1 request/2 seconds (1/30s for `action=parse`), cache aggressively, never re-request unchanged historical data, and send a descriptive user-agent identifying the project and a contact address. The standard applied to SullyGnome in §3 applies here too — being a good citizen of the sources is a project value, not an afterthought.

### 9.1 Twitch live collector (scheduled — Phase 1)
GitHub Actions cron workflow polling `Get Streams` for every tracked title plus the platform-wide totals, appending each poll to `data/raw/` as a timestamped file committed back to the repo (the "git scraping" pattern). A separate local ETL (`etl/load_snapshots.py`) lands committed snapshots into SQLite on demand.

**Capture scope — this is the setting that actually controls storage, not file format.** Three tiers, not two:

1. **Channels in `config/channels.yaml`** — always full detail, regardless of viewer count.
2. **Any other stream above a viewer-count threshold** — full detail *including title and tags*. This tier exists because co-stream detection (below) matches on title/tag text, and co-streamers by definition aren't on the curated list. Discarding their titles at capture time would permanently foreclose the detection, which §2 forbids.
3. **Everything below the threshold** — no individual record. Sum viewer counts into `category_totals_snapshots` and roll languages into `language_mix_snapshots` (§6).

Twitch viewership is heavily power-law distributed, so a threshold in the region of 50–100 viewers discards the large majority of *records* while retaining the large majority of *viewership*, and sits far below any co-stream worth counting. Set the exact value empirically rather than by guess: compute the record-count-vs-viewership retention curve from a real snapshot before fixing it, and record the chosen threshold in config so its effect on any time series is auditable later. Capturing the full untiered population instead inflates storage by roughly one to two orders of magnitude for records nothing in §6 uses. `thumbnail_url` and `type` are never worth keeping at any tier — the former is reconstructible from `user_login`, the latter is constant.

**`config/channels.yaml` is not just the primary org channel — co-streamers are the harder and more important part.** Major tournaments routinely draw more combined viewership on co-streams than on the primary broadcast; treating co-streams as general content understates esports engagement specifically for the titles that co-stream most, which biases §12's official-broadcast-share metric in a non-random way. Whether a co-streamer was formally authorized by the publisher doesn't change whether their viewers are engaging with esports content rather than general game content, and it's not a question this research needs answered — so `broadcast_tier` doesn't distinguish authorized from unauthorized, only tournament-specific from general. That collapses the problem from "research every event's approved partner list" to something fully automatable: a stream is tagged `detected_costream` when it's live during a known tournament's broadcast window (`tournaments.start_date`/`end_date`) *and* its title or tags match that tournament's aliases (`tournament_aliases`, §6). No manual research and no human confirmation step — every match lands as `confidence=proxy_estimate` and is usable as-is. This will misclassify some streams in both directions (passing mentions get caught, co-streams that don't name-check the tournament get missed); that's an accepted trade for zero ongoing labor, and any published share number built on it should be described as detected/approximate rather than authoritative. `primary_official` is still the one thing seeded manually, once per title — that list is small and essentially static.

- **Default cadence:** hourly, for tracked titles and platform totals. The research questions resolve at monthly and yearly granularity, so hourly loses little.
- **Event mode:** manually-triggered 5–15 minute polling for specific titles during specific broadcast windows, where an accurate peak-viewer figure matters.
- **Cost:** free on a public repo; on a private repo the 2,000 free Actions minutes/month comfortably cover hourly polling, with a few dollars of overage at heavy event-mode use.
- **Bonus property:** because raw snapshots are committed to git, the collection history is automatically versioned, backed up off-machine, and independently auditable. This is a large part of why this pattern is preferred over a VPS.

### 9.2 Liquipedia connector (on-demand)
Liquipedia operates two separate APIs, confirmed directly from their API Terms of Use: **LPDB**, the structured tournament/match/prize-pool endpoint, requires an approved request and is not self-service — their own site currently lists even the paid tiers as unavailable, so this isn't a dependency to build around. Separately, Liquipedia provides free, unauthenticated access to the same underlying content through the **standard MediaWiki API** — no registration, just a rate limit (1 request/2s generally, 1 request/30s for `action=parse`) and a descriptive User-Agent identifying the project and a contact address.

Build against the MediaWiki API: fetch each tournament page's wikitext and parse the "infobox" template parameters (date range, prize pool, tier, region) rather than querying LPDB directly — `mwparserfromhell` (Python) is built for exactly this. More parsing work than a clean structured endpoint, but zero access friction and officially sanctioned. Cache responses locally and re-request only what's missing or stale; historical tournament data doesn't change on a clock. If an LPDB request is later approved, it's a straightforward swap to a cleaner source for the same table — nothing else should be designed to depend on that outcome.

**Tier conventions are not uniform across game wikis — confirmed, and resolved for the known cases.** Tekken, Street Fighter, Mortal Kombat and Guilty Gear share Liquipedia's "fighters" wiki; the shared-wiki tournament-discovery issue (not a tier-convention issue as first suspected) was fixed by intersecting discovery against each title's verified per-game category. A separate, second bug — HTML rationale comments leaking into the raw tier value — additionally corrected several hundred tier readings for these same titles once found. Full detail in `milestone_reconciliation.md`. Whether fighting games turn out to organize around independent majors rather than publisher-run tiers, as originally hypothesized here, remains a live and separate question from the parsing bugs — not yet resolved either way.

### 9.3 Esports Charts connector (on-demand)
Event and peak viewership per title. Populates `viewership_snapshots` with `source=esportscharts`, `broadcast_tier=primary_official`, since event data is esports-specific by construction.

**Alternative landing zone (both 9.1 and 9.3):** the scheduled job could write directly to hosted Postgres (Supabase free tier) instead of committing files. Free-tier projects pause after a week of inactivity, which is a non-issue given hourly writes. This buys remote queryability at the cost of an external dependency and the loss of git's automatic versioning of raw data. Recommend git-scraping as the default; revisit only if multi-device access becomes necessary.

### 9.4 Manual and curated data
`failed_challengers`, cause-of-death annotations (the Overwatch case), and official-channel curation are entered directly with `source=manual`. No automation planned. Flagged as directional rather than exhaustive, per the brief's survivorship-bias limitation.

### 9.5 Optional
Reddit main-vs-esports subreddit snapshots; IGDB genre cross-reference. Both on-demand, both deferrable past V1.

### 9.6 Kaggle historical import (one-time)
A public Kaggle dataset ("Evolution of Top Games on Twitch") carries monthly top-200 game figures — hours watched, average and peak viewers — from 2016 onward. It's the only available source for *general category* Twitch attention predating the collector's start date; Liquipedia covers tournaments and Esports Charts covers events, neither of which is the same thing. That makes it worth importing for the Classic and Console phases of the emergence story, which no other source in this plan reaches.

Three constraints on how it lands:

- **Separate table, deliberately.** It's monthly pre-aggregated data, not poll-derived, so it goes to `monthly_category_history` rather than `viewership_snapshots` or `category_totals_snapshots`. Merging it would leave a future query silently comparing monthly averages against hourly polls.
- **Provenance is unverified.** The dataset page does not state its collection method, and datasets of this kind are frequently assembled by scraping a tracker — which would sit badly against the §3 non-goal. Import at `confidence=proxy_estimate` with `source=kaggle_import`, and check the dataset's discussion tab or contact the uploader before any published claim rests on it. If it turns out to be scraped from a tracker that prohibits it, drop it.
- **Game fandom, not esports fandom.** Category-level figures include ranked play, guides and cosmetics content, exactly as §4 warns for raw Twitch category data. Never fold it into an esports-specific metric without labelling.

One-time import, no scheduling, no ongoing maintenance.

### 9.7 YouTube live collector (scheduled — mirrors §9.1)
Auth is a plain API key against a Google Cloud project — no OAuth needed for public reads. The constraint is quota, not access, and it's sharply asymmetric: `videos.list` (viewer count for known video IDs) costs 1 unit and batches up to 50 IDs per call; `search.list` (the only way to discover which video a channel is *currently* live on) costs 100 units against a 10,000/day default — roughly 100 discovery checks a day, full stop.

That rules out continuous discovery polling. Baseline: check the official-channel list for live status a few times a day. Event mode, same concept as §9.1: bump discovery to a tight cadence for the channels relevant to a specific tournament during its known window (`tournaments.start_date`/`end_date`), concentrating the expensive call where it matters most. Once a live video ID is known, monitor its viewer count with the cheap batched call at Twitch-equivalent cadence.

Feeds the existing `channels` (`platform=youtube`) and `viewership_snapshots` tables — no schema change, since `platform` was already there for this. Real limitation, not a workaround: no affordable way to enumerate every live stream under a game the way `Get Streams` does, so YouTube populates the official-channel tier only, never `category_totals_snapshots` — no YouTube-side denominator. Optional, never required: if a tournament's YouTube stream URL is published in advance, noting the video ID directly skips a search call for that event — a free efficiency gain when convenient, not a dependency.

### 9.8 Chinese platforms (Douyu, Huya, Bilibili) — investigated, not pursued
Douyu runs an official Open Platform, but its developer agreement gates access behind "relevant legal qualifications" — in practice a registered business entity, not an individual researcher. What's reachable without that is unofficial, reverse-engineered endpoints built from captured mobile-app traffic — the same category of workaround already declined for SullyGnome and unofficial Liquipedia wrappers (§3), and not more defensible here for being harder to reach legitimately.

Access aside, these platforms report a Heat Index, not a viewer count — a composite blending stream duration, traffic and virtual gifting, with no fixed conversion to actual viewers. Esports Charts, tracking dozens of platforms professionally, state that a directly comparable number is technically out of reach even for them.

Realistic use of this market's data: cite published aggregate figures from firms tracking it professionally (Niko Partners, Streams Charts) as occasional `source=secondary_report` data points, not a connector. Not an open question — revisit only if a legitimate access route appears, not by default the next time China comes up.

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
- `get_success_milestone(title)` — the brief's definition, computed, always paired with the absolute-scale figure for that title's qualifying window (see §6) rather than returned alone.
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
- ~~**Liquipedia terms** — confirm current API terms, rate limits and attribution requirements before building against it.~~ Resolved: MediaWiki API confirmed free/open (§8, §9.2); LPDB requires approval and isn't assumed available.
- **IGDB and Reddit connectors** — V1 or deferred past the Post 2 deadline.
- **Event-mode trigger list** — which broadcasts warrant 5–15 minute polling, and who maintains that calendar.
- **Chat message volume as an interactivity metric** — a genuinely distinct signal from viewer count (active participation vs. passive attention), directly relevant to the digital-fandom framing. Not a Phase 1 addition: Twitch doesn't expose chat volume via `Get Streams`, so it needs a persistent connection (IRC or EventSub) rather than a periodic poll — a new component, not a new field. Naturally scoped to the official-channel list only, same as the rest of §9.1's curated capture. Worth its own phase once the core collector is stable.
- **Shared-wiki contamination sweep** — two ad hoc checks (fighting games, Age of Empires) both found real, large-scale cross-franchise contamination in tournament discovery (up to 62% of a title's rows). No systematic check across the other 21 titles has been done. Given that hit rate, worth prioritizing over new feature work — reconciliation and everything downstream of it is only as trustworthy as discovery being correctly scoped per title.
- **Title generational continuity — no stated policy.** Counter-Strike is tracked as one continuous entity across engine changes (1.6 through CS2); Tekken and Mortal Kombat are tracked per numbered installment, with no relationship asserted between generations. Currently an artifact of how `config/titles.yaml` was filled in, not a checked decision. Needs an explicit, consistent per-franchise criterion (continuity of roster/infrastructure/audience across a version change, or some other stated test) rather than being decided ad hoc — and it's a prerequisite for ever testing H2, since narrative-capital accumulation depends on which clock a franchise is measured against.
- **Whether `milestone_year` should eventually gate on the viewership clause** — currently informational only, because the viewership signal is game-fandom (category-wide), not esports-specific. Revisit once enough official-broadcast-tier Twitch history has accumulated to build an esports-specific version of the check.
