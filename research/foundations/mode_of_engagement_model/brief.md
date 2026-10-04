# Mode of Engagement: A Prior Classification Layer

Part of `foundations/` — see `../brief.md`. **Status: PENDING, but now
first in the working order (resequenced 2026-09-19)** — the
competitive-practice mode (§3) has a full, evidenced definition as of
`../posts/post_2_unit_of_analysis/` (this project's "Post 2"), which is
what actually resolved the sequencing question §6/§8-task-6 originally
left open on 2026-09-17. Still PENDING rather than ADOPTED: the
narrative-consumption and social-creative modes remain undeveloped (§3),
and §5's cross-mode comparability work hasn't started.

**Post 2's own scope narrowed as of its Draft 4 (2026-09-19)**: the
definition below is unchanged, but the post now stops there rather than
continuing into "how do we compare and contrast esports" (its own
"Problem 2") — that empirical work (genre/niche porousness, creator
crossover, region/language confounds) has been moved to a separate,
not-yet-titled follow-up post. `../notebooks/creator_crossover_subset.ipynb`
and `../notebooks/region_language_confound.ipynb`, built for that
section, are parked in `../posts/post_2_unit_of_analysis/` pending that
post's own folder — real, correct evidence, just not evidence *for this
post* anymore. See §9's last bullet.

## 1. Why this exists

Raised directly 2026-09-17, out of a felt problem with
`esports_vs_game_fandom_signal_model` rather than an abstract exercise:
strip out the narrow slice of people who watch a title's esports scene
but never play it, and "esports fandom" looks inseparable from "game
fandom" generally — esports viewership reads as a behaviour that emerges
in people who already play, not a distinct audience. (Testable, not yet
tested — see §5, task 4.)

But the reasonable-sounding fallback, "fine, then just compare against
*game* fandom broadly," doesn't survive scrutiny either. Is God of War
fandom the same kind of thing, at a sociological level, as VALORANT
fandom? One resembles being a film fan; the other resembles playing in a
5-a-side league. **"Game" (short for "video game") names a delivery
substrate — the fact that the activity is software — not a mode of
engagement or the role the activity plays in someone's life.** Treating
"game fandom" as a coherent category because its members share a
technology is the same move as treating "cinema fandom" as one thing
because action films and documentaries share celluloid.

## 2. The core claim

**The unit of analysis this project needs isn't "video game" (a
technology category) or a single esports/game-fandom split — it's *mode
of engagement*: the behaviour-group a title's fandom actually belongs to,
defined by what the activity is *for* in people's lives, not by what it
runs on.** Mode of engagement sits *above* genre, platform, and region in
the classification stack — those describe a title; mode describes what
kind of relationship people have with it.

This is deliberately fluid, not a clean partition — see §4. The point of
naming it isn't to force every title into exactly one box, but to stop
silently assuming two titles' fandoms are comparable just because they
share a genre tag or a delivery technology.

## 3. Candidate modes (draft, not final)

Three, provisionally, drawn from the titles already in this project's own
scope:

- **Competitive-practice.** Now has a full, evidenced definition, not
  just the sketch below — see `../posts/post_2_unit_of_analysis/`
  (drafted 2026-09-17 to 2026-09-19): **any persistent, competitive,
  community practice of play, mediated by software.** No
  professionalization gate — casual and competitive players differ by
  degree, not by type, and watching/playing are treated as the same
  underlying practice rather than two audiences to disambiguate.
  Deliberately not scoped to "video game": chess, poker, the Excel and
  GeoGuessr world championships all qualify on the same terms, which is
  the whole point (§3's chess/poker note below anticipated this before
  the post resolved it). VALORANT, Counter-Strike, Dota 2, Street
  Fighter all qualify straightforwardly. `esports_vs_game_fandom_signal_model`'s
  `broadcast_tier`-based work is now understood as *detecting* this mode
  in this project's Twitch data specifically, not as a separate,
  competing definition of it (§6). **Draft 4 sharpens the watch/play
  claim further, not just "differ by degree" but an explicit list of
  what the practice actually consists of**: playing, watching,
  Discord/chat participation, social-media engagement with pros,
  event travel, merchandise purchase — "a soup of behaviours," not one
  activity. That list is a first, prose-form draft of §5's still-undesigned
  cross-mode-comparable component dimensions (see §8 task 3) — a
  starting point to formalize, not yet a measurement framework.
- **Narrative-consumption.** Closer to a film or book than a sport —
  authored story, largely solitary or para-social engagement, no ranked
  or competitive structure. God of War is the reference case; none of
  the 23 currently-tracked titles are a clean example, since this
  project's tracked list was built esports-first (see `../brief.md`).
