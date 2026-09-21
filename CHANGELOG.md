# Changelog

## Unreleased
- Phase 0 scaffolding: transfer-vs-recompute crossover model (`hazardserve.crossover`, `docs/crossover.md`) with tests pinning it to the cost model the policy calls; `notebooks/derive-trigger.ipynb` (runs; derivations still TODO) validating the 16-cell loss integral against Monte Carlo and printing why the migration trigger stays silent; `examples/plot_cost_decomposition.py` for the paper's candidate figure; `docs/sweep-log.md` so the differentiation-table freeze is auditable. Design note now names the artifact behind each section.

## 0.1.0 — 2026-09-19
- Initial research scaffold: hazard model (Kaplan-Meier conditional survival), cost model, hazard-aware policy, baselines, churn simulator, tests, docs, plan.
