# Raw snapshot landing zone

> **Moved 2026-11-25: people-identifying raw data is now private.** `twitch/`, `twitch_platform/`,
> `youtube/`, `twitch_accounts/` and `twitch_arabic_snapshot/` contain channel logins, display names,
> stream titles and account creation dates, so they live in the private `fandomdatapuller-data` repo.
> The collector workflows write there with a deploy key (`DATA_REPO_DEPLOY_KEY`). Locally that repo is
> cloned to `data/private/` and `data/raw/<folder>` is a symlink to `../private/<folder>`, so every
> path below still works. Steam data (game-level, no people) stays here. Everything below still
> describes the files; only where they are stored changed.

Append-only. Every file here is committed to git and never edited after the
fact — this is the git-scraping pattern (PRD §9.1) and the permanent record
referenced in PRD §2. If the schema changes or the ETL has a bug, these
files are what everything gets re-derived from.

```
data/raw/twitch/<YYYY>/<MM>/<DD>/<YYYYMMDDTHHMMSSZ>.json.gz
```

Each file is one poll of the Twitch collector (`collectors/twitch_poll.py`):
per-title stream data, a platform-wide viewer/channel total, and basic run
metadata (start/finish time, status, any errors), gzip-compressed.

**Not a raw API dump.** Every stream is filtered through the tiered capture
policy in `config/capture.yaml` before being written — full per-stream
detail (including title and tags, for later co-stream detection) for
official channels (`config/channels.yaml`) and anything above a
viewer-count threshold; everything below that threshold is folded into a
per-title, per-poll aggregate instead of kept as an individual record. This
keeps the long tail of near-zero-viewer streams — the bulk of records, a
negligible share of viewership — from dominating storage. See
`config/capture.yaml` for the threshold and the data it was picked from,
and `collectors/twitch_poll.py`'s docstring for the exact snapshot shape.

Nothing under `data/raw/` is ever deleted or rewritten by later phases —
`etl/load_snapshots.py` (Phase 2) reads these files but does not touch them.
