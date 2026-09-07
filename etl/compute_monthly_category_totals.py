#!/usr/bin/env python3
"""Computes this project's OWN monthly category-wide hours_watched per
tracked title, from live-collected data, and writes it into
`monthly_category_history` alongside the Kaggle import
(collectors/kaggle_import.py) — same table, `source='own_collector'`
instead of `source='kaggle_import'`, so a single query against that table
can span both eras.

**Why `language_mix_snapshots`, not `viewership_snapshots`.**
`viewership_snapshots` only holds full-detail (tier-1/2) individual
streams — collectors/twitch_poll.py's capture policy folds anything below
`full_detail_min_viewers` into a per-poll aggregate instead of a per-stream
row. `language_mix_snapshots` is where that folded-in aggregate actually
lands (etl/load_snapshots.py's `load_one_file`): it already combines every
full-detail stream's own language AND the below-threshold aggregate's
`viewer_total_by_language`. Summed across all languages for a given
`(title_id, captured_at)`, it IS the true total concurrent viewers for
that title at that poll — the same category-wide quantity Kaggle's
`hours_watched` measures, not the narrower esports-specific slice
`viewership_snapshots` alone would give.

**Sparse/irregular polling means a real time-weighted integration, not a
flat "assume ~1 hour per poll."** Confirmed directly against this
project's actual poll history: 40 polls, gaps ranging from ~5 minutes to
~7.65 hours, median ~4.27 hours — nowhere near a clean hourly cadence (the
scheduled workflow is hourly in principle, but this data also includes
tighter event-mode bursts and real gaps). Each poll's contribution to a
month's hours_watched is `concurrent_viewers * hours_until_that_title's_next_poll`
— an actual timestamp delta, not an assumed constant. The very last poll in
the whole dataset gets NO forward-looking weight for any title: we cannot
extrapolate viewership into time we have not observed yet. This makes the
most recent partial period's total a deliberate, honest undercount, not a
bug — a title's true "hours so far this month" is somewhat higher than
what's reported here for the month containing the last poll.

**Known gaps, matching this table's existing Kaggle-side caveats:**
  - `monthly_category_history.UNIQUE (title_id, year_month)` does not
    distinguish `source` — a `kaggle_import` row and an `own_collector` row
    for the SAME (title_id, year_month) would silently overwrite each
    other under the existing upsert pattern. No current collision risk:
    Kaggle's dataset ends 2024-09, this collector's data starts 2026-08-31,
    a ~23-month gap. Worth knowing if either script is ever extended to
    close that gap.
  - This table is NOT covered by `etl/export_reference_data.py`'s
    `data/reference/` safety net (same gap CLAUDE.md documents for the
    Kaggle-sourced rows). A future `python etl/load_snapshots.py --rebuild`
    will silently drop these `own_collector` rows too — re-run this script
    afterward, not just `collectors/kaggle_import.py`.

Idempotent: recomputes and upserts per (title_id, year_month) from
whatever `language_mix_snapshots` currently holds, so it's safe — and
necessary — to re-run as more polls accumulate.

Usage:
    python etl/compute_monthly_category_totals.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from etl.db import get_connection  # noqa: E402


def main() -> int:
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT title_id, captured_at, SUM(viewer_count)
        FROM language_mix_snapshots
        GROUP BY title_id, captured_at
        ORDER BY title_id, captured_at
        """
    ).fetchall()

    by_title: dict[str, list[tuple[datetime, int]]] = defaultdict(list)
    for title_id, captured_at, total_viewers in rows:
        ts = datetime.strptime(captured_at, "%Y-%m-%dT%H:%M:%SZ")
        by_title[title_id].append((ts, total_viewers))

    # (title_id, year_month) -> accumulators
    monthly_hours: dict[tuple[str, str], float] = defaultdict(float)
    monthly_viewer_samples: dict[tuple[str, str], list[int]] = defaultdict(list)

    poll_count = 0
    gap_hours: list[float] = []

    for title_id, polls in by_title.items():
        for i, (ts, viewers) in enumerate(polls):
            poll_count += 1
            year_month = ts.strftime("%Y-%m")
            monthly_viewer_samples[(title_id, year_month)].append(viewers)

            if i + 1 < len(polls):
                next_ts, _ = polls[i + 1]
                hours_to_next = (next_ts - ts).total_seconds() / 3600
                gap_hours.append(hours_to_next)
                # Attribute the whole poll's weighted hours to THIS poll's own
                # month — a poll near a month boundary whose next poll falls
                # in the following month slightly overstates the earlier
                # month and understates the later one. A documented
                # simplification: splitting a single poll's weight across a
                # month boundary would need sub-poll date arithmetic for a
                # marginal accuracy gain, not worth it at this data volume.
                monthly_hours[(title_id, year_month)] += viewers * hours_to_next
            # else: last poll for this title overall — no forward weight (see docstring).

    for (title_id, year_month), samples in monthly_viewer_samples.items():
        hours_watched = monthly_hours.get((title_id, year_month), 0.0)
        avg_viewers = sum(samples) / len(samples)
        peak_viewers = max(samples)
        conn.execute(
            """
            INSERT INTO monthly_category_history
                (title_id, year_month, hours_watched, avg_viewers, peak_viewers,
                 source, confidence)
            VALUES (?, ?, ?, ?, ?, 'own_collector', 'verified')
            ON CONFLICT (title_id, year_month) DO UPDATE SET
                hours_watched = excluded.hours_watched,
                avg_viewers = excluded.avg_viewers,
                peak_viewers = excluded.peak_viewers,
                source = excluded.source,
                confidence = excluded.confidence
            """,
            (title_id, year_month, hours_watched, avg_viewers, peak_viewers),
        )

    conn.commit()

    n_rows = len(monthly_viewer_samples)
    print(f"wrote {n_rows} monthly_category_history row(s) (source=own_collector) "
          f"across {len(by_title)} title(s)")
    print(f"{poll_count} total poll-rows processed, "
          f"gap range {min(gap_hours):.2f}-{max(gap_hours):.2f}h, "
          f"median {sorted(gap_hours)[len(gap_hours)//2]:.2f}h" if gap_hours else "no inter-poll gaps (single poll)")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
