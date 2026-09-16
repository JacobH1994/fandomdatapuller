# Esports Fandom vs. Game Fandom: A Signal Model

Part of `foundations/` — see `../brief.md` for why this sits above the
research areas rather than inside one. **Status: PENDING.** This is the
first foundational task, ahead of `fandom_and_niche_model`.

## 1. Why this exists

Every area in this project reuses the same handful of underlying data
sources (Twitch viewership, creator/channel data, Steam reviews,
Liquipedia tournament records, Wikipedia pageviews), and none of those
sources cleanly labels itself as measuring *esports* fandom versus
*game* fandom versus something else entirely. Raised directly
2026-09-16: this isn't a side question, it determines how confidently
any given data point can be used, and different research questions need
different signals weighted differently — a claim about esports fandom
specifically should lean on official-broadcast viewership; a claim about
a title's general playerbase should lean on Steam data; conflating the
two silently produces a confident-sounding number that's actually
answering the wrong question.

## 2. The primary construct, and why the relationship isn't containment

**The near-term primary construct this project cares about is esports
fandom specifically** — most of this project's output is written for
esports industry professionals, and the immediate job of this brief is
to arrive at a working, defensible definition of esports fandom, using
game-fandom signals to bound and disambiguate it rather than to
co-define it as an equal partner category.

