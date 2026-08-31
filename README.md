# fandomdatapuller

A personal research platform for tracking digital-fandom metrics, starting
with esports live-viewership data. See `docs/esports_gauses_law_brief.md`
for the research question and `docs/esports_fandom_platform_prd_v2.md` for
the full build spec.

## Status

**Phase 1 only:** the Twitch live-viewership collector, tracked-title
config, raw snapshot landing zone, and heartbeat monitoring. No database,
ETL, or other connectors yet.

## Setup

1. Register an application at [dev.twitch.tv](https://dev.twitch.tv) to get
   a Client ID and Client Secret.
2. Copy `.env.example` to `.env` and fill in both values. `.env` is
   gitignored — never commit real credentials.
3. Add the same two values as GitHub Actions repository secrets
   (`TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`) so the scheduled workflow
   can authenticate — see below.
4. `pip install -r requirements.txt`

## Running the collector

```
python collectors/twitch_poll.py
```

Writes one timestamped JSON snapshot under `data/raw/twitch/`. In CI, the
`Twitch live-viewership poll` workflow (`.github/workflows/poll.yml`) does
this hourly and commits the result back to the repo.

To poll a specific title list or run tighter-interval "event mode" polling
during a broadcast window, trigger that workflow manually from the Actions
tab with the `titles`, `duration_minutes`, and `interval_minutes` inputs.

## Monitoring

`.github/workflows/healthcheck.yml` runs daily and fails (triggering
GitHub's default failure-notification email) if the newest raw snapshot is
older than 3 hours — the signal that the hourly collector has silently
stopped running.
