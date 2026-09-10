#!/usr/bin/env bash
# Local refresh routine (PRD §9.6a/§9.6b reference this concept; this is
# its actual implementation — it didn't exist as a runnable script before).
#
# Fixed order, explicit rather than left to be run correctly by memory:
#   1. Liquipedia crawl (on-demand, network, rate-limited — optional, see
#      --with-crawl) -> new/updated tournaments.
#   2. etl/load_snapshots.py -> loads Twitch raw snapshots AND
#      data/reference/*.jsonl (tournaments/tournament_aliases) into
#      research.db. Always safe to run, natural-key upserts throughout.
#   3. notebooks/official_channel_candidates.ipynb -> regenerates
#      config/channels.draft.yaml. Re-executed automatically (touches only
#      the draft, never the real config), but config/channels.yaml itself
#      is NOT auto-updated from it — that step needs a human to review and
#      delete wrong entries, by design (see that notebook's own docstring).
#   4. etl/generate_tournament_aliases.py -> populates tournament_aliases.
#      Rule-based only by default here (--skip-llm) — LLM-derived aliases
#      are a separate, deliberate, budget-limited step you run yourself
#      (see --with-llm-aliases), not something this routine fires
#      automatically on every refresh.
#   5. etl/export_reference_data.py -> writes data/reference/*.jsonl so
#      these become part of the next commit (research.db itself stays
#      gitignored/disposable).
#   6. etl/classify_broadcast_tier.py -> sets broadcast_tier on any newly
#      unclassified viewership_snapshots rows, using whatever
#      config/channels.yaml and tournament_aliases exist right now. If
#      you've just curated a new config/channels.yaml or added LLM
#      aliases, re-run with --full-reclassify separately afterward — this
#      routine's default is incremental only.
#   7. etl/classify_gta_content_segment.py -> sets content_segment
#      (nopixel/gta_rp_other/non_rp) on any newly unclassified GTA V rows
#      in platform_viewership_snapshots (PRD §9.16-adjacent, the nested
#      GTA RP taxonomy — user request, 2026-09-10). Same incremental-by-
#      default convention as step 6; re-run with --full-reclassify if the
#      classification ruleset itself changes.
#
# Usage:
#   scripts/local_refresh.sh                  # steps 2-7, no Liquipedia crawl
#   scripts/local_refresh.sh --with-crawl      # also runs the Liquipedia crawl first
#   scripts/local_refresh.sh --with-llm-aliases  # step 4 uses the LLM (costs money, needs ANTHROPIC_API_KEY)

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

WITH_CRAWL=false
WITH_LLM_ALIASES=false
for arg in "$@"; do
    case "$arg" in
        --with-crawl) WITH_CRAWL=true ;;
        --with-llm-aliases) WITH_LLM_ALIASES=true ;;
        *) echo "unknown argument: $arg" >&2; exit 1 ;;
    esac
done

if [ "$WITH_CRAWL" = true ]; then
    echo "=== 1/6: Liquipedia crawl ==="
    python3 collectors/liquipedia.py
else
    echo "=== 1/6: Liquipedia crawl skipped (pass --with-crawl to run it) ==="
fi

echo "=== 2/6: load_snapshots (Twitch raw + data/reference/) ==="
python3 etl/load_snapshots.py

echo "=== 3/6: official_channel_candidates.ipynb (draft only, not applied) ==="
jupyter nbconvert --to notebook --execute --inplace notebooks/official_channel_candidates.ipynb
echo "    -> review config/channels.draft.yaml and curate config/channels.yaml by hand if it changed."

echo "=== 4/6: generate_tournament_aliases ==="
if [ "$WITH_LLM_ALIASES" = true ]; then
    python3 etl/generate_tournament_aliases.py
else
    python3 etl/generate_tournament_aliases.py --skip-llm
fi

echo "=== 5/6: export_reference_data (data/reference/*.jsonl, for commit) ==="
python3 etl/export_reference_data.py

echo "=== 6/7: classify_broadcast_tier (incremental) ==="
python3 etl/classify_broadcast_tier.py

echo "=== 7/7: classify_gta_content_segment (incremental) ==="
python3 etl/classify_gta_content_segment.py

echo "=== done ==="
