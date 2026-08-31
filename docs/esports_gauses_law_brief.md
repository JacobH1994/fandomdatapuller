# Esports & Competitive Exclusion: Research Brief (Post 2)

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

## 7. Limitations — state explicitly, keep conclusions tentative

1. **Is the resource actually shared?** Gause's paramecia had no choice but to compete for one resource. Esports fans multi-home — many LoL viewers also watch VALORANT. If audience overlap is high, "crowding out" may be the wrong model. No current source measures this (aggregate hours-watched can't distinguish overlapping from disjoint audiences). Treat as an open question, not an assumption.
2. **Survivorship bias.** The dataset, like Liquipedia's coverage generally, mostly sees titles that got big enough to register. For Post 1's question this skews a denominator; for Post 2's exclusion question, the *failed challengers per niche-cell are the actual evidence*. A cell with one winner and no visible competitor is ambiguous between "no attempt" and "an attempt that got excluded." At minimum, do a qualitative pass on notable failed attempts per occupied cell, flagged as directional rather than rigorous.
3. **Structural death is not competitive death.** Overwatch is the one clean same-niche implosion in the dataset, which makes it tempting to read as an exclusion casualty. Reporting on its collapse points mainly to a flawed franchise business model and an Activision Blizzard scandal that drove sponsors away, with viewership declining alongside — not an obvious rival hero-shooter displacing it. State explicitly which deaths are being counted as "excluded" vs. "died for unrelated reasons."
4. **Game fandom vs. esports fandom conflation.** Several planned data sources — notably raw Twitch category hours-watched — measure game fandom diluted with esports fandom, not esports fandom specifically. See §4 and the mitigation built into §8's data plan.

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
