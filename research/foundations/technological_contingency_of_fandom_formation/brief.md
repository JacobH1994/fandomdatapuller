# Technological Contingency of Fandom Formation

Part of `foundations/` — see `../brief.md`. **Status: PENDING, but the
cheapest of the three foundational pieces to formalize** — real evidence
already exists (§2); third in the working order, not blocking the other
two.

Elevated here 2026-09-16 from `wider_game_fandoms/fandom_historical_contingency/`
(itself split out the same day from a single supporting notebook) once it
became clear the underlying claim isn't esports-specific at all.

## 1. The claim

**How a fandom forms is contingent on the technological and social
conditions available at the moment it forms** — not a timeless, general
process that looks the same regardless of when a title or platform
emerged. Digital fandom as a category only exists because of internet
access, affordable personal computing, and (more recently) livestreaming
— none of it is possible "in general," all of it is conditional on
infrastructure that arrived at specific points in time. Esports'
Classic (2013–15) / Console (2016–20) / Second Coming (2021–24)
emergence eras are this claim's **first case study**, not the claim
itself — the same mechanism should leave a mark on any digital fandom
that formed under different platform/technology conditions, esports or
not.

## 2. Case study 1: esports emergence eras

`streamer_ecosystem_by_phase.ipynb` was originally built inside
`research/esports_lifecycle_and_maturity/` (split out of
`cs_growth_trajectory.ipynb`'s own §18) to ask a narrower question, per
the Classic/Console/Second-Coming framework: do newer esports titles
simply have bigger creator ecosystems than older ones? Expanded to all
23 tracked titles across all 4 eras, the answer turned out to be more
specific and more interesting than "yes, newer is bigger":

- Fortnite (11.2M peak distinct monthly streamers), VALORANT (4.8M), and
  Apex Legends (4.7M) do dwarf every Classic- and Console-era title.
- But the rest of the Second Coming cohort does **not** follow that
  pattern: PUBG (1.85M) sits in the same range as Console-era Rocket
  League/Rainbow Six Siege/Overwatch (2.1-2.3M) and Classic-era
  Counter-Strike (1.85M); every mobile Second Coming title (Free Fire,
  Brawl Stars, Teamfight Tactics, PUBG Mobile, Wild Rift, Mobile Legends:
  Bang Bang) sits at or below Classic-era Dota 2/Hearthstone (642K).
- Dota 2 is the clearest outlier at the bottom of its own era — 336K-643K
  distinct streamers, smaller than several Second Coming *and*
  Console-era titles, despite total viewership hours comparable to or
  exceeding several of them.

**The revised read**: it isn't "newer titles have bigger creator
ecosystems" in general — it's that a specific handful of broad-audience,
easy-to-clip titles (the battle-royale/hero-shooter cohort built by
Epic/Riot/Respawn) do, and several of them happen to be recent. That's
already more specific than a naive era-model would predict, and it's
exactly the shape of evidence this brief's general claim (§1) needs:
not "newer = different" uniformly, but a *specific, identifiable
technological/cultural condition* (broad-audience, high-clip-affinity
platforms and mechanics) doing the actual work.

## 3. Research question (draft, not final)

**Does a title's era of emergence structurally shape its fandom/creator
ecosystem — not through a general "newer is bigger" trend, but through
specific historically-contingent mechanisms (which platforms existed,
which organizations were building audiences at the time, what
clip/stream culture looked like when the title launched)?** This is not
yet decomposed into named sub-mechanisms — §2's finding is suggestive
(a specific cohort, not a general trend) but doesn't yet pin down *which*
historical factors are doing the work. That's the next real piece of
work here, not something to guess at in this document.

## 4. A concrete forward connection, worth flagging now

`inter_esports_dynamics/questions/competitive_exclusion_in_niches/`
(formerly named H1) argues Counter-Strike, VALORANT, and Rainbow Six
Siege coexist in the `tac_fps`/`pc` niche because the niche split by age
cohort — VALORANT capturing a younger audience largely during its 2020
COVID-lockdown, Twitch-drops-gated beta. **That's already a
technological/social-contingency explanation in miniature**: a specific
condition present at the exact moment of VALORANT's emergence (lockdown
liquidity + a forcing-function access mechanic) shaped who its fandom
became, independent of any competitive-exclusion dynamic. Once this
brief has more than one case study, `competitive_exclusion_in_niches`
has a genuine alternative hypothesis to test against — not "does
exclusion explain tac-FPS coexistence" alone, but "is this contingency
doing some or all of the explaining instead."

## 5. Open items

- The research question (§3) needs sharpening — the immediate next step,
  not a data-collection task.
- No new data source identified yet — `streamer_ecosystem_by_phase.ipynb`
  draws on the same Kaggle `Streamers` column every other era-comparison
  notebook in this project uses; whether this brief needs something new
  (platform-launch-date data, organization-founding dates) is unresolved.
- **Case study 2 candidate**: `wider_game_fandoms/gta_launch_case_study/`'s
  GTA 6 work — untested whether this brief's mechanism-question even
  applies outside a multi-title, competitive-gaming "era" context, or
  needs a parallel, separately-derived framework for a single-title
  launch moment. Not assumed either way.
- Whether this brief's eventual findings should feed back into a
  revision of the Classic/Console/Second-Coming boundaries themselves,
  or whether those boundaries are stable enough to treat as fixed
  infrastructure regardless of what mechanism explains the pattern
  within them.
