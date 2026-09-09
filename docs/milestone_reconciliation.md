# Milestone reconciliation: differences and reasoning

PRD §9 requires `get_success_milestone`'s pipeline output to reconcile
against the hand-built milestone table (`data/manual/milestone_table.csv`),
with every discrepancy "either explained or corrected" before Phase 2
counts as done. As of 2026-09-05 (categories last refreshed 2026-09-09,
see Category B below), all 23 active titles still show a disagreement by
strict year-match — but every one now falls into a specific, understood
category below, rather than an undifferentiated mismatch count. This
document is that record; short per-title pointers also live in
`milestone_table.csv`'s own `notes` column (added by `data/manual/
normalize_original_export.py`'s `RECONCILIATION_NOTES`).

Reproduce this yourself: `notebooks/reconciliation.ipynb`, re-run top to
bottom. Its final cell shows the same categorization mechanically,
alongside each title's `viewership_check` and `qualifying_window_scale`.

## Three data-quality bugs found and fixed getting here

Re-running the reconciliation surfaced three real bugs in
`collectors/liquipedia.py` / `analysis/metrics.py` — not just definitional
differences. All three were silently corrupting pipeline input before
anyone had reconciled against an independent source to catch them.

### 1. HTML comments leaking into `tournaments.tier`

Liquipedia editors commonly leave a rationale comment immediately after a
field's value, e.g.:

```
|liquipediatier=2<!-- Tier was discussed on Discord: https://discord.com/... -->
```

`parse_infobox`'s field extractor used a raw `str()` of the template
parameter's wikitext value, which preserves that trailing comment
verbatim. `analysis/metrics.py`'s qualifying-tier check is an exact
`tier in {"1", "2"}` membership test, so `"2<!-- ... -->"` silently failed
it — the tournament was dropped from milestone computation as if it never
existed, with no error or warning.

**Fix (commit `3df651b`):** use `strip_code()` (mwparserfromhell's
plain-text rendering, which drops comments/refs/templates) instead of raw
`str()`. Reprocessed all 20,344 existing `tournaments` rows directly
against their already-cached wikitext under `data/cache/liquipedia/` — no
network calls needed. 811 rows changed; tier specifically corrected for:

| title | rows corrected |
|---|---|
| street_fighter | 210 |
| tekken | 148 |
| guilty_gear | 104 |
| mortal_kombat | 39 |
| age_of_empires_ii | 5 |
| dota2 | 4 |
| hearthstone | 1 |
| pubg_mobile | 1 |

### 2. Letter-tier wikis were never handled

`collectors/liquipedia.py`'s docstring claimed the infobox's raw
`liquipediatier` value is always a plain number, with S-Tier/A-Tier vs.
Tier 1/Tier 2 being purely a *display*-category difference over the same
underlying number — "confirmed empirically" against one wiki
(teamfight_tactics) and generalized to all of them. That generalization
was false: `counter_strike` and `valorant` genuinely author
`|liquipediatier=S-Tier` / `A-Tier` / `A` as the literal field value, not
a number, confirmed directly against their cached wikitext.

Before the fix, `DEFAULT_QUALIFYING_TIERS = {"1", "2"}` matched almost
nothing on these wikis: counter_strike had 10 of 1,300 tournament rows
recognized as qualifying-tier; **valorant had zero of 341**.
`get_success_milestone` returned no milestone at all for either title —
not a wrong year, no answer whatsoever, for two of this project's largest
tracked titles.

**Fix (commit `bbe18d9`):** `analysis/metrics.py` gained
`_normalize_tier`, mapping `S`/`S-Tier` → `"1"` and `A`/`A-Tier` → `"2"`
before the qualifying check. This isn't a fresh interpretation — it
extends a precedent `collectors/liquipedia.py` already establishes
elsewhere: `TIER_CONVENTIONS` already treats the category pair
`"S-Tier Tournaments"`/`"A-Tier Tournaments"` as equivalent to
`"Tier 1 Tournaments"`/`"Tier 2 Tournaments"` for *tournament discovery*.
The milestone check was simply missing the same normalization.

Result: counter_strike now finds `milestone_year=2001`; valorant now
finds `milestone_year=2021`. Both were previously unanswerable.

### 3. A third cross-franchise contamination instance (Age of Empires II)

The first version of this bug was found and fixed on 2026-09-01
(commit `aa2d13c`): Liquipedia's shared "fighters" wiki hosts Tekken,
Street Fighter, Mortal Kombat, Guilty Gear and others under the *same*
wiki-wide tier categories, so unfiltered tournament discovery attributed
every franchise's tournaments to every tracked title sharing that wiki.
Fixed by intersecting discovery against each title's verified per-game
`"<Game> <Version> Competitions"` category.

`age_of_empires_ii` never got the same filter — its
`config/titles.yaml` entry had `liquipedia_category: null`. The
`ageofempires` wiki turns out to host Age of Empires I, II, III, IV, and
Online together under the same shared tier categories. Confirmed live:
one of the "age_of_empires_ii" tournament rows was **"Rumble for Rome"**,
dated 1998-11-14 — an Age of Empires I *"Rise of Rome"*-expansion-era
tournament, over a year before Age of Empires II even existed. 19 other
rows were explicitly named `.../AoE4/...`.

**Fix (commit `3df651b`):** added the verified `Age of Empires II
Competitions` category filter (2,650 pages, confirmed live 2026-09-05),
then pruned every existing row that didn't appear in a fresh
`discover_tournament_pages` result under the new filter. **784 of 1,260
existing rows — 62% — were contamination from other AoE titles**,
deleted. `age_of_empires_ii`'s milestone moved from an impossible
`window_start_year=1998` to `1999` (the game's actual release year).

Not systematically re-checked: whether any other tracked title has
similar un-narrowed shared-wiki contamination beyond these two known
cases. Worth a sweep if this area is revisited.

## Per-title categorization (all 23 active titles)

### Category A — era-relative-tier pattern (22 titles)

The pipeline's `milestone_year` is earlier — often by several years —
than the hand-built table's figure, consistently, across nearly every
title in this category. This is understood and documented (PRD §6, added
2026-09-04): Liquipedia's tier label reflects a tournament's standing
relative to *that title's own contemporary competitive landscape*, not a
fixed production-scale bar. A title's very first tier-1 tournament can be
tiny in absolute terms and still earn the label, because at that point it
was simply the best that existed yet for that game. The hand-built
table's figures, by contrast, were built around an implicit sense of
"this felt like it had arrived" — closer to an absolute production/
viewership threshold than a relative competitive ranking.

**Explicit decision (user instruction, 2026-09-04): do not gate
`get_success_milestone` on an absolute production-scale threshold.**
Doing so would collapse two axes — "successful" (institutional
durability, what the tier-based milestone measures) and "scale" — that
the brief keeps deliberately separate, and this pattern is a plausible
explanation for Post 1's own unexplained finding that newer successful
titles run smaller in absolute scale than the classics. Instead,
`get_success_milestone` returns `qualifying_window_scale` as a permanent
companion field: the window's actual absolute prize-pool (broken out per
currency — never blended, since `tournaments.currency` is never converted
and raw values span currencies differing by orders of magnitude) and
average team count, sitting alongside `milestone_year` rather than gating
it.

Titles in this category: league_of_legends, dota2, counter_strike,
starcraft2, hearthstone, rocket_league, rainbow_six_siege, overwatch,
guilty_gear, tekken, mortal_kombat, valorant, apex_legends, fortnite,
pubg, pubg_mobile, free_fire, mobile_legends_bb, wild_rift,
teamfight_tactics, brawl_stars, age_of_empires_ii (22 titles as of
2026-09-09 — tekken and mortal_kombat moved here from the now-superseded
Category B above).

**The viewership clause is a related, separate axis.** The brief's full
definition also requires viewership "flat or growing" over the qualifying
window — `get_success_milestone` now evaluates this
(`viewership_check`), reading `viewership_snapshots` (official-broadcast
Twitch data, collection started 2026-08-31) first, falling back to the
Kaggle "Evolution of Top Games on Twitch" import
(`monthly_category_history`, category-wide and not esports-specific,
`confidence=proxy_estimate`, floor of 2016) when Twitch has no coverage.
As of 2026-09-05, 12 of these 20 titles (anything with a qualifying
window starting 2016 or later) get a real evaluated result; the rest stay
`None` — an honest "not automatable this far back," not a silent pass —
since their windows predate both sources. Of the 12 evaluated, 7 come
back "declining" under a strict flat-or-growing rule (overwatch,
apex_legends, fortnite, pubg_mobile, wild_rift, teamfight_tactics,
brawl_stars). This is informational only right now:
`get_success_milestone` does not gate `milestone_year` on this clause,
and a category-wide proxy's "decline" could reflect a game's whole
population cooling off rather than its competitive scene specifically.
Whether `milestone_year` should eventually be gated on this clause, to
match the brief's literal three-part definition, is an open design
question — not decided either way.

### Category B — superseded 2026-09-09 by the generational-continuity policy

This category, as originally written, no longer applies. It argued
tekken's and mortal_kombat's mismatch against the hand-built table could
never be closed, because this project tracked only the *current*
generation of each fighting-game franchise (`config/titles.yaml`'s
documented judgment call at the time) while the hand-built figures
described an earlier generation — two different products, not
comparable. That premise itself changed on 2026-09-09: per
`docs/system_reference.md`'s "Generational continuity" note,
`config/titles.yaml` and `collectors/liquipedia.py` now track every
generation of each fighting-game franchise as one continuous entity, the
same policy `counter_strike` already used. Re-running the crawl under
that policy moved all four fighting-game titles' pipeline milestones
much earlier (confirmed by re-executing `reconciliation.ipynb` against
current data, 2026-09-09):

| title | milestone before | milestone after |
|---|---|---|
| tekken | 2025 | 2008 |
| street_fighter | 2024 | 2008 |
| mortal_kombat | 2024 | 2012 |
| guilty_gear | 2022 | 2010 |

tekken and mortal_kombat aren't a "different product entirely" gap
anymore — the pipeline milestone is now *earlier* than the hand-built
figure (2018, 2015 respectively) rather than later, the same era-relative-
tier pattern every other title in Category A shows, not a distinct
mechanism. Both are reclassified into Category A below. guilty_gear
(previously in Category A already, on a smaller pre-fix gap) and
street_fighter (Category C, no hand-built comparison exists) shifted
earlier by the same mechanism and keep their existing category, just
with updated numbers.

### Category C — intentionally absent from the manual table (1 title)

- **street_fighter**: the original hand-built export merged Tekken and
  Street Fighter into one row, "Fighting Games (SF/Tekken)"
  (`data/manual/README.md`, `normalize_original_export.py`). Resolved
  2026-09-05, per instruction to treat them as the distinct esports they
  are: the row's only concrete corroborating evidence (TWT viewership) is
  Tekken-specific, so the row is mapped to `tekken` alone.
  `street_fighter` is deliberately left out of `milestone_table.csv`
  entirely — a genuine "the hand-built table never independently assessed
  this title," not a guessed figure borrowed from Tekken's evidence, and
  not the same thing as "reached the milestone: no." The reconciliation
  notebook reports this as `MISSING_IN_MANUAL`, distinct from `MISMATCH`.

## Still open

- The per-title explanations above exist in this document, in
  `milestone_table.csv`'s notes, and in commit history — but
  `milestone_year` itself has not been changed for any Category A/B
  title, since the brief's literal definition and this project's
  measurement of it are both internally consistent; only the *comparison*
  to the hand-built table is explained, not "corrected" toward it.
- A `rocket_league` tournament row has a malformed `start_date`
  (`"<s>2"`, likely leaked HTML from a Liquipedia infobox parse) —
  flagged during the tier-inflation investigation, never fixed.
- Whether the viewership clause should eventually gate `milestone_year`
  (Category A, above) is unresolved.
- No systematic sweep for further shared-wiki contamination beyond the
  two known instances (fighting games, Age of Empires) has been done.
