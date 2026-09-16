# The Niche Model: Definitions and Evidence

Part of `foundations/` — see `../brief.md`. **Status: PENDING** — real
evidence exists (§3), but not yet enough to move this to `ADOPTED`; §5
lists exactly what's missing. Second foundational task, after
`../esports_vs_game_fandom_signal_model/`.

## 1. Why this is foundational, not area-owned

The `{genre × platform × region}` niche cell is a *model* — a claim about
how audiences are structured — not a fact, and not a free definition.
`inter_esports_dynamics/questions/competitive_exclusion_in_niches/` needs
it to even be well-posed as a question; `esports_lifecycle_and_maturity`
implicitly leans on the same cell structure when comparing a title
against peers of "its own kind." Defining it at the level of one area
would let that area's own theoretical priors (originally: Gause's Law)
leak into what's supposed to be a neutral unit of analysis. Moved here
2026-09-16 for exactly that reason.

## 2. Scoping definitions (carried forward from Post 1)

- **Esports**: professional (financially incentivized, including salary)
  play of video games as a broadcast / media & entertainment product.
  Excludes grassroots "structured play."
- **Successful esport**: minimum 2-year history of A-tier-or-better
  competition across at least 2 continents, with viewership flat or
  growing over that period.
- **Niche** (the model under test here): a `{genre × platform × primary
  market/region}` cell — an operationalization of the genre/platform/
  market triangle Post 1's own prose ends on. Genre/platform
  categorization is currently inferred from that prose, not yet a fully
  systematic data column (see `config/titles.yaml`'s `genre`/`platform`
  fields, still `ai_assisted_unreviewed` confidence for all 23 titles).

## 3. Evidence so far

**First concrete shared-occupancy candidate, `notebooks/niche_membership.ipynb`,
checked 2026-09-12 — and it isn't the pair either of the original named
hypotheses predicted.** That notebook's audience-language-similarity
test, restricted to pairs clean of sample-size and live-tournament-
contamination issues (13 same-cell pairs total, only 3 survive that
filter this window), finds **Apex Legends and PUBG: BATTLEGROUNDS**
(`battle_royale`/`pc_console`) with the highest similarity *and* lowest
distance of the confident set — both metrics agreeing, not one an
artifact of the other. That's a real complication for a "genre/platform
differentiate audiences cleanly" reading, at least for this specific
pair (Apex/Fortnite, same cell, shows the opposite — lowest similarity
in the whole table). Directional only: one Twitch-language snapshot
under two weeks old, re-check once `language_mix_snapshots` has real
history.

**Six notebooks now formally assigned here**, each a data point toward
whether niches behave as real, coherent units:

- `notebooks/niche_membership.ipynb` — the audience-similarity test
  above; the primary evidence source for this brief.
- `notebooks/niche_stacked_area.ipynb` — per genre×platform cell,
  absolute-hours and 100%-normalized stacks over time (is the niche
  growing; is competitive balance shifting within it).
- `notebooks/title_geography_maps.ipynb` — six-title choropleth
  comparison of tournament-host country vs. audience-implied geography —
  a direct reading of whether *region*, one leg of the niche-cell
  triangle, actually differentiates the way the model assumes.
- `../esports_vs_game_fandom_signal_model/`'s own infrastructure —
  `analysis/fandom_region_decomposition.py` plus two notebooks that live
  in `../../inter_esports_dynamics/notebooks/` (`english_fandom_decomposition.ipynb`,
  `steam_review_playerbase_over_time.ipynb`) — built to answer
  whether "two titles' audiences look similar" means "actually the same
  people," which bears directly on whether a niche cell is a real shared
  resource pool or an artifact of coarse categorization. See §4 for the
  UTC-offset finding this produced.
- `../../inter_esports_dynamics/notebooks/creator_crossover.ipynb` — the
  creator-side (not viewer-side) analogue: does a niche cell's *creator*
  population overlap the way the audience-side evidence above suggests,
  or differently.

## 4. Is the resource actually shared? (multi-homing)

Gause's paramecia had no choice but to compete for one resource. Esports
fans multi-home — many League of Legends viewers also watch VALORANT. If
audience overlap is high, any "crowding out" hypothesis tested against a
niche cell may be the wrong model regardless of what the audience-
similarity numbers show. No single current source measures multi-homing
directly (aggregate hours-watched can't distinguish overlapping from
disjoint audiences) — treat as a genuinely open question, not an
assumption in either direction.

