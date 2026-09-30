#!/usr/bin/env python3
"""Forecasts upcoming tournament windows from LPDB data (docs/
liquipedia_lpdb_transition_plan.md Phase 1's forward-looking use case).

LPDB's `tournament` resource returns future/projected events alongside
historical ones -- confirmed live during the Phase 0 probe (a real 2028
CS2 Major turned up with status="unconfirmed") and again by
collectors/liquipedia_lpdb.py's own first real run (BLAST SLAM IX,
starting 2026-11-20, already in `tournaments_lpdb` after a 3-request
dota2 pull). That means once collectors/liquipedia_lpdb.py has run for a
title, this script can answer "what's coming up" for it for free -- no
separate forecasting model, just a query over data LPDB already provides.

What this is for: telling a human which upcoming windows are worth
watching closely -- specifically, whether it's worth manually triggering
the Twitch collector's event-mode polling (tighter interval during a
broadcast window; see the "Twitch live-viewership poll" GitHub Actions
workflow) for a specific tournament, or watching the fandom-concentration
questions in research/inter_esports_dynamics/questions/ around a date
where several titles' top-tier events cluster.

What this deliberately is NOT: this script only reads research.db and
prints a report. It does not call gh, does not touch any GitHub Actions
workflow, and does not modify any collector or its schedule. Per CLAUDE.md's
absolute rule, nothing about live Twitch/YouTube/Steam polling may be
risked -- so this stays a read-only advisory tool; deciding to actually
trigger event-mode polling for a window this script surfaces is left as a
separate, explicit, human action every time.

Usage:
    python etl/forecast_event_windows.py                          # next 60 days, tier 1-2, all titles
    python etl/forecast_event_windows.py --days-ahead 120 --tiers 1
    python etl/forecast_event_windows.py --titles dota2,counter_strike
    python etl/forecast_event_windows.py --cluster-gap-days 3      # also report overlapping-window clusters
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from etl.db import get_connection  # noqa: E402


def fetch_upcoming(conn, tiers: list[str], days_ahead: int, title_ids: list[str] | None) -> list[dict]:
    today = datetime.now(timezone.utc).date().isoformat()
    horizon = (datetime.now(timezone.utc).date() + timedelta(days=days_ahead)).isoformat()
    tier_placeholders = ",".join("?" for _ in tiers)
    query = f"""
        SELECT title_id, name, tier, game, status, start_date, end_date,
               country, region, prize_pool, liquipedia_wiki, liquipedia_page
        FROM tournaments_lpdb
        WHERE tier IN ({tier_placeholders})
          AND start_date IS NOT NULL
          AND start_date != '0000-01-01'  -- LPDB's own "never set" sentinel; collectors/liquipedia_lpdb.py normalizes this to NULL on write now, but this guard also covers rows loaded before that fix
          AND start_date >= ?
          AND start_date <= ?
    """
    params: list = list(tiers) + [today, horizon]
    if title_ids:
        placeholders = ",".join("?" for _ in title_ids)
        query += f" AND title_id IN ({placeholders})"
        params += title_ids
    query += " ORDER BY start_date ASC"
    cur = conn.execute(query, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def find_clusters(events: list[dict], gap_days: int) -> list[list[dict]]:
    """Groups events into clusters where each event's start falls within
    `gap_days` of the previous event's start in the sorted list -- i.e.
    windows where multiple titles' top-tier events land close together,
    useful for the inter_esports_dynamics attention-concentration
    questions (does attention concentrate onto one event even when
    several compete for the same window)."""
    clusters: list[list[dict]] = []
    current: list[dict] = []
    prev_date = None
    for ev in events:
        d = datetime.fromisoformat(ev["start_date"]).date()
        if prev_date is not None and (d - prev_date).days <= gap_days:
            current.append(ev)
        else:
            if len(current) > 1:
                clusters.append(current)
            current = [ev]
        prev_date = d
    if len(current) > 1:
        clusters.append(current)
    return clusters


def format_money(v) -> str:
    if v is None:
        return "—"
    return f"${v:,.0f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days-ahead", type=int, default=60, help="how far forward to look (default 60)")
    parser.add_argument("--tiers", default="1,2", help="comma-separated liquipediatier values to include (default '1,2')")
    parser.add_argument("--titles", help="comma-separated title ids to limit to (default: all)")
    parser.add_argument("--cluster-gap-days", type=int, default=0, help="if >0, also report clusters of events starting within this many days of each other")
    args = parser.parse_args()

    tiers = [t.strip() for t in args.tiers.split(",")]
    title_ids = [t.strip() for t in args.titles.split(",")] if args.titles else None

    conn = get_connection()
    events = fetch_upcoming(conn, tiers, args.days_ahead, title_ids)
    conn.close()

    if not events:
        print(
            f"No tier {','.join(tiers)} events found in the next {args.days_ahead} days. "
            "Has collectors/liquipedia_lpdb.py been run for these titles yet?"
        )
        return 0

    print(f"Upcoming tier {','.join(tiers)} tournament windows, next {args.days_ahead} days (as of {datetime.now(timezone.utc).date().isoformat()}):\n")
    for ev in events:
        window = ev["start_date"]
        if ev["end_date"] and ev["end_date"] != ev["start_date"]:
            window += f" → {ev['end_date']}"
        loc = ev["region"] or ev["country"] or "—"
        flag = " [unconfirmed]" if ev.get("status") == "unconfirmed" else ""
        print(f"  {window:24} T{ev['tier']:<2} {ev['title_id']:<16} {ev['name']:<40} {loc:<12} {format_money(ev['prize_pool'])}{flag}")

    if args.cluster_gap_days > 0:
        clusters = find_clusters(events, args.cluster_gap_days)
        if clusters:
            print(f"\nClustered windows (events starting within {args.cluster_gap_days} days of each other):\n")
            for i, cluster in enumerate(clusters, 1):
                titles_in_cluster = sorted({ev["title_id"] for ev in cluster})
                print(f"  Cluster {i}: {cluster[0]['start_date']} – {cluster[-1]['start_date']} ({len(cluster)} events across {len(titles_in_cluster)} titles: {', '.join(titles_in_cluster)})")
                for ev in cluster:
                    print(f"      {ev['start_date']:12} T{ev['tier']:<2} {ev['title_id']:<16} {ev['name']}")
        else:
            print(f"\nNo clusters found within a {args.cluster_gap_days}-day gap.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
