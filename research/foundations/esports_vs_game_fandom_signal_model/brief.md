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
| `broadcast_tier='primary_official'`/`detected_costream` viewership | Tournament-adjacent watching | High — but only where `config/channels.yaml` is curated (2 of 23 titles today: `counter_strike`, `dota2`) | Low |
| Raw category-wide Twitch viewership (`general` tier) | Watching *something* in this category | Low — could be a Major, a pro's practice stream, or an unrelated streamer | Medium |
| Steam reviews / player counts | Owning and playing the game | Near-zero | High |
| Liquipedia tournament data (tier, prize pool, dates) | Competitive infrastructure investment | N/A — this is supply, not fandom | N/A |
| Wikipedia pageviews | General interest/curiosity | Ambiguous | Ambiguous |
| Creator/channel crossover (`creator_crossover.ipynb`) | A creator's own audience following them across titles | Medium — stronger where the crossover is tournament-adjacent | Medium |
| Self-declared stream region tags | Streamer/organizer-labeled region | Weakly esports-leaning (tags cluster around organized play) but genuinely mixed | Low-medium |

**Practical rule this table implies**: a claim framed as "esports fandom"
should be able to point to a `primary_official`/`detected_costream` row,
or explicitly flag that it's using a weaker proxy and say so. A claim
about a title's general audience/playerbase can lean on Steam or raw
category viewership without the same caveat.

## 4. Task list

1. Arrive at a working definition of esports fandom specifically —
   operationalized against what `broadcast_tier` and the signal-to-axis
   map above can actually support, not an abstract definition divorced
   from measurement.
2. Extend `config/channels.yaml` curation beyond the current 2 of 23
   titles — the whole `primary_official` signal is structurally
   unavailable for every other title until this happens; this is the
   single highest-leverage unblock for this brief's own primary
   construct.
3. Build the comparative "does a competitive scene change observable
   fandom behavior" test (§2) using `broadcast_tier` against titles/
   periods with and without an active tournament calendar.
4. Revisit whether any additional signal (not yet collected) would
   meaningfully sharpen the esports-fandom axis specifically, versus
   accepting the current confidence ceiling.

## 5. Open items

- Whether the definition arrived at in task 1 needs revisiting once
  `config/channels.yaml` curation (task 2) changes the confidence
  picture for more titles.
- Whether this model, once built, actually generalizes cleanly to a
  future non-esports case study, or needs a second pass once
  `wider_game_fandoms` work resumes — flagged as a real risk, not
  assumed away by "built for generality" alone.
