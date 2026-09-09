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
  docs/
    esports_gauses_law_brief.md        # research questions, definitions, hypotheses
    esports_fandom_platform_prd_v2.md  # this document
    milestone_reconciliation.md        # Claude Code's own record of Phase 2 findings
    research_journal.md                # informal, unstructured — see CLAUDE.md
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
| `monthly_category_history` | id, title_id, year_month, hours_watched, avg_viewers, peak_viewers, esports_hours_watched, esports_share_pct, is_partial_month, source, confidence | Kaggle import (§9.6, `source=kaggle_import`, esports columns always NULL — Kaggle has no broadcast-tier information) **and**, going forward, a monthly rollup of the project's own collection (`source=own_collector`) — see below |
| `niche_similarity_history` | id, title_a, title_b, cosine_full, cosine_no_english, jensen_shannon_distance, computed_at, window_start, window_end, low_sample_flag | Appended by `notebooks/niche_membership.ipynb` on each run — a persisted history of the language-mix similarity work, not a live-only computation |
| `creator_crossover_history` | id, title_a, title_b, shared_crossover_channels, total_channels_a, total_channels_b, enrichment_ratio, hypergeometric_p_value, computed_at, window_start, window_end, low_channel_count_flag | Appended by `notebooks/creator_crossover.ipynb` on each run |
| `steam_release_history` | id, app_id, name, release_date, genres (list, includes "Indie" where applicable), developer, publisher, categories (includes VR flag once confirmed — §9.12a), recommendations_total, low_relevance_flag | One-time backfill via `IStoreService/GetAppList` + `appdetails` (§9.12a, Track A) — production metadata, not player counts; not subject to §2's backfill constraint since it's fixed historical fact |
| `steam_release_cohort` | id, app_id, discovered_at, tracking_window_end | Populated by `IStoreService/GetAppList` with `if_modified_since` (§9.12a, Track B) — every new/updated release enters here and gets lifecycle-tracked in `viewership_snapshots`-equivalent Steam player-count polling, hits and flops alike |
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

The viewership-flat-or-growing half of the original definition is now built (`viewership_check`): official-broadcast Twitch data first, falling back to the Kaggle category-wide import (floor 2016, `confidence=proxy_estimate`) where Twitch has no coverage; `None` — not a silent pass — where the qualifying window predates both. It is informational only, not a gate, precisely because the fallback source is a game-fandom signal, not an esports-specific one (§4) — a "declining" result can't yet distinguish a cooling competitive scene from a cooling general audience. **`None` means unevaluated, not stable — do not treat a title's absence from a "declining" list as evidence it isn't.** Because tier-inflation (above) pushes most classic titles' qualifying windows to 2001–2014, well before the 2016 floor, they land in `None` far more often than newer titles do — so any comparison across titles that doesn't account for this will systematically read the classics as fine by default, which is an artifact of coverage, not a finding. This exact misreading has already happened once, in discussion rather than in code; guard against it in any generated summary or chart, not just in the underlying computation. Full findings, per-title reasoning, and two real data-quality bugs the reconciliation process surfaced (an HTML-comment leak corrupting `tournaments.tier`, and letter-tier wikis — including VALORANT — silently returning no milestone at all before the fix) live in `milestone_reconciliation.md`, not duplicated here.

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
| Reddit access | Community signals, subreddit overlap | Unconfirmed — see note | Standard Data API use for research is a stated policy violation; requires applying through Reddit For Researchers instead. Eligibility for a non-academically-affiliated project is unconfirmed. Do not build against the standard API for this use case regardless of what the free tier technically permits. |
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

**`config/channels.yaml` is not just the primary org channel — co-streamers are the harder and more important part.** Major tournaments routinely draw more combined viewership on co-streams than on the primary broadcast; treating co-streams as general content understates esports engagement specifically for the titles that co-stream most, which biases §12's official-broadcast-share metric in a non-random way. Whether a co-streamer was formally authorized by the publisher doesn't change whether their viewers are engaging with esports content rather than general game content, and it's not a question this research needs answered — so `broadcast_tier` doesn't distinguish authorized from unauthorized, only tournament-specific from general.

**Detection requires three conditions together, not a single fuzzy match:**

