#!/usr/bin/env python3
"""Populate tournament_aliases (PRD §6/§9.1): rule-based extraction from
each tournament SERIES's own name, plus one LLM call per series for
colloquial nicknames fans actually type in stream titles or chat
("Worlds", "MSI", "TI", "Champs") — these feed
etl/classify_broadcast_tier.py's word-boundary alias match (PRD §9.1
condition 3).

**Scope: tier-1/tier-2 tournaments only** (analysis.metrics._normalize_tier,
so letter-tier wikis like counter_strike/valorant are handled correctly).
Lower-tier events don't get co-streamed, and restricting to tier-1/2 is
what keeps the series count in the low thousands instead of tens of
thousands — most of `tournaments` is tier-3 qualifiers that will never be
a co-stream match target.

**Series-key derivation** (rule-based, no LLM — the naming is regular
enough): take `liquipedia_page`'s first path segment, strip any embedded
4-digit year. If that first segment alone is a bare organizer acronym
(2-5 uppercase/digit characters, e.g. "ESL", "PGL", "MPL") AND the second
segment (year-stripped) is non-empty and not purely numeric, fold the
second segment in too — otherwise distinct branded sub-events sharing an
organizer prefix collapse into one meaningless series (real cases found
calibrating this against live data: "PGL/Arlington Major" and
"PGL/Bucharest Major" are different, well-known named events, not
editions of a generic "PGL"; same for "ESL/Pro League" vs
"ESL/Challenger", "MPL/Philippines" vs "MPL/Indonesia"). When the second
segment is just a year (already stripped to empty) or a bare number —
e.g. CS:GO's "PGL/2024/Copenhagen" — folding in would just re-fragment by
host city, so it falls back to the bare acronym alone; validated this is
the right call by checking that specific case against real data (all
CS:GO PGL Major host-cities correctly stay one "PGL" series, since fans
do just say "PGL Major" generically there).

**Deliberately does NOT strip season/week/stage/day/chapter markers
mid-key beyond the first 1-2 segments** — an earlier, more aggressive
draft that stripped every such marker throughout the whole page path
produced 9,689 series (vs 2,576 with this simpler first-segment rule),
because it kept splitting on genuinely meaningful sub-structure (regions,
brackets) that this coarser rule intentionally leaves merged. Confirmed
with the user which tradeoff to take: fans type brand names, not full
bracket paths, and the temporal condition (start_date/end_date) already
disambiguates which edition/region a given stream refers to for
matching purposes even when several distinct real-world regional splits
share one series_key.

**Incremental on two independent tracks, not one**: a series needs
rule-based generation if it has no `source='rule_based'` row yet, and
independently needs an LLM check if it has no
`tournament_alias_llm_checked` row yet — checking "any alias exists at
all" would be wrong, because a `--skip-llm` run (or one that ran out of
`--max-llm-calls`) leaves rule-based rows behind with no LLM attempt yet,
and a genuinely-empty LLM result (no well-known nickname exists) writes
zero alias rows, which would otherwise look identical to "never tried"
and get retried — and re-billed — every run.

Per series:
  - Three rule-based aliases: the "full name" (one representative/
    shallowest member's full liquipedia_page, spaces for slashes, WITH
    its year — e.g. "The International 2011"), "name minus year" (the
    series_key itself, spaces for slashes — e.g. "The International"),
    and an acronym from the initials of "name minus year"'s words (only
    if that name has >= 2 words, e.g. "TI", "VCT"). Deduped per series
    (a one-word series_key like "DreamLeague" naturally has no distinct
    acronym).
  - One LLM call for colloquial nicknames. The prompt also lists the
    series' distinct SUB-EVENT names (the segment right after whatever
    series_key consumed — e.g. "Champions"/"Masters" for VCT, "Bucharest
    Major"/"Arlington Major" for a fine-grained PGL series) so the LLM
    can also suggest nicknames like "VALORANT Champions" that a
    first-segment-only series_key would otherwise never recover — capped
    at 8, prioritized by tier then prize_pool, since some series have far
    too many sub-events to list sensibly.

**Aliases shorter than 4 characters are stored with case_sensitive=1**
("TI", "MSI", "EU" would otherwise false-positive against unrelated text
even under word-boundary matching) — etl/classify_broadcast_tier.py's
compile_alias_pattern() honors this flag.

Two provenance shapes, per PRD §14 / CLAUDE.md's provenance rule:
  - Rule-based aliases: source='rule_based', confidence='verified'.
  - LLM-derived aliases: source='ai_assisted', confidence=
    'ai_assisted_unreviewed' — never promoted without explicit human
    review.

**LLM calls are budget-limited by default (`--max-llm-calls`, default
50)** — this session already hit a monthly API spend limit once.
Requires ANTHROPIC_API_KEY (.env or environment); if unset, rule-based
aliases still get written and the LLM step is skipped with a clear
warning, not a crash.

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

from analysis.metrics import _normalize_tier  # noqa: E402
from etl.db import get_connection, utcnow_iso  # noqa: E402

DOTENV_PATH = REPO_ROOT / ".env"
LLM_MODEL = "claude-haiku-4-5-20251001"
MAX_SUB_EVENTS_FOR_PROMPT = 8

YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
BARE_ACRONYM_RE = re.compile(r"^[A-Z0-9]{2,5}$")


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


def _clean_segment(segment: str) -> str:
    return re.sub(r"\s+", " ", YEAR_RE.sub("", segment)).strip()


def series_key_and_depth(liquipedia_page: str) -> tuple[str, int]:
    """Returns (series_key, segments_consumed). segments_consumed lets
    callers find the next segment after the series_key (the "sub-event"
    name) without re-deriving the fold-in decision."""
    segments = liquipedia_page.split("/")
    seg1 = _clean_segment(segments[0])
    if BARE_ACRONYM_RE.match(seg1) and len(segments) > 1:
        seg2 = _clean_segment(segments[1])
        if seg2 and not re.fullmatch(r"\d+", seg2):
            return f"{seg1}/{seg2}", 2
    return seg1, 1


def sub_event_name(liquipedia_page: str, segments_consumed: int) -> str | None:
    """First descriptive segment after whatever series_key consumed —
    purely informational text for the LLM prompt, not a grouping decision,
    so unlike series_key_and_depth's fold-in check this DOES skip past a
    bare year (real paths are often Organizer/[SubBrand]/Year/Region/...,
    and the region — e.g. "China League", "North America" — is what's
    actually useful context, not the year in between)."""
    segments = liquipedia_page.split("/")
    for segment in segments[segments_consumed:]:
        candidate = _clean_segment(segment)
        if candidate and not re.fullmatch(r"\d+", candidate):
            return candidate
    return None


def rule_based_aliases(series_key: str, exemplar_page: str) -> set[str]:
    name_minus_year = series_key.replace("/", " ").strip()
    full_name = exemplar_page.replace("/", " ").strip()
    aliases = {name_minus_year}
    if full_name and full_name != name_minus_year:
        aliases.add(full_name)

    # Unicode-aware ([^\W_]+, not [A-Za-z0-9]+): the ASCII-only version
    # fragmented any accented word at the accent (e.g. "Brasileirão" ->
    # ["Brasileir", "o"], since "ã" isn't in [A-Za-z0-9]), which both
    # spuriously enabled acronym generation for single-word series names
    # that should have been skipped, and produced a wrong acronym for
    # multi-word ones — confirmed live: this generated "BO" for the
    # single-word "Brasileirão" series (both an incorrect acronym, and
    # incorrectly enabled at all), which then case-sensitive-matched the
    # unrelated Polish word "bo" ("because") in unrelated CS2 stream
    # titles. [^\W_]+ (not bare \w+, which also matches "_") keeps
    # Unicode letters together while still splitting on real
    # word-boundaries, and still treats digits as part of a token
    # (confirmed: "AoE2"/"1st"/"T90" stay single tokens, unlike a
    # letters-only Unicode class would give).
    words = [w for w in re.findall(r"[^\W_]+", name_minus_year, re.UNICODE)]
    if len(words) >= 2:
        acronym = "".join(w[0].upper() for w in words)
        if len(acronym) >= 2:
            aliases.add(acronym)

    return {a for a in aliases if a}


def call_llm_for_nicknames(client, title_display_name: str, series_key: str, sub_events: list[str]) -> list[str]:
    """One call, one series. Returns a possibly-empty list of colloquial
    nicknames — empty is the correct answer when nothing well-known
    exists, not a failure; the prompt says so explicitly to discourage
    invented aliases."""
    sub_events_line = (
        f"Notable sub-events within this series: {', '.join(sub_events)}\n" if sub_events else ""
    )
    prompt = (
        f"Game: {title_display_name}\n"
        f"Tournament series (Liquipedia grouping): {series_key}\n"
        f"{sub_events_line}\n"
        "List well-known, commonly-used colloquial nicknames or short names "
        "fans actually type for this tournament series OR its notable "
        "sub-events listed above, in stream titles, chat, or casual "
        "conversation (e.g. \"Worlds\", \"MSI\", \"TI\", \"Champs\", "
        "\"VALORANT Champions\"). Only include names you are confident are "
        "genuinely in common use — if you don't know of any well-established "
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
        title_filter = f"AND title_id IN ({','.join('?' for _ in title_ids)})"
        params = tuple(title_ids)

    rows = conn.execute(
        f"""
        SELECT id, title_id, liquipedia_page, tier, prize_pool
        FROM tournaments
        WHERE 1=1 {title_filter}
        """,
        params,
    ).fetchall()

    tier12_rows = [r for r in rows if _normalize_tier(r[3]) in ("1", "2")]
    print(f"{len(tier12_rows)} tier-1/2 tournament(s) out of {len(rows)} considered")

    # series (title_id, series_key) -> list of (tournament_id, page, prize_pool)
    series_members: dict[tuple[str, str], list[tuple[int, str, float | None]]] = defaultdict(list)
    depth_by_series: dict[tuple[str, str], int] = {}
    for tid, title_id, page, _tier, prize_pool in tier12_rows:
        key, depth = series_key_and_depth(page)
        series_members[(title_id, key)].append((tid, page, prize_pool))
        depth_by_series[(title_id, key)] = depth
        conn.execute("UPDATE tournaments SET series_key = ? WHERE id = ?", (key, tid))
    conn.commit()

    per_title_counts: dict[str, int] = defaultdict(int)
    for title_id, _key in series_members:
        per_title_counts[title_id] += 1
    print(f"{len(series_members)} distinct series across {len(per_title_counts)} title(s):")
    for title_id in sorted(per_title_counts):
        print(f"  {title_id:20} {per_title_counts[title_id]:5} series")

    already_rule_based = {
        (title_id, series_key)
        for (title_id, series_key) in conn.execute(
            "SELECT DISTINCT title_id, series_key FROM tournament_aliases WHERE source = 'rule_based'"
        ).fetchall()
    }
    already_llm_checked = {
        (title_id, series_key)
        for (title_id, series_key) in conn.execute(
            "SELECT title_id, series_key FROM tournament_alias_llm_checked"
        ).fetchall()
    }
    needs_rule_based = sorted(k for k in series_members if k not in already_rule_based)
    needs_llm = sorted(k for k in series_members if k not in already_llm_checked)
    print(f"{len(already_rule_based)} series already have rule-based aliases, "
          f"{len(needs_rule_based)} need them")
    print(f"{len(already_llm_checked)} series already LLM-checked (nickname found or confirmed "
          f"none exists), {len(needs_llm)} still need an LLM check")

    display_name_by_title: dict[str, str] = {}
    all_touched = sorted(set(needs_rule_based) | set(needs_llm))
    if all_touched:
        title_ids_needed = {title_id for title_id, _ in all_touched}
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

    def insert_alias(title_id: str, series_key: str, alias: str, source: str, confidence: str) -> bool:
        case_sensitive = 1 if len(alias) < 4 else 0
        cur = conn.execute(
            """
            INSERT INTO tournament_aliases (title_id, series_key, alias, case_sensitive, source, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (title_id, series_key, alias) DO NOTHING
            """,
            (title_id, series_key, alias, case_sensitive, source, confidence),
        )
        return cur.rowcount > 0

    needs_rule_based_set = set(needs_rule_based)
    needs_llm_set = set(needs_llm)
    rule_based_rows_written = 0
    llm_rows_written = 0
    llm_calls_made = 0
    llm_errors = 0

    for title_id, key in all_touched:
        members = series_members[(title_id, key)]
        depth = depth_by_series[(title_id, key)]

        if (title_id, key) in needs_rule_based_set:
            # Exemplar: shallowest page (most "top-level"), tie-broken by prize_pool desc.
            exemplar = min(members, key=lambda m: (m[1].count("/"), -(m[2] or 0)))
            exemplar_page = exemplar[1]
            for alias in rule_based_aliases(key, exemplar_page):
                if insert_alias(title_id, key, alias, "rule_based", "verified"):
                    rule_based_rows_written += 1

        if client is not None and (title_id, key) in needs_llm_set and llm_calls_made < args.max_llm_calls:
            # Sub-events, deduped, prioritized by prize_pool desc, capped.
            ranked_members = sorted(members, key=lambda m: -(m[2] or 0))
            sub_events: list[str] = []
            seen = set()
            for _tid, page, _pp in ranked_members:
                name = sub_event_name(page, depth)
                if name and name not in seen:
                    seen.add(name)
                    sub_events.append(name)
                if len(sub_events) >= MAX_SUB_EVENTS_FOR_PROMPT:
                    break

            display_name = display_name_by_title.get(title_id, title_id)
            try:
                nicknames = call_llm_for_nicknames(client, display_name, key, sub_events)
                llm_calls_made += 1
            except Exception as exc:  # one bad call shouldn't abort the whole run
                print(f"[error] LLM call failed for series {key!r} ({title_id}): {exc}", file=sys.stderr)
                llm_errors += 1
                conn.commit()
                continue  # don't mark as checked — a failed call should be retried, not treated as "confirmed none"

            for alias in nicknames:
                if insert_alias(title_id, key, alias, "ai_assisted", "ai_assisted_unreviewed"):
                    llm_rows_written += 1

            # Recorded even when nicknames is empty — that's a real "checked,
            # none exist" answer (see schema.sql), not a failure to retry.
            conn.execute(
                """
                INSERT INTO tournament_alias_llm_checked (title_id, series_key, checked_at, nickname_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (title_id, series_key) DO UPDATE SET
                    checked_at=excluded.checked_at, nickname_count=excluded.nickname_count
                """,
                (title_id, key, utcnow_iso(), len(nicknames)),
            )

        conn.commit()

    finished_at = utcnow_iso()
    llm_still_needed = len(needs_llm_set) - llm_calls_made if client is not None else len(needs_llm_set)
    llm_skipped = max(0, llm_still_needed)
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
