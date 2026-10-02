# Liquipedia LPDB Transition Plan

**Status: Phase 0 probe complete, Phase 1 built and live, Phase 2
reconciliation started with real cross-source data (all 2026-09-30).**
LPDB access was formally approved 2026-09-30; `LIQUIPEDIA_API_KEY` and
`LIQUIPEDIA_CONTACT_EMAIL` are in `.env`. A 7-request exploratory probe
against the live v3 API confirmed the access mechanics and answered most of
Phase 0's open questions with real data, not assumptions.
`collectors/liquipedia_lpdb.py` is built and has pulled real data for
`league_of_legends`, `dota2`, `counter_strike`, and (incompletely —
see Phase 2 below) `starcraft2`; `etl/forecast_event_windows.py` is built on
top of it. A first real reconciliation pass against those four titles'
`tournaments` data is written up under Phase 2. 19 of 23 titles still need
their first LPDB pull; `collectors/liquipedia_lpdb.py --status` reports the
live rolling-window request budget before starting more.
**Phase 4 started 2026-10-01**: player/roster data
(`collectors/liquipedia_lpdb_players.py`) and broadcast/channel data
(`collectors/liquipedia_lpdb_broadcasts.py`, `scripts/
build_channel_candidates_from_lpdb.py`) are built; `scripts/
lpdb_overnight_sync.py` is running unattended (23h window, started
2026-09-30 20:34 UTC) to finish the remaining 19 titles' tournament pulls,
pull player data, and sample broadcast data for already-ready titles —
see `logs/lpdb_overnight_sync.log` (gitignored) for live progress.
Drafted 2026-09-16, probed 2026-09-30, connector built 2026-09-30, Phase 4
started 2026-10-01.

Liquipedia has also directly advised against continuing to rely on the
standard MediaWiki API long-term — quoted risk: "timeouts and bans" — which
is the practical urgency behind this plan, on top of the data-quality
benefits below.

## Attribution and retention — confirmed vs. still open

Liquipedia's project lead has stated that final attribution via the blogs
(this project's Boudica-style reports/presentations, which already credit
Liquipedia in their Sources sections) is sufficient. That most likely covers
report/presentation citation, which is already standard practice here.

**Not yet explicitly confirmed, worth a direct follow-up before this becomes
load-bearing:**
- Whether the same attribution standard covers **committing derived
  tournament data to this project's public GitHub repo**
  (`data/reference/tournaments.jsonl` and friends) — a materially different
  thing from a blog citation, since it's redistributing structured, extracted
  data indefinitely in machine-readable form, not crediting a source in prose.
- Whether there's any **retention limit** on LPDB-sourced data specifically —
  CLAUDE.md already flags "retention clauses" as a thing to respect,
  separately from attribution, and this hasn't been asked about directly.

Resolve both before Phase 3 (cutover) commits LPDB-derived data to the
public reference-data export.

## Phase 0 — Confirm terms before writing any code

- [x] **LPDB's actual access mechanics** — confirmed live, not from docs
      alone: base URL `https://api.liquipedia.net/api/v3/`; auth via
      `Authorization: Apikey <key>` header (not a query param, not
      `X-API-Key` as some third-party summaries claim); required `wiki`
      query param (multi-wiki via `|`); GET-only; gzip required. Query
      syntax is SQL-like — `limit` (default 20, max 1000), `offset`,
      `conditions` (`[[field::value]]`, operators `::`/`::!`/`::<`/`::>`,
      AND/OR/parentheses, date functions), `query` (field projection,
      aggregate functions), `order`, `groupby`. Response shape:
      `{"result": [...], "error": [...], "warning": [...]}`. Rate limit
      confirmed at 60 req/hour on the free tier — the probe used 7 of the
      60, all HTTP 200, zero errors or warnings. The open-source
      `liquipydia` Python client (PyPI) wraps this correctly and already
      matches this project's `LIQUIPEDIA_API_KEY` env var naming.
