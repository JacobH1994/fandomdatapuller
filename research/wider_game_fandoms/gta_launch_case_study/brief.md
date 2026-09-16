# GTA 6 Launch: A Live Digital-Fandom Case Study

Part of the `wider_game_fandoms` research area — see `../brief.md` for the
area's shared context, data infrastructure (`collectors/twitch_platform_poll.py`),
and how this subproject relates to `fandom_historical_contingency/`.

## 1. Research question

**Does a non-esports blockbuster launch show the same lifecycle shape
(rapid rise, peak, plateau-or-decline) the `esports_lifecycle_and_maturity`
area already characterizes for esports titles?**

GTA 6 is the motivating case study — not because it's expected to behave
identically (it almost certainly won't: a single-player-capable open-world
title has a completely different attention driver than a competitive
scene's tournament calendar), but because watching a title of this scale
launch live, with this project's own collector already running, is a
genuinely new kind of observation nothing else in this project can
produce.

**Open item, not yet confirmed**: this brief does not assert a GTA 6
release date — Rockstar's own announced timeline should be checked
directly against the current date before treating any specific launch
window as fact, rather than assumed from anything written here.

## 2. Method

**Reuses `esports_lifecycle_and_maturity`'s method, not its data**: that
area's four-dimension "has this title finished growing" framework
(audience attention, infrastructure, new-vs-existing-audience,
concentration) generalizes directly to the research question above — GTA 6
obviously has no "tournament count" or "team count" dimension, so this
subproject needs its own adapted version of that framework once there's
launch data to apply it to, not a literal reuse.

Data source is the shared `collectors/twitch_platform_poll.py` collector
described in `../brief.md` §4 — this subproject is currently that
collector's primary real consumer, via GTA V/GTA VI's `platform_viewership_snapshots`
rows.

## 3. Findings

**First real findings, 2026-09-10, from Grand Theft Auto V specifically**
— genuine early results and directly useful groundwork for the GTA 6 case
study, even though GTA 6 itself hasn't launched yet:

- **GTA V's historical Twitch trajectory (2016-2024, read directly from
  the raw Kaggle CSV, not loaded into `monthly_category_history` since
  GTA V isn't a tracked title) shows four distinct step-changes, not
  smooth growth**: a 2017 jump, a much larger 2019 one, an all-time peak
  of 253M hours/month in 2021, then a stable #2-5 Twitch rank ever since —
  no meaningful decline since that 2021 peak, unlike several tracked
  esports titles this project has studied.
- **Grand Theft Auto VI already exists as its own Twitch category**
  (`game_id` 1867279146, confirmed live), with zero live streams as of
  this check — seeded ahead of any real gameplay availability. Directly
  useful for the research question above: this project can now watch that
  category activate in real time.
- **GTA V's non-esports creator ecosystem turned out to have real internal
  structure worth its own permanent classification**: `etl/classify_gta_content_segment.py`
  (added 2026-09-10, user request — "NoPixel as a subdivision of GTA RP,
  GTA RP as a subdivision of GTA V") persists a three-tier `content_segment`
  (`nopixel`/`gta_rp_other`/`non_rp`) on every GTA V row in
  `platform_viewership_snapshots`, the same pattern `classify_broadcast_tier.py`
  already established for the 23 tracked titles. Headline result: NoPixel
  (295 channels) carries 40.6% of all GTA V viewer-time — more than the
  2,945 channels spread across every *other* named RP server combined
  (18.6%). Full detail, including the language contrast (NoPixel 96.3%
  English vs. the broader RP scene's 36.0%), in `notebooks/gta_v_deep_dive.ipynb`.
- **GTA V is now this project's second proof point for PRD §9.17's
  English-language fandom decomposition subsystem** (built 2026-09-12,
  `research/inter_esports_dynamics/notebooks/english_fandom_decomposition.ipynb`),
  alongside the Apex Legends/PUBG pair that motivated it — confirms the
  subsystem's subject registry (`config/fandom_decomposition_subjects.yaml`)
  genuinely generalizes to a `game_id`/`content_segment`-keyed
  platform-wide subject, not just the 23 `title_id`-keyed tracked titles.
  `gta_v_nopixel` is configured as its own subject, separate from GTA V's
  undivided total, so the NoPixel-specific audience can eventually get its
  own region read distinct from the wider GTA RP scene's.
- **A general methodological lesson, not just a GTA V-specific one,
  surfaced 2026-09-10**: NoPixel's share of GTA V viewer-time turned out
  to cycle by time of day (roughly a third to over half, peaking CEST
  morning/midday) rather than holding steady or trending — a first read
  built from several polls that happened to all land in the same
  few-hour window read this as "a consistent climb, likely launch hype,"
  and a single poll taken at CEST evening prime time (requested directly
  by the user specifically *because* earlier checks all clustered in one
  window) contradicted that outright. Any single-snapshot or
  narrow-time-window share number from `platform_viewership_snapshots`,
  for GTA V or any other non-tracked title, should be treated the same
  way going forward — checked across varied times of day before being
  read as a trend.

## 4. Open items

- GTA 6's actual release timeline: not yet checked against a current,
  reliable source — needs verifying before this subproject's own research
  question can be scoped concretely, not assumed from this document.
- The adapted four-dimension "has this title finished growing" framework
  (§2) — not yet built, waiting on real GTA 6 launch data to apply it to.
