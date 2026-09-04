#!/usr/bin/env python3
"""One-time normalization of the original hand-built milestone sheet export
(data/manual/milestone_table_original_export.csv, preserved exactly as
delivered) into the title_id-keyed schema notebooks/reconciliation.ipynb
expects (see data/manual/README.md).

The original export uses free-text game names instead of config/titles.yaml
ids, has spreadsheet header cruft (two leading blank rows), includes titles
this project doesn't track (Crossfire, TrackMania, Halo), and merges Tekken
and Street Fighter into a single "Fighting Games (SF/Tekken)" row even
though Mortal Kombat and Guilty Gear each got their own row despite sharing
the same Liquipedia wiki.

Resolved 2026-09-05, per explicit direction to treat Tekken and Street
Fighter as the distinct esports they are rather than assume one row's
figures describe both. The row's own text supports the split cleanly: its
structural-founding citation names both circuits ("CPT (SF) & TWT
(Tekken)"), but its only concrete viewership corroboration ("TWT Peak
Viewership grew from 49.7K (2017) to 178.8K (2018)") is Tekken-specific —
TWT is the Tekken World Tour, not a Street Fighter circuit. So the row is
mapped to tekken alone below; street_fighter is deliberately left absent
from milestone_table.csv (not given a blank/guessed row) rather than
borrow Tekken's evidence for a title it wasn't measuring. That's a real
"hand-built table has no opinion on street_fighter" — not a "reached
never" judgment — see data/manual/README.md.

Run again only if milestone_table_original_export.csv changes.
"""

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_PATH = REPO_ROOT / "data" / "manual" / "milestone_table_original_export.csv"
OUT_PATH = REPO_ROOT / "data" / "manual" / "milestone_table.csv"

# Every mapping here is a manual, human-confirmable judgment call, not an
# inference — most are exact-name matches; the two non-obvious ones
# ("Counter-Strike" -> counter_strike, "Age of Empires" -> age_of_empires_ii)
# reuse judgment calls already made and documented in config/titles.yaml
# itself, for the same reason (current-gen entry per franchise).
NAME_TO_TITLE_ID = {
    "StarCraft II": "starcraft2",
    "League of Legends": "league_of_legends",
    "Dota 2": "dota2",
    "Counter-Strike": "counter_strike",
    "Hearthstone": "hearthstone",
    "Rocket League": "rocket_league",
    "Overwatch": "overwatch",
    "Rainbow Six Siege": "rainbow_six_siege",
    "Mortal Kombat": "mortal_kombat",
    "Fortnite": "fortnite",
    "Free Fire": "free_fire",
    "Brawl Stars": "brawl_stars",
    "Teamfight Tactics": "teamfight_tactics",
    "Age of Empires": "age_of_empires_ii",
    "Wild Rift": "wild_rift",
    "PUBG PC": "pubg",
    "Apex Legends": "apex_legends",
    "Guilty Gear": "guilty_gear",
    "PUBG Mobile (PUBGM)": "pubg_mobile",
    "VALORANT": "valorant",
    "Mobile Legends: BB (MLBB)": "mobile_legends_bb",
    # See module docstring: the row's only concrete viewership evidence
    # (TWT = Tekken World Tour) is Tekken-specific, so it's assigned to
    # tekken alone rather than treated as covering Street Fighter too.
    "Fighting Games (SF/Tekken)": "tekken",
}

# Not in config/titles.yaml at all — this project doesn't track them, so
# there's nothing for the pipeline side to reconcile against.
NOT_TRACKED = {"Crossfire", "TrackMania", "Halo"}

# Nothing left ambiguous as of 2026-09-05 (see module docstring) — kept as
# an empty set, not removed, so the "unhandled name" check below still has
# somewhere to route a genuinely new ambiguous case if one shows up later.
AMBIGUOUS: set[str] = set()


def main() -> None:
    raw = pd.read_csv(RAW_PATH, header=2)

    unhandled = set(raw["Game Title"]) - set(NAME_TO_TITLE_ID) - NOT_TRACKED - AMBIGUOUS
    if unhandled:
        raise ValueError(
            f"Original export has game name(s) this script doesn't know how to "
            f"handle: {unhandled}. Add them to NAME_TO_TITLE_ID, NOT_TRACKED, or "
            f"AMBIGUOUS above before re-running."
        )

    mapped = raw[raw["Game Title"].isin(NAME_TO_TITLE_ID)].copy()
    mapped["title_id"] = mapped["Game Title"].map(NAME_TO_TITLE_ID)
    mapped["milestone_year"] = mapped["Success Milestone Reached"]
    mapped["notes"] = mapped["Jake's Additional Validation"]

    out = mapped[["title_id", "milestone_year", "notes"]].sort_values("title_id")
    out.to_csv(OUT_PATH, index=False)

    skipped_untracked = sorted(set(raw["Game Title"]) & NOT_TRACKED)
    skipped_ambiguous = sorted(set(raw["Game Title"]) & AMBIGUOUS)
    print(f"wrote {len(out)} rows to {OUT_PATH}")
    print(f"skipped (not tracked in config/titles.yaml): {skipped_untracked}")
    print(f"skipped (ambiguous, needs manual split): {skipped_ambiguous}")


if __name__ == "__main__":
    main()
