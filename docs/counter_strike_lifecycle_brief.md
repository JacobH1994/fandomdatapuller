# Has Counter-Strike Esports Finished Growing? Research Brief

## 1. Context

Separate from [[esports_gauses_law_brief.md]] by deliberate choice (decided 2026-09-09, see §3) — that brief asks whether attention concentrates *within* a niche, across titles, at a point in time. This one asks whether a *single* title has reached the end of its own growth trajectory, independent of how it's doing relative to competitors.

**Motivating use: an argument to industry executives.** That shapes both what gets measured and how it gets shown (§6) — every underlying metric's own trajectory is shown plainly before any composite claim, uncertainty is shown rather than hidden, and confounds are labeled directly rather than smoothed over or left to a footnote a skeptical analyst would have to go looking for.

**Why Counter-Strike specifically:** it has the longest, most complete history of any title this project tracks. `tournaments` now spans one continuous history from 2000 through 2028 (1.6 through CS2, generational-continuity fix, 2026-09-09 — see `docs/system_reference.md` §5), and `monthly_category_history` has ~11 years of category-wide Twitch data (2016-01 onward). No other tracked title is as well-positioned for a genuine long-run maturity analysis — most have only a few years of history at most.

## 2. Research question

**Has Counter-Strike esports finished growing?**

Decomposed into sub-questions, since a single metric risks a false answer:

1. Has **audience attention** (category-wide Twitch hours, and — once mature — esports-specific broadcast-tier hours) plateaued?
2. Has **competitive infrastructure** (tournament count, real prize pool, team count, region count) plateaued?
3. Is attention growth being driven by genuinely **new audience**, by **existing fans absorbing more supply**, or **failing to keep pace with supply** (a saturation signal)? (§5c)
4. Is the market **concentrating** into fewer, bigger flagship events even while raw totals still rise — a maturity signal in its own right, and directly related to H3 in the Gause's Law brief?
5. Is CS's trajectory **distinct from the industry as a whole**, or part of a broader plateau/reversion already documented elsewhere (`notebooks/esports_share_of_twitch.ipynb`)?

## 3. Relationship to the Gause's Law brief

`esports_gauses_law_brief.md`'s named hypotheses (H1–H3) ask about competition *between* titles sharing a niche — does one title's share concentrate at another's expense. This brief asks about *one* title's own trajectory over time, independent of rivals. A title can be winning its niche (H1/H3) while *also* having finished growing in absolute terms — a mature incumbent — and those are different, complementary claims for an executive audience. "CS still dominates its niche" is not the same statement as "CS's own growth has plateaued," and conflating them would be a real mistake, not a stylistic one.

Where the two connect, noted rather than duplicated:

- The concentration/HHI method (§5e; `analysis/metrics.py:get_concentration()`) is the same tool H3 applies across titles on `get_championship_windows()` — here it's applied *within* CS (its own flagship event's share of its full slate) rather than across titles.
- A finding that CS has plateaued is a direct input to how H1's CS/VALORANT/Siege cohort-coexistence story should be read going forward: a plateaued incumbent facing a still-growing rival is a different competitive dynamic than two titles both still expanding, even if H1's cohort-differentiation explanation itself doesn't change.

## 4. Data sources and time horizons

Being explicit about which sources can speak to the question *today* vs. which are only now starting to accumulate history matters for an executive audience — a chart that quietly starts in 2026 looks the same as one that starts in 2016 unless the horizon is labeled.

