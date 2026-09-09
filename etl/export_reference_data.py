#!/usr/bin/env python3
"""Exports `tournaments`, `tournament_aliases`,
`tournament_alias_llm_checked`, `steam_release_history`, and
`monthly_category_history` to committed JSONL files under
`data/reference/`, so `research.db` is rebuildable from committed repo
contents ALONE (`data/raw/` + `data/reference/`), not just `data/raw/`.

**`monthly_category_history`, added 2026-09-09 — closing the exact gap
this file already exists to close, made a THIRD time (steam_release_history
was the second — see below).** Confirmed live: this table had regressed
to 0 rows (from a documented 1,690) after an `etl/load_snapshots.py
--rebuild` ran with this table still uncovered here. Both its sources are
themselves recoverable in principle (`collectors/kaggle_import.py`'s
manually-downloaded CSV, still present locally; `etl/
compute_monthly_category_totals.py`'s derivation from
`language_mix_snapshots`) — but "recoverable if you remember to rerun two
specific scripts" is exactly the kind of silent gap this export mechanism
exists to eliminate, and it had already bitten this project once before
without that being enough to close it. Keyed on `(title_id, year_month)`,
not the raw autoincrement `id` — same natural-key-upsert shape as every
other table here.

**`steam_release_history` (PRD §9.12a Track A), added 2026-09-08 —
closing the exact gap this file already exists to close, before it got
made a second time.** `collectors/steam_catalog_backfill.py` writes
straight into `research.db` with no raw-file backup, same as
`collectors/liquipedia.py`'s tournament writes — without this export, a
`--rebuild` run partway through (or any time after) the 1-2-week
catalog backfill would silently discard however much of it had been
crawled, with no recovery path except re-crawling the whole thing.
Unlike the tournament tables above, this one can genuinely reach
100K+ rows at full-catalog scale — still a full dump every run for the
same simplest-correct reasoning (avoids ever reconciling a partial diff
against what the DB currently holds), but if that ever becomes a real
problem (git diff size, repo bloat), incremental export is the fix, not
assumed unnecessary forever.

`tournament_alias_llm_checked` matters for the same reason as the other
two: `etl/generate_tournament_aliases.py`'s LLM nickname pass costs real
money, and without exporting which series have already been checked, a
`--rebuild` would silently forget that and re-spend the budget re-asking
questions already answered (including the negative answers — "checked,
no nickname exists" — which write zero alias rows and would otherwise
look identical to "never checked").

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

LLM_CHECKED_COLUMNS = ["title_id", "series_key", "checked_at", "nickname_count"]

STEAM_RELEASE_COLUMNS = [
    "app_id", "name", "app_type", "release_date_raw", "release_date", "is_released",
    "genres", "is_indie", "categories", "has_vr_support", "vr_only",
    "developers", "publishers", "recommendations_total", "low_relevance_flag",
    "fetched_at", "source", "confidence",
]

MONTHLY_CATEGORY_COLUMNS = [
    "title_id", "year_month", "hours_watched", "avg_viewers", "peak_viewers",
    "source", "confidence",
]


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

    llm_checked_path = REFERENCE_DIR / "tournament_alias_llm_checked.jsonl"
    with open(llm_checked_path, "w") as f:
        rows = conn.execute(
            f"SELECT {', '.join(LLM_CHECKED_COLUMNS)} FROM tournament_alias_llm_checked ORDER BY title_id, series_key"
        ).fetchall()
        for row in rows:
            f.write(json.dumps(dict(zip(LLM_CHECKED_COLUMNS, row))) + "\n")
    print(f"wrote {len(rows)} LLM-checked series marker(s) to {llm_checked_path}")

    steam_release_path = REFERENCE_DIR / "steam_release_history.jsonl"
    with open(steam_release_path, "w") as f:
        rows = conn.execute(
            f"SELECT {', '.join(STEAM_RELEASE_COLUMNS)} FROM steam_release_history ORDER BY app_id"
        ).fetchall()
        for row in rows:
            f.write(json.dumps(dict(zip(STEAM_RELEASE_COLUMNS, row))) + "\n")
    print(f"wrote {len(rows)} Steam release record(s) to {steam_release_path}")

    monthly_category_path = REFERENCE_DIR / "monthly_category_history.jsonl"
    with open(monthly_category_path, "w") as f:
        rows = conn.execute(
            f"SELECT {', '.join(MONTHLY_CATEGORY_COLUMNS)} FROM monthly_category_history ORDER BY title_id, year_month"
        ).fetchall()
        for row in rows:
            f.write(json.dumps(dict(zip(MONTHLY_CATEGORY_COLUMNS, row))) + "\n")
    print(f"wrote {len(rows)} monthly category history row(s) to {monthly_category_path}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