- [ ] The attribution/retention questions above — still genuinely open,
      not resolved by the probe (a technical test doesn't answer a legal
      question). Resolve directly with Liquipedia before Phase 3.
- [x] **Grassroots tiers (B/C-Tier) ARE reachable** — `[[liquipediatier::3]]
      OR [[liquipediatier::4]]` against `wiki=counterstrike` returned 5 real
      results (a mix of tier-3 qualifiers and a tier-4 regional league).
      The risk this checkbox existed to catch — grassroots data staying
      stuck on direct MediaWiki access, with its ban risk — does not apply.
      Phase 4's "full grassroots crawl for all 23 titles" unlock is real,
      not aspirational, pending the same field-completeness checks Phase 2
      already calls for at tier-1/2.
- [x] **`{{TeamPrizePool}}`-style per-team payouts DO surface as clean
      structured fields** — the biggest known gap, and it closes. Tested
      against a genuinely completed tournament (StarLadder StarSeries Fall
      2026, ended 2026-09-20, $500,000 total prize pool): the `placement`
      resource returned real per-team `prizemoney` for every placement —
      1st $200,000, 2nd $130,000, 3rd $70,000, 4th $40,000, 5th-6th
      $20,000 each — plus a separate `individualprizemoney` (per-player)
      figure on every row. This is a structured field, not a wikitext
      template to parse. (First probe attempt accidentally queried a
      placeholder 2028 Major with no real data yet — sorting by
      `startdate DESC` surfaces *future* projected tournaments, not just
      completed ones; filter on `enddate` for historical work.)
- [x] **`liquipediatier` is a clean, uniform digit string** (`'1'`, `'3'`,
      confirmed via raw JSON type inspection, not print-formatting
      guesswork) on every wiki tested, including the fighters wiki — the
      per-wiki S-Tier/A-Tier-vs-Tier-1/Tier-2 *label* inconsistency that
      `_normalize_tier()` exists to handle does not appear to reach the
      API layer at all; LPDB seems to normalize it before returning data.
      `analysis/metrics.py`'s existing `tier in {"1", "2"}` string
      comparison needs no change either way, since the type matches.
      **Not yet confirmed**: whether `_normalize_tier()` becomes fully
      redundant, or still earns its keep for some edge case — needs a
      wider sample across more wikis before retiring it.
- [ ] **Currency is NOT an explicit field anywhere in the schema** — checked
      the full field list on both `tournament` and `placement` resources
      (real record dumps, not docs) and no field name contains "curr" in
      either. `prizepool`/`prizemoney` are bare numbers, presumably
      pre-normalized to USD per Liquipedia's own display convention, but
      that's an inference, not something the API states explicitly
      anywhere seen so far. **This means LPDB does not close the existing
      1,541-row currency-null gap the way the other fields do** — it
      sidesteps the inconsistency (no field to be null) rather than fixing
      it. If currency-aware analysis ever matters, this needs a different
      answer, not "wait for LPDB."
- [x] **Bonus finding, not originally scoped by this plan**: the `match`
      resource's `stream` field returns actual broadcast channel names
      directly (e.g. `{"twitch_en_1": "Fragbite", "twitch": "Fragbite"}`
      on a real Svenska Cupen 2026 match) — a potential structured
      alternative or supplement to this project's own manually-curated
      `config/channels.yaml` (currently 2 of 23 titles curated) and the
      `detected_costream` text-matching heuristic in
      `etl/classify_broadcast_tier.py`. Not evaluated further here — a
      real Phase 4 candidate worth its own scoping pass.
- [x] **The shared `fighters` wiki exposes a clean `game` sub-field**
      (`ggst`, `tokon`, `gbvsr` seen in a 5-record sample) that cleanly
      separates sub-games within the shared wiki — structurally a much
      more robust mechanism for the generational-continuity policy than
      the current MediaWiki category-name matching (`Tekken 8` vs.
      `Tekken 7`, the deliberate `Street Fighter X Tekken` exclusion).
      **Not yet confirmed**: the exact `game` code values for this
      project's four tracked titles specifically (tekken/street_fighter/
      mortal_kombat/guilty_gear) — the sample pulled didn't happen to
      include them. A short follow-up query, well within budget, would
      settle this before Phase 1 relies on it.

