# Post 3 — "The anatomy of a network"

Working title, set 2026-09-21. Takes the mode-of-engagement definition
from Post 2 (`../post_2_unit_of_analysis/`) and asks what it actually
looks like in the Twitch creator-network data this project already has —
an empirical look at how the conceptual framework cashes out in
practice, not a new theoretical piece.

## The task, split in two — and this post is only the first half

Raised directly (2026-09-21), after several sessions of foundations
notebook work kept sliding between two genuinely different questions
without noticing:

1. **The shape of what's competing** — before anything can be said about
   titles crowding each other out of a shared niche, what actually *is*
   the unit an esports community of practice forms around? Title itself?
   Genre? Platform? Some genre-platform "niche" cell? **This post is
   about (1) only.**
2. **Competitive exclusion dynamics** — do titles within a shared unit
   crowd each other out over time? This is `inter_esports_dynamics/
   questions/competitive_exclusion_in_niches/`'s job, not this post's —
   and per the research journal (2026-09-21, second entry) and the note
   now added to that brief's own §0, this post's own findings directly
   complicate that question's founding assumption and should be read
   before any more work goes into it.

## The headline finding this post is actually built around

**Roughly three-quarters to four-fifths of tracked creators stream
exactly one title** — the naive figure is 90%, but
`research/foundations/notebooks/creator_specialization_rate.ipynb`
(built 2026-09-21, once this became the post's centerpiece rather than a
side observation) found that number is inflated by how little of the
population this project's own ~3-week-old collector has had time to
observe: channels caught in only 1-2 snapshots read as 90-100%
single-title mechanically, since there's been no real chance to catch a
second title. The rate stabilizes at ~74-80% for channels observed a
moderate number of times — the most defensible estimate of the
underlying rate, and the number this post should actually cite, not 90%.
That's still the first-order answer to "what is the shape of an esports
community of practice" — title itself, not genre, not platform, not
niche, is doing almost all of the boundary-drawing work. Everything this
project has built about cross-title creator communities (see notebooks
below) describes a *second-order* structure: how the remaining ~20-25%
who do cross a title boundary organize themselves when they do it. Real,
and worth reporting, but not a description of the typical creator of any
given title — a mistake this project's own notebooks made more than once
before catching it (see the research journal entry for the full
reasoning, including why the null result on "Community 0" is actually
*stronger* evidence for title-boundedness, not a complicating exception
to it).

## Update (2026-10-02): the specialization rate moved down and wider, not narrower — cite ~69-77%, not 74-80%

`creator_specialization_rate.ipynb` was re-run on the current ~5-week
window (180 collector snapshots, up from 120) as part of reconciling the
whole `creator_crossover` notebook family after a data refresh. The
unadjusted population figure moved from 90.3% to 88.8%. More importantly,
the defensible range — read from the moderate-exposure bins where the
estimate stabilizes, the actual number this section says to cite — **did
not narrow as this notebook's own previous run predicted it would; it
widened and shifted down**: the floor fell from ~74% (at 8-20 snapshots)
to ~69.3% (now at 12-20 snapshots), and the high-exposure recovery
weakened from ~84% to ~76.1%. **The number this post should cite going
forward is ~69-77%, not 74-80% and not 90%.** The exposure confound this
section already describes (thin observation reading as false
specialization) is confirmed real and, over this five-week horizon, does
not self-correct just by running the collector longer — worth stating
plainly since the previous run predicted it would. The core claim this
post is built on is unaffected by this revision: a solid majority of
creators still specialize in one title, title itself is still doing
nearly all the boundary-drawing work, and the first-order/second-order
distinction this section's argument depends on still holds — only the
precise number, and the confidence attached to it, have moved.

## Step 1 + Step 2, run 2026-09-24 — real, mixed result, not a clean confirmation

Redrawn plan (2026-09-24, following a live VCT Champions natural experiment):
Step 1 built a five-dimension behavioral battery (concentration, tenure,
cadence, primary/costream structure, identity-level linkage) on one title
(VALORANT) to the fullest degree possible —
`notebooks/valorant_network_anatomy.ipynb`. Step 2 ran the three
dimensions that don't depend on a live tournament (concentration, tenure,
cadence) across all 23 titles, clustered the results independently, and
checked whether that reproduces the Leiden crossover-graph communities —
`notebooks/cross_title_intra_community_comparison.ipynb`.

**Result: real, positive, genuinely mixed — not a clean win for the
generational hypothesis.** Adjusted Rand Index 0.34 (all 23 titles) /
0.42 (15 titles in the three real communities only) against the known
Leiden partition — clearly above random, well short of reproduction.
Breaking that down by community is where it gets interesting:

- **C1 (classic PC) is a perfect match** — all 6 titles land in the same
  behavioral cluster. The strongest single piece of evidence yet for the
  hypothesis, for this community specifically.
- **C0 (not a real crossover community, per the null-model test) shows
  real internal behavioral cohesion anyway** — 6 of 8 titles cluster
  together. Read carefully: this means audience-crossover-similarity and
  behavioral-similarity are separable properties, not two readings of the
  same thing — titles can resemble each other internally without their
  audiences actually moving between them. A complication, not a
  confirmation.
- **C3 (fighting games) — first reported as a clean contradiction with an
  earlier finding; checked properly (2026-09-24) and it's messier and
  more informative than that.** Not two notebooks disagreeing about one
  split — each of the four titles is pulled toward its cluster by a
  *different* one of the three features. Tenure alone reproduces
  `creator_current_tenure_by_title.ipynb`'s own pairing almost exactly
  (Tekken 8 + Guilty Gear oldest-skewing, Street Fighter 6 + Mortal
  Kombat 1 youngest) — the two notebooks were never actually in
  tenure-level disagreement. Concentration alone gives a different,
  equally real pairing (Street Fighter 6 + Mortal Kombat 1 both highly
  concentrated; Guilty Gear + Tekken 8 both spread out). Cadence
  separates Mortal Kombat 1 on its own (far higher single-session rate).
  The multivariate clustering landed Street Fighter 6 and Tekken 8 in C1's
  cluster for two different reasons (concentration for one, tenure for
  the other), not because they closely resemble each other. **C3's
  internal structure doesn't reduce to one axis the way C1's or C0's
  mostly do — that divergence is itself the finding**, not a bug in
  either analysis.

