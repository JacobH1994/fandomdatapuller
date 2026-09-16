# Historical Contingency in Fandom Formation: Research Brief (early stage)

Part of the `digital_fandoms` research area — see `../brief.md` for the
area's shared context. **This brief is genuinely early-stage, split out
2026-09-16 from a single supporting notebook and a live conversation — it
needs more work before its research question is fully settled**, not a
polished companion to `gta_launch_case_study/brief.md` yet.

## 1. Origin

`streamer_ecosystem_by_phase.ipynb` was originally built inside
`research/esports_lifecycle_and_maturity/` (split out of
`cs_growth_trajectory.ipynb`'s own §18) to ask a narrower question, per
`research/inter_esports_dynamics/brief.md`'s own Classic (2013-15) /
Console (2016-20) / Second Coming (2021-24) emergence-era framework: do
newer esports titles simply have bigger creator ecosystems than older
ones? Expanded to all 23 tracked titles across all 4 eras, the answer
turned out to be more specific and more interesting than "yes, newer is
bigger":

- Fortnite (11.2M peak distinct monthly streamers), VALORANT (4.8M), and
  Apex Legends (4.7M) do dwarf every Classic- and Console-era title.
- But the rest of the Second Coming cohort does **not** follow that
  pattern: PUBG (1.85M) sits in the same range as Console-era Rocket
  League/Rainbow Six Siege/Overwatch (2.1-2.3M) and Classic-era
  Counter-Strike (1.85M); every mobile Second Coming title (Free Fire,
  Brawl Stars, Teamfight Tactics, PUBG Mobile, Wild Rift, Mobile Legends:
  Bang Bang) sits at or below Classic-era Dota 2/Hearthstone (642K).
- Dota 2 is the clearest outlier at the bottom of its own era — 336K-643K
  distinct streamers, smaller than several Second Coming *and*
  Console-era titles, despite total viewership hours comparable to or
  exceeding several of them.

**The revised read**: it isn't "newer titles have bigger creator
ecosystems" in general — it's that a specific handful of broad-audience,
easy-to-clip titles (the battle-royale/hero-shooter cohort built by
Epic/Riot/Respawn) do, and several of them happen to be recent. That
finding is a structural-comparison result on its own, but it also opens a
bigger question, which is what this brief exists to track.

## 2. Research question (draft, not final)

**Does a title's era of emergence structurally shape its fandom/creator
ecosystem — not through some general "newer is bigger" trend, but through
more specific historically-contingent mechanisms (which platforms existed,
which organizations were building audiences at the time, what clip/stream
culture looked like when the title launched)?** Framed by the user
2026-09-16 as understanding "the way that historical context is a key
factor in the formation of fandoms" — esports is the primary case study
here because it's this project's best-instrumented population (23 titles,
known emergence eras, multiple ecosystem signals already collected), with
room to extend beyond esports later given the parent `digital_fandoms`
area's broader remit (§3).

This is not yet decomposed into named sub-hypotheses the way
`research/inter_esports_dynamics/brief.md`'s H1–H3 are — the §1 finding is
suggestive of a mechanism (a specific cohort, not a general trend) but
doesn't yet pin down *which* historical factors are doing the work
(platform-specific, organization-specific, clip-culture-specific, or some
combination). That's the next real piece of work here, not something to
guess at in this document.

## 3. Relationship to the other research areas

- **Reuses `research/inter_esports_dynamics/brief.md`'s era framework**
  (Classic/Console/Second Coming) as its starting taxonomy, but asks a
  different question of it — that brief asks about competitive exclusion
  *within* a niche at a point in time; this one asks whether the *era* a
  title emerged in leaves a lasting structural mark on its fandom,
  independent of niche.
- **Sits inside `digital_fandoms`, not `inter_esports_dynamics`**, despite
  using esports as its case study — the question is about historical
  contingency in fandom formation generally, of which esports titles'
  creator ecosystems are one instance, not the whole subject. If this
  brief's method later extends to a non-esports case (a genre with its
  own "eras" of emergence outside competitive gaming), that's exactly the
  kind of growth `digital_fandoms/brief.md` §1 already anticipates.

## 4. Open items

- The research question itself needs sharpening (§2) — this is the most
  immediate next step, not a data-collection task.
- No new data source identified yet — `streamer_ecosystem_by_phase.ipynb`
  currently draws on the same Kaggle `Streamers` column every other
  era-comparison notebook in this project uses; whether this brief needs
  something new (platform-launch-date data, organization-founding dates)
  is unresolved.
- Whether/how this connects to `gta_launch_case_study/`'s own work is
  untested — GTA V predates the esports era framework entirely, so it's
  not yet clear whether this brief's mechanism-question even applies
  outside a competitive-gaming context, or needs a parallel, separately-
  derived framework for non-esports titles.
