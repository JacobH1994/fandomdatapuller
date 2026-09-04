# Manual landing zone

Hand-entered data with no automated source — `source='manual'` per PRD §14.
Unlike `data/raw/` this isn't collector output, but it's still committed to
git and edited by replacing the whole file, not patched in place: these are
the independent test fixtures PRD §13 reconciles pipeline output against,
so their history has to be as trustworthy as the pipeline's.

```
data/manual/milestone_table.csv
```

The original hand-built success-milestone table (one row per title, from
before this pipeline existed), used by `notebooks/reconciliation.ipynb` to
check `analysis/metrics.py:get_success_milestone`'s output against
independently-produced numbers. Columns:

| column | required | meaning |
|---|---|---|
| `title_id` | yes | must match an `id` in `config/titles.yaml` — this is the join key |
| `milestone_year` | yes | the year the hand-built table says the title met the brief's success criteria (§4); blank/empty if it hadn't, by that reckoning |
| `notes` | no | free text — e.g. the reasoning behind a judgment call, or a flag from the sheet's own validation column (PRD §14 mentions this column already caught one suspect figure) |

One row per tracked title, including ones that haven't hit the milestone
(blank `milestone_year`) — the reconciliation notebook needs the full table
to tell "hand-built says not yet" apart from "hand-built has no opinion."

```
data/manual/milestone_table_original_export.csv
data/manual/normalize_original_export.py
```

`milestone_table.csv` above is generated, not hand-typed directly: the
original sheet export (preserved byte-for-byte in
`milestone_table_original_export.csv`, free-text game names and all) is
normalized into the `title_id` schema by `normalize_original_export.py`.
That script is also where **Crossfire, TrackMania, and Halo were dropped**
(not in `config/titles.yaml`) and where the original export's merged
`"Fighting Games (SF/Tekken)"` row was resolved (2026-09-05): its only
concrete corroboration (Tekken World Tour viewership) is Tekken-specific,
so it's mapped to `tekken` alone. `street_fighter` is deliberately absent
from this table — a real "hand-built table has no opinion," not a guessed
figure borrowed from Tekken's evidence.