| Metric | Source | Coverage as of 2026-09-09 | Status |
|---|---|---|---|
| Category-wide Twitch hours (game fandom, not esports-specific) | `monthly_category_history` (`kaggle_import` 2016–2024 + `own_collector` 2026–present) | 2016-01 – 2026-09, 107 months | Long-run, usable now |
| Tournament count, prize pool, team count, region — tier-1/2 | `tournaments` | 2000–2028 (continuous, post generational-continuity fix) | Long-run, usable now — but see §5b on partial/future years |
| Esports-*specific* Twitch hours (`broadcast_tier='primary_official'`/`'detected_costream'`, excludes general category noise) | `viewership_snapshots` | 2026-08-31 – present, ~1.5 weeks | **Prospective only, and currently undercounted, not just low-confidence.** `classify_broadcast_tier.py` re-run 2026-09-09 (§7): for CS, 919 rows classified `detected_costream` (title/date/alias match), 0 `primary_official` (which requires `is_official_broadcast=1`, structurally impossible while `channels.yaml` is empty — confirmed 0 rows platform-wide, not CS-specific), 31,785 `general`. `detected_costream` catches most genuine official broadcasts anyway, since their titles usually name the tournament — but an official stream with a generic title (pre-show downtime, an unusual naming convention) has no other way to be caught right now and silently falls into `general`. A real, likely-nontrivial undercount, not only a confidence-labeling gap (§7 has the full distinction) |
| Steam concurrent players (underlying game population, not esports-specific) | `steam_player_counts` (`title_id='counter_strike'`, appid 730) | 2026-09-08 – present, 6 hourly points | **Prospective only** — no legitimate historical backfill path exists (CLAUDE.md's SteamDB/SteamCharts prohibition), so this dimension can only ever answer the question going forward |

**Real numbers already visible, to ground the design rather than leave it abstract** (tier-1/2 prize pool by year, nominal USD, from a live query 2026-09-09): rises to a $20.3M peak in 2020, dips to $15.7M (2021) and $11.4M (2022), then recovers — $15.5M (2023), $15.4M (2024), $27.8M (2025), and already $38.6M logged for 2026 with the year only 9 months elapsed. Not a clean curve — exactly why §5b's confound handling matters, not a detail to skip.

## 5. Analytical design

### 5a. Four dimensions, tracked independently before any synthesis

Audience attention, competitive infrastructure, concentration, and player base (§2) are tracked as **separate trajectories**, not folded into one number before being shown. See §6 — this is a deliverable requirement, not just an analysis-hygiene preference.

### 5b. Confounds handled explicitly, not smoothed over

- **Partial/future-year censoring.** 2026 is 9 months elapsed and already exceeds most complete prior years (§4); 2027–2028 contain only currently-announced events. All trend analysis restricts to *fully completed* calendar years; the current year is shown separately and clearly labeled partial, never blended into a "2026" bar as if it were comparable to "2020."
- **CS2 relaunch (August 2023).** A real structural break — engine change, a real disruption/return cycle in the scene — not noise to average through. Modeled as a labeled regime marker on every chart; checked explicitly by comparing the first 12 months after launch against the most recent 12 months, to distinguish a fading novelty bump from sustained post-relaunch growth.
- **COVID-era spike (2020–2021).** A known industry-wide, not CS-specific, temporary boost. Before adopting a specific treatment (a COVID-period dummy, exclusion, detrending), check whether `esports_share_of_twitch.ipynb` or the Gause's Law brief's H1 already establishes a standard approach for this window — reusing an existing methodology beats inventing a second, potentially inconsistent one.
- **`broadcast_tier` quality break at 2026-09-09** (§7) — `config/channels.yaml` was empty before this date and has three curated CS channels after it, so `primary_official` classification (vs. `detected_costream`/`general`) is only possible from this date forward. The esports-specific-attention series is not uniform-confidence end to end; the break is labeled on the chart, not left implicit.

### 5c. Supply vs. demand decomposition — where is attention growth actually coming from?

Raised directly by the user (2026-09-09): total hours watched can grow for reasons that mean very different things for "has CS finished growing," and conflating them would make the headline number misleading. Decompose hours-watched growth against tournament-supply growth via an **intensity ratio** — hours watched per tournament, and separately (more economically meaningful, since a $50K regional and a $2M Major both count as "1" in a raw tournament count) hours watched per real prize-pool dollar (§5d) — tracked over time, by fully-completed year:

- **Ratio rising** — each additional unit of supply draws a *larger* audience than the last. Clear evidence of genuine new-audience inflow (the extensive margin). Strong "not finished growing" signal.
- **Ratio flat / keeping pace with supply** — added supply is being absorbed without dilution: existing fans are watching *more* as more is offered, rather than the same fixed pool of attention being spread thinner across more content. This is *not* a saturation signal on its own — it means the ceiling on the existing fanbase's total viewing capacity hasn't been hit yet, even though it doesn't distinguish "new fans" from "existing fans watching more." Worth stating precisely, since a flat ratio is easy to misread as stagnation when it's actually still a positive signal.
- **Ratio falling** — supply is outpacing demand: additional tournaments no longer find proportional additional attention, meaning a roughly fixed pool of fan-hours is being spread across more events. **This is the actual saturation signal** — the one case where rising raw totals (more tournaments, even rising total hours) can coexist with a genuinely plateaued or shrinking core audience, and the case most worth flagging clearly to an executive audience since it's the one raw headline numbers alone would hide.

*(Framing above sharpens the middle case from how it first came up in conversation — flagging that refinement explicitly for confirmation, not asserting it as unquestionably settled.)*

### 5d. Real (inflation-adjusted) prize pool — CPI deflator

Nominal-USD prize pool trends overstate real growth across an 11+ year window purely from inflation — 2020 dollars and 2026 dollars aren't comparable as-is.

- **Source**: US BLS CPI-U (Consumer Price Index for All Urban Consumers, all items) — the standard general-purpose US inflation index, publicly published by a government statistical agency for exactly this kind of use. No ethical/ToS concern of the kind CLAUDE.md flags for SullyGnome/SteamDB/Esports Charts — this is a different category of source entirely (a public statistical release, not a competitor's proprietary tracked-content site).
- **New small reference component**: `data/reference/cpi_deflator.csv` (or similar), one row per year, sourced from BLS's public CPI-U annual-average series. Not a live "one rule" collector — a small, static, occasionally-refreshed reference table, the same category as the Kaggle CSV import (`collectors/kaggle_import.py`), not a scheduled poller. Not yet built.
- **Base year**: deflate to the most recently *fully completed* year's dollars (2025 as of this writing), re-based forward each year rather than pinned to a fixed distant base year — so headline figures always read as "in today's money" for whoever is looking at them.
- **Applies to**: tournament prize pool by year (both the raw real-dollar trend and the real-dollar version of §5c's intensity ratio).

### 5e. Primary synthesis — logistic (S-curve) growth model

Fit a logistic curve to the two long-run series (category-wide Twitch hours; real tournament prize pool by completed year) and ask whether the current value sits within a tolerance band of the estimated asymptote (*K*), reporting a confidence interval on *K* rather than a bare point estimate — ~11 years of usable history is not a lot to pin an asymptote down precisely, and that uncertainty should be visible on the chart, not hidden by presenting one fitted line as settled fact.

This is the natural fit both statistically (the standard product-lifecycle/diffusion curve) and thematically: it is *literally* the equation underlying Gause's Law itself — population growth toward a carrying capacity. Framing "has CS finished growing" as "how close is it to its estimated *K*" ties this brief's method directly to the project's own established ecological framing, without forcing the two briefs' research questions together (§3).

**Triangulation, so the S-curve doesn't carry the whole conclusion alone**: trailing 3-year YoY growth rate per metric; the §5e concentration/HHI trend; and a cross-title comparison against a title clearly still growing (VALORANT) and one of comparable vintage (Dota 2) as baselines — if CS's curve flattens while comparably-aged Dota 2's doesn't, that's a CS-specific finding; if both flatten together, that points to something industry-wide instead (§2, sub-question 5).

## 6. Deliverable requirements (audience: industry executives)

- Every underlying metric (§5a's four dimensions, plus §5c's intensity ratio) shown as **its own trajectory over time first**, before any composite view — transparency over persuasion-by-omission. An executive's own analyst should be able to trace any composite claim back to a specific, inspectable chart.
- The composite S-curve fit shown **last**, as the synthesizing view, with its uncertainty band on *K* visible, not a bare point estimate presented as certain.
- Confounds (§5b: CS2 relaunch, COVID, partial-year censoring) labeled **directly on the charts themselves**, not relegated to a footnote or methods appendix a reader has to go find.
- Chart design itself is a build-time decision (the project's `dataviz` skill/conventions apply once building starts) — not further specified here.

## 7. Prerequisites / operational notes

- `viewership_snapshots.broadcast_tier` — re-run 2026-09-09 (`python etl/classify_broadcast_tier.py`, after this session's `--rebuild` recovery work had left it unset for every title). Results and what they mean for this brief are in §4.
- Steam player-count and broadcast-tier Twitch hours both remain prospective-only (§4) regardless of when this brief's first analysis runs — worth explicitly starting/continuing their clock now independent of today's answer, so a future rerun of this same analysis has genuinely esports-specific series available instead of relying solely on the category-wide Twitch proxy.
- **The CPI reference table (§5d) is built**, `data/reference/cpi_deflator.csv` — sourced from FRED's `CPIAUCNS` series (a direct public mirror of BLS's own CPI-U, All Urban Consumers, All Items, Not Seasonally Adjusted; cross-validated against BLS's own public API for 2024, which matched exactly), monthly data averaged to annual, base year 2025 (the most recently fully-completed calendar year as of this build — 2025 itself only had 11 of 12 months, October missing due to a lapse in appropriations, matching BLS's own published annual figure for the same reason).
- **`config/channels.yaml` — curated for CS 2026-09-09** (`blastpremier`, `eslcs`, `betboom_cs_ru` — reviewed against `notebooks/official_channel_candidates.ipynb`'s draft, not a blind copy; several higher-viewer-time candidates from the same draft were deliberately excluded as personality/co-stream channels, not organizer broadcasts). Two genuinely different fields, easy to conflate: `is_official_broadcast` (what `channels.yaml` gates, baked in at *capture time* — `collectors/twitch_poll.py`, deliberately, since channels change season to season and a later `channels.yaml` must not retroactively relabel an earlier era) vs. `broadcast_tier` (computed after the fact, retroactively re-runnable over full history at any time). This brief's esports-specific signal is `broadcast_tier`, not `is_official_broadcast` directly — but `broadcast_tier`'s own `primary_official` value *is* just `is_official_broadcast=1` read back, so it inherits the same capture-time dependency one level removed. **Practical effect of curating it today**: every CS snapshot collected *before* 2026-09-09 stays exactly as classified (§4's 919 `detected_costream` / 0 `primary_official` / 31,785 `general` numbers, permanent for that window) — only polls from now on can produce `primary_official` rows for these three channels. So this brief's eventual analysis will need to treat the esports-specific-attention series as having a **quality break at 2026-09-09**, not a uniform-confidence series end to end — worth stating on the chart itself (§6), not just here.

## 8. Open decisions

- Whether §5b's COVID-period treatment should be a new, dedicated methodology here or should explicitly reuse whatever `esports_share_of_twitch.ipynb`/H1 already establish — not yet checked.
- **Deliverable format — first pass built as a notebook**, `notebooks/cs_growth_trajectory.ipynb` (2026-09-09), matching this project's existing pattern (executed in place, real output embedded). The standalone executive-facing packaging question is still open — this is working analysis, not that deliverable yet.

## 9. Findings from the first run (2026-09-09)

No single metric answers the headline question cleanly — deliberately, per §5a's four-dimension design, since a false answer from one metric was exactly what that was meant to avoid.

**A real, load-bearing coverage gap found while building this**: the Kaggle category-wide Twitch dataset ends 2024-09, and this project's own `own_collector` polling only starts 2026-08 — a genuine ~23-month blind spot with zero category-wide attention data for CS (confirmed dataset-wide, not CS-specific: VALORANT and Dota 2 show the identical cutoff). The single most useful thing to do next for this brief specifically is close that gap going forward — it already is, passively, as `own_collector` and the newly-curated `config/channels.yaml` keep accumulating — there's no way to backfill 2024-2025 itself.

**Against "finished growing"**: 2025's real (CPI-deflated, 2025 dollars) tier-1/2 prize pool is a genuine record — about 10% above the prior 2020 real peak, not just a nominal one (the deflator changes this read: nominally 2025 barely edges past 2020). Within-title prize-money concentration (HHI/top-3 share, `get_concentration()` applied within CS) is at the low end of the 2016-2025 window — the opposite of a market consolidating into a few dominant flagship events.

**Against "still growing" cleanly**: tournament count, hours-watched-per-tournament intensity, and the flagship single event's own prize pool (`get_championship_windows()`) all show a shared 2021-2023 trough that has only partially recovered — none has clearly exceeded its own 2018-2021-era peak in the most recent complete data. Tournament count specifically continued down into 2025 (45, below even 2022's low of 43) rather than recovering.

**The logistic (S-curve) fit — attempted, and it failed informatively.** Both series it was fit to (category-wide hours, real prize pool) came back with a standard error on the estimated asymptote *larger than the estimate itself* (221% and ~48,000% of *K*, respectively) — the model is effectively unidentified on this data. That's a real finding, not a failed analysis to discard: a logistic curve assumes monotonic approach to a ceiling, and CS's actual shape (rise → COVID surge → CS2-transition trough → partial, uneven recovery) structurally isn't that. A market cleanly saturating would show smooth deceleration; CS instead shows a real shock-and-recovery pattern. The notebook reports this directly rather than forcing a "CS is at N% of its ceiling" headline the data doesn't support.

**Read overall**: not "finished growing" in the sense of a market smoothly maturing to a ceiling — more a title that took a real, multi-metric hit around its 2023 engine transition and remains in a partial, uneven recovery from it, further along on money than on raw activity and per-event audience depth.

**Robustness check, added same day**: does the Esports World Cup (Saudi state-backed, launched 2024) drive the real-prize-pool-record finding on its own? Checked directly — and found a broader lineage than the name alone suggested: EWC's direct predecessors, Gamers Without Borders (2020-2021) and Gamers8 (2023), share the same funding source and were already in this dataset, including 2020's own flagship event (§7's "2020 peak," the exact baseline the record claim was measured against). Excluding the *whole* lineage from every affected metric: **2025 remains the real-dollar peak of the 2016-2025 window, and the margin over 2020 widens from 10.1% to 16.7%**, since 2020 loses proportionally more of its total than 2025 does. Concentration (§6) shifts by at most 0.003 HHI in any year — negligible. The one flagship-event change (§7): 2020's credited event switches from "Gamers Without Borders/2020" to "ESL/One/2020/Rio," which happens to tie it exactly at $2M, so even that chart's shape is unaffected. A real, well-motivated confound to check, and checking it directly (rather than assuming either way) left the prize-pool finding intact — slightly strengthened, not weakened.
- Deliverable format: a notebook (`notebooks/cs_growth_trajectory.ipynb`, matching this project's existing pattern) vs. something more directly executive-facing (a standalone report/deck built from the notebook's outputs) — notebook-first either way, but worth deciding the final packaging before that stage.