- **Social/creative-sandbox.** Community forms around a shared space or
  shared activity, not around competition or an authored story. GTA
  Online's NoPixel roleplay scene is the case already sitting in this
  project's own data (`platform_viewership_snapshots.content_segment`,
  `research/wider_game_fandoms/gta_launch_case_study/`) — intense,
  sustained fandom with no ranked ladder and no authored narrative arc
  driving it.

**These are not substrate-exclusive.** Chess and poker are not video
games and predate digital delivery entirely, yet both show the same
competitive-practice fandom shape this project associates with esports —
ranked play, professional circuits, livestreamed tournaments, a
watch-but-play-casually-or-not-at-all audience. That's evidence "digital"
is infrastructure, not the sociologically load-bearing part of the
category: what matters is a legible competitive structure plus a
broadcast mechanism, and most of this project's titles happen to deliver
both through video-game software because that's the infrastructure that
existed when they formed (a direct connection to
`../technological_contingency_of_fandom_formation/`'s own claim — worth
making explicit there once this model firms up).

## 4. Fluidity: mode is per-context, not always per-title

A single title can occupy more than one mode depending on which part of
its audience or which mode of play is in view. GTA V's mainline campaign
is narrative-consumption; GTA Online's roleplay servers are
social-creative sandbox; neither is competitive-practice. Treating "GTA
V" as one title with one mode would erase exactly the distinction this
model exists to draw. **Mode may need to be a property of a
community/context (a subreddit, a stream category, a server type) rather
than a title-level tag in `config/titles.yaml`** — an open question, not
resolved here (§5, task 1).

## 5. Why comparability matters, and what it requires

