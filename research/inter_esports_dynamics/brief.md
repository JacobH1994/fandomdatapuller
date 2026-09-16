# Inter-Esports Dynamics: Research Brief (Post 2)

*Originally "Esports & Competitive Exclusion" — renamed 2026-09-16 to
reflect a broader scope than the single Gause's Law framing this brief
started from (§3 still argues for that framing as the primary theoretical
lens; the area itself isn't limited to it). Content and section numbering
unchanged by the rename.*

## 1. Context

Post 1 ("Is the rate at which successful esports emerge decreasing?") established:

- Working definitions of **esports** and **successful** (carried forward below)
- Finding: the rate of new successful esports is *increasing*, not decreasing, over the last 3–5 years vs. the prior 15
- Three emergence phases: **Classic** (2013–15, PC, CIS/China-heavy: StarCraft II, Dota 2, League of Legends, Counter-Strike, Hearthstone), **Console** (2016–20: Rocket League, Siege, fighting games, Overwatch), **Second Coming** (2021–24, mobile-heavy, diverse regions: Brawl Stars, TFT, Free Fire, PUBG, VALORANT, PUBG Mobile, ML:BB, Apex, Fortnite, etc.)
- A secondary finding: newer successful titles are systematically *smaller in scale* (seat cap, prize pool, peak viewers) than the "classic" titles, with VALORANT as the one clear exception
- Post 1 closes on a speculative claim, unlabeled at the time: markets seem to spontaneously adopt a first title into an open genre/platform/market gap, which then crowds out competitors — i.e., competitive exclusion.

This brief scopes Post 2: does that closing speculation hold up as **Gause's Law / the competitive exclusion principle**, and if so, along which vector?

## 2. Research questions

1. Within a given niche (defined below), does one title's share of attention concentrate over time at the expense of others (exclusion), or do multiple titles sustain stable, differentiated shares (coexistence)?
2. Where coexistence holds, what is the actual differentiation vector — sub-genre, platform, region, demographic cohort, format — rather than assuming genre/platform/market are the only candidates?
3. Does "rising emergence rate + scale concentration within niches" hold up across the full ~25-title dataset, or is it an artifact of the six hand-picked comparison titles used in Post 1?

## 3. Theoretical framework

Pure competitive exclusion (Gause's Law) assumes competitors draw on a **fixed** resource pool. Post 1's own headline finding — more successful esports, not fewer — says the pool isn't fixed; new "habitat" keeps opening as platforms mature, regions come online, and genres get invented. The better fit is **adaptive radiation followed by competitive exclusion**: new habitat opens, a burst of new successful titles fills it, and exclusion sorts the winner(s) *within* each new niche over time.

This reframe explains both Post 1 findings at once:

- Rising emergence rate = radiation into newly available habitat
- Scale stratification / incumbent dominance (LoL and CS pulling away in seat cap, prize pool, and peak viewers) = exclusion working itself out within already-occupied niches

**Working definition of niche:** a `{genre × platform × primary market/region}` cell — an operationalization of the genre/platform/market triangle Post 1 ends on.

**Working rule for coexistence vs. exclusion-in-progress** *(provisional — revisit once real time-series data is in hand)*: within a niche-cell containing 2+ successful titles, if the leading title's share of cell-level attention has risen for several consecutive years while others' fell, treat it as exclusion-in-progress. If shares have stayed within a roughly stable band over the same window, treat it as coexistence, and go looking for the differentiation vector sustaining it. A cell with a single successful title is ambiguous by default — it may mean no real contest occurred, or that one occurred and resolved before this dataset's window starts (see Limitation 2).

## 4. Definitions

**Carried forward from Post 1:**

- *Esports*: professional (financially incentivized, including salary) play of video games as a broadcast / media & entertainment product. Excludes grassroots "structured play."
- *Successful esport*: minimum 2-year history of A-tier-or-better competition across at least 2 continents, with viewership flat or growing over that period.

**New for Post 2:**

- *Niche*: see §3.
- *Esports fandom* (narrow): engagement specifically with the competitive/broadcast apparatus — official tournament/league viewership, team/player storylines, LAN attendance, org-specific merchandise.
- *Game fandom* (broad): engagement with the underlying game/IP as an entertainment product — playing, casual streaming or content, cosmetics, lore — with or without any competitive engagement.

These last two are not interchangeable, and several planned data sources measure one but not the other cleanly (§8).

## 5. Named hypotheses

### H1 — Cohort differentiation in PC tac-FPS (primary, this post)

CS, VALORANT, and (to a lesser extent) Siege coexist not because tac-FPS-PC is undersaturated, but because the niche has split by **age cohort** — a long-tenured CS audience and a younger VALORANT audience acquired disproportionately during 2020.

This is likely compounded, not singular. VALORANT's closed beta (April 2020) ran almost entirely on Twitch-drops access — viewers had to link accounts and watch specific streamers to earn a key — driving beta viewership past 1.7M concurrent before public launch. Coverage from that week credits both the lockdown context (spare attention to give) and the drops mechanic (a forcing function that captured it). Riot also pointed an existing League of Legends audience directly at the new title. COVID-liquidity and deliberate audience capture likely reinforced each other rather than competing as explanations.

**Tests:**

- *Cross-title/cross-genre check* — if COVID-liquidity is a general phenomenon, other unrelated 2020-breakout titles (Fall Guys, Among Us) and Rocket League's own 2020 trajectory should show comparable anomalous stickiness. If only VALORANT shows it, the marketing/halo explanation is doing more work than the liquidity one.
- *Direct cohort test* — age/gender breakdowns by title, if obtainable (Esports Charts' enterprise tier advertises this; cost and access unconfirmed).
- *Baseline comparison* — pre-2020 tac-FPS launch curves (CS:GO's or Siege's own early growth) as a reference for judging whether VALORANT's curve is genuinely anomalous, not just a normal successful launch.

### H2 — Accumulated fandom value increases resilience (secondary — name, don't resolve, this post)

Longer-tenured fanbases should be more resilient to shocks (a bad season, scandal, a flashy new competitor) than newer ones, because accumulated shared history raises the payoff of continued engagement — a close parallel to Iannaccone's "religious human capital," where accumulated ritual and history knowledge raises the expected benefit of continued participation in a tradition.

**Test (future post, not this one):** compare relative viewership drawdown of older titles (LoL, CS) during their own past rough patches against newer titles under comparable stress. Needs multi-year, per-title volatility data not yet in hand.

### H3 — Attention concentrates even as production fragments (named 2026-09-09, formalizing research question 3 in §2)

Two things happening at once, not one: the Twitch work already found platform *attention* concentrating hard within esports (esports' own share of top-200 Twitch attention nearly halved 2016-2024, and Just Chatting/GTA V drove most of the platform's growth — `research/inter_esports_dynamics/notebooks/esports_share_of_twitch.ipynb`). H3 asks whether *production* is doing the opposite at the same time — more titles being made, a longer tail, even as the audience's attention concentrates onto fewer winners within any given niche. If both are true simultaneously, that's the emergence-and-consolidation pattern Post 1 already found for esports specifically (rising emergence rate, smaller individual scale) showing up one level up, as a general property of digital-fandom production and attention rather than something specific to esports.

**Tests, two independent sub-tests on different datasets, not the same claim measured twice:**

- *Supply side — Steam production composition* (PRD §9.12a): indie vs. core (AAA) release volume and lifecycle-shape comparison, drawn from a full historical Steam catalog backfill (`collectors/steam_catalog_backfill.py`, in progress as of 2026-09-08). Tests whether game *production* is fragmenting (more indie, more studios, longer tail) using the same "does sustained investment predict durability" logic H2 already names, just on a dataset entirely outside esports.
- *Demand side — championship-viewership concentration within esports itself* (PRD §9.3a): for each tracked title, its highest-prize-pool tier-1 tournament per year (`analysis/metrics.py:get_championship_windows`, built 2026-09-08 — 283 windows across all 23 titles as of the current corrected count, see below) as an objective "world championship window," with peak viewership pooled across titles per year to compute HHI/top-3 share and a power-law-vs-log-normal fit over time. **Paused, not built**: the peak-viewership figure this needs was meant to come from Esports Charts, and automated access there is now confirmed blocked (checked directly 2026-09-09, PRD §9.3) — this sub-test has no confirmed data source yet, only the window-identification half.
  - **Real bug found and fixed 2026-09-09, directly relevant if this sub-test is ever resumed**: `get_championship_windows()` originally picked the numerically-largest `prize_pool` with no currency normalization — a raw KRW/CNY/JPY/etc. figure could (and did) beat a much larger real-USD prize purely on magnitude. Affected 95 of 291 windows at the time (32.6%), including *every* `league_of_legends` year 2012-2025. Fixed to require `currency='USD'` or `currency IS NULL`; a title-year whose only candidate is non-USD now correctly gets no window rather than a wrong one (hence 291→283, not just the 95 rows changing value). Covered by three new tests in `tests/test_metrics.py`. Found while building `research/esports_lifecycle_and_maturity/notebooks/dota2_growth_trajectory.ipynb`, not while working on this brief directly — recorded here since this function is this section's own citation.

## 6. What the existing title list already shows

Genre/platform categorization below is inferred from Post 1's prose — not yet a formal data column.

| Genre | Coexisting successes | Pattern | Worth checking |
|---|---|---|---|
| MOBA | LoL, Dota 2 (PC) · Wild Rift, ML:BB (mobile) | Two long-running pairs | PC pair may split on complexity/region; mobile pair looks like live exclusion-in-progress, not settled |
| Tac FPS (PC) | CS, VALORANT, arguably Siege | 3-way coexistence | See H1 — the strongest counter-example to a simple one-winner story |
| Battle royale | PUBG, Apex (PC/console) · PUBG Mobile, Free Fire (mobile) · Fortnite (cross-platform, outside the charted 6) | Many successes | Fits differentiation cleanly — same genre, different hardware/region pools |
| Fighting games | Tekken, Street Fighter, Mortal Kombat, Guilty Gear | Many, long-coexisting | Possibly structurally exclusion-resistant — differentiation is baked into each roster/mechanics, and shared "majors" (EVO) may pool audiences rather than split them |
| Hero/arena shooter | Overwatch (alone, then gone) | No coexistence example survives | Cleanest single-niche case — but see Limitation 3 on cause of death |
| RTS | SC2, Age of Empires | Two, ~7 years apart | Sequential, not simultaneous — probably not a real coexistence case |

**A structural Classic-vs-Second-Coming difference found while working the CS/Dota 2 lifecycle briefs (`research/esports_lifecycle_and_maturity/brief.md` §15, 2026-09-09), not this brief's own line of investigation but directly relevant to the era framework above** — now its own notebook, `research/digital_fandoms/fandom_historical_contingency/notebooks/streamer_ecosystem_by_phase.ipynb`, expanded from 6 titles/2 eras to all 23 titles/4 eras: distinct monthly Twitch streamer counts (`Streamers`, Kaggle) show a real gap, but only for part of the Second Coming cohort, not the era as a whole. Fortnite, VALORANT, and Apex Legends do dwarf every Classic and Console title (5-10x, in Fortnite's case), but PUBG and every mobile Second Coming title (`free_fire`, `brawl_stars`, `teamfight_tactics`, `pubg_mobile`, `wild_rift`, `mobile_legends_bb`) sit at or below Classic-era `dota2`/`hearthstone` — so the mechanism is more likely "a specific broad-audience, high-clip-affinity title cohort" than "newer titles in general." Dota 2 still sits at the bottom of its own era, the smallest of all 23 despite total viewership comparable to or exceeding several larger-ecosystem titles. Worth keeping in mind, with this revision, if H1-H3's differentiation-vector work ever turns to creator-side (not just viewer-side) evidence. **This finding is now also the seed of its own subproject** — `research/digital_fandoms/fandom_historical_contingency/brief.md` (split out 2026-09-16) — which asks the broader question this paragraph's "specific cohort, not a general trend" result opens up: does era-of-emergence leave a structural mark on fandom formation generally, not just creator-ecosystem size.

**First concrete shared-occupancy candidate, `research/inter_esports_dynamics/notebooks/niche_membership.ipynb`, checked 2026-09-12 — and it isn't the pair either named hypothesis predicted.** That notebook's audience-language-similarity test, restricted to pairs clean of the sample-size and live-tournament-contamination issues documented there (13 same-cell pairs total, only 3 survive that filter this window), finds **Apex Legends and PUBG: BATTLEGROUNDS** (`battle_royale`/`pc_console`) with the highest similarity *and* lowest distance of the confident set — both metrics agreeing, not one an artifact of the other. That's a real complication for this row's "fits differentiation cleanly" read, at least for this specific pair (Apex/Fortnite, same cell, shows the opposite — lowest similarity in the whole table, the `ja`-share gap already on record). Meanwhile H1's own `tac_fps`/`pc` cell and the MOBA row's Dota 2/LoL pair currently have **zero** surviving high-confidence pairs (see limitation 5 below) — not evidence against those hypotheses, just not testable from this window. Directional only: one Twitch-language snapshot under two weeks old, re-check once `language_mix_snapshots` has real history.

**Three more notebooks formally assigned here 2026-09-16**, on the reasoning that each is a data point toward this brief's own core question — is there real dynamics/crossover *between* individual esports titles — rather than belonging to `esports_lifecycle_and_maturity` (which asks about one title's own trajectory) or standing alone as exploratory work:

- `notebooks/creator_crossover.ipynb` — the enrichment-ratio/insularity work already cited throughout §6-§7; formally lives here as this brief's primary creator-side (not viewer-side) cross-title evidence.
- `notebooks/steam_review_playerbase_over_time.ipynb` and `notebooks/english_fandom_decomposition.ipynb` — the English-language fandom decomposition subsystem's own notebooks (§7 limitation 1), which exist specifically to distinguish "two titles' audiences look similar" from "actually the same people" — directly this brief's own multi-homing question, not a general-purpose utility that happens to touch it.
- `notebooks/title_geography_maps.ipynb` — six-title choropleth comparison of tournament-host country vs. audience-implied geography; another concrete reading of the "what is the actual differentiation vector" question in §2 (research question 2), alongside `niche_membership.ipynb`'s language-based approach above. Not yet cross-referenced into this brief's own prose findings — worth doing once its results are read against H1-H3 specifically, not done as part of this reassignment.

## 7. Limitations — state explicitly, keep conclusions tentative

1. **Is the resource actually shared?** Gause's paramecia had no choice but to compete for one resource. Esports fans multi-home — many LoL viewers also watch VALORANT. If audience overlap is high, "crowding out" may be the wrong model. No current source measures this (aggregate hours-watched can't distinguish overlapping from disjoint audiences). Treat as an open question, not an assumption. **Partially addressable now (PRD §9.17, built 2026-09-12)**: the English-language fandom decomposition subsystem (`analysis/fandom_region_decomposition.py`, `research/inter_esports_dynamics/notebooks/english_fandom_decomposition.ipynb`) breaks Twitch's undifferentiated `en` tag down by likely region via timezone deconvolution, self-declared stream tags, Wikipedia pageviews, and Steam review data — this is the first infrastructure this project has that can distinguish "two titles' audiences look similar" from "actually the same people," at least along the region axis rather than the multi-homing axis directly. Still not a full answer to this limitation (region similarity isn't the same claim as one person watching both titles), but a real step past "no current source measures this." **Extended to the whole `tac_fps`/`pc` cell, 2026-09-15**: `rainbow_six_siege` and `valorant` added as subjects (`config/fandom_decomposition_subjects.yaml`), alongside the already-configured `counter_strike`, so H1's own niche cell can now be read this way, not just Apex/PUBG. **A real limitation of the method itself surfaced by running all three together, not a title-specific finding — and now reflected in how results are labeled, not just caveated in prose (2026-09-15).** South Africa's fixed UTC+2 offset is structurally indistinguishable from Central/Western Europe (also UTC+2, but only during CEST — currently in season) — see `analysis/fandom_region_decomposition.py`'s own module docstring. The old country-named output (`South_Africa`) came back as the largest single bucket for *every* subject in the whole registry (44–53% for Apex/PUBG/Siege/VALORANT/GTA V, 26.7% for CS specifically) — a uniform-across-unrelated-subjects pattern that was itself evidence of a Western-Europe-shaped hole in `CANDIDATE_ENGLISH_COUNTRIES` (no Western Europe candidate existed), not a genuine South African audience finding. **`decompose_by_timezone` now returns the resolved UTC offset itself as the label (e.g. `UTC+2`) rather than a candidate country name** — the offset is the actual thing clock-time activity can support a claim about, and it's a stable key regardless of which candidates get added later. A separate function, `reference_cities_for_offsets()`, gives the illustrative "which cities share this offset right now" annotation (e.g. `UTC+2 → Johannesburg`) — deliberately never merged into the same table as a real measured category (a language code, a self-declared tag), so a reader can't mistake "an example of what this offset might be" for "what we measured." `UTC+2`'s share for CS/Siege/VALORANT is 26.7%/53.1%/45.0% respectively — cross-checked against Signal 2 (self-declared tags) for CS, which independently shows EU+UK at ~52% of tagged streams, consistent with `UTC+2` being mostly Europe rather than South Africa specifically. Adding a real Western Europe candidate (so the seasonal auto-merge can split `UTC+2` into its own label and separate cleanly outside CEST season) remains a real, scoped next step, not done yet.
2. **Survivorship bias.** The dataset, like Liquipedia's coverage generally, mostly sees titles that got big enough to register. For Post 1's question this skews a denominator; for Post 2's exclusion question, the *failed challengers per niche-cell are the actual evidence*. A cell with one winner and no visible competitor is ambiguous between "no attempt" and "an attempt that got excluded." At minimum, do a qualitative pass on notable failed attempts per occupied cell, flagged as directional rather than rigorous.
3. **Structural death is not competitive death.** Overwatch is the one clean same-niche implosion in the dataset, which makes it tempting to read as an exclusion casualty. Reporting on its collapse points mainly to a flawed franchise business model and an Activision Blizzard scandal that drove sponsors away, with viewership declining alongside — not an obvious rival hero-shooter displacing it. State explicitly which deaths are being counted as "excluded" vs. "died for unrelated reasons."
4. **Game fandom vs. esports fandom conflation.** Several planned data sources — notably raw Twitch category hours-watched — measure game fandom diluted with esports fandom, not esports fandom specifically. See §4 and the mitigation built into §8's data plan.
5. **Live-tournament contamination currently disables the MOBA/PC same-cell test specifically (checked 2026-09-12).** `research/inter_esports_dynamics/notebooks/niche_membership.ipynb` cross-checks `language_mix_snapshots`' exact window against `tournaments.start_date`/`end_date` before trusting any audience-similarity read — a title with a tier-1 event live during the window has its language mix pulled toward that broadcast's host region, which is a confound, not signal, for the coexistence-vs-exclusion question this brief asks. As of 2026-09-12, **both** League of Legends and Dota 2 have a tier-1 event live simultaneously (previously Dota 2 was the "no overlap" clean baseline, useful for judging whether LoL's own skew was unusual). With both sides of the §6 MOBA/PC pair now tournament-skewed at once, this window's LoL/Dota2 audience-similarity number can't distinguish "genuinely similar audiences" from "both temporarily pulled toward their own event's broadcast language" — treat it as not currently testable, not as a data point, until the overlap passes. Re-check the notebook's contamination table before citing this pair again.

## 8. Data & variables needed

| Variable | Why | Source | Status / access notes |
|---|---|---|---|
| Tournament tier, prize pool, league-founding dates | Success-milestone inputs (currently hand-collected) | Liquipedia LPDB API | Official, structured, 15+ years of history; registration required — confirm current terms at liquipedia.net/api |
| Peak/average viewership per title, over time | Scale + niche-share metrics | Esports Charts (already in use) | Public site for browsing; private API for deeper/bulk pulls is a paid, enterprise product |
| Live viewer counts, forward-collected | Extends viewership beyond what Esports Charts readily surfaces | Twitch Helix API (`Get Streams`, polled and aggregated in-house) | Free, self-hosted; architecture already scoped |
| Genre / platform / primary-region tags per title | Populates the niche-cell matrix (§6) at full scale | Manual curation from Post 1's categorization, cross-checked against IGDB | Not yet systematic — currently only implied in prose |
| Age/gender breakdown per title | Direct test of H1's cohort claim | Esports Charts enterprise tier | Cost/access unconfirmed — worth a scoping email |
| Official broadcast-channel IDs per title | Numerator for "% of category attention on official channels" (mitigates Limitation 4) | Manual curation | Not started |
| General vs. esports-specific community engagement | Independent signal for the fandom-vs-attention split | Paired subreddits (main game sub vs. esports-scene sub) where they exist | Not started; subscriber/activity snapshots likely sufficient to start |
| Notable failed challengers per niche-cell | Mitigates survivorship bias (Limitation 2) | Qualitative pass — esports news archives, Liquipedia inactive-tournament histories | Not started; scope as directional, not exhaustive |
| Pre-2020 tac-FPS launch curves | Baseline for judging whether VALORANT's growth is genuinely anomalous | Liquipedia + Esports Charts, historical | Not started |
| 2020-vintage breakout titles outside esports (Fall Guys, Among Us) | Tests whether COVID-liquidity is general or VALORANT-specific | Historical Twitch data (Sullygnome-style) or the previously-scoped Kaggle "top games" dataset | Not started |

## 9. Build plan (for Claude Code)

Phased so each stage produces something usable on its own:

1. **Foundation** — Liquipedia LPDB pull for the full ~25+ title milestone table, replacing the hand-built version; stored in SQLite.
2. **Viewership** — Esports Charts pull for the same full title list, extending the current 6-title hand-charted comparison; Twitch API forward-collector stood up in parallel for anything Esports Charts doesn't cover.
3. **Classification layer** — genre/platform/region tags per title, Claude-assisted first pass, human-reviewed.
4. **Derived metrics** — niche-cell shares over time; a concentration measure per cell; "% of category attention on official channels" per title.
5. **Case-study data** — Esports Charts enterprise scoping conversation (demographics); pre-2020 baseline pull; cross-genre 2020 check; subreddit-pair snapshots; qualitative failed-challenger notes per cell.
6. **Analysis & output** — the charts and write-up for Post 2, built on stages 1–5.

## 10. Open decisions

- Firm up the coexistence/exclusion threshold rule in §3 once real multi-year, per-cell data exists — the current version is a starting point, not a final rule.
- Decide how far to pursue the Esports Charts enterprise conversation; cost may not be justified by a single post.
- Decide the rigor bar for the failed-challengers pass — directional color vs. something closer to systematic.
- Decide whether H2 (fandom value over time) gets a named-but-untested paragraph in Post 2, or waits entirely for a future post.