Raw probe request/response JSON (7 requests: tournament schema, placement
schema, grassroots-tier check, fighters-wiki schema, match schema, plus
the completed-tournament re-test) is not committed to the repo — it
includes a placeholder future tournament with no real meaning and isn't
durable reference material, just scratch verification. Re-running the
probe is cheap (well under the hourly budget) if these fields need
re-checking later.

## Phase 1 — Build the LPDB connector alongside the current one

- [x] `collectors/liquipedia_lpdb.py` built, same CLI shape as
      `collectors/liquipedia.py`, scoped by `config/titles.yaml`'s
      `liquipedia_wiki` field. Real run 2026-09-30: 39,140 rows across
      `league_of_legends`/`dota2`/`counter_strike`/`starcraft2` before
      hitting the per-run request cap (starcraft2's pull is incomplete —
      see Phase 2). 19 titles not yet pulled.
- [x] **Generational-continuity policy carried forward.** `GAME_CODES_BY_TITLE`
      in `collectors/liquipedia_lpdb.py` maps each of the 4 `fighters`-wiki
      titles to its real LPDB `game` codes, derived live via
      `groupby=game ASC` (2026-09-30, 118 distinct codes seen), not guessed.
      `sfxt` (Street Fighter X Tekken) deliberately excluded from
      `street_fighter`'s list, carrying forward the same crossover-exclusion
      judgment call. Not yet re-verified end-to-end against real fighting-game
      data (no fighting-game title has been pulled yet) — do this as part of
      finishing the remaining 19 titles.
- [x] New rows carry `source='liquipedia_lpdb'`, written into `tournaments_lpdb`
      — `tournaments`'s own `source='liquipedia'` rows are never touched.
