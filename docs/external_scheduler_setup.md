# External scheduler setup — working around GitHub Actions' unreliable `schedule` event

## Why this exists

Confirmed 2026-09-10, against a week of `poll.yml` run history: real
average gap between scheduled runs was **3.8 hours**, against a
configured **1-hour** cron (`0 * * * *`). Checked that this predates the
addition of most of this repo's other scheduled workflows (same
magnitude present back to 2026-09-04), which rules out our own
concurrent-workflow count as the cause — this looks like GitHub
deprioritizing `schedule`-triggered runs for this repo at the platform
level, not something fixable by editing our own workflow files.

This matters far beyond inconvenience: `poll.yml` is the collector
CLAUDE.md protects as the project's "one rule" — *"an hour the collector
isn't running is an hour of data lost permanently, at any price."* A
3.8h real cadence against a 1h target means a large, ongoing,
unrecoverable gap in exactly the data this project exists to capture.

`workflow_dispatch` (API-triggered) runs are not subject to the same
observed delay. `.github/workflows/dispatch_hourly.yml` and
`dispatch_daily.yml` exist to be triggered externally, on schedule, from
*outside* GitHub's own scheduler — and fan out to `workflow_dispatch`
every real collector (plus the healthcheck) using the repo's own
built-in `GITHUB_TOKEN`, so only the first hop (external service →
GitHub) needs a credential at all.

Every underlying collector keeps its native `schedule:` trigger too, as
a free fallback — this is additive, not a replacement.

## What you need to do (two steps, both require your own GitHub/external-service accounts — not something Claude can do on your behalf)

### 1. Create a fine-grained Personal Access Token (PAT)

GitHub → Settings → Developer settings → Personal access tokens →
Fine-grained tokens → **Generate new token**.

- **Repository access**: "Only select repositories" → `fandomdatapuller` only. Not all repos.
- **Permissions**: Repository permissions → **Actions** → **Read and write**. Nothing else is needed — no Contents, no Issues, no anything else.
- **Expiration**: GitHub caps fine-grained PATs at 1 year max. Set a calendar reminder to rotate it, or set it shorter and rotate more often — your call.
- Copy the token once it's generated (starts `github_pat_...`) — GitHub only shows it once.

This token can do exactly one thing on exactly one repo: trigger
`workflow_dispatch` runs. It cannot read or write code, issues, or
anything else.

### 2. Set up two scheduled HTTP calls on a free cron service

Any service that can POST an HTTP request on a schedule works —
[cron-job.org](https://cron-job.org) is free, no credit card, and
commonly used for exactly this. Create two jobs:

**Job 1 — hourly**, e.g. every hour at :05:
- URL: `https://api.github.com/repos/JacobH1994/fandomdatapuller/actions/workflows/dispatch_hourly.yml/dispatches`
- Method: `POST`
- Headers:
  - `Authorization: Bearer <your PAT>`
  - `Accept: application/vnd.github+json`
  - `Content-Type: application/json`
- Body: `{"ref": "main"}`

**Job 2 — daily**, e.g. once at 03:00 UTC:
- Same as above, but URL ends `dispatch_daily.yml/dispatches`.

### Verifying it worked

```
gh workflow run dispatch_hourly.yml --ref main   # manual test, same effect as the external cron hitting it
gh run list --workflow=dispatch_hourly.yml --limit 5
gh run list --workflow=poll.yml --limit 5
```

After a day or two, re-run the same gap analysis this finding came from
(pull `gh run list --workflow=poll.yml --json createdAt,event`, filter
`event == "workflow_dispatch"` now instead of `"schedule"`, compute
gaps) to confirm real cadence is back near 1 hour. If it isn't, the
external cron service itself is the next thing to check, not this
repo's configuration.

## Rotating or revoking the PAT

Settings → Developer settings → Personal access tokens → Fine-grained
tokens → find it → Delete. The two dispatcher workflows and everything
else in this repo are unaffected either way — only the external cron
service's ability to trigger them stops.
