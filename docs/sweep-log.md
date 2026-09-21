# arXiv sweep log

!!! note "Phase 0 deliverable"
    `PLAN.md` Phase 0 requires a fresh sweep **before** the differentiation table in [prior art](related-work.md) is frozen, and design note §5 requires the freeze to be auditable. One row per sweep. Never edit a past row; add a new one.

## How to run a sweep

1. Query cs.DC and cs.LG for the last 6 months: `LLM inference spot`, `preemptible serving`, `KV cache migration`, `survival analysis scheduling`, `volunteer inference`, `hazard rate placement`, `elastic serving reclamation`.
2. For each hit, decide against the three columns only: per-node survival hazard | one cost function for placement *and* pre-emptive migration | KV-transfer vs recompute choice.
3. Add any new row to `docs/related-work.md` with one sentence naming the exact thing it does *not* do.
4. Verify every arXiv ID already in `paper/references.bib` still resolves to the paper it claims.
5. Record the sweep below, including the queries that returned nothing — a null result is evidence for the novelty claim.

## Sweeps

| Date | Queries | New entries | arXiv IDs verified | Pivot triggered? | Notes |
|---|---|---|---|---|---|
| _pending_ | – | – | – | – | Pre-freeze sweep not yet run. The table in `docs/related-work.md` is dated September 2026 and is **not** frozen. |

## Pivot rule

If a sweep finds a preprint that ships **all three** columns, trigger the `PLAN.md` Phase 5 pivot immediately rather than waiting for Phase 3: reposition around the survival-model formalization, the open simulator and trace suite, and a head-to-head benchmark. Record the decision in the row above.