1. **Same title.** The stream's `title_id` must equal the candidate tournament's `title_id`. Temporal overlap with *any* running tournament proves nothing on its own — a CS2 stream live during a concurrent LoL tournament must not be tagged as costreaming it.
2. **Temporal window.** `captured_at` falls within that tournament's `start_date`/`end_date`. Multiple qualifying tournaments for the same title can be running at once (parallel regional splits); match against any one of them.
3. **Alias match, word-boundary aware.** The stream's title or tags contain one of that tournament's `tournament_aliases`, matched with word boundaries (e.g. `\bmsi\b`), not naive substring search — a plain substring check would false-positive on an alias appearing inside an unrelated word or an unrelated use of the same short string.

Applies only to streams captured at tier-1 or tier-2 detail (§9.1) — tier-3 streams never had title or tags retained, so they are structurally outside this check, not a gap in it. No manual research and no human confirmation step — every match lands as `confidence=proxy_estimate` and is usable as-is. This will still misclassify some streams in both directions even with all three conditions satisfied (a streamer reacting to highlights without showing the live feed can still match on text) — an accepted, already-priced-in trade for zero ongoing labor, not a new gap to close. Any published share number built on it should be described as detected/approximate rather than authoritative. `primary_official` is still the one thing seeded manually, once per title — that list is small and essentially static.

**Separate, currently undesigned axis: individual creator vs. media-org channel.** A channel_id simulcasting several different titles' official tournaments (a media network) is a different phenomenon from one creator crossing over, and `broadcast_tier` doesn't distinguish them — flagged in `creator_crossover.ipynb`'s own caveats, not yet resolved. Track as its own open item rather than folding into this one.

- **Default cadence:** hourly, for tracked titles and platform totals. The research questions resolve at monthly and yearly granularity, so hourly loses little.
- **Event mode:** manually-triggered 5–15 minute polling for specific titles during specific broadcast windows, where an accurate peak-viewer figure matters.
- **Cost:** free on a public repo; on a private repo the 2,000 free Actions minutes/month comfortably cover hourly polling, with a few dollars of overage at heavy event-mode use.
- **Bonus property:** because raw snapshots are committed to git, the collection history is automatically versioned, backed up off-machine, and independently auditable. This is a large part of why this pattern is preferred over a VPS.

### 9.2 Liquipedia connector (on-demand)
Liquipedia operates two separate APIs, confirmed directly from their API Terms of Use: **LPDB**, the structured tournament/match/prize-pool endpoint, requires an approved request and is not self-service — their own site currently lists even the paid tiers as unavailable, so this isn't a dependency to build around. Separately, Liquipedia provides free, unauthenticated access to the same underlying content through the **standard MediaWiki API** — no registration, just a rate limit (1 request/2s generally, 1 request/30s for `action=parse`) and a descriptive User-Agent identifying the project and a contact address.

Build against the MediaWiki API: fetch each tournament page's wikitext and parse the "infobox" template parameters (date range, prize pool, tier, region) rather than querying LPDB directly — `mwparserfromhell` (Python) is built for exactly this. More parsing work than a clean structured endpoint, but zero access friction and officially sanctioned. Cache responses locally and re-request only what's missing or stale; historical tournament data doesn't change on a clock. If an LPDB request is later approved, it's a straightforward swap to a cleaner source for the same table — nothing else should be designed to depend on that outcome.

**Tier conventions are not uniform across game wikis — confirmed, and resolved for the known cases.** Tekken, Street Fighter, Mortal Kombat and Guilty Gear share Liquipedia's "fighters" wiki; the shared-wiki tournament-discovery issue (not a tier-convention issue as first suspected) was fixed by intersecting discovery against each title's verified per-game category. A separate, second bug — HTML rationale comments leaking into the raw tier value — additionally corrected several hundred tier readings for these same titles once found. Full detail in `milestone_reconciliation.md`. Whether fighting games turn out to organize around independent majors rather than publisher-run tiers, as originally hypothesized here, remains a live and separate question from the parsing bugs — not yet resolved either way.

### 9.3 Esports Charts connector — automated access confirmed blocked, not pursued (2026-09-09)

Event and peak viewership per title was the plan. **Checked directly before building anything against it, per this project's own discipline (§9.12's SteamDB check, §9.13a's planned Discord check)**: `escharts.com/robots.txt`, its terms-of-use page, and its plain homepage all return HTTP 403 behind an active Cloudflare bot-challenge page, from a plain, honestly-identified request (this project's real User-Agent, no spoofing). Not a robots.txt-specific quirk — confirmed site-wide. This is a stronger, more direct signal than a written no-scraping clause: the site's own infrastructure is actively rejecting non-browser clients before any request-level judgment call even comes up. No workaround was attempted (headless browser, CAPTCHA-solving, etc.) — that would be circumventing an active technical anti-bot measure, the same category of thing already ruled out for SullyGnome and SteamDB (§3, §9.12). **Not pursued. This project has browsed the site manually in the past; that does not extend to automated access, which is a new use this checks and rejects, not a continuation of an already-cleared one.**