**Three robustness checks run 2026-09-24 (same day) substantially
downgrade C0's evidence and leave C1 as the one genuinely solid
result:**

1. **Pool-size confound, checked directly**: Gini correlates significantly
   with log(channel-pool-size) (r=0.42, p=0.048); tenure and cadence do
   not. Re-clustering on pool-size-residualized features: **C1's perfect
   match survives unchanged. C0's 6-title cohesion does not** — it splits
   into {Apex, Overwatch, VALORANT} and {Fortnite, Rainbow Six Siege,
   Rocket League}. The real-communities-only ARI actually *improves*
   (0.416 → 0.505) once the confound is removed — it was diluting C1/C2/C3's
   own signal, not producing it.
2. **Bootstrap stability (200 resamples, channels resampled within each
   title)**: C1's core membership and most of its "guest" members
   (Hearthstone, TFT, PUBG, AoE2, CS2, Dota 2, Street Fighter 6) are
   robust at 74-84% co-clustering. **Tekken 8's placement with C1 is not**
   (34.9%). **The cluster this brief called "C0's cohesive six" is the
   least stable result in the whole notebook — 39-54% across every
   member** — and now has two independent reasons not to trust it as
   originally reported (confounded *and* unstable). Wild Rift/Guilty
   Gear's pairing is similarly weak (38.5%).
3. **Chance-adjusted enrichment for VALORANT's identity-linkage
   crossover** (18 C0 / 1 C1 title-instances, pool-ratio-adjusted):
   enrichment C0 = 1.20, C1 = 0.25 — the direction survives adjustment,
   but N=15 channels (the C1 figure rests on a single observed channel)
   means this is a low-power, suggestive data point, not something to
   lean on.

**Net effect: C1 is the one result in this entire line of work that's
survived every check thrown at it (raw clustering, pool-size correction,
bootstrap stability). Nearly everything about C0's apparent behavioral
cohesion — the headline of the previous entry — turns out to be
substantially weaker than first reported.** This is the corrected
picture going forward, not the original Step 2 read.

## Update (2026-10-02): the clustering result partially reversed — StarCraft II left C1's "perfect match"

`cross_title_intra_community_comparison.ipynb` was re-run on the current
~5-week window (up from ~2 weeks) as part of the same data-refresh
reconciliation. **This section's own headline claim, "C1 is a perfect
match," no longer holds**: StarCraft II has defected from C1's cluster to
the one now shared with Guilty Gear -Strive- and Tekken 8, leaving 5 of 6
C1 titles together (Age of Empires II, Counter-Strike 2, Dota 2,
Hearthstone, PUBG), not all 6. Not a fresh surprise — the bootstrap-
stability check above had already flagged StarCraft II as C1's one shaky
member (74.3% co-clustering, lowest of the six) before this happened; the
resampling test correctly predicted the member that wouldn't hold up.

The two ARI figures moved in opposite directions: **0.26 for all 23
titles (down from 0.34), but 0.47 for the 15 real-community titles only
(up from 0.42)** — agreement weakened once the non-real C0 community is
folded in, but strengthened for the three statistically real communities
specifically, consistent with C0 being noise a different feature mix
will always reshuffle while the real communities' signal, if anything,
firms up with more data.

**C2 (mobile) moved the opposite direction from C1 — it got more
cohesive, not less**: Wild Rift rejoined the mobile cluster (Brawl Stars,
Mobile Legends: Bang Bang, PUBG Mobile, Wild Rift all four together now,
up from 3 of 5), leaving only Free Fire split off. **C0's apparent
six-title cohesion has dissolved into a different five-title group**
(Fortnite, Rocket League, Rainbow Six Siege, Free Fire, Mortal Kombat 1)
that is, confusingly, now considerably *more* stable than the original
"cohesive six" ever was (0.71-0.86 bootstrap co-clustering, versus
0.41-0.54 before) — read this as the clustering re-converging on a
different, better-supported grouping with more data, not as the original
C0 finding being vindicated.