Two things need to be true at once, per direct instruction 2026-09-17:
mode-of-engagement should let this project **compare fandom components
across modes** (is a competitive-practice fandom's community intensity
comparable to a social-creative sandbox's, on some shared axis?) as well
as **compare subtypes within a mode** (VALORANT vs. Counter-Strike, both
competitive-practice, as `fandom_and_niche_model` already does). The
second is what this project already does. The first requires something
that doesn't exist yet: **fandom decomposed into component dimensions
that aren't mode-specific**, e.g. ritual/routine engagement frequency,
creator/parasocial attachment, competitive-identity investment,
social-coordination intensity, narrative/lore investment, collecting or
completionism behaviour. A competitive-practice fandom and a
social-creative one will score differently across those dimensions, but
the dimensions themselves should be measurable in both — that's what
makes "compare across modes" a real claim rather than a category error
repeated one level down. Not designed yet (§8) — though see §7 for a
first prose-form candidate list Post 2's Draft 4 already sketched.

## 6. Relationship to the other three foundational pieces

- **`esports_vs_game_fandom_signal_model`** — **reconciled 2026-09-19,
  not left ambiguous.** Its old operational definition (§4 of that
  brief: esports fandom = viewership in `broadcast_tier ∈
  {primary_official, detected_costream}`) is retained, but reframed as a
  *measurement operationalization* of this model's competitive-practice
  mode, not a competing conceptual definition of esports fandom itself.
  That brief's §2 is rewritten to drop the game-fandom-vs-esports-fandom
  disambiguation project entirely and cite this brief instead — see that
  brief's own §2 for the rewrite.
- **`fandom_and_niche_model`** — **reconciled 2026-09-19.** Its old §2
  scoping definitions ("Esports": professional/cash-gated;
  "Successful esport": a 2-year A-tier history as the entry bar) directly
  conflicted with this model's definition, which drops professionalization
  entirely. Fixed by citing this brief for what counts as an esport at
  all, and reframing "Successful esport" as a maturity/scale threshold
  measured *within* the competitive-practice-mode category rather than
  the gate into it — `get_success_milestone`'s pipeline is unaffected,
  only what its output is understood to mean. This was also the
  concrete argument for sequencing mode *before* niche: a `{genre ×
  platform × region}` cell built on an unrevised "Esports" definition
  would have been comparing across the exact category gap this model
  exists to name.
- **`technological_contingency_of_fandom_formation`** — see §3's chess/
  poker point: if competitive-practice fandom predates digital delivery,
  then "digital substrate" is one technological condition among several
  that can produce this mode, which is squarely that brief's own claim
  (fandom formation is contingent on the tech/social conditions present
  when it formed) rather than a separate idea living here by accident.
  **A second, opposite-direction connection surfaced in Post 2's Draft 4
  postscript**: citing a 2023 Deloitte report on traditional-sports fans
  increasingly engaging via second-screen, social platforms, betting,
  and VR interest — "are there any sports that aren't esports now?" That's
  the same contingency claim running forward instead of backward: not
  "esports emerged because specific tech conditions existed," but
  "traditional sports are being reshaped toward competitive-practice-mode
  behaviour as those same conditions arrive for them, later." A genuine
  candidate second case study for that brief, not yet written up there —
  currently just an observation in a postscript.

## 7. A practical implication, from Post 2's Draft 4: attention over video games

Not a research question, a business-facing consequence worth recording
since it's new to this brief and speaks directly to the audience
`../brief.md` names (esports-industry professionals): **if the video game
is an interchangeable substrate and the human network is the actual unit
of analysis, then the thing that generates value is attention, and
attention is a property of the network, not of any one piece of
software.** Practically, that argues against scanning multiplayer-title
release calendars as the primary way to find new esports-adjacent
opportunity — the Excel/GeoGuessr World Championship examples (§3) are
the concrete illustration — and toward looking for *any* substrate
capable of generating a persistent, competitive, community practice of
play, regardless of whether it was built as a game at all. Not yet
connected to anything measurable in this project's own data; recorded
here as a live idea Post 2 raised, not a task with a method behind it
yet.

## 8. Task list

1. Decide whether mode is title-level or context-level (§4), and if
   context-level, what the actual unit is (subreddit, stream category,
   server/game-mode) — needed before any title in `config/titles.yaml`
   can be tagged. Still open.
2. ~~Draft structural markers for the competitive-practice mode
   specifically~~ — **done, superseded by a cleaner result.**
   `../posts/post_2_unit_of_analysis/` didn't produce a checklist of
   structural markers, it produced an actual definition (§3) that
   doesn't need one: persistent + competitive + community +
   software-mediated, no professionalization gate. Whether this
   reproduces or disrupts the current genre taxonomy if applied to all
   23 tracked titles is still open — that's now task 2a below.
   2a. Apply the §3 definition to all 23 tracked titles and check
       whether it reproduces or reshuffles the current genre-based
       grouping. Not started.
3. Design the cross-mode-comparable fandom-component dimensions in §5.
   Not started; this is the harder and more novel half of the work here.
4. Test the premise in §1 directly: does Twitch viewership decouple from
   Steam playerbase for competitive-practice titles (viewership
   sustaining or growing while playerbase flattens), which would be
   evidence of a real watch-only segment, against a stable/correlated
   relationship, which would support the "viewing is emergent from
   playing" reading. Both series already exist in this project's data.
   Still not run — the most concrete, cheapest-to-answer open task here.
5. ~~Reconcile with `esports_vs_game_fandom_signal_model`~~ — **done,
   2026-09-19. See §6.**
6. ~~Decide sequencing~~ — **done, 2026-09-19.** This brief is now
   position 1 in `../brief.md`'s working order.

## 9. Open items

- Whether three modes (§3) is the right cardinality, or an artifact of
  this project's own esports-first title list. `wider_game_fandoms`
  resuming may surface titles that don't fit cleanly (a live-service
  game with light PvP and heavy narrative content, for instance).
- The chess/poker evidence (§3) is a suggestive analogy, not a tested
  claim — this project has no data on either, so it can motivate the
  model but shouldn't be cited as validating evidence.
- Whether "mode" and "niche" end up as two independent axes
  (`{mode × genre × platform × region}`) or mode subsumes/replaces one of
  the existing niche-cell dimensions once §8 task 2 is done.
- This brief was written directly from a research-journal reflection
  (`docs/research_journal.md`, 2026-09-17 entry) and then from
  `posts/post_2_unit_of_analysis/`'s own drafted argument, rather than
  from a notebook finding — unlike the other three foundational pieces,
  the competitive-practice mode's definition (§3) is argued, not yet
  measured. Task 4 above is the actual empirical test that definition is
  still waiting on.
- **`../notebooks/creator_crossover_subset.ipynb` and
  `../notebooks/region_language_confound.ipynb` are now orphaned from the
  post they were built for.** Both are evidence for a related but
  distinct claim (genre bins don't track real creator affinity; region/
  language is a real but non-general confound on that pattern) — real
  data, not a direct test of this brief's own central definition, and
  built for Post 2's "Problem 2" section before that section moved to a
  separate, not-yet-titled follow-up post (2026-09-19, Draft 4). Left
  parked in `../posts/post_2_unit_of_analysis/` pending that post
  getting its own folder — a housekeeping item, not a research one.

## 10. A candidate sequence for §5's component dimensions (2026-09-25) — and why milestone_year isn't a network-maturity measure

