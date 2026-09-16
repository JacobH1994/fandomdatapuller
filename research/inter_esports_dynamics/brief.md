# Inter-Esports Dynamics: Research Area

Restructured 2026-09-16 into a genuinely neutral area document. Previously
this brief opened with the Gause's Law / competitive-exclusion framing as
the area's own organizing lens — on reflection, that pre-loads the
vocabulary of every question asked under it (primes for "exclusion" as
the default expected shape) and presupposes a dynamic this project hasn't
actually established. Gause's Law is a hypothesis this project holds
about inter-esports dynamics, not what the area *is*. It now lives as one
question-brief among several (`questions/competitive_exclusion_in_niches/`),
on equal footing with the others, not the area's own self-description.

## 1. What this area studies

Dynamics *between* esports titles — as distinct from
`esports_lifecycle_and_maturity` (one title's own trajectory,
independent of rivals) and `wider_game_fandoms` (non-esports fandom
behavior). The founding observation, from this project's original
research post ("Post 1," "Is the rate at which successful esports emerge
decreasing?"): the rate of new successful esports is *increasing*, not
decreasing, over the last 3–5 years vs. the prior 15; newer successful
titles are systematically smaller in scale than the "classic" titles
(VALORANT the one clear exception); and three emergence eras are visible
in the data (Classic 2013–15, Console 2016–20, Second Coming 2021–24 —
now formalized, with the model itself under test, in
`../foundations/technological_contingency_of_fandom_formation/`).

Post 1's own measurements are inherited context here, kept as observed
facts. Its closing speculation — that markets spontaneously adopt a
first title into an open gap, which then crowds out competitors — is the
interpretive leap this area no longer treats as settled framing; it's
`questions/competitive_exclusion_in_niches/`'s own hypothesis to test.

## 2. Shared foundations this area depends on, but doesn't own

- **The niche-cell model** (`{genre × platform × region}`) and its
  supporting definitions (esports, successful esport) —
  `../foundations/fandom_and_niche_model/`. Status: PENDING.
- **The esports-fandom/game-fandom signal model** — which data sources
  can actually support an esports-fandom claim, and how confidently —
  `../foundations/esports_vs_game_fandom_signal_model/`. Status: PENDING.
- **The emergence-era framework** (Classic/Console/Second Coming) and
  the general historical-contingency claim it's a case study of —
  `../foundations/technological_contingency_of_fandom_formation/`.

Every question-brief below should cite these rather than re-deriving
them.

## 3. Taxonomy of question-types this area houses

New research questions land in one of these, or justify a new bucket:

1. **Within-niche coexistence vs. exclusion** — does one title's share
   of a niche concentrate over time (exclusion), or do multiple titles
   sustain stable, differentiated shares (coexistence), and along what
   vector? `questions/competitive_exclusion_in_niches/`.
2. **Fandom durability/resilience** — does accumulated fandom history
   change how a title weathers shocks (a bad season, scandal, a flashy
   new competitor)? `questions/fandom_value_resilience/`.
3. **Platform-level concentration vs. fragmentation** — does attention
   concentrate even as production fragments, one level up from any
   single niche? `questions/platform_attention_concentration/`.

## 4. Question-brief index

| Question-brief | Status | Notes |
|---|---|---|
| `competitive_exclusion_in_niches/` | Active — primary evidence (tac-FPS cohort story) written, tests not yet run | Waits on `../foundations/fandom_and_niche_model` reaching ADOPTED before its own niche-level claims can be trusted |
| `fandom_value_resilience/` | Named, not tested | Needs multi-year per-title volatility data not yet in hand |
| `platform_attention_concentration/` | Active — one sub-test paused (Esports Charts blocked), one not yet started | |

**Candidates spotted but not yet written** (from §5's niche-cell survey):
Battle Royale's own differentiation story (the Apex/PUBG shared-occupancy
finding directly complicates the "fits differentiation cleanly" read),
Fighting Games' apparent structural exclusion-resistance, the MOBA PC
pair (currently untestable — tournament-contaminated), Overwatch's
competitive-vs-structural death. Not scoped further here — add a row
above and a `questions/` folder if and when one of these gets worked.

## 5. What the existing title list already shows

Genre/platform categorization below is inferred from Post 1's prose —
not yet a formal, verified data column (`../foundations/fandom_and_niche_model/`
§2).

| Genre | Coexisting successes | Pattern | Worth checking |
|---|---|---|---|
| MOBA | LoL, Dota 2 (PC) · Wild Rift, ML:BB (mobile) | Two long-running pairs | PC pair may split on complexity/region; mobile pair looks like live exclusion-in-progress, not settled. **Currently untestable**: as of the last check, both League of Legends and Dota 2 had a tier-1 event live simultaneously — see `../foundations/fandom_and_niche_model/`'s contamination discipline |
| Tac FPS (PC) | CS, VALORANT, arguably Siege | 3-way coexistence | The strongest counter-example to a simple one-winner story — see `questions/competitive_exclusion_in_niches/` |
| Battle royale | PUBG, Apex (PC/console) · PUBG Mobile, Free Fire (mobile) · Fortnite (cross-platform) | Many successes | Looked like clean differentiation (same genre, different hardware/region pools) — complicated by `../foundations/fandom_and_niche_model/`'s Apex/PUBG shared-occupancy finding |
| Fighting games | Tekken, Street Fighter, Mortal Kombat, Guilty Gear | Many, long-coexisting | Possibly structurally exclusion-resistant — differentiation baked into roster/mechanics, shared "majors" (EVO) may pool audiences rather than split them |
| Hero/arena shooter | Overwatch (alone, then gone) | No coexistence example survives | Cleanest single-niche case — but its collapse points mainly to a flawed franchise business model and a sponsor-driving scandal, not an obvious rival hero-shooter displacing it. State explicitly which deaths count as "excluded" vs. "died for unrelated reasons" if this is ever worked as its own question |
| RTS | SC2, Age of Empires | Two, ~7 years apart | Sequential, not simultaneous — probably not a real coexistence case |

## 6. Notebooks

Shared, general-purpose area evidence — none of it belongs to one
question-brief exclusively, so all of it stays here rather than under
`questions/`:

- `notebooks/creator_crossover.ipynb` — enrichment-ratio/insularity
  analysis across all 23 titles; this area's primary creator-side (not
  viewer-side) cross-title evidence.
