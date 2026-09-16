# Does Attention Concentrate Even as Production Fragments?

Part of `inter_esports_dynamics` — see `../../brief.md` §3 (taxonomy
bucket 3: platform-level concentration vs. fragmentation). Formerly
labeled H3, named 2026-09-09 formalizing the area brief's original
research question 3.

## 1. Hypothesis

Two things happening at once, not one: the Twitch work already found
platform *attention* concentrating hard within esports (esports' own
share of top-200 Twitch attention nearly halved 2016-2024, and Just
Chatting/GTA V drove most of the platform's growth —
`../../notebooks/esports_share_of_twitch.ipynb`). This hypothesis asks
whether *production* is doing the opposite at the same time — more
titles being made, a longer tail, even as the audience's attention
concentrates onto fewer winners within any given niche. If both are true
simultaneously, that's the emergence-and-consolidation pattern Post 1
already found for esports specifically (rising emergence rate, smaller
individual scale) showing up one level up, as a general property of
digital-fandom production and attention rather than something specific
to esports.

**Directly extended, one level further, by `../../../wider_game_fandoms/brief.md`**
§3 (its own open question 2): what does this look like across all of
Twitch, not just the 23 tracked titles. Not yet a named sub-test there —
a live connection, not duplicated as a second hypothesis until there's
actually something to test.

## 2. Tests — two independent sub-tests on different datasets, not the same claim measured twice

- **Supply side — Steam production composition** (PRD §9.12a): indie vs.
  core (AAA) release volume and lifecycle-shape comparison, drawn from a
  full historical Steam catalog backfill (`collectors/steam_catalog_backfill.py`,
  in progress). Tests whether game *production* is fragmenting (more
  indie, more studios, longer tail) on a dataset entirely outside
  esports.
- **Demand side — championship-viewership concentration within esports
  itself** (PRD §9.3a): for each tracked title, its highest-prize-pool
  tier-1 tournament per year (`analysis/metrics.py:get_championship_windows`
  — 283 windows across all 23 titles as of the current corrected count,
  see §3) as an objective "world championship window," with peak
  viewership pooled across titles per year to compute HHI/top-3 share
  and a power-law-vs-log-normal fit over time. **Paused, not built**: the
  peak-viewership figure this needs was meant to come from Esports
  Charts, and automated access there is confirmed blocked (checked
  directly, PRD §9.3) — this sub-test has no confirmed data source yet,
  only the window-identification half.

## 3. A real bug found and fixed along the way, directly relevant if this sub-test resumes

`get_championship_windows()` originally picked the numerically-largest
`prize_pool` with no currency normalization — a raw KRW/CNY/JPY/etc.
figure could (and did) beat a much larger real-USD prize purely on
magnitude. Affected 95 of 291 windows at the time (32.6%), including
*every* `league_of_legends` year 2012-2025. Fixed to require
`currency='USD'` or `currency IS NULL`; a title-year whose only
candidate is non-USD now correctly gets no window rather than a wrong
one (hence 291→283, not just the 95 rows changing value). Covered by
three new tests in `tests/test_metrics.py`. Found while building
`research/esports_lifecycle_and_maturity/notebooks/dota2_growth_trajectory.ipynb`,
not while working on this question-brief directly — recorded here since
this function is this question's own citation.

## 4. Open items

- The demand-side sub-test has no confirmed data source — decide whether
  to pursue an Esports Charts enterprise conversation (shared with
  `../competitive_exclusion_in_niches/`'s own open item on this) or drop
  this sub-test.
- The supply-side sub-test's dependency (`collectors/steam_catalog_backfill.py`)
  is a slow, intermittent background job — check current progress before
  assuming this sub-test is ready to run.