Raised directly out of the `post_3_anatomy_of_a_network` milestone_year
robustness work, not designed from scratch here: `get_success_milestone()`
(this project's only "when did a title's scene mature" measure, load-bearing
across `../posts/post_3_anatomy_of_a_network/brief.md`,
`../../esports_lifecycle_and_maturity/brief.md`, and
`docs/milestone_reconciliation.md`) is confirmed, from the actual code, to
be entirely a professionalized-competitive-infrastructure signal: the last
year of the earliest 2-consecutive-year window containing an S/A-tier
(Liquipedia's own top two tiers) tournament each year, spanning 2+
continents cumulatively. Viewership is evaluated (`viewership_check`) but
non-gating and frequently `None`. No signal about grassroots play, casual
playerbase, audience size, social behaviour, event attendance, or
purchasing enters the calculation anywhere.

That's narrower than what this whole project has been using it to mean.
Every notebook built on "milestone_year measures when the community/
network matured" — post_3's era hypothesis chief among them — has
actually been testing "when the *professionalized competitive tier*
reached a specific, fairly high, international bar." A real thing, but
one specific rung of something bigger, not the network's maturity as a
whole.

**The sharper diagnosis: this makes milestone_year a *lagging* indicator
of network maturity, not a leading one.** A professional/elite
competitive tier requires an existing playerbase large enough to produce
elite players and organizations willing to invest in them — it cannot
exist before a real base of play does. Wherever milestone_year has been
read as "the moment this title's community formed" (its use throughout
this project so far), the more accurate reading is "the moment the
community had already matured enough, for long enough, to support
professionalization" — a downstream consequence of network maturity, not
the event itself. This also directly explains why the independent
changepoint-detection check in post_3's brief lands at or after
milestone_year for every title it could test (0 to +3 years, never
negative): Twitch viewership — a much closer proxy for Watch — isn't
tracking milestone_year, it's usually leading it slightly.

**A candidate structure for what actually needs measuring, proposed
directly and not yet tested:**

`Play → Elite Play → Professionalised Play → Watch → Socialise → Attend → Purchase`

— not strictly linear. Watch is plausibly *ahead of* Professionalised
Play, not behind it, for any title released after livestreaming
technology matured: a title can build a large spectator audience around
high-level-but-not-yet-institutionally-professionalized play (arguably
closer to what actually happened for this project's own deepest case
study, VALORANT). Socialise/Attend/Purchase likely have no single fixed
position relative to each other or to Watch — a critical-path model
probably breaks down past Watch, and a second, parallel fork is likely
needed for the *streaming/creator* side of the network (a distinct
population from players, feeding back into Watch) rather than folding
creators into one single-file sequence.

This is the same idea as §5's still-undesigned "cross-mode-comparable
fandom-component dimensions" and §7's prose-form list from Post 2 Draft 4
(playing, watching, Discord/chat, social-media engagement with pros,
event travel, merchandise) — arrived at independently, from interrogating
milestone_year's limits rather than designing §5 from a blank page. Two
independent routes landing on the same rough list is a good sign it's
pointing at something real.

**What this project can and can't currently measure of that sequence:**
- **Play / Elite Play** — not measured directly. No grassroots
  participation or matchmaking-tier data for any title (Steam player
  counts are the closest proxy, and they're aggregate, not skill-tiered).
- **Professionalised Play** — `get_success_milestone()`'s current
  definition. A real measurement, just of one specific rung.
- **Watch** — `viewership_snapshots` (Twitch), the Kaggle historical
  import, YouTube. By far the best-covered component in this project's
  data.
- **Socialise** — no direct source. Reddit was investigated and shelved
  (API access blockers — see `project_creator_crossover_and_reddit_status.md`);
  Discord has never been pursued.
- **Attend** — no source exists or is planned. Neither physical
  event attendance nor live-viewership-of-events-specifically is
  collected anywhere in this project.
- **Purchase** — no source exists. Steam wishlist/purchase data is
  publisher-only (`reference_steam_wishlist_api.md`); no merch/ancillary-
  spend source has been considered.

Three of seven candidate components are entirely dark to this project's
current data, and the strongest-covered one (Watch) is exactly the one
milestone_year's current framing leaves out.

**Build this a priori or induce it from data? Both, but sequenced — and
the first test is already affordable.** This project already has two of
the components measured for every title (Professionalised Play via
milestone_year's tournament data, Watch via Twitch/Kaggle). The cheap,
immediate first test: for each of the 23 titles, does Watch activity
visibly precede, coincide with, or lag Professionalised Play's own
milestone_year, and is the direction consistent across the generational
communities already found via Leiden clustering? Answerable with data
already in hand, no new collection needed — and it should be run before
any larger framework gets built on top of an unchecked intuition.

**Scope of impact, flagged rather than immediately actioned.** This
doesn't invalidate what `get_success_milestone()` actually computes —
that computation is correct for what it measures. It complicates every
place this project has *read* milestone_year as "network/community
formation," which is most of the era-hypothesis work in
`../posts/post_3_anatomy_of_a_network/brief.md` and touches
`../../esports_lifecycle_and_maturity/brief.md` and
`docs/milestone_reconciliation.md`. Not rewriting those now — recorded
here as the reason a future pass through that work needs to distinguish
"when did professionalization happen" from "when did the network
mature," rather than treating them as the same question.

Task list addition (see §8 numbering above; appended here rather than
renumbering the existing list):

7. Test whether Watch (Twitch/Kaggle viewership) leads, lags, or
   coincides with Professionalised Play (milestone_year) per title, using
   data already collected — the cheap, immediate first test of the
   sequence claim above. Not started.
8. Decide whether Socialise/Attend/Purchase are worth pursuing a data
   source for at all, given none currently exists and CLAUDE.md's
   ethical-scraping constraints likely rule out several obvious
   shortcuts (e.g. scraping event ticketing or merch storefronts). Not
   started — may resolve to "structurally out of scope" rather than a
   data task.

## 11. Behaviours and artifacts of competitive-practice networks, drafted (2026-10-03) — and a three-level structure this surfaces

**Superseded in large part by §12 (2026-10-04) — kept as-is rather than
rewritten, since the collapse-test reasoning that got from this table to
§12's leaner one is itself worth keeping on record.** In particular: the
behaviour/institution split wasn't in this version at all (added in
§12), Elite Play/Professionalised Play are no longer separate behaviours
(folded into Play), Organise never made it in here but was considered
and folded into Create/Discuss in §12, and Purchase/Socialise — both
listed as ordinary behaviours below — are demoted to cross-cutting
dimensions in §12. Read this section as the historical first pass, §12
as current.

Raised directly, out of the `post_3_anatomy_of_a_network` milestone_year
discussion (§10): §10's ladder (Play -> Elite Play -> Professionalised
Play -> Watch -> Socialise -> Attend -> Purchase) and §7's prose-form
"soup of behaviours" are formalized here into one fixed table, per
behaviour: a candidate artifact (what it leaves behind, measurably) and
this project's actual current data status against it. **Scoped
explicitly to the competitive-practice mode only** — not a universal
behaviour taxonomy across all three candidate modes (§3). Narrative-
consumption and social-creative-sandbox almost certainly need their own,
differently-shaped lists (neither has an "Elite Play"/"Professionalised
Play" equivalent at all — there is no ranked ladder to ascend in God of
War), not yet drafted.

| # | Behaviour | Status | Candidate artifact(s) | Data status in this project |
|---|---|---|---|---|
| 1 | **Play** | existing (§10) | Steam concurrent-player count | **Have** — live, 11 titles, aggregate/flow not stock (`collectors/steam_poll.py`) |
| | | | Wikipedia article pageviews | **Have, unused this way** — `collectors/wikipedia_pageviews_pull.py` exists |
| 2 | **Elite Play** | existing (§10) | Grassroots (tier-3/4) tournament volume | **Have, unused this way** — sits in `tournaments_lpdb_competitive`, currently only used as Pro Play's exclusion set |
| | | | Ranked/MMR distribution | **Don't have** — no matchmaking-tier data anywhere |
| 3 | **Professionalised Play** | existing (§10) | Tournament records, prize pools, `milestone_year` | **Have** — best-built pipeline in the project |
| | | | Roster/org stability | **Have** — the pro-cohort thread (`research/foundations/notebooks/pro_player_*.ipynb`) |
| 4 | **Watch** | existing (§10) | Twitch/YouTube viewership, Kaggle historical | **Have** — best-covered behaviour overall |
| 5 | **Discuss** | *proposed addition* | Liquipedia edit-history volume | **Have, unused this way** — connector exists, edit activity never pulled as its own signal |
| | | | Reddit, Discord | **Don't have** — Reddit shelved (API blockers), Discord never pursued |
| 6 | **Socialise** | existing (§10) | Reddit, Discord | **Don't have** — same sources as Discuss; the two verbs may be practically inseparable at the artifact level even if kept conceptually distinct |
| 7 | **Attend** | existing (§10) | Event scale (team/participant counts) | **Partial** — tournament metadata gives `team_number`, not attendance |
| | | | Ticket sales, venue capacity | **Don't have** |
| 8 | **Purchase** | existing (§10) | Wishlist/sales data | **Don't have** — publisher-only (confirmed, `reference_steam_wishlist_api.md`) |
| | | | Sponsorship/merch deal announcements | **Don't have** — not collected |
| 9 | **Create** | *proposed addition* | Liquipedia guide/page authorship | **Have, unused this way** — same connector as Discuss's artifact, different edit-type if distinguishable |
| | | | Fan-platform content (art, edits, cosplay) | **Don't have** — likely out of scope |

**Discuss and Create are proposed, not settled** — flagged as open rather
than folded into the existing §10 ladder silently. Discuss is a small
addition (already implicit in §7's "Discord/chat participation," just
not yet its own rung). Create is a larger, structurally different one:
it's a plausible candidate for the "second, parallel fork... for the
streaming/creator side of the network" §10 already said the main
Play-through-Purchase chain would eventually need, rather than another
item on the same single-file sequence — fed by Watch (people who watch
become the ones who create guides/content/edits), not by Play directly.

**What the table surfaces operationally**: three artifacts are "have,
unused this way" — Steam concurrent-players, Liquipedia edit history,
and grassroots tournament volume — meaning Play, Discuss, and Elite Play
all have real, already-collected data sitting idle, not requiring new
collection. Larger immediately-actionable surface than assumed before
this table existed.

**A three-level structure this draft makes explicit, clarifying §5's
open "cross-mode-comparable dimensions" problem rather than just
restating it**: (1) **Mode** (§3) — which kind of relationship a title/
context has; (2) **mode-specific behaviours** — this table, valid only
for competitive-practice; (3) **§5's still-undesigned cross-mode-
comparable dimensions** (ritual/routine frequency, parasocial attachment,
competitive-identity investment, social-coordination intensity,
narrative/lore investment, completionism) — not verbs, but intensity-axes
abstracted enough to be computed from whatever mode-specific behaviours
actually apply, so a competitive-practice fandom and a social-creative-
sandbox fandom can be compared on the same axis despite sharing almost
no behaviour-vocabulary. Level 3 is presumably derived *from* comparing
several modes' own level-2 tables side by side — which means drafting
narrative-consumption's and social-creative-sandbox's own behaviour/
artifact tables (even argued-not-measured, matching competitive-
practice's own current evidentiary status) is likely a real prerequisite
for designing level 3 at all, not a separate, lower-priority task.

Task list addition:

9. Decide Discuss and Create's status (fold into the existing ladder,
   keep as open/provisional, or reject) -- not decided here.
10. Draft narrative-consumption's and social-creative-sandbox's own
    level-2 behaviour/artifact tables, as a likely prerequisite for §5
    task 3 (cross-mode-comparable dimensions) rather than independent of
    it. Not started.

## 12. Consolidated reference (2026-10-04) -- participation behaviours, institutions, and the dimensions that cut across both

**Purpose of this section**: a single, current reference for a live
working session's worth of conceptual development, written explicitly
so the framework survives a context-window reset -- not a notebook
finding, not yet tested against data, argued from first principles the
same way §3's original mode definitions were. Supersedes §11's table in
most particulars; §11 kept for its own reasoning trail, not deleted.

### 12.1 The governing methodological commitment

**Narrative-consumption and social-creative-sandbox (§3) are hypotheses,
not proven categories -- and the count of three modes is itself not
guaranteed.** The right move is not to presuppose modes and look for
confirming behaviour, but to build behaviour/institution measurement
vectors that are genuinely comparable across any network regardless of
type, cluster real networks on those vectors, and test statistically
whether the resulting clusters are real -- the same move already proven
in this project at `creator_crossover_null_model_test.ipynb` (let Leiden
find communities from the crossover graph, then test each against a
configuration-model null; one of four clusters found that way turned
out statistically indistinguishable from random). Modes, if they exist
at all, should be an *output* of clustering on the framework below, not
an input to it.

**The collapse test, used repeatedly below and worth naming as a
reusable tool**: for any candidate behaviour, ask whether it is a
genuinely distinct verb with its own output or goal, or whether it is
better modelled as a *dimension* that modifies one or more other
behaviours. Four candidates failed this test during this session's
discussion (Elite Play, Professionalised Play, Stream, Organise,
Purchase, Socialise -- six, not four) and were folded into either a
surviving behaviour or a cross-cutting dimension rather than kept as
their own line.

### 12.2 Participation behaviours

*A participation behaviour is a voluntary, individually-performed act,
bounded in time, whose performance is what constitutes a person's
membership in the network at that moment -- episodic and renewable, not
a permanent status change.* One real soft spot in this definition,
flagged rather than resolved: "opt-in" undersells how much some
behaviour (Watch especially) is algorithmically induced rather than
purely elective -- activation plausibly sits on a spectrum from
self-initiated to platform-induced.

Five survive the collapse test as their own verbs:

| Behaviour | Definition | Episodic or intensity-measured? |
|---|---|---|
| **Play** | Direct participation in the core practice/substrate -- spans casual through highest-stakes competing; institutional context is tracked as a separate dimension (12.3), not encoded in the verb itself (this is where Elite Play/Professionalised Play went -- see 12.6) | Intensity |
| **Watch** | Spectate, live or recorded | Intensity |
| **Discuss** | Commentary, analysis, meta-discourse -- verbal, bilateral or multilateral, genuinely episodic in a way Socialise turned out not to be (12.4) | Intensity |
| **Attend** | Synchronized physical or virtual co-presence at an event | Episodic |
| **Create** | Produces an output that becomes part of the network and would not otherwise exist -- the admission test that pulled Stream and event-organising in (12.6). Has real internal structure by output-type: **broadcast** (streams/VODs), **reference** (guides, wikis), **creative/fan** (art, fiction, edits, cosplay), **competitive-structure** (tournaments, leagues -- i.e. what "organising" actually is) | Intensity |

### 12.3 Institutions

*An institution is a persistent, supra-individual, nameable structure
that forms when sustained participation behaviour crosses a threshold
sufficient to justify external investment in formalizing it -- outlives
individual participants and individual behavioural instances, has its
own lifecycle (form / grow / stabilize / decline), and feeds back to
reshape the rate and shape of future participation.* That last clause is
not speculative inside this project: VCT's franchising (an
institutional change) measurably changed roster churn afterward, in a
direction opposite to what a purely-passive-residue model would predict
(`pro_player_roster_churn.ipynb`) -- institutions are not just sediment,
they actively reshape the behaviour-space going forward.

