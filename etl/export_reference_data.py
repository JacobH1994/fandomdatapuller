#!/usr/bin/env python3
"""Exports `tournaments` and `tournament_aliases` to committed JSONL files
under `data/reference/`, so `research.db` is rebuildable from committed
repo contents ALONE (`data/raw/` + `data/reference/`), not just
`data/raw/`.

This closes a real gap: PRD §9.6b's weekly Action (scheduled
`niche_similarity_history`/`creator_crossover_history` computation) runs
on an ephemeral GitHub Actions runner with no access to a local
`research.db` (gitignored, laptop-only) and no Liquipedia crawl budget of
its own — it can only rebuild from what's checked into git.
`etl/load_snapshots.py --rebuild` already replays `data/raw/twitch/`, but
`collectors/liquipedia.py` writes tournament data directly into
`research.db` with no raw-file backup (CLAUDE.md's own documented
caveat) — without this export, a rebuilt database would have zero
tournament data, and every computation downstream of it (milestones,
co-stream detection, the region profile in niche_membership.ipynb) would
silently run against an empty table instead of failing loudly.

**Run this after any Liquipedia crawl or tournament_aliases
generation** — same trigger point as `etl/generate_tournament_aliases.py`.
A full dump each run, not incremental: the data is small enough (a few MB
even at current scale) that a full rewrite is simplest-correct, and
avoids ever reconciling a partial diff against what the DB currently
holds.

**tournament_aliases is keyed on (title_id, series_key), not a raw
numeric tournament_id** (etl/generate_tournament_aliases.py) — series_key
is itself a stable string derived from liquipedia_page, so unlike the
tournament_id-keyed scheme this replaced, no autoincrement-id resolution
at load time is needed; the export/import round-trip is a direct
natural-key upsert.

Usage:
    python etl/export_reference_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from etl.db import get_connection  # noqa: E402

REFERENCE_DIR = REPO_ROOT / "data" / "reference"

TOURNAMENT_COLUMNS = [
    "title_id", "liquipedia_wiki", "liquipedia_page", "name", "tier", "prize_pool",
    "currency", "start_date", "end_date", "country", "region", "region_confidence",
    "team_number", "series_key", "fetched_at", "source", "confidence",
]

ALIAS_COLUMNS = ["title_id", "series_key", "alias", "case_sensitive", "source", "confidence"]


def main() -> int:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()

    tournaments_path = REFERENCE_DIR / "tournaments.jsonl"
    with open(tournaments_path, "w") as f:
        rows = conn.execute(
            f"SELECT {', '.join(TOURNAMENT_COLUMNS)} FROM tournaments ORDER BY liquipedia_wiki, liquipedia_page"
        ).fetchall()
        for row in rows:
            f.write(json.dumps(dict(zip(TOURNAMENT_COLUMNS, row))) + "\n")
    print(f"wrote {len(rows)} tournament(s) to {tournaments_path}")

    aliases_path = REFERENCE_DIR / "tournament_aliases.jsonl"
    with open(aliases_path, "w") as f:
        rows = conn.execute(
            f"SELECT {', '.join(ALIAS_COLUMNS)} FROM tournament_aliases ORDER BY title_id, series_key, alias"
        ).fetchall()
        for row in rows:
            f.write(json.dumps(dict(zip(ALIAS_COLUMNS, row))) + "\n")
    print(f"wrote {len(rows)} tournament alias(es) to {aliases_path}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