That said, **this model must be built for generality, not just validated
esports-first** (`../brief.md`'s design principle) — the underlying
intellectual project is digital fandom formation broadly, and esports is
the first case study, not the only one this model will ever need to
serve.

**The old framing — "esports fandom (narrow) ⊂ game fandom (broad)" —
doesn't survive scrutiny and is retired here.** A committed tournament
viewer who has never played the game in years is a real category (the
same shape as a sports fan who's never played the sport), and that
person isn't a subset of "game fandom" by any reasonable reading of the
term. Esports fandom and game fandom are better modeled as two
partially-overlapping *modes of engagement* — a title can have audiences
in either, both, or neither — not a narrow category nested inside a
broad one.

**The more tractable reframe, given what this project's data can
actually support**: rather than trying to decompose a single viewership
number into "X% esports-fandom, Y% game-fandom" (not reliably answerable
with what's collected), ask the comparative question instead — *does
having a competitive scene measurably change a title's observable
fandom behavior, relative to a title without one, or relative to the
same title before/after a scene develops?* That's answerable with
existing infrastructure: `viewership_snapshots.broadcast_tier`
(`primary_official`/`detected_costream`/`general`) already exists
specifically to separate tournament-driven viewership from everything
else — built for a narrower purpose (official-broadcast-share), but
it's the right instrument for this question too, not something new to
build.

## 3. Signal-to-axis map

Honest, not aspirational — several cells below are genuinely thin.

| Signal | What it actually measures | Esports-fandom confidence | Game-fandom confidence |
|---|---|---|---|
| `broadcast_tier='primary_official'`/`detected_costream` viewership | Tournament-adjacent watching | High (`primary_official`) / Medium (`detected_costream`) — `config/channels.yaml` curated for 5 of 23 titles as of 2026-09-16 (`counter_strike`, `dota2`, `street_fighter`, `valorant`, `pubg`); `primary_official` itself still zero for 3 of those 5, curated too recently for polls to have accumulated | Low |
| Raw category-wide Twitch viewership (`general` tier) | Watching *something* in this category | Low — could be a Major, a pro's practice stream, or an unrelated streamer | Medium |
| Steam reviews / player counts | Owning and playing the game | Near-zero | High |
| Liquipedia tournament data (tier, prize pool, dates) | Competitive infrastructure investment | N/A — this is supply, not fandom | N/A |
| Wikipedia pageviews | General interest/curiosity | Ambiguous | Ambiguous |
| Creator/channel crossover (`creator_crossover.ipynb`) | A creator's own audience following them across titles | Medium — stronger where the crossover is tournament-adjacent | Medium |
| Self-declared stream region tags | Streamer/organizer-labeled region | Weakly esports-leaning (tags cluster around organized play) but genuinely mixed | Low-medium |

## 4. Operational definition (Step 3, drafted 2026-09-16)

Grounded in `notebooks/tournament_window_comparison.ipynb`'s real output
across five titles, not written in the abstract.

**Esports fandom, for this project's purposes, is viewership occurring
in `broadcast_tier ∈ {primary_official, detected_costream}` — not
"watching a tracked esports title's Twitch category" generally.**
`general`-tier viewership for a curated title does run measurably above
a non-esports baseline (1.5x-3.9x average viewers across all five
curated titles, confirmed in the tournament-window notebook), but that's
a softer, different finding — "this is a notable esports title" — not
evidence of esports-fandom engagement specifically. A title can clear
that bar in every poll and still not be esports fandom by this
definition if no tournament window is live.

**Two confidence tiers within that, not one flat category**, since
`primary_official` and `detected_costream` aren't equally strong
evidence:

- **Tier A — `primary_official`.** A confirmed, live-verified official
  broadcast channel (`config/channels.yaml`). Highest confidence, but
  structurally unavailable for 18 of 23 tracked titles, and thin even
  for 3 of the 5 curated ones (zero rows so far for Street Fighter/
  VALORANT/PUBG — curated same-day as this definition, not yet enough
  polls).
- **Tier B — `detected_costream`.** A title/date/alias match against a
  live tournament (`etl/classify_broadcast_tier.py`) — doesn't depend on
  channel curation, so it's available for any of the 23 tracked titles
  in principle, wherever `tournaments`/`tournament_aliases` coverage
  exists. Weaker: a title-text heuristic, not confirmed channel
  identity.

**A claim citing this definition should say which tier it's resting on.**
A Tier-A-only claim and a Tier-B-only claim are not interchangeable
evidence, even though both currently get pooled as "tournament-adjacent"
in the comparison notebook for sample-size reasons.

**What the definition deliberately does *not* build in: audience
concentration.** The five-title comparison found concentration
(top-channel share) and the average-viewer effect are different
mechanisms, not two readings of the same thing — Counter-Strike shows
the *smallest* concentration jump of all five titles despite one of the
*largest* average-viewer jumps, because its broad co-stream culture
spreads tournament attention across many channels rather than
funneling it into one or two. A distributed tournament-adjacent audience
is still esports fandom by this definition; concentration is useful
*diagnostic* evidence about a title's broadcast structure, not part of
what makes viewership count as esports fandom in the first place.

**A minimum-evidence caveat, stated rather than silently assumed**:
some titles' tournament-adjacent samples are small enough that a single
title-year claim shouldn't be built on them without checking row counts
first — Dota 2's `detected_costream` tier is 79 rows, PUBG's 161. Treat
anything under a few hundred rows as directional, the same bar
`fandom_and_niche_model` already applies to its own thin-sample niche
pairs.

## 5. Task list

1. ~~Arrive at a working definition of esports fandom specifically~~ —
   **done, §4 above.** Revisit if curation (task 2) or more
   `primary_official` data changes the confidence picture enough to
   warrant it.
2. **In progress.** `config/channels.yaml` extended 2026-09-16 from 2 to
   5 of 23 titles (Street Fighter, VALORANT, PUBG added). Sixteen
   uncurated titles remain; no further curation scheduled yet.
3. ~~Build the comparative "does a competitive scene change observable
   fandom behavior" test~~ — **done**, `notebooks/tournament_window_comparison.ipynb`,
   run against 2 titles then extended to 5.
4. Revisit whether any additional signal (not yet collected) would
   meaningfully sharpen the esports-fandom axis specifically, versus
   accepting the current confidence ceiling. Not started — the two tiers
   in §4 are still the ceiling.

## 6. Open items

- Whether the definition in §4 needs revisiting once `primary_official`
  data actually exists for Street Fighter/VALORANT/PUBG (task 2) — right
  now it's validated almost entirely on `detected_costream` for three of
  its five source titles.
- Whether this model, once built, actually generalizes cleanly to a
  future non-esports case study, or needs a second pass once
  `wider_game_fandoms` work resumes — flagged as a real risk, not
  assumed away by "built for generality" alone.
- Whether a formal minimum-row-count threshold (§4) should be codified
  somewhere machine-checkable, or stays a documented convention
  notebooks are expected to follow by hand.
- Status remains PENDING, not ADOPTED — a real operational definition
  now exists and has survived a five-title check, but three of those
  five titles' evidence is still Tier B only, and 18 of 23 tracked
  titles have no signal at either tier yet.
