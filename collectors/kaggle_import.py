#!/usr/bin/env python3
"""One-time Kaggle historical import (PRD §9.6).

Twitch's own collector (collectors/twitch_poll.py) only sees the world
from 2026-08-31 onward — CLAUDE.md's "one rule," it cannot be backfilled.
For anything before that, the "Evolution of Top Games on Twitch" Kaggle
dataset (monthly top-200 game figures, 2016 onward) is the only source in
this project reaching Twitch *category-wide* viewership that far back.
Liquipedia covers tournaments; Esports Charts (if pursued, PRD §9.3) covers
events; neither is the same thing as raw category attention.

Three constraints from the PRD, load-bearing, not stylistic:

  1. Separate table. Writes to `monthly_category_history`, never
     `viewership_snapshots` — that table is poll-derived (hourly, per
     stream); this is monthly pre-aggregated. Merging them would leave a
     future query silently comparing incompatible granularities.
  2. Unverified provenance. The dataset page doesn't document its own
     collection method, which is exactly the shape of thing PRD §3 warns
     against (scraped-tracker data dressed up as a dataset). Imported at
     confidence='proxy_estimate', source='kaggle_import' — never promoted
     without checking the dataset's discussion tab / contacting the
     uploader first, per PRD §9.6.
  3. Game fandom, not esports fandom. Category-wide figures include ranked
     play, guides, cosmetics content — see PRD §4. analysis/metrics.py
     labels every result sourced from this table accordingly
     (esports_specific=False); never present it as equivalent-strength
     evidence to real broadcast/tournament data.

The CSV itself is NOT checked into this repo — data/kaggle/ is gitignored
(see .gitignore's comment: unlike Twitch's own data, this is a stably
hosted external dataset, re-downloadable anytime, so there's no
CLAUDE.md "one rule" reason to keep a permanent copy in git). To get it:

  1. Search Kaggle for "Evolution of Top Games on Twitch" (free account
     required) and download the CSV.
  2. Save it anywhere under data/kaggle/.
  3. python collectors/kaggle_import.py --input data/kaggle/<file>.csv

One-time, no scheduling. Re-run only if the dataset changes — it's an
UPSERT on (title_id, year_month), so re-running is safe and idempotent.

The four fighting-game titles (tekken, street_fighter, mortal_kombat,
guilty_gear) map ONLY via their exact, unambiguous current-generation
Kaggle names ("TEKKEN 8", "Street Fighter 6", "Mortal Kombat 1", "Guilty
Gear: Strive" — see NAME_TO_TITLE_ID). Bare/older-generation names the
dataset also carries ("Tekken 7", "Street Fighter V", "Mortal Kombat 11",
"Mortal Kombat X", "Guilty Gear Xrd: Revelator", "Guilty Gear Xrd Rev 2",
"Ultra Street Fighter IV", "Street Fighter III: 3rd Strike") stay
unmapped, same reasoning as every other franchise here: this project's
title_ids track one current generation per franchise only
(config/titles.yaml's own judgment-call comments), a raw generation-
ambiguous name predates our tracked title entirely, and guessing which
generation a given month's figures belong to is exactly the kind of
silent misattribution collectors/liquipedia.py's own docstring already
flags as a past mistake for this same wiki/title group. 2026-09-07: found
live in notebooks/esports_share_of_twitch.ipynb that "Street Fighter 6"
was being excluded entirely even though it's unambiguous — fixed, and the
other three checked at the same time.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yaml

from etl.db import get_connection

TITLES_CONFIG = REPO_ROOT / "config" / "titles.yaml"

# Kaggle "Game" column value -> this project's title_id. Exact-match,
# case-sensitive-normalized (compared via .strip().lower()) against
# whatever string the dataset actually uses for a Twitch category name.
# Deliberately conservative: an unmapped game name is just skipped (this
# dataset covers ~200 games per month, the overwhelming majority of which
# this project doesn't track at all — unlike data/manual's hand-built
# export, an unmapped name here is the expected case, not a gap to flag
# loudly). What DOES get reported at the end is the reverse: any tracked
# title with zero matching rows, since that's the signal something in this
# mapping doesn't match the file's actual spelling.
NAME_TO_TITLE_ID = {
    "league of legends": "league_of_legends",
    "dota 2": "dota2",
    "counter-strike: global offensive": "counter_strike",
    "counter-strike": "counter_strike",
    "counter-strike 2": "counter_strike",
    "starcraft ii": "starcraft2",
    "hearthstone": "hearthstone",
    "rocket league": "rocket_league",
    "tom clancy's rainbow six: siege": "rainbow_six_siege",
    "tom clancy's rainbow six siege": "rainbow_six_siege",
    "rainbow six siege": "rainbow_six_siege",
    "overwatch": "overwatch",
    "overwatch 2": "overwatch",
    "valorant": "valorant",
    "apex legends": "apex_legends",
    "fortnite": "fortnite",
    "playerunknown's battlegrounds": "pubg",
    "pubg: battlegrounds": "pubg",
    "pubg mobile": "pubg_mobile",
    "free fire": "free_fire",
    "garena free fire": "free_fire",
    "mobile legends: bang bang": "mobile_legends_bb",
    "mobile legends": "mobile_legends_bb",
    "league of legends: wild rift": "wild_rift",
    "wild rift": "wild_rift",
    "teamfight tactics": "teamfight_tactics",
    "brawl stars": "brawl_stars",
    "age of empires ii": "age_of_empires_ii",
    "age of empires ii: definitive edition": "age_of_empires_ii",
    "tekken 8": "tekken",
    "street fighter 6": "street_fighter",
    "mortal kombat 1": "mortal_kombat",
    "guilty gear: strive": "guilty_gear",
}

# Column-name candidates per field, checked case-insensitively in order.
# The dataset's exact header varies by upload/version; fail loudly (listing
# what IS present) rather than silently reading the wrong column.
COLUMN_CANDIDATES = {
    "game": ["game", "name", "game_name"],
    "year": ["year"],
    "month": ["month"],
    "hours_watched": ["hours_watched", "hours watched"],
    "avg_viewers": ["avg_viewers", "average viewers", "avg viewers"],
    "peak_viewers": ["peak_viewers", "peak viewers"],
}


def resolve_columns(fieldnames: list[str]) -> dict[str, str]:
    lower_to_actual = {f.strip().lower(): f for f in fieldnames}
    resolved = {}
    missing = []
    for field, candidates in COLUMN_CANDIDATES.items():
        match = next((lower_to_actual[c] for c in candidates if c in lower_to_actual), None)
        if match is None:
            missing.append(field)
        else:
            resolved[field] = match
    if missing:
        raise ValueError(
            f"CSV is missing column(s) for {missing}. Available columns: {fieldnames}. "
            f"Add the actual header name(s) to COLUMN_CANDIDATES in this script if the "
            f"dataset uses different naming."
        )
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="path to the downloaded Kaggle CSV")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"[error] {input_path} not found. See this script's docstring for how to get it.", file=sys.stderr)
        return 1

    with open(TITLES_CONFIG) as f:
        tracked_ids = {t["id"] for t in yaml.safe_load(f)["titles"]}
    unknown_mapped_ids = set(NAME_TO_TITLE_ID.values()) - tracked_ids
    if unknown_mapped_ids:
        raise ValueError(
            f"NAME_TO_TITLE_ID maps to title_id(s) not in config/titles.yaml: {unknown_mapped_ids}"
        )

    matched_counts: dict[str, int] = defaultdict(int)
    skipped_unmapped = 0

    # Aggregate in memory, keyed by (title_id, year_month), before writing —
    # NAME_TO_TITLE_ID sometimes maps more than one raw Kaggle "Game" name to
    # the same title_id for the same month: confirmed live (2026-09-05) that
    # a straight per-row upsert silently OVERWRITES in that case rather than
    # combining, which corrupted counter_strike (a "Counter-Strike 2" beta-
    # test category briefly coexisted with "Counter-Strike: Global
    # Offensive"/"Counter-Strike" around the real CS2 launch, Sept 2023) and
    # overwatch (same shape, the Overwatch 2 beta before its Oct 2022
    # launch) with a near-zero value for several months — a fake "dip," not
    # a real one. hours_watched/avg_viewers are additive (both categories'
    # viewers are real, concurrent audience) so they're summed; peak_viewers
    # is NOT summed — two categories' peaks likely didn't occur at the same
    # instant, so the max of the two is the correct "highest concurrent
    # viewership seen" reading, not their sum.
    aggregated: dict[tuple[str, str], dict[str, float | None]] = {}
    collisions: dict[tuple[str, str], int] = defaultdict(int)

    # cp1252, not utf-8: confirmed against the actual downloaded file
    # (2026-09-05) — it has non-ASCII punctuation (e.g. an en-dash) in some
    # game names that isn't valid UTF-8, and decodes cleanly as cp1252.
    with open(input_path, newline="", encoding="cp1252") as f:
        reader = csv.DictReader(f)
        cols = resolve_columns(reader.fieldnames or [])

        for row in reader:
            game_name = (row.get(cols["game"]) or "").strip()
            title_id = NAME_TO_TITLE_ID.get(game_name.lower())
            if title_id is None:
                skipped_unmapped += 1
                continue

            try:
                year = int(row[cols["year"]])
                month = int(row[cols["month"]])
            except (TypeError, ValueError):
                continue
            year_month = f"{year:04d}-{month:02d}"

            def to_float(key: str) -> float | None:
                raw = (row.get(cols[key]) or "").replace(",", "").strip()
                return float(raw) if raw else None

            hours_watched, avg_viewers, peak_viewers = (
                to_float("hours_watched"), to_float("avg_viewers"), to_float("peak_viewers")
            )
            key = (title_id, year_month)
            existing = aggregated.get(key)
            if existing is None:
                aggregated[key] = {
                    "hours_watched": hours_watched, "avg_viewers": avg_viewers, "peak_viewers": peak_viewers,
                }
            else:
                collisions[key] += 1

                def add(a, b):
                    return a + b if a is not None and b is not None else (a if a is not None else b)

                def take_max(a, b):
                    return max(a, b) if a is not None and b is not None else (a if a is not None else b)

                existing["hours_watched"] = add(existing["hours_watched"], hours_watched)
                existing["avg_viewers"] = add(existing["avg_viewers"], avg_viewers)
                existing["peak_viewers"] = take_max(existing["peak_viewers"], peak_viewers)
            matched_counts[title_id] += 1

    conn = get_connection()
    for (title_id, year_month), vals in aggregated.items():
        conn.execute(
            """
            INSERT INTO monthly_category_history
                (title_id, year_month, hours_watched, avg_viewers, peak_viewers,
                 source, confidence)
            VALUES (?, ?, ?, ?, ?, 'kaggle_import', 'proxy_estimate')
            ON CONFLICT (title_id, year_month) DO UPDATE SET
                hours_watched = excluded.hours_watched,
                avg_viewers = excluded.avg_viewers,
                peak_viewers = excluded.peak_viewers
            """,
            (title_id, year_month, vals["hours_watched"], vals["avg_viewers"], vals["peak_viewers"]),
        )
    conn.commit()
    conn.close()

    print(f"wrote {len(aggregated)} monthly_category_history row(s) across {len(matched_counts)} title(s)")
    print(f"skipped {skipped_unmapped} row(s) for games this project doesn't track")
    if collisions:
        print(f"[info] combined {len(collisions)} (title_id, year_month) collision(s) instead of overwriting:")
        for (title_id, year_month), extra_rows in sorted(collisions.items()):
            print(f"  {title_id} {year_month}: {extra_rows + 1} raw rows merged")

    unmatched_tracked = set(NAME_TO_TITLE_ID.values()) & tracked_ids - set(matched_counts)
    if unmatched_tracked:
        print(
            f"[warn] mapped title_id(s) with ZERO matching rows in this file — check "
            f"NAME_TO_TITLE_ID's spelling against the file's actual 'Game' values: "
            f"{sorted(unmatched_tracked)}",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
