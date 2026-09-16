# Digital Fandoms: Research Area

## 1. Context

The third research area in this project (added 2026-09-09 as "How Do Wider
Game Fandoms Operate on Twitch?"; restructured 2026-09-16 into this umbrella
plus two subprojects — see §2) — and the first whose subject isn't esports
at all. It exists because both other research areas kept running into the
edge of what a 23-esports-title-only dataset can answer:

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

**This area is deliberately broader and less settled than the other two.**
It doesn't have named hypotheses the way `research/inter_esports_dynamics/`
does (H1–H3) — closer to a genuine open area expected to grow its own
sub-questions and subprojects as data accumulates, not a single claim to
prove or retract. The two subprojects below are the first two such
sub-questions to mature enough to deserve their own brief; more may follow.

## 2. Subprojects

- **`gta_launch_case_study/`** — does a non-esports blockbuster launch show
  the same lifecycle shape (rapid rise, peak, plateau-or-decline) the
  `esports_lifecycle_and_maturity` area already characterizes for esports
  titles? GTA 6 as the live, motivating case. See that subproject's own
  `brief.md`.
- **`fandom_historical_contingency/`** — does a title's era of emergence
  structurally shape its fandom/creator ecosystem, using esports as the
  primary case study (this project's best-instrumented population), with
  room to extend beyond esports later given this area's own broader remit.
  Split out 2026-09-16 from this brief's original question 3 once it
  became clear the question was really about historical contingency in
  fandom formation generally, not just "does genre-comparison hold outside
  esports." See that subproject's own `brief.md`.

Both subprojects share this brief's data infrastructure (§4) and both
report back into this umbrella's open questions (§5) where their findings
connect to something not yet owned by either one specifically.

## 3. Open, umbrella-level questions

Not yet owned by either subproject — either genuinely cross-cutting, or not
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
   production fragments" (`research/inter_esports_dynamics/brief.md`'s H3)
   look like one level up, across all of Twitch rather than within the 23
   tracked titles? Doesn't commit to a specific test yet — recorded here
   as the connective thread to keep in mind as findings accumulate.

## 4. Data source: `collectors/twitch_platform_poll.py` (built 2026-09-09)

Shared infrastructure for this whole research area — both subprojects and
both open questions above draw on it, not duplicated per-subproject.

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
- Whether this area eventually needs its own named hypotheses (H-something)
  once question 2 has an actual test design, the way
  `research/inter_esports_dynamics/`'s H1–H3 emerged from its own original
  open questions.
- Whether a third subproject emerges as this area's own work accumulates —
  deliberately left open, not scoped in advance (§1).