Consequence for the championship-concentration work (brief H3, see §9.3a below): the within-title share and cross-title concentration/power-law analyses that depended on Esports Charts' historical peak-viewer data cannot be built as originally specified. `tournaments.tier`/`prize_pool`/dates (already in the database, Liquipedia-sourced) remain fully available and are what §9.3a's championship-window definition is built on; only the peak-VIEWERSHIP figure for each identified window is blocked, not the window-identification step itself.

**Alternative landing zone (both this section and §9.1):** the scheduled job could write directly to hosted Postgres (Supabase free tier) instead of committing files. Free-tier projects pause after a week of inactivity, which is a non-issue given hourly writes. This buys remote queryability at the cost of an external dependency and the loss of git's automatic versioning of raw data. Recommend git-scraping as the default; revisit only if multi-device access becomes necessary.

### 9.3a Championship windows — defined and built (2026-09-08); the notebook depending on them is paused

`analysis/metrics.py:get_championship_windows` — for each (title, calendar year), the tier-1 tournament with the highest non-NULL `prize_pool`, i.e. that title-year's "world championship window." Deliberately objective (no name-matching against "Worlds"/"TI"/etc., which varies per title), tier-1 only (not tier-1-or-2 the way `get_success_milestone`'s default is), and reuses `_normalize_tier`/year-from-`start_date` exactly as `get_success_milestone` already does. A title-year with no tier-1 tournament, or where every tier-1 tournament that year has a NULL prize_pool, correctly gets no window rather than a guessed one. Ties (equal prize_pool) broken by earliest `start_date`, then `liquipedia_page`, for determinism.

Run against the real database (2026-09-08): 248 windows across all 23 tracked titles, 2000-2028. Surfaced the generational-continuity gap (§19) concretely, not just abstractly: `counter_strike` spans the full 2000-2028 range (its entire franchise lineage, 1.6 through CS2), while `tekken`/`mortal_kombat`/`street_fighter` only cover 2-4 years (their current generation only) — the exact inconsistency §19 already names, now visible as a real difference in how many data points each title contributes to any year-over-year concentration analysis.