- `notebooks/english_fandom_decomposition.ipynb`, `notebooks/steam_review_playerbase_over_time.ipynb`
  — the English-language fandom decomposition subsystem; see
  `../foundations/fandom_and_niche_model/` §4 for what it's found.
- `notebooks/category_trajectories.ipynb`, `notebooks/esports_share_of_twitch.ipynb`,
  `notebooks/present_day_snapshot.ipynb` — general viewership-trajectory
  groundwork feeding this area's whole Post-1-lineage framing.

## 7. Limitation still owned at this level

**Survivorship bias.** The dataset, like Liquipedia's coverage
generally, mostly sees titles that got big enough to register. For this
area's own exclusion-vs-coexistence question, the *failed challengers
per niche-cell are the actual missing evidence* — a cell with one winner
and no visible competitor is ambiguous between "no attempt" and "an
attempt that got excluded." At minimum, a qualitative pass on notable
failed attempts per occupied cell is worth doing, flagged as directional
rather than rigorous. Not started.

(Multi-homing/audience-overlap, live-tournament contamination, and
game-fandom-vs-esports-fandom conflation have all moved to
`../foundations/` — they're about whether the niche model or the signal
model itself is trustworthy, not specific to this area's own questions.)

## 8. Open decisions

- Decide how far to pursue an Esports Charts enterprise-tier
  conversation for demographic data — relevant mainly to
  `questions/competitive_exclusion_in_niches/`'s own cohort-test needs;
  cost may not be justified by a single question-brief.
- Decide the rigor bar for the failed-challengers pass (§7) — directional
  color vs. something closer to systematic.
