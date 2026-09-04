#!/usr/bin/env python3
"""Populate tournament_aliases (PRD §6/§9.1): rule-based extraction from
each tournament's own name/page path, plus one LLM call per tournament
SERIES (not per event) for colloquial nicknames fans actually type in
stream titles or chat ("Worlds", "MSI", "TI", "Champs") — these feed
etl/classify_broadcast_tier.py's word-boundary alias match (PRD §9.1
condition 3).

Two provenance shapes, per PRD §14 / CLAUDE.md's provenance rule:
  - Rule-based aliases: source='rule_based', confidence='verified' — a
    deterministic transform of already-verified tournament data (same
    reasoning tier/prize_pool already get).
  - LLM-derived aliases: source='ai_assisted', confidence=
    'ai_assisted_unreviewed' — never promoted without explicit human
    review.

**"Series" is a judgment call, not a Liquipedia-native concept.** Defined
here as the first path segment of `liquipedia_page` (e.g. "VCT" from
"VCT/2024/Masters/Madrid", "Six Invitational" from "Six Invitational/
2027/Global Standings"). This groups reasonably well but can over-merge
distinct sub-circuits sharing an organizer prefix (e.g. a hypothetical
"BLAST/Open/..." and "BLAST/Premier/..." would both group under "BLAST")
— a documented limitation, not silently assumed correct. Aliases are
still stored per tournament_id (fanned out to every tournament sharing a
series), since the alias match in classify_broadcast_tier.py needs one.

**Incremental by construction**: a series is skipped if ANY tournament in
it already has a tournament_aliases row (rule-based or LLM). Run after
any Liquipedia crawl, since new tournaments can introduce new series.

**LLM calls are budget-limited by default (`--max-llm-calls`, default
50).** As of this script's first run, there are ~2,400 distinct series in
`tournaments` — an unbounded first run would fire that many paid API
calls at once. The cap makes incremental progress safe; re-run to
continue past it. Requires ANTHROPIC_API_KEY (.env or environment) — if
unset, rule-based aliases still get written and the LLM step is skipped
with a clear warning, not a crash.

Usage:
    python etl/generate_tournament_aliases.py
    python etl/generate_tournament_aliases.py --titles league_of_legends,dota2
    python etl/generate_tournament_aliases.py --max-llm-calls 200
    python etl/generate_tournament_aliases.py --skip-llm
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from etl.db import get_connection, utcnow_iso  # noqa: E402

DOTENV_PATH = REPO_ROOT / ".env"
LLM_MODEL = "claude-haiku-4-5-20251001"


def load_dotenv(path: Path) -> None:
    """Minimal .env loader, same approach as collectors/twitch_poll.py —
    real environment variables always win."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def series_key(liquipedia_page: str) -> str:
    return liquipedia_page.split("/")[0].strip()


def rule_based_aliases(series: str, name: str) -> set[str]:
    aliases = {series}
    readable = name.replace("/", " ").strip()
    if readable and readable != series:
        aliases.add(readable)
    return {a for a in aliases if a}


