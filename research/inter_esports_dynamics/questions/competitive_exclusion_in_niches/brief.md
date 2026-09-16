# Does Competitive Exclusion Explain Niche Dynamics?

Part of `inter_esports_dynamics` — see `../../brief.md` §3 (taxonomy
bucket 1: within-niche coexistence vs. exclusion). Formerly this area's
own framing device ("Gause's Law"); demoted 2026-09-16 to one hypothesis
among several, per the concern that foregrounding it at the area level
presupposed a dynamic rather than testing one. Formerly labeled H1
(cohort-differentiation mechanism) plus the area brief's own theoretical
framework section — merged here since the framework and its primary
worked example were never really separable.

**Depends on `../../../foundations/fandom_and_niche_model/` reaching
ADOPTED** before any niche-level claim here can be fully trusted — the
niche-cell unit this question is posed in terms of is itself still
PENDING.

## 1. Theoretical framework

Pure competitive exclusion (Gause's Law) assumes competitors draw on a
**fixed** resource pool. Post 1's own headline finding — more successful
esports, not fewer — says the pool isn't fixed; new "habitat" keeps
opening as platforms mature, regions come online, and genres get
invented. The better fit, if this hypothesis holds at all, is **adaptive
radiation followed by competitive exclusion**: new habitat opens, a
burst of new successful titles fills it, and exclusion sorts the
winner(s) *within* each new niche over time.

This reframe would explain two Post 1 findings at once, if it holds:

- Rising emergence rate = radiation into newly available habitat.
- Scale stratification / incumbent dominance (LoL and CS pulling away in
  seat cap, prize pool, and peak viewers) = exclusion working itself out
  within already-occupied niches.

**Working rule for coexistence vs. exclusion-in-progress** *(provisional
— revisit once real time-series data is in hand)*: within a niche-cell
containing 2+ successful titles, if the leading title's share of
cell-level attention has risen for several consecutive years while
others' fell, treat it as exclusion-in-progress. If shares have stayed
within a roughly stable band over the same window, treat it as
coexistence, and go looking for the differentiation vector sustaining
it. A cell with a single successful title is ambiguous by default — it
may mean no real contest occurred, or that one occurred and resolved
before this dataset's window starts.

## 2. Primary hypothesis — cohort differentiation in PC tac-FPS

CS, VALORANT, and (to a lesser extent) Siege coexist not because
tac-FPS-PC is undersaturated, but because the niche has split by **age
cohort** — a long-tenured CS audience and a younger VALORANT audience
acquired disproportionately during 2020.

This is likely compounded, not singular. VALORANT's closed beta (April
2020) ran almost entirely on Twitch-drops access — viewers had to link
accounts and watch specific streamers to earn a key — driving beta
viewership past 1.7M concurrent before public launch. Coverage from that
week credits both the lockdown context (spare attention to give) and the
drops mechanic (a forcing function that captured it). Riot also pointed
an existing League of Legends audience directly at the new title.
COVID-liquidity and deliberate audience capture likely reinforced each
other rather than competing as explanations.

**A genuine alternative worth testing before concluding this is
exclusion-resolved-by-differentiation at all**: see
`../../../foundations/technological_contingency_of_fandom_formation/`
§4 — VALORANT's 2020 capture mechanism is itself a technological/social-
contingency story, independent of any competitive dynamic with CS. This
question-brief should test both explanations against each other, not
assume competitive exclusion is the operative mechanism just because a
cohort split is visible.

**Tests:**

- *Cross-title/cross-genre check* — if COVID-liquidity is a general
  phenomenon, other unrelated 2020-breakout titles (Fall Guys, Among Us)
  and Rocket League's own 2020 trajectory should show comparable
  anomalous stickiness. If only VALORANT shows it, the marketing/halo
  explanation is doing more work than the liquidity one.
- *Direct cohort test* — age/gender breakdowns by title, if obtainable
  (Esports Charts' enterprise tier advertises this; cost and access
  unconfirmed).
- *Baseline comparison* — pre-2020 tac-FPS launch curves (CS:GO's or
  Siege's own early growth) as a reference for judging whether
  VALORANT's curve is genuinely anomalous, not just a normal successful
  launch.

## 3. Current evidence

`tac_fps`/`pc`'s own audience-similarity read (`../../../foundations/fandom_and_niche_model/notebooks/niche_membership.ipynb`)
is currently **not testable** — as of the last check, Counter-Strike,
Rainbow Six Siege, and VALORANT all had a tier-1 event live
simultaneously, pulling all three titles' language mix toward their own
broadcast's host region at once. Re-check once that contamination clears
before citing a `tac_fps`/`pc` audience-similarity number here.

## 4. Data & variables needed

| Variable | Why | Source | Status |
|---|---|---|---|
| Age/gender breakdown per title | Direct test of the cohort claim | Esports Charts enterprise tier | Cost/access unconfirmed — worth a scoping email |
| Pre-2020 tac-FPS launch curves | Baseline for judging whether VALORANT's growth is genuinely anomalous | Liquipedia + Esports Charts, historical | Not started |
| 2020-vintage breakout titles outside esports (Fall Guys, Among Us) | Tests whether COVID-liquidity is general or VALORANT-specific | Historical Twitch data or the Kaggle "top games" dataset | Not started |

## 5. Open decisions

- Firm up the coexistence/exclusion threshold rule (§1) once real
  multi-year, per-cell data exists — the current version is a starting
  point, not a final rule.
- Decide whether this question-brief tests the cohort-differentiation
  and technological-contingency explanations as competing hypotheses
  from the start, or resolves the cohort story first and treats
  contingency as a follow-up robustness check.