`analysis/metrics.py:get_concentration` was also built alongside this (HHI + top-3 share over a set of raw values, not pre-computed shares — closes the gap that module's own docstring already named as planned-but-not-built).

**The notebook itself (`notebooks/championship_concentration.ipynb`) is paused, not built**, blocked on this section's Esports Charts finding — the within-title share, cross-title HHI/top-3, and power-law-vs-log-normal fit all need a peak-viewership figure per championship window that has no confirmed source yet.

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

### 9.6a Own-collector monthly rollup (extends 9.6, ongoing)
Kaggle's coverage ends where it ends; the project's own collection continues past it. `analysis/rollup_category_monthly.py` computes, per title per month, from data already being collected — `category_totals_snapshots` for the total, `viewership_snapshots` filtered to `broadcast_tier IN (primary_official, detected_costream)` for the esports-specific portion — and upserts a row into `monthly_category_history` with `source=own_collector`. Hours-watched is estimated by integrating `viewer_count` over the polling interval within the month, matching the shape of Kaggle's own metric.

**Backfill-aware, not current-month-only.** On each run, the script finds the latest `source=own_collector` checkpoint per title and computes every missing month between that point and now, not just the current one — this is what makes it safe to run infrequently. Raw collection never has gaps (it runs independently of local engagement), so a late run produces an identical historical record to an on-time one; there is no cost to a long gap between runs for this specific table.

This produces something Kaggle structurally cannot: `esports_hours_watched` and `esports_share_pct` alongside the total, every month, going forward — Kaggle has no broadcast-tier information and never will, so those columns are permanently `NULL` on `source=kaggle_import` rows and populated only from here on. The current in-progress month is marked `is_partial_month=true` so an incomplete month's lower total is never mistaken for decline. Idempotent — safe to re-run mid-month as more data lands, upserting rather than duplicating that month's row.

Trigger: local refresh routine is sufficient for this table specifically, since backfilling closes any gap without loss. Contrast with §9.6b — the similarity and crossover trackers lose real information (temporal resolution) from an irregular trigger, even with backfill logic, and are scheduled instead.

### 9.6b Scheduling niche_similarity_history and creator_crossover_history
Unlike the monthly rollup, these benefit from *regular* checkpoints, not just eventually-complete ones — "has this stabilized" is read off a curve, and a sparse, irregular curve (however backfilled) is a worse curve. Scheduled weekly via GitHub Actions rather than tied to local refresh.

Mechanically different from §9.1's live polling: this job has no external API calls, so its work is entirely against already-collected data — but the runner is ephemeral and has no access to a local `research.db` (gitignored, laptop-only). Each run: check out the repo, rebuild a database from the committed raw snapshot files under `data/raw/` via the existing ETL, run the similarity/crossover computations against that freshly-built copy, and commit the resulting history rows back to the repo via the same git-scraping pattern already used for Twitch snapshots. The next local refresh picks these up alongside everything else. Negligible additional cost against the Actions-minutes budget already spent on hourly polling (§17).

### 9.7 YouTube live collector (scheduled — mirrors §9.1)
Auth is a plain API key against a Google Cloud project — no OAuth needed for public reads. The constraint is quota, not access, and it's sharply asymmetric: `videos.list` (viewer count for known video IDs) costs 1 unit and batches up to 50 IDs per call; `search.list` (the only way to discover which video a channel is *currently* live on) costs 100 units against a 10,000/day default — roughly 100 discovery checks a day, full stop.

That rules out continuous discovery polling. Baseline: check the official-channel list for live status a few times a day. Event mode, same concept as §9.1: bump discovery to a tight cadence for the channels relevant to a specific tournament during its known window (`tournaments.start_date`/`end_date`), concentrating the expensive call where it matters most. Once a live video ID is known, monitor its viewer count with the cheap batched call at Twitch-equivalent cadence.

Feeds the existing `channels` (`platform=youtube`) and `viewership_snapshots` tables — no schema change, since `platform` was already there for this. Real limitation, not a workaround: no affordable way to enumerate every live stream under a game the way `Get Streams` does, so YouTube populates the official-channel tier only, never `category_totals_snapshots` — no YouTube-side denominator. Optional, never required: if a tournament's YouTube stream URL is published in advance, noting the video ID directly skips a search call for that event — a free efficiency gain when convenient, not a dependency.

### 9.8 Chinese platforms (Douyu, Huya, Bilibili) — investigated, not pursued
Douyu runs an official Open Platform, but its developer agreement gates access behind "relevant legal qualifications" — in practice a registered business entity, not an individual researcher. What's reachable without that is unofficial, reverse-engineered endpoints built from captured mobile-app traffic — the same category of workaround already declined for SullyGnome and unofficial Liquipedia wrappers (§3), and not more defensible here for being harder to reach legitimately.

Access aside, these platforms report a Heat Index, not a viewer count — a composite blending stream duration, traffic and virtual gifting, with no fixed conversion to actual viewers. Esports Charts, tracking dozens of platforms professionally, state that a directly comparable number is technically out of reach even for them.

Realistic use of this market's data: cite published aggregate figures from firms tracking it professionally (Niko Partners, Streams Charts) as occasional `source=secondary_report` data points, not a connector. Not an open question — revisit only if a legitimate access route appears, not by default the next time China comes up.

### 9.9 Kick live collector (scheduled — mirrors §9.1, access confirmed 2026-09-07)
Kick operates an official public API (`docs.kick.com`), OAuth-based, with livestream and category endpoints including live viewer counts — a genuine access path, not a Douyu/TikTok situation. Worth adding given real creator migration from Twitch toward Kick — a platform-level version of Limitation 1 (is the audience actually shared), one level up from title-level. Specific rate limits and quota structure not yet confirmed — check current docs before designing polling cadence, same discipline as every other connector here, not an assumption to carry over from Twitch's or YouTube's limits.

### 9.10 TikTok — no viable path for live viewership, a separate uncertain path for video content
Confirmed: TikTok has no public API for live-stream viewer counts, chat, or gifts. Every source that provides this is built on reverse-engineering TikTok's internal WebCast protocol — the same category of access already declined for SullyGnome and the Chinese platforms (§3, §9.8); not more defensible here for being a larger, more mainstream platform. Not pursued for live data.

A separate, legitimate door exists but answers a different question: TikTok's Research API, restricted to vetted approved researchers (same structure as Reddit's program, §8), covers public video content — not live-stream data. Could support a distinct future question (are esports/gaming clips gaining or losing traction on TikTok over time), not viewership share. Same eligibility uncertainty as Reddit and Liquipedia LPDB; not pursued now.