def call_llm_for_nicknames(client, title_display_name: str, series: str, sample_names: list[str]) -> list[str]:
    """One call, one series. Returns a possibly-empty list of colloquial
    nicknames — empty is the correct answer when nothing well-known
    exists, not a failure; the prompt says so explicitly to discourage
    invented aliases."""
    prompt = (
        f"Game: {title_display_name}\n"
        f"Tournament series (Liquipedia grouping): {series}\n"
        f"Example event names in this series: {', '.join(sample_names[:5])}\n\n"
        "List well-known, commonly-used colloquial nicknames or short names "
        "fans actually type for this tournament series in stream titles, "
        "chat, or casual conversation (e.g. \"Worlds\", \"MSI\", \"TI\", "
        "\"Champs\"). Only include names you are confident are genuinely "
        "in common use — if you don't know of any well-established "
        "nickname, return an empty list rather than guessing or inventing "
        "one. Respond with ONLY a JSON array of strings, nothing else. "
        'Example: ["Worlds", "Worlds Finals"]'
    )
    response = client.messages.create(
        model=LLM_MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        result = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    return [str(a).strip() for a in result if isinstance(a, str) and a.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--titles", help="comma-separated title ids (default: all)")
    parser.add_argument("--max-llm-calls", type=int, default=50, help="cap on LLM calls this run (default: 50)")
    parser.add_argument("--skip-llm", action="store_true", help="rule-based aliases only, no API calls")
    args = parser.parse_args()

    load_dotenv(DOTENV_PATH)

    conn = get_connection()
    started_at = utcnow_iso()

    title_filter = ""
    params: tuple = ()
    if args.titles:
        title_ids = [t.strip() for t in args.titles.split(",")]
        title_filter = f"WHERE title_id IN ({','.join('?' for _ in title_ids)})"
        params = tuple(title_ids)

    rows = conn.execute(
        f"SELECT id, title_id, liquipedia_page, name FROM tournaments {title_filter}", params
    ).fetchall()

    series_to_tournaments: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    title_by_series: dict[str, str] = {}
    for tid, title_id, page, name in rows:
        s = series_key(page)
        series_to_tournaments[s].append((tid, page, name or page))
        title_by_series[s] = title_id

    already_aliased_series = set()
    for s, members in series_to_tournaments.items():
        tournament_ids = [m[0] for m in members]
        placeholders = ",".join("?" for _ in tournament_ids)
        n = conn.execute(
            f"SELECT COUNT(*) FROM tournament_aliases WHERE tournament_id IN ({placeholders})",
            tournament_ids,
        ).fetchone()[0]
        if n > 0:
            already_aliased_series.add(s)

    new_series = sorted(s for s in series_to_tournaments if s not in already_aliased_series)
    print(f"{len(series_to_tournaments)} distinct series found, {len(already_aliased_series)} already aliased, "
          f"{len(new_series)} new")

    display_name_by_title: dict[str, str] = {}
    if new_series:
        title_ids_needed = {title_by_series[s] for s in new_series}
        for row in conn.execute(
            f"SELECT id, canonical_name FROM titles WHERE id IN ({','.join('?' for _ in title_ids_needed)})",
            tuple(title_ids_needed),
        ).fetchall():
            display_name_by_title[row[0]] = row[1]

    client = None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not args.skip_llm and api_key:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            print("[warn] anthropic package not installed — skipping LLM aliases (rule-based only). "
                  "pip install anthropic to enable.", file=sys.stderr)
    elif not args.skip_llm:
        print("[warn] ANTHROPIC_API_KEY not set — skipping LLM aliases (rule-based only).", file=sys.stderr)

    rule_based_rows_written = 0
    llm_rows_written = 0
    llm_calls_made = 0
    llm_errors = 0

    for s in new_series:
        members = series_to_tournaments[s]
        for tid, page, name in members:
            for alias in rule_based_aliases(s, name):
                conn.execute(
                    """
                    INSERT INTO tournament_aliases (tournament_id, alias, source, confidence)
                    VALUES (?, ?, 'rule_based', 'verified')
                    ON CONFLICT (tournament_id, alias) DO NOTHING
                    """,
                    (tid, alias),
                )
                rule_based_rows_written += 1

        if client is not None and llm_calls_made < args.max_llm_calls:
            title_id = title_by_series[s]
            display_name = display_name_by_title.get(title_id, title_id)
            sample_names = [m[2] for m in members]
            try:
                nicknames = call_llm_for_nicknames(client, display_name, s, sample_names)
                llm_calls_made += 1
            except Exception as exc:  # one bad call shouldn't abort the whole run
                print(f"[error] LLM call failed for series {s!r}: {exc}", file=sys.stderr)
                llm_errors += 1
                nicknames = []

            for tid, _page, _name in members:
                for alias in nicknames:
                    conn.execute(
                        """
                        INSERT INTO tournament_aliases (tournament_id, alias, source, confidence)
                        VALUES (?, ?, 'ai_assisted', 'ai_assisted_unreviewed')
                        ON CONFLICT (tournament_id, alias) DO NOTHING
                        """,
                        (tid, alias),
                    )
                    llm_rows_written += 1

        conn.commit()

    finished_at = utcnow_iso()
    llm_skipped = max(0, len(new_series) - llm_calls_made) if client is not None else len(new_series)
    conn.execute(
        """
        INSERT INTO collector_runs (collector, raw_file, started_at, finished_at, status, rows_written, error)
        VALUES ('generate_tournament_aliases', NULL, ?, ?, 'ok', ?, ?)
        """,
        (
            started_at,
            finished_at,
            rule_based_rows_written + llm_rows_written,
            f"{llm_errors} LLM call error(s)" if llm_errors else None,
        ),
    )
    conn.commit()
    conn.close()

    print(f"wrote {rule_based_rows_written} rule-based alias row(s), {llm_rows_written} LLM-derived alias row(s)")
    print(f"{llm_calls_made} LLM call(s) made this run, {llm_errors} error(s)")
    if llm_skipped > 0:
        print(f"[info] {llm_skipped} series still need LLM aliases — re-run to continue "
              f"(--max-llm-calls {args.max_llm_calls} reached, or LLM unavailable this run)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
