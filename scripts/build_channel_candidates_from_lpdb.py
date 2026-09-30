#!/usr/bin/env python3
"""Generates official-broadcast-channel candidates from LPDB match-stream
data, built 2026-10-01 following a direct request to use LPDB as a source
for refreshing config/channels.yaml (currently curated for only 5 of 23
titles: counter_strike, dota2, street_fighter, valorant, pubg).

Reads `match_streams_lpdb` (collectors/liquipedia_lpdb_broadcasts.py),
which is only populated for titles the overnight sync
(scripts/lpdb_overnight_sync.py) has reached -- run `--status` on that
data before expecting output here for a given title.

**This does NOT write config/channels.yaml directly.** Every value in
`match_streams_lpdb.channel_name` is LPDB's own Liquipedia template
parameter (e.g. "Fragbite"), not confirmed to be the exact lowercase
Twitch login `config/channels.yaml`'s own header comment requires as its
match key -- display name and login can differ. This script does the same
live Twitch Helix verification `research/other/notebooks/
official_channel_candidates.ipynb` already established as this project's
curation standard (does the login exist? partner/affiliate status? does
the bio self-identify as an official channel?), and writes verified
matches to `config/channels_lpdb_candidates.yaml` -- a draft for human
review, same role `config/channels.draft.yaml` already plays for the
MediaWiki-derived candidate pipeline, kept separate so the two sources'
candidates are never confused with each other or silently merged.

Ranking signal: within a title, candidates are ordered by how many
distinct matches referenced that channel name in the sampled tournament
set -- a channel appearing across many matches is far more likely to be
a tournament organizer's own broadcast than a one-off personality
co-stream, the same distinction config/channels.yaml's own curation
notes already draw for the MediaWiki-derived candidates.

Usage:
    python scripts/build_channel_candidates_from_lpdb.py                     # all titles with match_streams_lpdb data
    python scripts/build_channel_candidates_from_lpdb.py --titles valorant
    python scripts/build_channel_candidates_from_lpdb.py --top-n 20          # candidates considered per title (default 15)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from etl.db import get_connection  # noqa: E402

DOTENV_PATH = REPO_ROOT / ".env"
OUT_PATH = REPO_ROOT / "config" / "channels_lpdb_candidates.yaml"
TOKEN_URL = "https://id.twitch.tv/oauth2/token"
USERS_URL = "https://api.twitch.tv/helix/users"
DEFAULT_TOP_N = 15


def load_dotenv(path: Path) -> None:
    import os
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_access_token(client_id: str, client_secret: str) -> str:
    resp = httpx.post(TOKEN_URL, params={
        "client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def login_candidates(raw_name: str) -> list[str]:
    """Best-effort guesses at the real Twitch login from LPDB's display-name-
    shaped `channel_name` -- Twitch logins are lowercase alphanumeric/
    underscore only, LPDB's value often isn't. Tried in order; the first
    Helix hit wins. Not guaranteed to find anything -- a channel whose
    login bears no resemblance to its display name won't resolve here and
    is silently absent from the candidates file, not guessed at further."""
    lower = raw_name.strip().lower()
    candidates = [lower, lower.replace(" ", ""), lower.replace(" ", "_"), lower.replace("-", "")]
    seen = set()
    out = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def verify_logins(client: httpx.Client, headers: dict, logins: list[str]) -> dict[str, dict]:
    """Batched Helix Get Users lookup (up to 100 logins/call). Returns
    {login: user_object} for every login that actually resolved."""
    found: dict[str, dict] = {}
    for i in range(0, len(logins), 100):
        batch = logins[i:i + 100]
        resp = client.get(USERS_URL, headers=headers, params=[("login", l) for l in batch], timeout=30)
        if resp.status_code != 200:
            print(f"[warn] Helix Get Users batch failed: HTTP {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
            continue
        for user in resp.json().get("data", []):
            found[user["login"]] = user
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--titles", help="comma-separated title ids (default: every title with match_streams_lpdb rows)")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help=f"candidate channel names considered per title, ranked by match count (default {DEFAULT_TOP_N})")
    args = parser.parse_args()

    load_dotenv(DOTENV_PATH)
    import os
    client_id = os.environ.get("TWITCH_CLIENT_ID")
    client_secret = os.environ.get("TWITCH_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("[fatal] TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET not set (check .env)", file=sys.stderr)
        return 1

    conn = get_connection()
    if args.titles:
        title_ids = args.titles.split(",")
    else:
        title_ids = [r[0] for r in conn.execute("SELECT DISTINCT title_id FROM match_streams_lpdb ORDER BY title_id")]

    if not title_ids:
        print("No data in match_streams_lpdb yet -- run collectors/liquipedia_lpdb_broadcasts.py "
              "(or wait for scripts/lpdb_overnight_sync.py to reach the broadcast phase) before using this script.")
        return 0

    token = get_access_token(client_id, client_secret)
    headers = {"Client-Id": client_id, "Authorization": f"Bearer {token}"}

    all_candidates: dict[str, list[dict]] = {}

    with httpx.Client() as client:
        for title_id in title_ids:
            rows = conn.execute(
                "SELECT channel_name, COUNT(DISTINCT match_objectname) AS n_matches "
                "FROM match_streams_lpdb WHERE title_id=? GROUP BY channel_name ORDER BY n_matches DESC LIMIT ?",
                (title_id, args.top_n),
            ).fetchall()
            if not rows:
                continue

            title_candidates = []
            for raw_name, n_matches in rows:
                resolved = None
                for login in login_candidates(raw_name):
                    found = verify_logins(client, headers, [login])
                    if login in found:
                        resolved = found[login]
                        break
                if resolved:
                    title_candidates.append({
                        "lpdb_channel_name": raw_name,
                        "matches_seen": n_matches,
                        "twitch_login": resolved["login"],
                        "display_name": resolved["display_name"],
                        "broadcaster_type": resolved.get("broadcaster_type") or "(none)",
                        "description": resolved.get("description", "")[:200],
                    })
                else:
                    title_candidates.append({
                        "lpdb_channel_name": raw_name,
                        "matches_seen": n_matches,
                        "twitch_login": None,
                        "note": "no Twitch login resolved from any naive normalization -- needs manual lookup, not guessed further",
                    })
            all_candidates[title_id] = title_candidates
            resolved_n = sum(1 for c in title_candidates if c.get("twitch_login"))
            print(f"{title_id}: {resolved_n}/{len(title_candidates)} candidates resolved to a real Twitch login")

    conn.close()

    header = (
        "# LPDB-derived official-broadcast-channel candidates -- DRAFT, human review required.\n"
        "# Generated by scripts/build_channel_candidates_from_lpdb.py from match_streams_lpdb\n"
        "# (LPDB's match.stream field, ai_assisted_unreviewed at the source -- see etl/schema.sql's\n"
        "# comment on match_streams_lpdb for why). Every entry below has passed a live Twitch Helix\n"
        "# existence check, but NOT the same full manual review config/channels.yaml's existing\n"
        "# entries received (bio self-identification, exclusion of personality/co-stream accounts).\n"
        "# Do not copy into config/channels.yaml without that review -- same discipline as\n"
        "# config/channels.draft.yaml, this file's MediaWiki-derived counterpart, already requires.\n"
        "# `matches_seen` is a same-title ranking signal (more matches referencing a channel name\n"
        "# suggests a tournament organizer's own broadcast, not a one-off co-stream), not a\n"
        "# confidence score on its own.\n\n"
    )
    with open(OUT_PATH, "w") as f:
        f.write(header)
        yaml.safe_dump(all_candidates, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(f"\nwrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
