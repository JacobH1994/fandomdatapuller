# Wider Game Fandoms: Research Area

Renamed 2026-09-16 from "Digital Fandoms" — "digital fandom" turned out
to be the project's own overarching frame (see `../foundations/brief.md`),
not one area's private name; this area is specifically the non-esports
case studies within that frame. Content and section numbering otherwise
unchanged by the rename.

## 1. Context

The third research area in this project (added 2026-09-09 as "How Do
Wider Game Fandoms Operate on Twitch?") — and the first whose subject
isn't esports at all. It exists because both other research areas kept
running into the edge of what a 23-esports-title-only dataset can
answer:

- `research/inter_esports_dynamics/notebooks/esports_share_of_twitch.ipynb`
  already found that Just Chatting and GTA V — neither an esports title —
  drove most of Twitch's own platform growth 2016–2024, while the 23
  tracked titles' combined share of platform attention nearly halved. That
  finding could only ever be a footnote as long as nothing outside esports
  was actually being collected.
- Building `research/inter_esports_dynamics/notebooks/creator_crossover.ipynb`'s
  enrichment-ratio heatmap and insularity ranking (2026-09-09) led directly
  to Q1 below: are esports creator communities unusually insular, or do
  *all* Twitch creator communities specialize like this? Answering that
  needs a genuine non-esports baseline, which this project didn't have —
  `collectors/twitch_poll.py` has only ever queried the 23 tracked titles'
  own Twitch category IDs.
- Separately, the user is tracking an anticipated GTA 6 launch as a live
  case study — now `gta_launch_case_study/` (§2).

**This area is deliberately broader and less settled than the other
esports-focused two.** It doesn't have named hypotheses — closer to a
genuine open area expected to grow its own sub-questions and subprojects
as data accumulates, not a single claim to prove or retract. It's also
this project's designated on-ramp for broadening scope beyond esports
once the esports-focused areas mature — see `../foundations/brief.md`
for how that long-term trajectory relates to this area's near-term,
esports-industry-facing output.

## 2. Subprojects

- **`gta_launch_case_study/`** — does a non-esports blockbuster launch show
  the same lifecycle shape (rapid rise, peak, plateau-or-decline)
  `esports_lifecycle_and_maturity` already characterizes for esports
  titles? GTA 6 as the live, motivating case. See that subproject's own
  `brief.md`.

**`fandom_historical_contingency/` moved out 2026-09-16**, elevated to
`../foundations/technological_contingency_of_fandom_formation/` once it
became clear its actual claim (fandom formation is contingent on the
technological/social conditions present when a fandom forms) isn't
esports-specific or wider-game-fandom-specific either — it's prior to
and larger than any one area. This area's own GTA 6 work is flagged
there as a candidate second case study, not owned by this document.

## 3. Open, umbrella-level questions

Not yet owned by a subproject — either genuinely cross-cutting, or not
mature enough to be split out yet.

1. **Are esports creator communities more insular than the wider Twitch
   creator population?** `research/inter_esports_dynamics/notebooks/creator_crossover.ipynb`'s
   insularity ranking already shows every one of the 23 tracked titles
   keeps 64–95%+ of its own creator base exclusive to it, this window —
   but insular *relative to what*? Without a non-esports baseline, there's
   no way to tell whether that's an esports-specific dedication effect or
   just how Twitch creator communities generally behave. The most
   immediately answerable question here once `platform_viewership_snapshots`
   (§4) accumulates a comparable window. **Still needs a longer window —
   nothing has changed here since this brief was first written.**
2. **General, open-ended**: what does "attention concentrating even as
   production fragments" (`inter_esports_dynamics/questions/platform_attention_concentration/`)
   look like one level up, across all of Twitch rather than within the 23
   tracked titles? Doesn't commit to a specific test yet — recorded here
   as the connective thread to keep in mind as findings accumulate.

## 4. Data source: `collectors/twitch_platform_poll.py` (built 2026-09-09)

Shared infrastructure for this whole research area — both the subproject
and both open questions above draw on it, not duplicated per-subproject.

**The core constraint, same as everywhere else in this project (CLAUDE.md's
"one rule," now covering a fourth live collector alongside Twitch/YouTube/
Steam)**: Twitch's live-viewer API has no historical endpoint. Whatever
this collector captures starts accumulating from whenever it actually
started running — there is no way to retroactively reconstruct non-esports
Twitch history the way `monthly_category_history`'s Kaggle import did for
the 23 tracked titles (and even that import stops at 2024-09 and only ever
covered categories that made Twitch's own top-200, so it wouldn't have
covered most non-esports titles this area cares about anyway). **Practical
implication for the GTA 6 case study specifically**: the earlier this
collector has been running before launch, the more of the pre-launch
baseline and launch-week spike actually gets captured — there is no
substitute for starting collection now rather than waiting.

**Why a separate script, config, and workflow from `collectors/twitch_poll.py`**
— the same discipline `collectors/youtube_poll.py`/`collectors/steam_poll.py`
already established for exactly this reason: a change here must never be
able to put the 23-title collector's uptime at risk. `collectors/twitch_platform_poll.py`
imports (never modifies) `twitch_poll.py`'s auth/retry/dotenv helpers, and
writes to its own `data/raw/twitch_platform/` subtree, its own
`.github/workflows/twitch_platform_poll.yml` (offset 15 minutes from the
other three collectors' schedules), and its own schema tables
(`platform_viewership_snapshots`, `platform_viewership_below_threshold` —
see `etl/schema.sql` for why these can't reuse the `title_id`-keyed pattern
the tracked-title tables use).

**Scope, and why it isn't "capture literally everything on Twitch"**:
discussed directly with the user before building this (2026-09-09) — a
full, unthresholded capture of every live channel platform-wide would mean
permanently committing channel logins, freeform stream titles, and tags
for tens of thousands of ordinary streamers with no connection to any
research question here, to this project's *public* GitHub repository,
forever. Instead this collector reuses `config/capture.yaml`'s proven
tiered approach (full detail above a viewer-count threshold, aggregate-only
below it) — re-derived for the general Twitch population rather than
assumed to carry over from the 23-tracked-titles threshold, since the two
populations' viewer-count distributions aren't guaranteed to look alike.
See `config/twitch_platform_capture.yaml` for that derivation. The 23
tracked titles' own game IDs are excluded from this collector's output
entirely (that data already lives in `viewership_snapshots`; duplicating
it here would let a future query silently double-count a title's own
attention).

**Known limitation, not yet addressed**: Twitch's category list includes
non-game entries (Just Chatting, IRL, Music, Sports, Slots, ...) that this
collector currently has no way to distinguish from an actual game —
confirmed live 2026-09-09 that a raw sample includes several of these
among the largest "categories" by viewer count. Anything reading this data
for a genuinely game-vs-game comparison should filter known non-game
category IDs explicitly rather than assume every `game_id` in
`platform_viewership_snapshots` is a game.

## 5. Open items

- Whether question 1 (insularity comparison) needs the same hypergeometric
  chance-adjustment `creator_crossover.ipynb` applies within esports, given
  the general Twitch population's total-channel-count denominator is
  vastly larger and the pool-size mechanics may not transfer directly —
  check once there's real data, not decided in advance.
- A non-game category exclusion list (§4's known limitation) — not yet
  built.
- Whether a second subproject emerges as this area's own work
  accumulates — deliberately left open, not scoped in advance (§1).
