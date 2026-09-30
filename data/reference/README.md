# data/reference/ — provenance

This repo's own code is MIT-licensed (see the root `LICENSE`). That does
**not** extend to the third-party data below — each file here carries
whatever license its original source does, independent of the code
license.

Exported, disposable-and-rebuildable reference data (see the root
`CLAUDE.md`'s "rebuildable from committed repo contents alone" section —
`python etl/load_snapshots.py --rebuild` replays this alongside
`data/raw/`). Not all files here share one source; attribution below is
per file, not blanket.

## Liquipedia-derived — CC BY-SA, attribution required

**`tournaments.jsonl`, `tournament_aliases.jsonl`,
`tournament_alias_llm_checked.jsonl`** are derived from
[Liquipedia](https://liquipedia.net/) — an independent, community-maintained
esports wiki — pulled via `collectors/liquipedia.py` against 20 of
Liquipedia's per-game sub-wikis (see `config/titles.yaml`'s
`liquipedia_wiki` field for the full list: Age of Empires, Apex Legends,
Brawl Stars, Counter-Strike, Dota 2, the shared fighting-games wiki,
Fortnite, Free Fire, Hearthstone, League of Legends, Mobile Legends:
Bang Bang, Overwatch, PUBG, PUBG Mobile, Rainbow Six, Rocket League,
StarCraft II, Teamfight Tactics, VALORANT, and Wild Rift).

Liquipedia's own content is published under
[Creative Commons Attribution-ShareAlike](https://liquipedia.net/commons/Liquipedia:Copyrights)
(CC BY-SA). Per Liquipedia's own terms and direct written guidance to this
project (2026-09-30): credit is required in close proximity to the data,
with backlinking where possible — this file is that credit for the three
tournament files above. `tournament_alias_llm_checked.jsonl` additionally
carries LLM-generated nickname/alias judgments layered on top of
Liquipedia's own tournament-name data (see
`etl/generate_tournament_aliases.py`) — those judgments are this
project's own, but the underlying tournament identity they're attached to
is still Liquipedia-sourced.

`tournaments.tier`, `.prize_pool`, `.start_date`/`.end_date`, and similar
fields are extracted from Liquipedia's own `Infobox league` wikitext
template, not independently verified — see the root `CLAUDE.md`'s
provenance section (`source`/`confidence` columns) for this project's
general handling of ingested-vs-inferred data.

## Not Liquipedia — other sources

- **`monthly_category_history.jsonl`** — the Kaggle "Evolution of Top
  Games on Twitch" historical dataset (`collectors/kaggle_import.py`).
- **`steam_release_history.jsonl`** — Valve's own Steam Web API
  (`collectors/steam_catalog_backfill.py`).
- **`cpi_deflator.csv`** — a public CPI/inflation-deflator series (see the
  script that generates it for the exact source), used for real-dollar
  prize-pool normalization.
