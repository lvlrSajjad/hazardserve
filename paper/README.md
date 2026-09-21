# Paper

Target: MLSys 2027 (submission ≈ end of Oct 2026, verify on mlsys.org) or EuroSys / SoCC. ~10 pages, two-column, double-blind, artifact evaluation.

Files:
- `outline.md` — section skeleton with the claims each section must carry
- `references.bib` — bibliography (verify every arXiv ID before submission; several are 2026 preprints)
- `design-note.md` — Phase 0 deliverable (skeleton; §-by-§ artifact table at the top)
- `figures/` — generated, not committed: `examples/plot_cost_decomposition.py` now, `examples/plot_results.py` in Phase 2

Companion artifacts for Phase 0 live outside this directory: `notebooks/derive-trigger.ipynb` (the derivation), `docs/crossover.md` (transfer vs recompute), `docs/sweep-log.md` (the auditable freeze of the differentiation table).

Rule: one figure carries the paper. Candidate: the cost decomposition *E = T + L* over time on a decreasing-hazard laptop vs an increasing-hazard spot instance, showing why the same request should be placed differently. Draw it with:

```
python examples/plot_cost_decomposition.py
```

Not chosen yet — see design note §6 for why the honest version is harder to read than it sounds.