### 9.11 SOOP (formerly AfreecaTV) — investigated, not pursued, but one finding feeds directly into H2
No developer API exists; available data is third-party paid analytics (Streams Charts), not a connector target. Not pursued, same verdict as §9.8.

One fact surfaced while checking is directly relevant to the StarCraft II case in the brief's H2: Twitch shut down entirely in South Korea in February 2024, and AfreecaTV rebranded to SOOP that June partly in response. StarCraft II's audience has always skewed heavily Korean — see the brief's H2 refinement for the resulting confound on its measured Twitch decline, now backed by confirmed scale (SOOP ~1.2B hours/year, Twitch was running ~100M hours/month of Korean content pre-exit) and a directly analogous, precisely-dated precedent (LCK's YouTube share falling 46.5%→25.5% in one year as viewers moved to SOOP/CHZZK).

### 9.12 Steam — current players confirmed (already scoped); no historical backfill exists, urgency matches §2
Valve's official API (`ISteamUserStats/GetNumberOfCurrentPlayers`) is confirmed current-only, no historical parameter — same irreplaceable-if-missed property as every other live source here. Covers CS2, Dota 2, PUBG, Apex, Age of Empires; misses Riot titles and everything mobile entirely.

**No legitimate historical backfill exists — checked both realistic candidates, both ruled out (2026-09-07).** SteamDB explicitly prohibits this: their own FAQ states plainly that they do not allow scraping/crawling, with an explicit warning that automated access risks a ban. Not inferred — their stated position, in their own words, the same category as SullyGnome's request and given the same answer: not pursued. SteamCharts.com's own displayed data is limited to roughly a 30-day window in practice, not the multi-year depth an earlier version of this document claimed based on a third-party scraper's marketing description rather than a direct check of the site itself — that was a real error, corrected here. Neither source backfills.

**Consequence: the current-player collector carries the same urgency as §2's core constraint, not "nice to have when convenient."** With no historical path available from any source, every day this isn't running is Steam player-count history permanently lost, exactly like the Twitch collector's Phase 1 framing. Should not be left as a lower-priority addition behind Kick or Discord.

**No regional breakdown at the game level.** Steam publishes country-level data for its overall user base and region-specific storefront data (top-sellers, pricing) — neither is a per-game concurrent-player breakdown by region. Not available from any source checked.

### 9.12a Steam production patterns (indie/core, lifecycle, VR) — why this exists, then how it works
**This section is missing from every prior version of this document, not because it was rejected, but because it was designed entirely in conversation and never written down — the gap Claude Code correctly flagged (2026-09-07).**

**Why it belongs here.** The brief's founding premise (§1) is that esports is one instance of digital fandom, not the whole subject — "certain dynamics are likely to be consistent across entertainment types." Everything built through Phase 2 tests that claim only inside esports. Steam production and playtime data is the first real chance to test it somewhere genuinely different, on three specific threads already open elsewhere in this project:

- **H3's fragmentation/concentration pairing, tested on both sides at once.** The Twitch work already found attention concentrating hard — esports' share of top-200 nearly halved, Just Chatting and GTA V driving most of the platform's growth. This section asks the supply-side complement: is game *production* simultaneously fragmenting — more indie titles, more studios, a longer tail — even as consumption concentrates? That pairing is H3's actual claim; so far it's only been tested from the attention side.
- **H2's mechanism, tested outside esports entirely.** Comparing indie vs. core lifecycle shape (a sharp launch spike that fades, versus a sustained plateau backed by ongoing content investment) is a second, independent test of "does sustained investment predict durability" — different dataset, different genre space, from anything else in this project.
- **Post 1's emergence framing, generalized.** Post 1 found more esports reaching success, at smaller individual scale, over time. Whether all game production shows the same shape — rising volume of attempts, few reaching major scale — is the same question asked one level up, not a new one invented for Steam specifically.

Genre-composition questions (roguelites and similar) are more exploratory and not tied to a named hypothesis — useful for characterizing what indie production actually looks like, in the spirit of staying curious rather than only confirming.

**How it works.** Two tracks sharing one underlying mechanism, `IStoreService/GetAppList` — confirmed working with an ordinary Web API key (no publisher account needed), confirmed to default to games-only (`include_dlc`/`include_software`/`include_videos`/`include_hardware` all default false), and confirmed to support `if_modified_since` for incremental catch-up. The old `ISteamApps/GetAppList/v2` is genuinely deprecated per Valve's own docs; this is the sanctioned replacement, not a workaround.

