# Liquipedia LPDB Transition Plan

**Status: not yet active.** Liquipedia's project lead has committed to granting
LPDB access for the 20 wikis backing this project's 23 tracked titles (see
`config/titles.yaml`'s `liquipedia_wiki` field for the full list). This plan
is written ahead of that access actually landing, so the transition can start
immediately once it does, rather than being designed from scratch at that
point. Drafted 2026-09-16; activate (start Phase 0) once LPDB credentials are
in hand.

Liquipedia has also directly advised against continuing to rely on the
standard MediaWiki API long-term — quoted risk: "timeouts and bans" — which
is the practical urgency behind this plan, on top of the data-quality
benefits below.

## Attribution and retention — confirmed vs. still open

Liquipedia's project lead has stated that final attribution via the blogs
(this project's Boudica-style reports/presentations, which already credit
Liquipedia in their Sources sections) is sufficient. That most likely covers
report/presentation citation, which is already standard practice here.

**Not yet explicitly confirmed, worth a direct follow-up before this becomes
load-bearing:**
- Whether the same attribution standard covers **committing derived
  tournament data to this project's public GitHub repo**
  (`data/reference/tournaments.jsonl` and friends) — a materially different
  thing from a blog citation, since it's redistributing structured, extracted
  data indefinitely in machine-readable form, not crediting a source in prose.
- Whether there's any **retention limit** on LPDB-sourced data specifically —
  CLAUDE.md already flags "retention clauses" as a thing to respect,
  separately from attribution, and this hasn't been asked about directly.

Resolve both before Phase 3 (cutover) commits LPDB-derived data to the
public reference-data export.

## Phase 0 — Confirm terms before writing any code

- [ ] LPDB's actual access mechanics: endpoint, auth (API key? account-tied?),
      query language, rate limits/quotas. Same "confirmed, not assumed"
      discipline already applied to Twitch/YouTube/Steam in this project.
- [ ] The attribution/retention questions above.
- [ ] Whether LPDB exposes **grassroots tiers** (B/C-Tier, Tier 3/4) on the
      same wikis, or only tier-1/2. `collectors/liquipedia_grassroots.py`
      currently covers only `counter_strike`/`dota2` via direct MediaWiki
      access — if LPDB doesn't reach those tiers, that script keeps needing
      direct wiki access, which is exactly the ban risk just flagged. Don't
      assume this risk is fully retired without checking.
- [ ] Whether `{{TeamPrizePool}}`-style per-team payouts actually surface as
      usable structured fields in LPDB, not assumed better just because it's
      a cleaner source in general.

## Phase 1 — Build the LPDB connector alongside the current one

- [ ] New module (e.g. `collectors/liquipedia_lpdb.py`), same CLI shape as
      `collectors/liquipedia.py`, scoped by `config/titles.yaml`'s
      `liquipedia_wiki` field — already matches the exact 20-wiki grant.
- [ ] **Carry forward the generational-continuity policy explicitly.**
      `tekken`/`street_fighter`/`mortal_kombat`/`guilty_gear` share
      Liquipedia's `fighters` wiki; policy (set 2026-09-09) treats each as
      one continuous franchise across engine generations, implemented today
      as `liquipedia_category` accepting a **list** of per-generation
      categories, unioned before filtering. `Street Fighter X Tekken
      Competitions` is deliberately **excluded** as a genuine crossover
      product, not a version — a judgment call, not a parsing artifact.
      LPDB's query model is almost certainly shaped differently (wiki +
      structured filters, not MediaWiki categories) — re-express this exact
      filter logic in LPDB's native equivalent, and re-verify the crossover
      exclusion still holds rather than being silently reintroduced by a
      differently-shaped filter.
- [ ] New rows get a distinct `source` value (e.g. `liquipedia_lpdb`) —
      never silently overwrite existing `source='liquipedia'` rows. This is
      what makes Phase 2 possible.
- [ ] Land in a staging area (parallel table, or a clearly source-flagged
      subset of `tournaments`) — not a blind merge into the live table.

## Phase 2 — Reconciliation, before anything is trusted

Same shape as the Phase 2 reconciliation already run once on the original
build (which found 3 real bugs) — applied here to a source swap instead of
a first build.