**Partially addressable (PRD §9.17, built 2026-09-12)**: the
English-language fandom decomposition subsystem breaks Twitch's
undifferentiated `en` tag down by likely region via timezone
deconvolution, self-declared stream tags, Wikipedia pageviews, and Steam
review data — the first infrastructure this project has that can
distinguish "two titles' audiences look similar" from "actually the same
people," at least along the region axis rather than the multi-homing
axis directly. Still not a full answer (region similarity isn't the same
claim as one person watching both titles), but a real step past "no
current source measures this."

**Extended to the whole `tac_fps`/`pc` cell, 2026-09-15**:
`rainbow_six_siege` and `valorant` added as decomposition subjects
alongside the already-configured `counter_strike`.

**A real limitation of the method itself, surfaced by running all three
together, not a title-specific finding — and now reflected in how
results are labeled, not just caveated in prose.** South Africa's fixed
UTC+2 offset is structurally indistinguishable from Central/Western
Europe (also UTC+2, but only during CEST) — see
`analysis/fandom_region_decomposition.py`'s own module docstring. The old
country-named output came back as the largest single bucket for *every*
subject in the whole registry (44–53% for Apex/PUBG/Siege/VALORANT/GTA V,
26.7% for CS specifically) — uniform-across-unrelated-subjects evidence
of a Western-Europe-shaped hole in the candidate list, not a genuine
South African finding. `decompose_by_timezone` now returns the resolved
UTC offset itself as the label (e.g. `UTC+2`) rather than a candidate
country name, with `reference_cities_for_offsets()` as a separate,
never-merged illustrative lookup. `UTC+2`'s share for CS/Siege/VALORANT
is 26.7%/53.1%/45.0% respectively — cross-checked against self-declared
tags for CS, which independently show EU+UK at ~52% of tagged streams,
consistent with `UTC+2` being mostly Europe. Adding a real Western
Europe candidate (so the seasonal auto-merge can separate it cleanly
outside CEST season) remains a real, scoped next step, not done yet.

## 5. What's left before this can move to ADOPTED

Named directly 2026-09-16: "prove the niche model to the degree
possible" is a real task, not a formality.

1. **A longer collection window.** Every finding in §3-4 is drawn from
   under two weeks of `language_mix_snapshots` history — every one of
   them is explicitly flagged directional, not settled, in its own
   notebook. Re-run the audience-similarity test once real
   multi-month history exists.
2. **A full sweep across every niche cell**, not just whichever happen
   to be uncontaminated in a given window. As of the last check, `tac_fps`/`pc`
   (Counter-Strike, Rainbow Six Siege, VALORANT) and the MOBA `pc` pair
   (League of Legends, Dota 2) were *both* tournament-contaminated
   simultaneously — a full audit needs either a wider window or repeated
   checks until every cell has had a clean read at least once.
3. **Genre/platform tag verification.** `config/titles.yaml`'s tags are
   `ai_assisted_unreviewed` for all 23 titles — the niche-cell model is
   only as good as the categorization feeding it. A human-reviewed pass,
   promoting confident tags to `verified`, is real work this status
   upgrade depends on.
4. **Live-tournament contamination discipline stays required.**
   `notebooks/niche_membership.ipynb` cross-checks `language_mix_snapshots`'
   exact window against `tournaments.start_date`/`end_date` before
   trusting any audience-similarity read — a title with a tier-1 event
   live during the window has its language mix pulled toward that
   broadcast's host region, a confound for the coexistence-vs-exclusion
   question specifically, not signal. Re-check the notebook's
   contamination table before citing any pair again; don't assume last
   quarter's clean-vs-contaminated read still holds.

## 6. Survivorship bias

The dataset, like Liquipedia's coverage generally, mostly sees titles
that got big enough to register. For a niche-cell model, the *failed
challengers per cell are the actual missing evidence* — a cell with one
winner and no visible competitor is ambiguous between "no real attempt"
and "an attempt that got excluded" (or simply never got measured). At
minimum, a qualitative pass on notable failed attempts per occupied cell
is worth doing, flagged as directional rather than rigorous. Not started.
