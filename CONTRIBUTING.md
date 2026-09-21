# Contributing

The project is small on purpose: one problem, one cost function, one policy, one simulator, one reference implementation. Please keep it that way.

## Ground rules
- **No new features without a baseline.** Anything that changes scheduling behaviour must be compared against `reactive_fastest` and `oracle` in `examples/compare_policies.py` and the numbers pasted in the PR.
- **Numbers must be reproducible.** Fix seeds, state the config, commit the JSON output under `results/` only for tagged releases.
- **Prefer deleting code.** The cost function in `policy.py` is the paper. Complexity there needs a written justification in `docs/algorithm.md`.
- Format with `ruff`, test with `pytest`. CI runs both.

## Where things live
| Path | What |
|---|---|
| `src/hazardserve/hazard.py` | Survival estimation (Kaplan-Meier + conditional survival) |
| `src/hazardserve/cost.py` | Time and migration cost models |
| `src/hazardserve/crossover.py` | Transfer-vs-recompute crossover |
| `src/hazardserve/policy.py` | The algorithm + baselines |
| `src/hazardserve/simulator.py` | Churn-driven discrete-time simulator |
| `examples/` | Runnable experiments |
| `notebooks/` | Derivations that back the design note |
| `docs/` | GitHub Pages (MkDocs Material) |
| `paper/` | Paper source and figures |
| `PLAN.md` | Phases, milestones, pivot thresholds |

## Good first issues
See `PLAN.md` Phase 1 and Phase 2 checklists; anything unchecked is open.