- [ ] **Tier values**: does LPDB's tier field need `_normalize_tier()`'s
      existing per-wiki label-vs-digit handling, or does it already come
      normalized?
- [ ] **Prize pool**: check specifically whether the `{{TeamPrizePool}}` gap
      actually closes (BLAST SLAM and Dota 2's 31%-vs-CS's-85% coverage gap),
      and whether CS's own smaller, never-fully-checked exposure to the same
      bug shows up now.
- [ ] **Currency**: does LPDB give clean, consistently-populated currency
      alongside every prize figure? If so, this is the first real chance to
      fix the already-flagged 1,541-row gap elsewhere in `tournaments`
      (`currency IS NULL` with a populated `prize_pool`), rather than just
      filtering around it the way `get_championship_windows()` does today.
- [ ] **Dates**: does the `start_date`/`end_date` NULL/placeholder problem
      (13 titles affected today) improve?
- [ ] **Shared-wiki contamination**: re-run the same clean-wiki check already
      done once for all 23 titles — confirm LPDB's query model doesn't
      reintroduce cross-game bleed on `fighters` or any other shared wiki.
- [ ] **Generational continuity re-verified end to end**: confirm the four
      fighting-game titles still span their full multi-generation history
      under LPDB (currently 2006–2026 for three of them, 2011–2025 for
      Mortal Kombat) and that the crossover exclusion held.
- [ ] Written up as its own dated doc, same pattern as
      `docs/milestone_reconciliation.md` — not folded silently into the
      swap.

## Phase 3 — Cutover

- [ ] Once reconciliation is clean (or every discrepancy is understood and
      either fixed or accepted), swap `etl/load_snapshots.py`'s
      Liquipedia-loading step to LPDB as the source of truth — the
      "straightforward swap" the PRD already anticipated when LPDB was
      first deferred (§9.2).
- [ ] Decide `collectors/liquipedia.py`'s fate explicitly: keep the code as
      a documented fallback (e.g. for a future title added to
      `config/titles.yaml` before any expanded grant covers its wiki), but
      stop actively running it against live Liquipedia once LPDB is
      confirmed working. Given Liquipedia's own advice against continued
      MediaWiki use, this should be a stated decision, not something that
      just quietly stops.
- [ ] Re-run `generate_tournament_aliases.py` → `export_reference_data.py`
      → `classify_broadcast_tier.py` in the standard order against the new
      data.
- [ ] Update `docs/system_reference.md`, PRD §9.2, and CLAUDE.md once this
      is real, not preemptively.

## Phase 4 — Capture the benefits

- [ ] **Player/roster connector (PRD §9.15)** — previously blocked
      specifically on `Infobox player`'s nested transfer-history wikitext
      and `Infobox team` not enumerating membership. Re-scope once it's
      known what LPDB actually exposes here; this could go from "scoped,
      not built" to genuinely tractable.
- [ ] **Per-tournament participant lists** — the qualifier-normalized
      entry-rate question (`research/esports_lifecycle_and_maturity/brief.md` §10)
      was flagged as needing this and "not yet scoped at all." Same story.
- [ ] **`series_key`/`tournament_aliases`** — check whether LPDB has a
      native tournament-series identifier more reliable than the current
      rule-based name-minus-year/acronym approach; could simplify or retire
      half of `generate_tournament_aliases.py` (the LLM nickname pass stays
      useful regardless).
- [ ] **Full grassroots crawl for all 23 titles** — currently a ~8-10 hour
      rate-limited MediaWiki job, only ever run for CS/Dota2. If LPDB
      reaches B/C-Tier cleanly, this becomes realistic project-wide — a
      real capacity unlock, not just a risk-reduction one.

## What this plan deliberately does not cover

- Live viewership data (Twitch/YouTube/Steam) — entirely unrelated to
  Liquipedia/LPDB, unaffected by any of the above.
- Esports Charts / peak-viewership data — LPDB is tournament/match/prize-pool
  data only; the championship-concentration work (inter_esports_dynamics/questions/platform_attention_concentration's
  demand-side sub-test) stays blocked on Esports Charts regardless of LPDB
  access. Don't read LPDB landing as unblocking that too.