- [x] Landed in a staging area: `tournaments_lpdb`, a fully separate table
      (not a source-flagged subset of `tournaments`, since that table's
      `UNIQUE (liquipedia_wiki, liquipedia_page)` constraint doesn't include
      `source` — see `etl/schema.sql`'s own comment on the table for why a
      shared table wasn't safe).
- [x] Rate-limit safety: `RequestBudget` enforces both a per-run cap and a
      **persisted, cross-run** rolling 60-minute request log
      (`data/cache/liquipedia_lpdb/request_log.json`, gitignored) — added
      2026-09-30 after noticing a per-run-only counter can't stop two runs
      minutes apart from together exceeding the real server-side limit.
      `--status` reports current usage and reset ETA with no API calls.

## Phase 2 — Reconciliation, before anything is trusted

Same shape as the Phase 2 reconciliation already run once on the original
build (which found 3 real bugs) — applied here to a source swap instead of
a first build. First real pass run 2026-09-30 against the 3 titles with a
complete LPDB pull (`league_of_legends`, `dota2`, `counter_strike` —
`starcraft2` excluded, see below) by joining `tournaments` and
`tournaments_lpdb` on `liquipedia_page`.

- [x] **Page-name format bug found before any of the below could even run**:
      `tournaments.liquipedia_page` stores spaces (`"ESL One/Cologne/2023"`);
      LPDB's own `pagename` field returns MediaWiki's real underscore
      convention (`"ESL_One/Cologne/2023"`). A naive join matched only ~2,700
      of counter_strike's ~19,400 pages (14%) until this was normalized —
      after normalizing underscores↔spaces, match rate is 99.9%+ for all
      three titles. **Not yet fixed in either collector** — anything that
      joins across the two tables (this reconciliation, a future Phase 3
      cutover, a future `series_key` regeneration against LPDB data) needs
      to normalize this first, or pick one convention and store it
      consistently going forward.
- [x] **Tier values**: LPDB's tier field is clean digit strings, confirmed —
      no `_normalize_tier()`-style per-wiki label handling needed on the
      LPDB side. Cross-checked against `tournaments`' own (only
      partially-normalized — `_normalize_tier()` in `analysis/metrics.py`
      handles S/A-Tier but was never extended to B/C-Tier) raw tier labels:
      99.7-100% agreement once B-Tier→3/C-Tier→4 mapped by hand for this
      check. Remaining "mismatches" are overwhelmingly LPDB returning an
      empty tier where `tournaments` had one (a small number of pages LPDB
      hasn't tier-tagged), not contradictory values — real semantic
      disagreement was ~1 row out of ~26,000 checked. **This directly fixes
      a real, currently-shipped gap**: `_normalize_tier()`'s missing B/C-Tier
      case means any current B/C-tier (grassroots) filtering on `tournaments`
      is working against inconsistently-labeled data today.
- [ ] **Prize pool `{{TeamPrizePool}}` coverage gap**: not yet re-checked —
      needs a `placement`-resource pull (not done for any title yet, see
      Phase 1's own docstring) to compare against `tournaments.prize_pool`'s
      known gap, not just the `tournament`-resource `prizepool` field
      already pulled.
- [x] **Currency: the field is still absent, but the practical risk this
      was flagging turned out much smaller than feared — UPDATED 2026-10-02,
      upgraded from inference to confirmed.** `tournaments_lpdb.currency`
      remains `NULL` on every row, by construction (no currency field exists
      anywhere in LPDB v3's schema) — that part hasn't changed. What changed:
      while migrating `mlbb_russia_deep_dive.ipynb`, cross-checked
      `tournaments_lpdb.prize_pool` against `tournaments.prize_pool`/
      `currency` for every non-USD MediaWiki-sourced row that also exists in
      the new table (dozens of matches across `age_of_empires_ii` alone, plus
      a real MLBB example) — the implied conversion rates are genuine,
      plausible, date-varying market exchange rates, not noise: CNY
      ~6.76-6.83/USD, KRW ~1,133-1,310/USD, EUR ~0.82-0.92/USD, GBP ~0.64/USD,
      and RUB ~82.7/USD for a real 2026 BetBoom Rise of Legends prize pool
      (₽9,000,000 in `tournaments` → $108,856.92 in `tournaments_lpdb`,
      implying almost exactly that rate). **`tournaments_lpdb.prize_pool`
      is genuinely pre-converted to USD by Liquipedia's own display
      convention** — this is now a confirmed cross-source finding, not an
      assumption, even though LPDB's own API never states it. `etl/schema.sql`'s
      comment on `tournaments_lpdb.currency` updated accordingly.
      **Practical consequence**: `prize_pool` can be treated as USD directly
      for new analysis built on `tournaments_lpdb`/`tournaments_lpdb_competitive`
      — the "silently loses non-USD flagging ability" risk this item
      originally flagged doesn't apply, because the values are already
      converted, not left in their original currency with the label
      stripped. The remaining real gap is narrower than first thought: no
      way to tell *which* rows were originally non-USD (useful for a
      currency-composition question specifically), and no independent way
      to verify the conversion's accuracy beyond this cross-check sample —
      but prize-pool *totals* built on the new table should already be
      correct in USD terms, not systematically biased.
- [x] **Dates**: genuinely improves, not just changes. Raw start_date string
      agreement on matched pages was only 71.5% (counter_strike) to 91.1%
      (league_of_legends), but inspecting the disagreements shows the large
      majority are `tournaments.start_date IS NULL` (unparsed/missing from
      wikitext) where `tournaments_lpdb` has a real date — LPDB is filling
      gaps, not contradicting existing values. One concrete parsing-artifact
      case found: dota2's `StarLadder/i-League Invitational/5/South America`
      had `mediawiki="2018-03-21f"` (a stray trailing character from the
      wikitext scrape) vs. `lpdb="2018-03-21"` (clean) — a second, independent
      confirmation LPDB's structured dates are more reliable, not just
      differently-sourced.
- [ ] **Shared-wiki contamination** / **generational continuity**: not yet
      checked — no fighting-game title (the only shared-wiki case, `fighters`)
      has been pulled through `collectors/liquipedia_lpdb.py` yet. Do this
      as part of the remaining-19-titles run, not deferred further.
- [x] **New finding, not anticipated when this plan was drafted — `series_key`
      has no LPDB equivalent.** `tournaments.series_key` (rule-based, derived
      by `etl/generate_tournament_aliases.py` from `liquipedia_page`) is the
      join key the entire `tournament_aliases` → `classify_broadcast_tier.py`
      co-stream-detection pipeline depends on. `tournaments_lpdb` has no such
      column. Migrating broadcast-tier classification to LPDB data requires
      re-running `series_key_and_depth()`'s derivation logic against LPDB's
      `liquipedia_page` values (once the page-name format bug above is fixed)
      and re-validating `tournament_aliases` against it — real, bounded work,
      not a blocker, but genuinely Phase 3 scope, not something that happens
      for free.
- [x] **Row-count / coverage comparison** (the "how much does this actually
      change" read): after normalizing page-name format, LPDB is close to a
      strict superset of `tournaments` for all three reconciled titles, with
      very different *scale* of gain per title:
      - `counter_strike`: 19,425 (mediawiki) → 19,492 (lpdb), +67 net (+0.3%).
        `collectors/liquipedia_grassroots.py` already gave this title solid
        B/C-Tier coverage (18,134 of the mediawiki rows are already
        grassroots) — LPDB adds comparatively little.
      - `dota2`: 5,668 → 5,735, +67 net (+1.2%). Same story — already had a
        dedicated grassroots crawl (3,027 of 5,668 rows).
      - `league_of_legends`: **1,060 → 3,870, +2,810 net (+265%)**. This
        title never had a grassroots crawl at all — `tournaments`' tier
        breakdown for it is 100% tier-1/tier-2 (zero B/C-Tier rows).
        `tournaments_lpdb`'s breakdown is tier1=315 / tier2=748 / tier3=1,425
        / tier4=1,060 / tier5=292 — **2,485 grassroots-tier League of
        Legends tournaments now exist in this project for the first time.**
        This is the headline finding for the grassroots comparative analysis
        the user asked about — League of Legends is the title where LPDB
        isn't an incremental improvement, it's a wholly new dataset.
      - `starcraft2`: **excluded from this comparison — its LPDB pull is
        known-incomplete.** The collector run hit its 40-request cap exactly
        on starcraft2's 10th consecutive full (1,000-row) page, with no
        signal that pagination was actually finished — the reported 10,000
        rows is very likely a truncated count, not a true total (compare:
        `tournaments` has only 2,263 starcraft2 rows, and every other
        overlapping title's true LPDB total came in within a few percent of
        its MediaWiki count once fully paginated — a title landing at
        exactly a round multiple of the page size, cut off by the request
        cap, is the one number in this batch that should not be trusted yet).
        Finish this title's pull (a handful more requests, `--titles
        starcraft2`) before using it for anything.
- [ ] Written up as its own dated doc, same pattern as
      `docs/milestone_reconciliation.md` — the findings above are a first
      pass folded into this plan directly; promote to a separate doc once
      all 23 titles are reconciled, not before.

### Notebooks and scripts touching `tournaments` today (impact map, 2026-09-30)

Everything below reads `tournaments` either directly via SQL or through
`analysis/metrics.py`'s `get_success_milestone()` / `get_championship_windows()`
— none of it currently reads `tournaments_lpdb`, so none of it is affected by
Phase 1's build yet. This is the concrete list Phase 3's cutover has to
migrate (and, if a notebook's own analysis is worth updating sooner, can
start doing so *ahead of* cutover on a case-by-case basis — see "should we
wait" below).

**Direct SQL on `tournaments`, in research notebooks:**
- `research/foundations/fandom_and_niche_model/notebooks/niche_membership.ipynb`
- `research/esports_lifecycle_and_maturity/notebooks/grassroots_scene_comparison.ipynb` —
  heaviest user: tier, region, country, prize_pool, currency, team_number, dates
- `research/exploratory/notebooks/mlbb_russia_deep_dive.ipynb`
- `research/esports_lifecycle_and_maturity/notebooks/cs_growth_trajectory.ipynb` —
  prize_pool + currency filtering, team_number, broadcast_tier
- `research/esports_lifecycle_and_maturity/notebooks/dota2_growth_trajectory.ipynb` —
  same shape as the CS one
- `research/foundations/fandom_and_niche_model/notebooks/title_geography_maps.ipynb` —
  source for `reports/title_geography_maps/`'s "tournament host country" figure
- `research/esports_lifecycle_and_maturity/notebooks/china_cs_scene.ipynb`
- `research/esports_lifecycle_and_maturity/notebooks/fastest_growing_cs_regions.ipynb`
- `research/inter_esports_dynamics/notebooks/esports_share_of_twitch.ipynb`
- `research/other/notebooks/official_channel_candidates.ipynb` — config-generation,
  not a research finding, but still a real consumer
- `research/other/notebooks/reconciliation.ipynb` — QA against the hand-built
  milestone table; this one specifically should NOT move to `tournaments_lpdb`
  until Phase 3, since its whole job is checking `tournaments` against ground
  truth

**Via `analysis/metrics.py` (so any current or future notebook calling these
inherits whichever table they point at):**
- `get_success_milestone()` — used directly by
  `research/inter_esports_dynamics/notebooks/category_trajectories.ipynb` and
  `research/foundations/notebooks/milestone_year_reverse_engineering_check.ipynb`,
  and indirectly by `reconciliation.ipynb`
- `get_championship_windows()` — used by `grassroots_scene_comparison.ipynb`,
  `cs_growth_trajectory.ipynb`, `dota2_growth_trajectory.ipynb`

**Indirectly, via the `tournament_aliases`/`broadcast_tier` pipeline** (reads
`tournaments.series_key`, not `tournaments` directly, but traces back to it):
- `etl/classify_broadcast_tier.py`, `etl/generate_tournament_aliases.py`
- Any notebook consuming `viewership_snapshots.broadcast_tier` /
  `platform_viewership_snapshots.content_segment` downstream of that, e.g.
  `research/wider_game_fandoms/gta_launch_case_study/notebooks/gta_v_deep_dive.ipynb`

**Pipeline/export scripts, not research notebooks:**
- `etl/export_reference_data.py` — exports `tournaments`/`tournament_aliases`
  to `data/reference/` for the `--rebuild` safety net (CLAUDE.md's own rule)
- `etl/load_snapshots.py` — the eventual Phase 3 cutover point

### Should new analysis wait for all 23 titles, or start now? (2026-09-30)

**Start now for `league_of_legends`, `dota2`, and `counter_strike` — don't
wait for the remaining 19.** The reconciliation above gives real, not
assumed, confidence for these three specifically: near-total page overlap
with `tournaments` once the naming-format bug is worked around, tier data
that's cleaner than what's in production today, and dates that fill gaps
rather than contradict them. There's no reason a new notebook (e.g. a
grassroots comparative piece) needs to wait on unrelated titles' pulls to
finish.

Two things this does NOT mean:
- **`starcraft2` specifically is not ready** — finish its pull first (see
  above).
- **This is not yet a decision to deprecate `tournaments`/
  `collectors/liquipedia.py` project-wide.** New analysis can be built
  directly against `tournaments_lpdb` for the titles that have it, in
  parallel with `tournaments` staying the source of truth for everything
  else — that's exactly what a staging table is for. The two real blockers
  to an actual cutover (currency loss, `series_key` having no LPDB
  equivalent yet) are Phase 3 concerns and don't block starting new,
  LPDB-native work today.

For the grassroots comparative analysis specifically: `league_of_legends`
is the standout case, since `tournaments` has literally zero B/C-Tier rows
for it today (no grassroots crawl was ever built for this title) while
`tournaments_lpdb` already has 2,485. A League of Legends vs.
Counter-Strike/Dota2 grassroots comparison is meaningfully *only* possible
with the new source — the old one can't answer it for League at all.

## Phase 3 — Cutover

- [ ] Once reconciliation is clean (or every discrepancy is understood and
      either fixed or accepted), swap `etl/load_snapshots.py`'s
      Liquipedia-loading step to LPDB as the source of truth — the
      "straightforward swap" the PRD already anticipated when LPDB was
      first deferred (§9.2).
- [ ] Decide `collectors/liquipedia.py`'s fate explicitly: keep the code as
      a documented fallback (e.g. for a future title added to
      `config/titles.yaml` before any expanded grant covers its wiki), but
      stop actively running it against live Liquipedia once LPDB is
      confirmed working. Given Liquipedia's own advice against continued
      MediaWiki use, this should be a stated decision, not something that
      just quietly stops.
- [ ] Re-run `generate_tournament_aliases.py` → `export_reference_data.py`
      → `classify_broadcast_tier.py` in the standard order against the new
      data.
- [ ] Update `docs/system_reference.md`, PRD §9.2, and CLAUDE.md once this
      is real, not preemptively.

## Phase 4 — Capture the benefits

- [x] **Player/roster connector (PRD §9.15) — built 2026-10-01**,
      following a direct request for a player database to support
      playerbase cohort analysis (age, career duration, regionalization —
      extending the streamer/community cohort work already done for
      post 3). Confirmed live what LPDB's `player` and `squadplayer`
      resources actually expose, previously unknown: `player` gives
      `birthdate`, `nationality`/`region`, current team, `status`
      (Active/Retired/Inactive), and `earnings`/`earningsbyyear`;
      `squadplayer` gives real `joindate`/`leavedate` per roster stint —
      the actual source for career-duration/team-hopping cohort work,
      which `player.status` alone can't reconstruct. New tables:
      `players_lpdb`, `player_earnings_by_year_lpdb`, `squadplayers_lpdb`
      (`etl/schema.sql`); new collector: `collectors/liquipedia_lpdb_players.py`.
      **Deliberately excludes the shared `fighters` wiki (4 titles)** —
      confirmed live that `player` has no per-title `game` field, only a
      multi-game list in `extradata.games` (a real sampled player listed
      Mortal Kombat, Street Fighter, Injustice, and 2XKO simultaneously),
      so no safe per-title split exists yet without risking the same
      cross-game attribution error the tournament collector's
      `GAME_CODES_BY_TITLE` was built specifically to avoid.
- [ ] **Per-tournament participant lists** — the qualifier-normalized
      entry-rate question (`research/esports_lifecycle_and_maturity/brief.md` §10)
      was flagged as needing this and "not yet scoped at all." Still open
      — not the same thing as player/roster data above.
- [ ] **`series_key`/`tournament_aliases`** — see Phase 2's own finding:
      LPDB has NO native tournament-series identifier — confirmed, not
      still open. `series_key_and_depth()`'s rule-based approach would
      need re-running against LPDB's `liquipedia_page` values (after the
      page-name format fix) rather than being retired. Still a real Phase
      3 item, just resolved in the opposite direction this checklist item
      originally expected.
- [ ] **Full grassroots crawl for all 23 titles** — in progress via
      `scripts/lpdb_overnight_sync.py` (below), not yet complete for all
      titles as of 2026-10-01.
- [x] **Broadcast/channel data — built 2026-10-01**, following a direct
      request to evaluate LPDB as a structured alternative to
      `config/channels.yaml`'s manually-curated list (5 of 23 titles
      curated as of 2026-10-01: counter_strike, dota2, street_fighter,
      valorant, pubg) and `classify_broadcast_tier.py`'s text-matching
      `detected_costream` heuristic. Confirmed live: the `match` resource's
      `stream` field gives real, structured per-match Twitch channel
      identifiers (e.g. `{"twitch_en_1": "Fragbite", "twitch": "Fragbite"}`)
      — ground truth ("this channel broadcasts this specific match"), not
      an inference from stream-title text. New table: `match_streams_lpdb`
      (`ai_assisted_unreviewed` by construction — LPDB's value is a
      display-name-shaped template parameter, not confirmed to be the
      exact Twitch login `config/channels.yaml` needs); new collector:
      `collectors/liquipedia_lpdb_broadcasts.py`, scoped to a sample of
      each title's most recent tier-1/2 tournaments rather than an
      exhaustive pull (Counter-Strike alone already has 1,293 tier-1/2
      tournament pages — exhaustively pulling match data for all of them
      across 23 titles would cost several thousand requests, far beyond
      what's responsible against the confirmed 60/hour ceiling in any
      short window). `scripts/build_channel_candidates_from_lpdb.py` takes
      the most-referenced channel names per title, live-verifies each
      against Twitch Helix (the same standard `research/other/notebooks/
      official_channel_candidates.ipynb` already established), and writes
      a draft (`config/channels_lpdb_candidates.yaml`) for the same human
      review `config/channels.yaml`'s existing entries already went
      through — does NOT write `channels.yaml` directly.
      **Also captured**: `broadcasters_lpdb` (cast talent — analysts/hosts/
      casters — a different signal from channel identity, not analyzed
      further here).
      **The channel-tiering refit itself (making `classify_broadcast_tier.py`
      actually use this new signal) is not yet built** — real match-stream
      data needs to accumulate first (the overnight sync only just started
      pulling it), and rewriting a pipeline several existing notebooks
      depend on (`cs_growth_trajectory.ipynb`, `dota2_growth_trajectory.ipynb`,
      the `title_geography_maps` report, ...) without validated real data
      behind it would be premature. Proposed design once data exists: a
      third, higher-precision tier — `match_streams_lpdb` gives direct
      per-match channel ground truth, strictly better than `channels.yaml`'s
      static list (which only ever proves "this channel exists," not "this
      channel aired this match") or `detected_costream`'s title-text
      inference — sitting alongside, not replacing, the existing two
      signals until it's been checked against known cases the way every
      other LPDB field in this plan has been.
- [x] **`scripts/lpdb_overnight_sync.py` — unattended sync loop, built
      2026-10-01**, following a direct request to keep pulling data
      automatically as the rate-limit window resets rather than requiring
      a person to re-trigger collectors by hand. Works through tournament
      pulls (remaining 19+ titles), then player pulls, with broadcast
      sampling for already-tournament-complete titles given a 1-in-3-cycle
      priority slot so channel data doesn't wait behind the entire player
      phase. Every invocation shares the same persisted, cross-process
      request budget `collectors/liquipedia_lpdb.py` already tracks
      (`data/cache/liquipedia_lpdb/request_log.json`) — this script cannot
      cause the combined tools to exceed the real 60/hour ceiling, and
      deliberately runs each invocation below it
      (`MAX_REQUESTS_PER_INVOCATION`), not constantly saturating it.
      `collectors/liquipedia_lpdb.py` and `_players.py` both gained
      offset-based resume (`tournament_offsets.json`) so a budget-
      interrupted pull continues next cycle instead of re-paying for
      already-fetched pages. Launched 2026-09-30 for a 23-hour window;
      check `logs/lpdb_overnight_sync.log` (gitignored) for progress.

## What this plan deliberately does not cover

- Live viewership data (Twitch/YouTube/Steam) — entirely unrelated to
  Liquipedia/LPDB, unaffected by any of the above.
- Esports Charts / peak-viewership data — LPDB is tournament/match/prize-pool
  data only; the championship-concentration work (inter_esports_dynamics/questions/platform_attention_concentration's
  demand-side sub-test) stays blocked on Esports Charts regardless of LPDB
  access. Don't read LPDB landing as unblocking that too.