**Institution is not a second, parallel list -- it is the reified,
named state a behaviour's own institutionalization reading (12.4)
produces once it crosses a threshold and holds.** `milestone_year`
(`analysis/metrics.py`) is exactly this move already built and running:
the dated moment Play's own institutionalization axis first crossed a
specific line, for a specific title. Paired by originating behaviour,
for concreteness, not as a separate taxonomy to maintain:

| Originates from | Institution category | Examples |
|---|---|---|
| Play | Competitive/league institutions, spanning informal ladders through franchised pro leagues | VCT, publisher matchmaking infrastructure, ESL/PGL as organizers |
| Watch | Broadcast/platform institutions | Official broadcast rights holders, the platform itself (Twitch) |
| Discuss | Discourse institutions | Subreddits (as moderated bodies), Liquipedia, dedicated esports journalism |
| Attend | Event institutions | **Blizzcon** -- notably *not* a Play-institution even though it hosts competitive content, which means institutions can nest/overlap, not sit in one clean bucket |
| Create | Content-economy institutions | Twitch/YouTube Partner programs, organized wiki-editor bodies |

### 12.4 Dimensions that cut across multiple behaviours

Two families, one behaviour-side (supply), one person-side (demand).

**Institutionalization (behaviour-side)**: how organized/formalized the
context of a behaviour-instance is, from none through informal,
semi-organized, to fully institutional. Applies natively to Play. Also
applies to Watch, Discuss, and Attend, but there it reads the
institutionalization of *what is being consumed*, not of the consuming
act itself -- watching an individual creator's Create-output (low) vs.
watching an institutional broadcast (high) is a materially different
experience even when the raw volume is identical, a distinction a
title's "mode" label would otherwise hide (the creator-composite vs.
institutional-broadcast case worked through in this session's Watch
discussion). Does **not** obviously apply to Purchase as its own
independent axis -- see 12.6, likely correlates with the parent
behaviour's own institutionalization closely enough to be redundant,
untested.