**Net: the single result this brief called "the strongest in this entire
line of work" (C1, intact) has partially reversed, and that's reported
plainly rather than downgraded quietly.** C1 minus StarCraft II is still
the most robust individual result in this notebook — its remaining five
members' bootstrap stability is, if anything, higher now (0.880-0.896)
than the original six-title figure. The clean "all 6 classic-PC titles
land together" story this post was built around should be read as "5 of
6, StarCraft II now closer behaviorally to the fighting-game cluster"
going forward, not as a clean perfect match. StarCraft II's own
behavioral profile hasn't changed (see `## What each community/title
actually looks like behaviorally` below) — only its cluster *membership*
moved.

Other ARI figures elsewhere in this brief (the 4-feature and 11-feature
battery comparisons, both dated 2026-09-25) are relative, same-day
comparisons against that day's own 3-feature baseline and have not been
independently re-verified against this 2026-10-02 refresh — flagged, not
re-run, since those specific extended-feature passes haven't been redone.

## Extended battery (2026-09-25) — more features made the clustering worse, but surfaced the one non-tautological confirmation this line of work has found

Requested directly: extend the 3-feature battery with nine more candidates
(retention, language entropy, session duration, scheduling regularity,
bot-command rate, tags-per-stream, mean viewers per channel,
affiliate/partner rate), screen each against `log(n_channels)` *before*
adding it — the check Gini failed after the fact, done up front this
time.

**Availability, checked against `etl/schema.sql` rather than assumed**:
everything needed is persisted (`started_at`, `tags`, `language`,
`stream_title` all ~0% null; `broadcaster_type` 90.6% coverage) except
`is_mature`, which the collector captures but never persists — not one
of the candidate features, so not pursued further.

**Screening results**: `retention_rate` (r=-0.42, p=0.048) and
`mean_tags_per_stream` (r=+0.49, p=0.018) are significantly confounded
with pool size — residualized, not dropped, same treatment as Gini.
`median_session_minutes` is excluded outright for a different, more
fundamental reason already established in this project's own prior work
(`streamerbase_anatomy_pilot_cs.ipynb`): most sessions are single-snapshot
lower bounds, and the alternative (multi-snapshot only) is inspection-paradox
biased — a measurement-validity problem pool-size screening can't fix.
Everything else went in raw.

**Re-clustering with the resulting 11-feature battery made the headline
result worse, not better: ARI drops to 0.152 (all 23) / 0.388 (real 15),
down from 0.341/0.416 — and C1's perfect match does not survive**, splitting
5-1 across two clusters. A textbook curse-of-dimensionality effect on 23
observations — **the 3-feature battery is the one to keep using going
forward**, not because more features are illegitimate in principle, but
because this specific expansion measurably hurt the one result that had
survived every prior check.

**But the actual point of the exercise — is there a non-tautological
axis (not tenure, which is a cohort measure by construction) that
independently tracks era — has a real, positive answer: exactly one.**
`mean_viewers_per_active_channel` correlates significantly with
`milestone_year` (r=-0.52, p=0.010), clean of the pool-size confound
(r=0.14, p=0.53 against log(n_channels) separately). Newer titles have
lower average viewership per active channel than older ones — plausibly
because older titles' ecosystems have had more time to concentrate
audience onto fewer, bigger channels, consistent with the tier/concentration
pattern already visible elsewhere in this line of work. **None of the
other seven new features come within p=0.1 of significance** — checked
and ruled out, not just unreported. Smaller in scope than the original
"C0 clusters together" finding, but more trustworthy: it survived being
asked to independently confirm something, rather than just correlating
with it after the fact.

## The 4-feature battery (2026-09-25) — a real improvement, kept honest about why

Raised directly: is it bad practice to drop the seven null features and
specifically keep the one (`mean_viewers_per_active_channel`) that
passed the milestone_year test? Only if the two questions get blurred
together. The milestone_year correlation is a standalone test of the
era hypothesis, already reported on its own terms. Adding the same
feature to the *clustering* is a different question — does it help
reproduce the Leiden communities — and has to be answered on its own
evidence, not by re-citing the correlation that motivated trying it.

**Two further checks, requested directly (2026-09-25), meaningfully
revise how this result should be read:**

1. **Gini and `mean_viewers_per_active_channel` are highly correlated
   (r=0.84, p<0.0001)** — real redundancy, not a false alarm, since both
   are functions of the same per-channel viewer distribution. But
   replacing gini with mean_viewers (rather than using both) performs
   *worse* (ARI 0.272/0.357) than either gini alone (0.341/0.416) or
   both together (0.388/0.505) — C1 doesn't even hold together as one
   cluster in that version. The ~16% of variance the two features don't
   share turns out to matter. Honest description: this is "three
   independent axes plus a partially-redundant second look at
   concentration/scale," not four clean independent axes — still the
   best-performing configuration of the three tested, kept for that
   reason, not despite it.
2. **The ARI improvement is partly circular, and the bootstrap result is
   the one to lead with.** `mean_viewers_per_active_channel` was added
   *because* it correlates with milestone_year, and the Leiden
   communities it's tested against (C1 especially) are themselves already
   shown to be era-structured — the selection criterion and the
   evaluation target share a root cause. The **bootstrap stability
   result is genuinely independent of that** (it never references
   milestone_year or the community labels, only whether resampling
   produces the same neighbor structure) — and on that test, **the C0
   cluster (39-54% stability with 3 features) jumps to 68-73% for six of
   its eight members with 4.** That's the real evidence the feature is
   useful; the ARI gain is the weaker, partly-circular result and
   shouldn't be cited as if it were independent confirmation.

**The 4-feature battery is still the one to use going forward** — on the
strength of the stability result specifically, described accurately
(partial redundancy, partly-circular ARI gain, genuinely independent
stability gain) rather than as an unqualified win.

**Standalone finding, worth recording on its own terms**: of the nine
screened candidates, the two that carry era signal — tenure and mean
viewers per channel — are both measures of *who's in the population and
how attention distributes across it*. The seven that came back null
(scheduling regularity, bot-command rate, tags per stream, language
entropy, affiliate/partner rate, retention) are, without exception,
measures of what creators actually *do*. **Era appears to shape audience
structure, not streaming practice** — a title's generation predicts the
shape of its population, not the operational habits of the people in it.

## Correction (2026-09-25, same day): `mean_viewers_per_active_channel`'s
milestone_year finding does not survive raising the capture floor —
withdrawn as established, not just downgraded

Raised directly: is the mean-viewers/era pattern "immaturity," structural
fragmentation from more creators splitting a similar-sized audience, or
an artifact of `config/capture.yaml`'s fixed 3-viewer floor ("suddenly
every channel seems relevant")? Tested all three directly rather than
argued from intuition.

**The fragmentation/platform-growth story is checked and not the primary
mechanism**: `n_channels` and `total_mass` (total attention) scale
almost exactly proportionally with each other across the whole 23-title
size range (log-log slope ≈ 1.04, r=0.97), regardless of era, and
neither individually correlates with milestone_year (r=0.14 and r=-0.12
respectively) — only their ratio does. If newer titles were simply more
creators splitting a similarly-sized pool of attention, total attention
should grow measurably slower than channel count specifically for newer
titles. It doesn't.

**The capture-floor concern is the one that held up, and it's decisive.**
Raising the simulated viewer floor from the real 3 up through 100, the
milestone_year correlation for `mean_viewers_per_active_channel` weakens
monotonically and loses significance by floor≈10: r=-0.52 (p=0.010) at
3, r=-0.44 (p=0.034) at 5, r=-0.32 (p=0.14, not significant) at 10,
essentially zero (r=-0.09 to -0.005) by 50-100. **Gini shows the
identical pattern** — not specific to the mean_viewers formulation, a
property of the concentration axis generally at this resolution. The
mechanism is confirmed directly: newer titles have a significantly
larger share of their population sitting close to the floor (%channels
under 10 viewers correlates with milestone_year at r=+0.45, p=0.033) —
exactly the population a fixed absolute floor measures least reliably,
with a completely invisible population just below it.

**This doesn't rule out a real "immaturity" effect** — newer titles
genuinely could have a fatter tail of small, unconsolidated streamers —
**but this dataset, at this capture floor, can't currently distinguish
that from a measurement artifact.** Both are equally consistent with
everything checked here. The honest status is "not established," not
"smaller than first reported" — the previous entry's framing overstated
it, and this corrects that rather than merely qualifying it further.
`mean_viewers_per_active_channel` should not be treated as a validated
non-tautological era feature going forward without new data (e.g. a
lower or relative capture floor) that can actually see below the current
one.

**Tenure checked against the identical test and it survives — this is
now the strongest single result in this line of work.** A real but weak
channel-level relationship exists between viewer count and account age
(r=0.18 across 263,519 channels) raising the possibility tenure shares
concentration's vulnerability. Checked directly: raising the same
viewer floor from 3 to 50, tenure's correlation with milestone_year does
not weaken — it strengthens slightly, from r=-0.465 (p=0.025) to r=-0.511
(p=0.013). The opposite signature from concentration. Tenure is not
living in the fragile, near-floor part of the distribution the way
concentration was — it should now be read as the best-supported
individual piece of evidence for the era hypothesis anywhere in this
project, specifically *because* it was tested against and survived the
exact mechanism that broke the other candidate.

## A framing caveat that applies to every section below citing milestone_year (2026-09-25)

`get_success_milestone()` measures one specific thing — the earliest
2-consecutive-year window of top-tier (S/A) professional tournament
activity spanning 2+ continents — and this whole post has been using it
as a stand-in for "when the title's community/network matured" more
broadly. Those aren't the same claim: professionalization requires an
existing playerbase to draw elite talent from, so milestone_year is
better understood as a **lagging** indicator of network maturity, not
the maturation event itself. Full reasoning, and a candidate framework
for what a fuller measure would need (Play → Elite Play →
Professionalised Play → Watch → Socialise → Attend → Purchase, not
strictly linear), now lives in
`../../mode_of_engagement_model/brief.md`'s §10 — this post's era
hypothesis is a real finding about *when professionalization happened*
and correlates with, but is not the same claim as, *when the network
matured*. Not rewriting the rest of this brief to reflect that
distinction yet; flagging it here so it isn't read past.

## Is milestone_year itself robust? Independently checked (2026-09-25), not assumed

Raised directly, given how much of this post's argument leans on it:
`analysis/metrics.py:get_success_milestone()` is entirely tournament/
Liquipedia-derived (last year of the earliest 2-consecutive-year window
with qualifying-tier tournaments across 2+ continents) — it has never
been checked against Twitch viewership directly. Built
`research/foundations/notebooks/milestone_year_reverse_engineering_check.ipynb`
to do that: a non-parametric changepoint detector (the Pettitt statistic)
on each title's own historical Kaggle monthly viewership (2016–2024),
tested for significance the same way this project validated the Leiden
communities — 500 permutations of the title's own data, not the test
statistic's asymptotic formula.

**Where testable, real convergent validation**: for the 12 titles whose
milestone_year falls inside Kaggle's own 2016–2024 window, the
independently-detected changepoint lands a mean of 1.17 years away — 4
exact matches, 7 within a single year. Two completely different data
sources (tournament records vs. Twitch viewership) and methods
(tier/region rule vs. changepoint statistics) landing this close is real
corroboration `milestone_year` never had before.

**Where it fails, the reason is structural, not a mark against
milestone_year**: for the 8 titles whose real milestone predates 2016,
Kaggle's data doesn't go back far enough to see it — mean |diff| = 12.9
years, because the test is forced to report *some* break within its
visible window regardless of the title's true history. **An unplanned
bonus finding inside that failure mode**: nearly every one of those 8
titles' detected "changepoint" lands in the same 2019–2023 band —
independently rediscovering the same platform-wide 2019–2021 clustering
`creator_current_tenure_by_title.ipynb` already found via account-arrival
timing (14 of 23 titles). Two unrelated methods landing on the same
signal is stronger evidence it's real than either alone.

**Net: milestone_year is independently confirmed for about half the
tracked titles, and this specific check simply can't speak to the other
half** (8 pre-2016, Tekken 8/Mortal Kombat 1 excluded for too little
Kaggle coverage, Teamfight Tactics just short of significance at
p=0.052) — not "shaky," not "solid," a calibrated answer that says
exactly which titles' era values carry independent corroboration.

### Correction (2026-09-25): the pre-2016 titles' detected "changepoint" is not an unconfirmable echo of their own milestone — it's a different, later, identifiable event

Sharpened directly: for the 12 in-window titles, `diff` (detected year
minus milestone_year) is 0 to +3 for every single one — a consistent,
title-specific signal, always at or shortly after the real event, never
before. The 8 pre-2016 titles don't show a fuzzy version of that same
pattern; their diffs are wildly inconsistent with their own real ages
(AoE2 milestone 2000, Hearthstone milestone 2014 — 14 years apart in
real history) yet 6 of the 8 detected changepoints land within a tight
2019–2021 band regardless. A detector that's genuinely tracking each
title's own delayed milestone should scatter with each title's own
distance from 2016; instead it converges — which means it isn't finding
each title's own signal at all, it's finding something else that
happens to be the biggest break sitting in the window it can see.

**Checked what that something else actually is, rather than leaving it
as "platform-wide, TBD":** summed Kaggle's `Hours_watched` across all
~200 tracked categories (not just this project's 23 titles) into one
platform-wide monthly series and ran the identical Pettitt test on it.
Result: the single largest break in Twitch's own aggregate viewership,
2016–2024, is **March 2020** (p<0.002 against 500 permutations) — driven
by the two largest month-over-month jumps anywhere in the series (+26%
March 2020, +50% April 2020, roughly doubling hours watched by mid-2020
and staying elevated through 2021 before receding from 2022 onward).
This is squarely the COVID-19 lockdown period, not a coincidence of
calendar placement, and it directly explains why an old title's own
changepoint detector — blind to its real pre-2016 history — latches onto
2019–2021 as the "biggest break": for most categories on the whole
platform, it genuinely was. It's also the same underlying event the
2019–2021 creator-account-creation clustering
(`creator_current_tenure_by_title.ipynb`, 14/23 titles) most plausibly
reflects — a huge wave of new streamers and viewers joining Twitch
during lockdowns would show up in both an aggregate-viewership
changepoint and a currently-active-account-age distribution, via two
completely unrelated measurement methods.

**Not a universal explanation for every date in the cluster, worth
being honest about**: League of Legends/Hearthstone/AoE2 (2019) and
Counter-Strike 2 (2020) sit right at COVID's leading edge and are well
explained by it. Guilty Gear -Strive- (2022) and Street Fighter 6 (2023)
more plausibly reflect their own real relaunch events (Strive shipped
2021, SF6 shipped 2023) landing in the same broad multi-year window by
coincidence, not the pandemic surge itself. The core of the cluster has
a real, dated, external cause; the tail members likely conflate a
title-specific event with sitting in the same neighborhood.

### Does COVID also explain the 12 in-window titles' good milestone_year agreement? Checked directly — partially, for about half

Raised directly, since the 12 in-window titles' changepoints (used above
as the strong validation case) also land disproportionately close to
2020. **First-order evidence against it being COVID wholesale**: unlike
the pre-2016 group, these 12 changepoints don't collapse onto one
common date — they spread 2018–2023, tracking each title's own
milestone_year with a small, consistent lag (0–3 years). A pure
rising-tide effect should produce the same convergence-onto-2020 pattern
seen in the pre-2016 group; it doesn't.

**But raw Hours_watched rides on top of the platform's own level, so
isolated each title's *share* of total platform attention
(title_hours ÷ platform_total_hours per month) and re-ran the identical
Pettitt test — this cancels COVID's level shift and isolates whether a
title gained or lost *relative* standing.** Genuine split, not one
story:
- **Six titles' share-changepoint lands at essentially the same date as
  their raw-hours changepoint** (Rocket League, Fortnite, Free Fire,
  VALORANT, Wild Rift, Mobile Legends: Bang Bang) — real, independent
  gains in relative platform attention, not an artifact of the tide.
  Milestone_year agreement for these is solid.
- **Six others' share-changepoint lands considerably later** (Overwatch,
  Rainbow Six Siege, PUBG, PUBG Mobile, Apex Legends, Brawl Stars) —
  their absolute-hours break tracked milestone_year well, but their
  relative share of the platform didn't actually shift until years
  later. Part of why their raw numbers broke near milestone_year is that
  COVID lifted everyone's absolute hours together, coincidentally
  overlapping these titles' own milestone window rather than being
  independently caused by it.
- **Rainbow Six Siege's share-changepoint lands in March 2020 exactly**
  — the same month as the platform-wide aggregate break. Read as a real,
  title-specific COVID effect in its own right (a squad-based tactical
  shooter picking up disproportionate relative share exactly as
  lockdowns hit), distinct from and unrelated to its 2017 milestone.

**Net: COVID is tangled into roughly half of the 12-title validation
set, not all of it and not none of it.** The other half's agreement
survives this check as genuinely independent corroboration.

## What each community/title actually looks like behaviorally

Written up 2026-09-25 from `cross_title_intra_community_comparison.ipynb`'s
full 23-title profile (Gini/concentration, median account age/tenure, %
single-session/occasional-ness, all z-scored against the 23-title
median) — the descriptive companion to the clustering-vs-Leiden test
above, read with the same robustness caveats: lean on the C1 story with
confidence, read C0/C3 as individual titles rather than cohesive groups.

**C1 (classic PC) — the one community with a real, coherent, shared
profile: high concentration, old population, relatively frequent (not
one-off) streamers.** (See the 2026-10-02 update above — StarCraft II's
*cluster membership* has since moved to the fighting-game group; its own
behavioral profile, described below, is unchanged.) Dota 2 is the single most concentrated title in
the entire dataset; StarCraft II has by far the oldest population despite
being one of the smaller pools (636 channels) — a small, aging, dedicated
scene, not a large one. Matches the "top-heavy, veteran, dedicated"
shape you'd expect from long-established PC esports with a real
semi-professional streaming layer under the top broadcasts.

**C0 — no shared profile, consistent with it failing every robustness
check above; each title reads on its own.** League of Legends and
Teamfight Tactics both look like C1 transplants behaviorally (high
concentration, old tenure, low occasional-ness) — see below for why
that doesn't actually put them in C1. Fortnite, Rainbow Six Siege, and
Rocket League instead read as broad and casual — all three near the top
of the whole dataset on occasional-ness, Fortnite despite having the
single largest creator pool of any tracked title (54,645 channels): a
huge, shallow-engagement population, not a huge dedicated one. Apex
Legends, Overwatch, and VALORANT are the closest thing to "unremarkable"
in this battery — near-zero on all three axes.

**C2 (mobile) — a real "young population" story for three of five
members, with two clean, already-explained exceptions.** Brawl Stars,
Mobile Legends: Bang Bang, and PUBG Mobile are all well below median on
tenure; PUBG Mobile is the most extreme (youngest tenure of all 23
titles *and* the most dedicated/least-occasional pattern — young and
frequent, not young and casual). Free Fire trades "young" for "broad and
casual" (low concentration, high occasional-ness, closer to Fortnite's
shape than its own siblings'). Wild Rift keeps the low concentration but
drops "young" entirely — the LoL-veteran-carryover population its
milestone year alone wouldn't predict.

**C3 (fighting games) — four genuinely different profiles, no shared
fighting-game signature.** Guilty Gear -Strive- has the single lowest
concentration of any title in the dataset. Mortal Kombat 1 has the
second-highest occasional-ness of all 23 (behind only Siege/Rocket
League) — a one-off-streamer-dominated population, plausible for the
newest-launched of the four (2023) still attracting drive-by attention.
Street Fighter 6 looks concentration-wise like a C1 title. **Tekken 8
pairs low concentration with high tenure — old, veteran-skewing, despite
being the single newest release in this entire 23-title set (2024) — the
clearest single-title evidence anywhere in this line of work for the
franchise-carryover "razor" raised earlier this session: Tekken 7's
audience didn't reset when Tekken 8 launched.**

**Why League of Legends' C1-like behavior doesn't put it in C1**:
behavioral resemblance and audience crossover are the two separable
properties this whole robustness-check round exists to keep apart, and
LoL is the clearest single illustration of why that distinction matters.
Checked directly, not assumed: LoL's creator-crossover enrichment against
every C1 title is *below* 1.0 — 0.07 with Dota 2, 0.23 with PUBG, 0.27
with Counter-Strike, 0.35-0.41 with StarCraft II/Age of Empires
II/Hearthstone. LoL creators cross over with C1 titles *less* than
chance would predict, not more — the opposite of enrichment. The Leiden
partition is built entirely from that crossover graph, so LoL was never
going to land in C1 regardless of how similar its internal community's
character turns out to be. LoL and C1 are (loosely) the same species —
similar conditions of genesis producing similar internal behavior — but
not remotely the same interbreeding population.

## New thread (2026-10-02): pro-player cohorts, extending this post to the "Professionalised Play" rung

Raised directly: everything above is creator/streamer-side ("Watch," on
the `mode_of_engagement_model` ladder). Does the same community structure
(C1/C0/C2/C3) organize the *professional player* population the same way,
or does that clock run independently? Uses `players_lpdb`/
`squadplayers_lpdb` (LPDB Phase 4, built 2026-10-01) — a different
population from the creator-cohort work, not a re-check of it.

**First pass — `research/foundations/notebooks/pro_player_debut_age_and_tenure.ipynb`
(2026-10-02): debut age and career length, by community.** Scope: C0/C1/C2
only — C3 (fighting games) has no player data at all, a deliberate gap
(LPDB's `player` resource can't cleanly attribute a fighting-game pro to
one title; see that collector's own docstring), needing its own
crossover-style analysis rather than being forced into this one. C2's
numbers here are a 2-of-5-titles preview (Free Fire, PUBG Mobile only —
Brawl Stars/Mobile Legends/Wild Rift still mid-sync) and should be
re-read once that lands.

**The standing hypothesis going in — that C0 titles skew younger at
debut, across every cohort — did not hold.** Instead: **C1 (classic PC)
debuts oldest of the three measured communities, consistently across
every debut-year cohort with real data.** C1 also has the longest median
career length. **This is a real, if modest, piece of convergent
evidence**: C1's audience was already found to be old/concentrated/
dedicated (`cross_title_intra_community_comparison.ipynb`); this notebook
finds C1's *pro population* independently shows the same "veteran,
dedicated" shape, on a completely different data source (LPDB roster
history, not Twitch viewership).

**Update (2026-10-02), re-run once C2 gained its 3 missing titles: the
three-way separation softened to a two-way one.** Pooled medians: C1
20.1 years, C0 19.3, C2 19.2 (n=7,520/16,440/3,419). **C1 is still
significantly older-debuting than both C0 and C2 — but C0 and C2 are no
longer statistically distinguishable from each other** (p=0.353, was
p=5.04e-10 on C2's earlier 2-title preview). C2's "youngest" reading
turned out to be partly an artifact of which 2 of its 5 titles had data
first, not a settled trait — C0's lack of a standout profile now extends
to being indistinguishable from C2 too, not just "unremarkable" in
isolation.

**Two follow-ups added the same day, both real negative results, not
confirmations:**
- **Does a title's own age (franchise release year, not debut-year
  cohort) predict its pros' debut age? No** — Pearson r=-0.225 (p=0.354),
  Spearman rho=-0.315 (p=0.190) across 19 titles. The debut-age
  differences found above are a community effect, not simply "older
  game, older debuts." C3's fighting titles have known franchise years
  (Street Fighter 1987, the oldest in the dataset) but no player data to
  plot against them — listed for the record, not dropped.
- **Is career length actually power-law distributed, the way its
  mean-roughly-double-the-median shape suggests? No, checked properly
  (Clauset-Shalizi-Newman MLE fitting + likelihood-ratio comparison,
  `powerlaw` package) and decisively rejected for all three communities**
  — lognormal and exponential both fit significantly better than a power
  law (p=0.0 in every comparison). Even taken at face value, the
  power-law regime would only ever have covered 20-34% of each
  community's upper tail. The real skew is lognormal-shaped, not a power
  law — worth describing that way going forward, not with power-law
  language.

**A third follow-up, and the cleanest result in the whole pro-cohort
thread: within a title, launch-era pros are consistently older than
established-era pros.** A different question from the franchise-age
check above — not "is an old title's overall median debut age
different," but "for one title, is its own pioneer cohort older than
the cohort that debuts once the scene is established." Tested on the 15
titles whose real release year falls inside this project's actual
roster-history coverage (League of Legends/Dota 2/Counter-Strike/
StarCraft II all launched before there's any roster data to see their
launch in). **14 of 14 computable titles show the same direction** —
launch-cohort median age higher than established-era median, every
time (a sign test alone puts this around p=0.0001) — with 6 clearing
significance individually on real sample sizes: Fortnite (+2.60 years),
PUBG (+1.85), Rainbow Six Siege (+1.48), VALORANT (+1.10), Overwatch
(+0.95), Apex Legends (+0.42). Rocket League is the one genuine
exception (+0.04, flat on a real sample). **Unlike every other axis in
this thread, this doesn't separate by community** — C0, C1, and C2 all
show comparable-sized gaps where sample size allows. Read as a general
esports-scene-maturation effect (a new scene's first cohort draws on
older, likely cross-trained talent; a title only develops its own
younger pipeline once established), not a community-level trait — and
as the reason the franchise-age pooled check came back null: pooling
every cohort together dilutes an old title's long-past launch moment
into decades of established-era data, washing out exactly this effect.

**A fourth follow-up, the most direct test yet of a genuinely
generational-cohort hypothesis: do newer titles draw from a younger
pool of people than older titles, structurally — not just "right now"?**
Sharpened directly with a worked example (Fortnite should be younger
than Counter-Strike both in any given calendar year *and* at the same
point in each title's own lifecycle, if newer titles genuinely capture
younger people rather than just happening to be newer). Birth year — not
debut age — is the right variable here, since it's fixed per player
regardless of career timing. **Three tests, three different controls,
two different answers:**
- **Pooled birth year vs. release year, and a fixed-calendar-year
  snapshot, both confirm it, consistently**: release_year correlates
  with median birth year across each title's whole tracked population
  (r=0.633, p=0.0036), and newer titles have significantly younger
  *currently active* rosters at a fixed calendar moment, replicated at
  two different snapshot years (2020: r=-0.542, p=0.0166; 2023:
  r=-0.539, p=0.0172).
- **Controlling for lifecycle stage (same years-since-release across
  titles) makes the relationship vanish almost completely** (r=-0.035,
  p=0.893). An older title has simply had longer for its own cohort to
  age in place by any fixed calendar year — that alone produces the
  snapshot pattern above without needing a real "newer titles capture
  younger people" mechanism.
- **The Fortnite/Counter-Strike pair itself is a genuine exception that
  holds at both levels** — but PUBG and Fortnite, released the *same
  year* (2017), sit 4 years apart in median age at the identical
  lifecycle point. That's a title-specific (likely genre/audience-
  targeting: broad casual battle royale vs. hardcore tactical shooter)
  effect, not a chronological law that applies evenly across the 17-19
  titles measured.

**Net**: real, significant support for the hypothesis in the pooled and
calendar-snapshot views; no support for it as a general structural
tendency once lifecycle stage is controlled for. It's true for some
titles (Fortnite clearly one), for reasons that look like
audience/genre targeting rather than era itself — worth a dedicated
look at specific title pairs (Fortnite vs. PUBG is the cleanest
starting point) rather than treating "newer = younger" as a title-
spanning law.

**A fifth follow-up, formalized into its own notebook —
`research/foundations/notebooks/pro_player_roster_aging_curve.ipynb`
(2026-10-03): is there a shape to how rookie dilution fades as a title
matures?** Defines one clean benchmark per title-year: a fully-stagnant
roster (zero effective rookie replacement) would show its median active-
player age rising by exactly +1.0 year every calendar year
(`delta=1.0`); `delta=0` means rookies exactly offset aging
(steady-state); `delta<0` means actively getting younger. **Real, highly
significant shape, not a flat constant**: pooled across 187 title-years,
delta correlates with years-since-release (r=0.325, p=0.000006) —
climbing from 0.05 in years 2-4 (the point of maximum rejuvenation) to
0.83 by 12-20 years since release (near-full stagnation). **Checked
whether that's a real within-title pattern or a cross-title pooling
artifact: mostly real** — 4 of 9 titles with 10+ years of their own
history show individually significant positive trends (Overwatch
r=0.803, Dota 2 r=0.624, Counter-Strike 2 r=0.540, StarCraft II
r=0.536), 4 more point the same direction without clearing significance
on small samples, and only Age of Empires II shows no relationship at
all (it never had much of a rejuvenation gap to begin with — visually
confirmed, it tracks the fully-stagnant line almost from its first
plotted year, unlike CS2/Dota2/StarCraft II/LoL's visible bend from flat
to steep). **Reframes the earlier "mean delta ~0.45" finding**: that
number isn't a stable property of esports rosters — it's an average
taken across titles sitting at very different points on one shared
maturation curve. Includes full small-multiples charts for every title.

**A sixth follow-up, testing what actually drives rejuvenation —
`research/foundations/notebooks/pro_player_rejuvenation_drivers.ipynb`
(2026-10-03): a 6-candidate battery (scene growth rate, roster churn,
grassroots tournament count, grassroots tournament share, audience
growth, franchised league structure), each tested two ways — a raw
pooled correlation against `delta`, and a partial correlation
controlling for `years_since_release` (since several candidates
plausibly correlate with title age themselves, and only the partial
correlation is evidence of something beyond "this title is young/old").**
**None of the five continuous candidates clear significance on the
partial correlation.** Churn rate comes closest (partial r=-0.122,
p=0.097) after looking strong raw (r=-0.203, p=0.0053) — most of its
apparent relationship turns out to be the age effect already known
about, not an independent driver. Audience growth, grassroots
tournament share, and scene growth rate are all indistinguishable from
zero. **The grassroots-tournament-opportunity hypothesis specifically
is not supported** — grassroots_count's partial correlation (r=-0.046,
p=0.530) is essentially no signal. **Franchising is the one suggestive
exception, on too small a sample to confirm**: both observable
transitions (LCS 2018, VCT Partnership 2023) show delta rising
(toward *more* stagnation) after franchising, not less — consistent in
direction with the churn notebook's own franchising finding — but n=2
titles is nowhere near enough to call this settled. **Net: this battery
rules out more mechanisms than it confirms** — the real driver of why
rejuvenation fades as a title matures remains open, with title-specific
idiosyncrasy (the same kind already seen in the Fortnite-vs-PUBG
divergence) still the leading unexplained candidate.

**A seventh follow-up, directly testing whether this whole thread is
being distorted by data-population issues —
`research/foundations/notebooks/pro_player_tail_and_elite_robustness.ipynb`
(2026-10-03): (1) is there a long tail of short-career "never-quite-
made-it" pros, and is it skewing anything, and (2) do the community
findings hold at the elite tier specifically?** On (2): real tier-level
filtering isn't possible yet — there's no data linking a player to
which tournaments they actually competed in at what tier; a background
task is building an LPDB `placement`-resource collector to fix this
(not finished). This notebook uses an earnings-based proxy (top 25% by
`total_earnings` per title) instead, explicitly flagged as approximate.

**The tail is real, and it's large: 55.0% of players with a fully-ended
career never had more than a single roster stint, and 34.6% (24,085
players) meet a strict "flash" definition** (single stint, under 6
months) — not a footnote, over a third of the entire ended-career
population. **But it doesn't distort any of the three headline findings
tested against it:**
- **Debut-age-by-community**: excluding the flash tail moves medians by
  0.05–0.10 years (noise-level); every pairwise significance result
  holds at the same order of magnitude.
- **Elite-tier (earnings-proxy) robustness**: C1 still debuts oldest,
  C0/C2 still indistinguishable, among top-25%-earners specifically —
  but every community's median drops by roughly a full year at the
  elite tier, uniformly (debuting young correlates with eventual
  top-earner success, consistently across all three communities — a
  real secondary finding).
- **The roster-aging-curve finding**: restricting to players with a
  real eventual career (≥1 year) leaves the years-since-release/delta
  relationship essentially unchanged, if anything marginally stronger
  (r=0.356 vs. the original 0.325).

**Net: the short-career tail is real and worth knowing about on its own
terms, but none of this thread's community-level or maturation findings
turn out to depend on how it's handled.** The elite-proxy check should
be re-run once the real placement-tier data lands.

**Second pass — `research/foundations/notebooks/pro_player_roster_churn.ipynb`
(2026-10-02): roster churn/team-hopping, over time and by community.**
Tested directly: does franchising a league reduce roster churn? **Mixed,
not confirmed.** League of Legends shows the opposite — churn *rose*
after LCS franchised in 2018 (0.45-0.51 before, climbing to 0.70 by 2025),
not fell. VALORANT's trend is gentler and partially consistent in
direction (peaking at 0.611 in 2022, the year *before* VCT Partnership
franchised in 2023, then declining to 0.51 by 2025) but the peak
precedes the transition, so it reads more like a cycle turning over than
a franchising-caused drop. Two titles is too small to generalize from
either way.

**The community-level comparison is the more solid result, and adds a
third axis to C1's "veteran, dedicated" profile.** C1 has the lowest
roster churn of the three measured communities (median 0.272,
2019-2025 pooled) and **C0 has the highest (0.497)** — the first measure
in this whole thread where C0 shows a distinctive character rather than
sitting in the unremarkable middle (debut age and career length both put
it there). Two likely-artifactual zero-churn outliers (Hearthstone,
Teamfight Tactics — both individual-competitor formats where a "squad"
doesn't mean the same thing as a traditional 5-player roster) were
checked and don't drive this: excluding Teamfight Tactics *raises* C0's
median to 0.512, strengthening rather than explaining away its
high-churn character.

**Third pass — `research/foundations/notebooks/pro_player_earnings_concentration.ipynb`
(2026-10-02): does pro earnings concentration mirror audience-attention
concentration?** Checked directly via Spearman correlation against
`cross_title_intra_community_comparison.ipynb`'s own audience-Gini
table: **no, genuinely not** — rho=0.235, p=0.365 across all 17 covered
titles. A title's audience piling onto a few huge channels does not
predict its pro scene's earnings piling onto a few huge earners; these
are independent kinds of concentration, not two readings of the same
property, and should keep being reported separately rather than assumed
to track each other.

**The community-level earnings pattern is different from every other
axis in this thread: C0 and C1 are tied, and C2 is the one that stands
apart.** Mean Gini: C0 0.843, C1 0.836 (not meaningfully different from
each other), both well above C2's 0.740 — mobile pro earnings are
genuinely more evenly spread, not winner-take-all the way C0/C1 both
are. StarCraft II (0.915), not Dota 2, is the single most
earnings-concentrated title, despite Dota 2 holding that title on the
audience side. **Checked whether this is just a side-effect of C1's
longer average careers (part 1's tenure confound) — it isn't**: Gini on
earnings-per-active-year gives the same C0≈C1>C2 ordering (0.799, 0.815,
0.685), essentially unchanged from the raw lifetime figures.

**Fourth pass — `research/foundations/notebooks/pro_player_regional_distribution.ipynb`
(2026-10-02): does pro regional concentration mirror audience regional
concentration?** On the community axis: **C2 (mobile) is the regionally
concentrated one, not C0 or C1** — mean top-region-share 55.98% (vs.
C0's 38.20%, C1's 42.85%), every one of its 5 titles dominated by
Asia-Pacific specifically. **This is the fourth axis in this thread, and
the fourth time a different community has come out as the distinctive
one** (C1 on age/tenure/churn-stability, C0 on churn-instability
specifically, C2 now on regional concentration) — no single community is
uniformly "the odd one out" across every measure.

**The cross-check against audience-dominant-region produced a real,
directional finding, not just a mismatch count.** Checked against
`creator_crossover_community_detection.ipynb`'s own audience-region table
(language-based): only 6 of 18 comparable titles match. Of the 11 genuine
mismatches, **9 have Asia-Pacific as the dominant *pro* region while the
dominant *audience* region is CIS, Europe, or Latin America** — Asia-Pacific
supplies pro talent for a title far more often than it is that title's
dominant viewing region. **CIS runs the opposite pattern: it never once
is the dominant pro region among these 17 titles, despite being the
dominant audience region for 6 of them** — a title's competitive talent
pool and its audience are frequently geographically different
populations, not the same population described twice (Counter-Strike 2
is the clean illustration: Europe-dominant pro scene, CIS-dominant
audience). One real methodological note carried through this pass: the
audience scheme (language-based) structurally cannot see North America,
most of Latin America, or MENA as a dominant region, so a subset of
"mismatches" are scheme artifacts, not real divergence — checked and
separated from the genuine ones, not pooled together.

The C3 pro-crossover analysis mirroring `creator_crossover.ipynb`'s own
method is the one piece of this thread not yet started.

## Material already in hand (shared area notebooks, not duplicated here)

All in `research/foundations/notebooks/`:

- `creator_specialization_rate.ipynb` — the 88.8%-vs-69-77% headline
  number itself (updated 2026-10-02, see above — was 90%-vs-74-80%),
  robustness-checked (per-title breakdown, the observation-window/
  exposure confound). Built 2026-09-21, once this stopped being a side
  observation and became the post's centerpiece.
- `creator_crossover_community_detection.ipynb` — the core crossover
  graph, Louvain communities, publisher/platform/genre/region/era
  cross-tabs.
- `creator_crossover_null_model_test.ipynb` — the configuration-model
  significance test; the source of "3 of 4 communities are real, one
  (Community 0) is not."
- `creator_crossover_leiden.ipynb` — replication via a second community-
  detection algorithm (identical partition, ARI=1.000).
- `creator_crossover_subset.ipynb` — the 7-title mobile-readable subset
  built for Post 2.
- `region_language_confound.ipynb` / `region_coverage_artifact_test.ipynb`
  — the region/language variable, including the Europe-coverage-artifact
  retraction.
- `creator_current_tenure_by_title.ipynb` — account-creation-date /
  "razor" work: the PUBG Mobile/MLBB step (real, dated, tied to Russia's
  2024-08-01 YouTube throttling), the recent-recruitment-vs-hours
  correlation (N=8, r=0.80), and the survivorship-bias confound (title
  age alone explains 39% of the "peak arrival window" gap) — all
  creator-side, not audience-side; that caveat carries into this post
  directly.

In `notebooks/` (this subproject's own, not shared — event- and
comparison-specific):

- `valorant_network_anatomy.ipynb` — Step 1, the five-dimension VALORANT
  battery (see above).
- `cross_title_intra_community_comparison.ipynb` — Step 2, the 23-title
  clustering and Leiden comparison (see above).

## Open, not yet decided

- Exact structure/argument of the post itself — not started, this is
  still a materials-gathering brief, not a draft.
- How much of the survivorship-bias/churn material (real and important,
  but a methods caveat more than a "shape of the network" finding)
  belongs in this post directly vs. a methods appendix/footnote.