- **Track A — one-time production backfill**, analogous to the Kaggle import. No urgency (release metadata is a fixed historical fact, unlike live player counts — it doesn't decay the way everything else in this document does). Full historical sweep via `GetAppList`, `appdetails` pulled once per app for genre tags (including whether "Indie" appears — note `genres` is a multi-valued list, not a taxonomy; a title can carry both "Indie" and "Action" simultaneously, and there is no positive "AAA" tag, only the absence of "Indie"), release date, developer/publisher, and `categories` (VR-support flag — see open item below). Stored permanently in `steam_release_history`.
- **Track B — go-forward discovery**, feeding the release-cohort lifecycle tracking: the same `GetAppList` call, run periodically with `if_modified_since` set to the last check, picking up new and updated releases. Each new title enters `steam_release_cohort` and gets `GetNumberOfCurrentPlayers` polled daily for ~90 days, tapering to weekly out to about a year — capturing full lifecycle shape for hits *and* flops alike, which is what makes an indie-vs-core comparison meaningful rather than survivorship-biased.

**Two things confirmed not yet verified, do not build against either until checked directly:**
- Whether Steam's `categories` field actually carries a VR-support flag — check by pulling `appdetails` for a known VR title (Half-Life: Alyx) and reading the real response, not by trusting documentation.
- Whether `GetTagList`/`GetMostPopularTags` (same `IStoreService` interface) can answer "which games carry tag X" — the possible sanctioned path to genre-level tags like "Roguelite" that are confirmed absent from `appdetails.genres`. Unconfirmed either way.

### 9.13 Discord — community size confirmed available; member overlap still blocked
Two token-free, official public endpoints, not scraping: `/invites/{code}?with_counts=true` (approximate member and online counts for any public server with a known invite link, no server cooperation needed beyond the invite existing) and `/guilds/{id}/widget.json` (richer — voice channels, a sample of online members — but only if the server owner has explicitly enabled it; most haven't). Neither exposes message content or a full member list.

Worth adding as a new, cheap signal: community size (member count, current online count) per tracked title's official Discord, as a fandom-scale metric independent of viewership. Does not revive the member-overlap approach considered and set aside earlier in this project — testing actual overlap between two communities still requires bot membership in both servers, which neither endpoint provides. Size, not overlap.

### 9.13a Discord integration plan — shelved 2026-09-08, not built

Designed in conversation, not started. Recorded here per §15's documentation workflow so the design isn't lost between sessions, the same reason §9.12a exists.

**Verify first, before building anything** — the "confirmed available" framing above hasn't actually been re-checked live in this build pass, and this project's own discipline (see §9.12a's Steam verification, or the SteamDB FAQ check in §9.12) is to confirm a claim like that directly rather than carry it forward untested:
1. `GET /invites/{code}?with_counts=true` — confirm it genuinely returns `approximate_member_count`/`approximate_presence_count` with no token, against a real public invite.
2. `GET /guilds/{id}/widget.json` — confirm it fails cleanly (not some other failure mode) when a server hasn't opted the widget in, since most won't have.
3. Check Discord's own current API Terms of Service for these two specific endpoints directly, the same way SteamDB's FAQ was checked directly rather than assumed.

**The real bootstrapping problem, harder than YouTube's channel curation (§9.7).** This needs a stable Discord invite code (or guild ID) per tracked title, and unlike a Steam AppID there's no clean official lookup for "the correct Discord server for game X" — invite links can be non-official, fan-run, or expired, and some titles (Riot's especially) may route community discussion through their own forums more than Discord, with no single obvious canonical server. Has to be human-curated per title, individually verified — the same draft-then-curate pattern `notebooks/official_channel_candidates.ipynb`/`config/channels_youtube.yaml` already established, not something to guess reliable invite codes for.

**Schema**: a new table, NOT a reuse of `community_signals` (§6) — checked directly, that table is already Reddit-shaped specifically (`subreddit_type`, `subscriber_count`), not platform-general despite its generic name. Proposed: `discord_community_snapshots` (`title_id, captured_at, member_count, online_count, source, confidence`) — one table per genuinely distinct data source, the same discipline `steam_player_counts`/`monthly_category_history` already follow rather than overloading a table across conceptually different sources.

**Architecture**, mirroring the YouTube/Steam pattern exactly (§9.7, §9.12): `config/discord_servers.yaml` (separate file, empty until curated — same bootstrap shape as `config/channels_youtube.yaml`), `collectors/discord_poll.py` (no OAuth/bot token needed for these two specific endpoints, plain REST via httpx, no new dependency), `.github/workflows/discord_poll.yml`.

**Cadence — the one place this genuinely differs from every other live collector here.** Member/online counts change slowly compared to live viewership, so hourly polling isn't needed — daily is almost certainly sufficient. Still technically unbackfillable (no historical endpoint), so it still belongs in the "one rule" family (CLAUDE.md) and should run on a schedule rather than on-demand like Track A's catalog backfill, but the actual urgency of a missed day is much lower than Twitch/YouTube/Steam's live numbers.

### 9.14 CPI deflator reference table — for `docs/counter_strike_lifecycle_brief.md` §5d, not built

Designed 2026-09-09, recorded per §15 the same way §9.12a/§9.13a were before being built. Needed so tournament prize-pool trends spanning an 11+ year window (2016–2026+) can be read in real, inflation-adjusted terms rather than nominal USD, which overstates growth purely from inflation over that span.

**Source**: US BLS CPI-U (Consumer Price Index, All Urban Consumers, all items) — a public government statistical release, not a competitor's proprietary tracked-content site. A different category of source from the ones CLAUDE.md's ethical non-goals section names (SullyGnome, SteamDB, Esports Charts) — no scraping-prohibition or ToS concern applies here the way it does there.

**Shape**: `data/reference/cpi_deflator.csv` (or similar), one row per year, from BLS's public CPI-U annual-average series. NOT a scheduled "one rule" collector — a small, static, occasionally-refreshed reference table, the same category as `collectors/kaggle_import.py`'s CSV (§9.6): fetched/updated by hand on some infrequent cadence (annually, once the prior year's average is final), not polled.

**Base year**: re-based to the most recently *fully completed* calendar year each time this is refreshed (2025 as of this writing) — not pinned to a fixed distant base year — so a reader always sees figures in approximately today's money rather than an arbitrary historical year's.

**Consumer**: only `docs/counter_strike_lifecycle_brief.md`'s prize-pool-by-year and hours-per-real-dollar intensity metrics (§5c/§5d there) as of this writing — but shaped as a general-purpose reference table (year → deflator), not CS-specific, so any other title's nominal-dollar series can reuse it later without a redesign.

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
- **General convention:** any metric whose reliability depends on accumulating sample size over time (niche similarity, creator-crossover enrichment) should append its result to a `_history` table (§6) on each run, not only return a live value — the question "has this stabilized yet" is unanswerable from a single run, however carefully caveated.
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
- **Documentation workflow (added 2026-09-07):** this PRD and the research brief are edited by Claude Code directly, in this repo, the same as code. They are not maintained anywhere else and then copied in. If a chat session describes a design decision, a data source, or a research connection that isn't reflected here, treat that as this document being incomplete, not as a different, ungrounded request — ask for the missing content rather than guessing, but don't assume the absence means the work doesn't belong in this project.

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

Reviewed 2026-09-09 against live repo/DB state (not just re-read) — several items below turned out stale; corrected in place rather than left for the next pass, per §15.

**Priority 1 — blocked on the same unfinished prerequisite, not urgent until it's done:**

- **`config/channels.yaml` curation is still empty** (0 `is_official_broadcast`/`broadcast_tier='official'` rows in `research.db`, confirmed live) — this is the shared blocker behind the next two items, not a separate one:
  - **Individual creator vs. media-org channel** — `broadcast_tier` doesn't distinguish a single creator crossing over from a network channel simulcasting several titles' tournaments. Undesigned; affects how much to trust `creator_crossover.ipynb`'s results once channels are curated and official-org channels start appearing in that analysis.
  - **Whether `milestone_year` should eventually gate on the viewership clause** — currently informational only, because the viewership signal is game-fandom (category-wide), not esports-specific. Literally cannot be revisited until official-broadcast-tier Twitch history exists to build an esports-specific check against, independent of how much calendar time passes.

**Priority 2 — genuinely open, no urgency signal:**

- **IGDB connector** — V1 or deferred past the Post 2 deadline. No work started either way.
- **Event-mode trigger list** — which broadcasts warrant 5–15 minute polling, and who maintains that calendar.
- **Chat message volume as an interactivity metric** — a genuinely distinct signal from viewer count (active participation vs. passive attention), directly relevant to the digital-fandom framing. Not a Phase 1 addition: Twitch doesn't expose chat volume via `Get Streams`, so it needs a persistent connection (IRC or EventSub) rather than a periodic poll — a new component, not a new field. Naturally scoped to the official-channel list only, same as the rest of §9.1's curated capture. Worth its own phase once the core collector is stable.
- **Reddit access is blocked pending Reddit For Researchers approval** (§8) — do not build the subreddit-overlap notebook (multi-homing test, Limitation 1) or any community-signals connector against the standard API. Apply and wait; treat as a real gate, not a formality. If eligibility fails, Limitation 1 (multi-homing) has no remaining identified path and should be documented as unresolved rather than worked around.

**Resolved or superseded since last written — kept here (struck through) rather than deleted, so the reasoning stays visible:**

- ~~**Liquipedia terms** — confirm current API terms, rate limits and attribution requirements before building against it.~~ Resolved: MediaWiki API confirmed free/open (§8, §9.2); LPDB requires approval and isn't assumed available.
- ~~**Repo visibility** (§11) — public vs. private, recommend deciding before the first push.~~ Resolved by action, not a memo: confirmed live 2026-09-09, the repo has been public (`gh repo view` → `isPrivate: false`) throughout, several weeks and many pushes past "before the first push."
- ~~**Git-scraping vs. Supabase landing zone.~~ Resolved by consistent implementation: every collector (Twitch, YouTube, Steam ×3) uses the git-scraping pattern with no exceptions; Supabase was never pursued. Revisit only if remote (non-git) access becomes an actual requirement, not proactively.
- ~~**Esports Charts enterprise** — first confirm what's actually available, then whether demographic/geographic data justifies cost.~~ Superseded, not answered: §9.3's live check (2026-09-08/09) found their *public* site returns a site-wide 403 behind a Cloudflare bot challenge for automated access — confirmed blocking, not merely rate-limited or robots.txt-restricted. Enterprise/paid-tier terms were never separately checked and remain genuinely unknown, but the question as originally framed (is public access usable) is answered in the negative; pursuing paid access would be a new, larger decision (cost, and re-clearing the same ethical bar §9.3 applied to public access) rather than a continuation of this item.
- ~~**Similarity/crossover tracker scheduling** — moved from "align with local refresh" to a weekly scheduled Action (§9.6b) after review.~~ Correction, 2026-09-09: this item previously read as resolved, but the design decision and the implementation are two different things — §9.6b's weekly Action was designed but **never built**; no workflow file references `creator_crossover` or `niche_similarity`, and `niche_similarity_history`/`creator_crossover_history` are still populated only by running the notebooks locally/manually. Reopening this as a build task, not a design question — the design in §9.6b stands, it just doesn't exist yet.
- ~~**Shared-wiki contamination sweep.**~~ Swept 2026-09-09, all clean: the other 18 titles (beyond the fighting-game/AoE fixes already made) had never been checked for hosting more than one franchise on their wiki. Checked live via two independent signals — each wiki's own `siteinfo` sitename (all 18 report a clean, single-game name, unlike the "Liquipedia Fighting Games Wiki" umbrella) and an actual discovery run's sampled page titles (no cross-game bleed-through in any of the 18). Documented in `config/titles.yaml`'s header comment and `docs/system_reference.md` §5; re-check before adding any new title to a wiki that already hosts a tracked one.
- ~~**Title generational continuity — no stated policy.**~~ Policy decided 2026-09-09: align every franchise with how `counter_strike` is already tracked — one continuous entity across engine/version changes, at the Liquipedia/tournament-data layer. Implemented by extending `collectors/liquipedia.py`'s `liquipedia_category` filter to accept a list (unioned before intersecting with tier categories) and setting `tekken`/`street_fighter`/`mortal_kombat`/`guilty_gear` in `config/titles.yaml` to the live-verified list of every generation's own category on the shared `fighters` wiki (`Street Fighter X Tekken Competitions` deliberately excluded as a genuine crossover product, not a version — flagged as a judgment call, same as every other one in that file). **Explicitly does NOT extend to Twitch polling** — Twitch's category IDs are genuinely separate per generation (unlike Counter-Strike's one category, renamed in place across CS:GO→CS2), and historical viewership under a retired category has no backfill path; `twitch_category_id` for these four titles necessarily still tracks the current generation only. A re-crawl to backfill the newly-included generations' tournament history was started the same day — see `docs/system_reference.md` §5 for whether it had finished by the time that document was last regenerated.