**Parasocial attachment and social-embeddedness (person-side)**:
theoretically real, deliberately kept explicit rather than dropped, and
honestly marked as **not currently measurable with this project's
data** -- the point of naming them precisely even though they're out of
reach now is that measurement techniques change; a named-but-unmeasured
axis can be picked up later, a dimension never named cannot.
- **Parasocial attachment**: one-directional attachment, orthogonal to
  (not opposite of) social-embeddedness -- the two cross into four real,
  distinguishable cases (watching a favourite creator *with* your friend
  group, who share the attachment, is high on both at once; a lone
  superfan is high-parasocial/low-social; a watch party for the shared
  occasion more than the specific players is low-parasocial/high-social).
  Attachment object can be an individual *or* an institution (devotion to
  a team brand is still one-directional). Closest available proxy:
  audience concentration (Gini/top-N-channel-share, already computed
  throughout this project) as a rough population-level signal. **A
  stronger, not-yet-checked candidate surfaced this session**: Twitch
  Bits/cheer volume per channel, if accessible in any aggregate form,
  would be a direct monetary parasocial-intensity signal -- a concrete
  data-availability question for later, not resolved here.
- **Social-embeddedness**: degree to which a behaviour-instance is
  co-experienced with a person's own real, reciprocal relationships. No
  proxy identified -- would need a friend-graph over participants, which
  this project has no access to and which would sit squarely behind the
  same confidentiality wall as individual-level Play data generally.

