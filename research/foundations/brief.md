# Foundations

Added 2026-09-16, split out from `inter_esports_dynamics/brief.md` and
`wider_game_fandoms/fandom_historical_contingency/` once it became clear
both were carrying genuinely general-purpose material that every research
area depends on, not material owned by one of them.

## What this layer is

**The overarching intellectual project here is digital fandom
formation** — not esports specifically. Esports (`inter_esports_dynamics`
+ `esports_lifecycle_and_maturity`) is the first, deepest case study
within that project, chosen because the professional audience this
project's writing is aimed at is esports-industry-adjacent and because
this project's own data is richest there (23 tracked titles, tournament
records, years of category history). `wider_game_fandoms` is the
already-designated on-ramp for broadening scope to non-esports fandoms,
expected once the esports work matures, not a hedge held in reserve.

That relationship — general frame, esports-first application — is the
design principle for everything in this folder: **built for generality,
validated and applied esports-first.** A model that only works for
esports isn't actually a foundation, it's just `inter_esports_dynamics`'s
own preamble wearing a bigger folder name.

## What lives here, and why each is foundational rather than area-owned

- **`esports_vs_game_fandom_signal_model/`** — before any question in any
  area can be answered honestly, this project needs to know what its own
  data sources actually measure: esports-specific engagement, general
  game engagement, or something ambiguous between the two. Every area
  reuses the same underlying signals (Twitch viewership, Steam reviews,
  creator/channel data), so this can't be re-derived per area without
  drifting into three inconsistent answers to the same question.
- **`fandom_and_niche_model/`** — the `{genre × platform × region}` niche
  cell is a *model*, not a fact, and it's already load-bearing for
  research questions across multiple areas. Treating it as a free
  definition anywhere would smuggle in an unproven claim as though it
  were settled.
- **`technological_contingency_of_fandom_formation/`** — the claim that
  how a fandom forms is contingent on the technological and social
  conditions available at the moment it forms. Not unique to esports:
  digital fandom as a category only exists because of internet access,
  affordable personal computing, and livestreaming. Esports' own
  emergence eras (Classic/Console/Second Coming) are this claim's first
  case study, not the claim itself.

## Status and sequencing

Each brief below carries its own explicit status marker
(`PENDING`/`ADOPTED`) — `ADOPTED` means a deliberate, evidence-based
decision has been made to build on it, not that it's beyond revision.
Downstream question-briefs cite an `ADOPTED` model rather than
re-arguing it; a `PENDING` one should be read as "in use provisionally,
not yet load-bearing for a headline claim."

Working order, agreed 2026-09-16:

1. **`esports_vs_game_fandom_signal_model`** — first, because it settles
   what this project's core construct (esports fandom, for the current
   esports-first application) actually means, and every other piece
   reads its evidence through that lens.
2. **`fandom_and_niche_model`** — second, now properly informed by (1)
   rather than assuming a fandom definition it doesn't have yet. This is
   the actual next research task for the project as a whole, ahead of
   resuming any `inter_esports_dynamics/questions/` work.
3. **`technological_contingency_of_fandom_formation`** — not blocking
   either of the above, and cheaper to formalize since real evidence
   already exists (`streamer_ecosystem_by_phase.ipynb`'s finding is most
   of a first draft). High-value once `inter_esports_dynamics` resumes:
   see that brief's own connection to the old H1 cohort-differentiation
   story.