### 12.5 Centrality / Investment -- the row-wise twin of Institution

**A new construct surfaced this session, not a renaming of Socialise.**
Institutionalization aggregates one behaviour *across all people* to
produce a network-level object (an Institution) -- a column operation
over a people-x-behaviours matrix. This is the transpose: aggregating
*all of a person's behaviours* to produce an individual-level object --
a row operation over the same matrix. Inputs include both overall
behavioural intensity across the behaviour-set and social-embeddedness
specifically; social-embeddedness is one input into this construct, not
identical with it, which is why Socialise itself doesn't survive as its
own behaviour (12.6) even though the intuition that produced it was
real.

The reified individual-level state this produces -- tentatively named
**Centrality** (positional: core vs. periphery) or **Investment**
(mechanistic: how much identity/personal value is stored in the
network) -- plausibly also feeds back to reshape future behaviour,
mirroring Institution's own feedback property: a core, identity-invested
member should be more resistant to leaving through a quality dip, more
likely to recruit others, more likely to defend the community. **Stated
here as a hypothesis carried by the structural parallel, not yet shown
by anything in this project's data.** Name not settled; both candidates
kept live.

### 12.6 What collapsed, and why -- the full record

| Candidate | Verdict | Reasoning |
|---|---|---|
| Elite Play, Professionalised Play | Folded into **Play** | Not separate verbs -- one behaviour (Play) read at different points on the institutionalization dimension (12.4). `milestone_year` already measures exactly this threshold-crossing. |
| Stream | Folded into **Create** | Passes Create's own admission test (composes an output into the network that wouldn't otherwise exist) more cleanly than it fits Play. Generalizes: creators and tournament organizers sit on the same spectrum -- both produce a consumable output, differing only in output-type. |
| Organise | Folded into **Create** (event/tournament production, an output-type) and **Discuss** (community moderation, already covered there) | No residual instance survived that wasn't already one of these two. |
| Purchase | Demoted to a cross-cutting **quantified-expression metric**, not a behaviour | Reads off institutionalization (official vs. informal purchase channel) and/or parasocial or social-embeddedness (paying *because of* a one-directional attachment, vs. paying to *signal* community membership to one's own social circle -- the hoodie case). Raw currency value is not a stable cross-context unit (purchasing power varies by region) -- prefer counting discrete purchase-decisions over summing value, or PPP-normalize if magnitude is specifically needed. Total network economic value remains a legitimate, separate, simpler metric on its own, independent of this resolution. |
| Socialise | Demoted -- absorbed into **Centrality/Investment** (12.5) | Doesn't share Discuss's episodic, timebound shape ("private -> socialised" is a state change, not a bounded act). Social-embeddedness survives as a dimension; "Socialise" the verb does not survive as its own behaviour. |

### 12.7 Open, not yet resolved

- Centrality/Investment's name, and whether social-embeddedness and raw
  behavioural intensity are its only two inputs or whether parasocial
  attachment contributes too.
- Whether institutionalization is worth tracking as Purchase's own
  independent axis or is redundant with the parent behaviour's reading
  -- an empirical question, not resolved by reasoning alone.
- Play and Attend have not had the same scrutiny pass Watch, Purchase,
  and Socialise just had.
- Discuss's own boundary was redrawn relative to Socialise in this
  session but not independently re-examined on its own terms.
- The Bits/cheer-volume parasocial proxy's actual data availability --
  unchecked.
- Task list items 9-10 (§8) -- Discuss/Create's exact status, and
  drafting narrative-consumption's and social-creative-sandbox's own
  behaviour tables -- remain open and are arguably more urgent now that
  12.1's clustering plan depends on having more than one mode's table to
  compare.
