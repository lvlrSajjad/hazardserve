# PLAN

Single contribution, shipped the way Kazemi & Sullivan shipped face alignment: one well-posed problem, one simple algorithm, one clean evaluation, one reference implementation inside libraries people already run. Everything not on this path is out of scope (no platform, no incentives, no chat UI).

Timeline is nominal for one person working part-time. Weeks overlap by design.

---

## Phase 0 — Formalize (weeks 1–4)

Goal: a problem statement a reviewer cannot poke holes in, and a differentiation table we can defend.

- [ ] Write `docs/problem.md`: nodes, hazard *h<sub>i</sub>(t | age)*, requests, KV state, unplanned vs planned migration, objective.
- [ ] Write `docs/algorithm.md`: derive the migration trigger from *E*; state assumptions (append-only KV, tokens streamed so recompute is always possible, estimates of output length may be noisy).
- [ ] Decide the transfer-vs-recompute crossover model (start from ShuntServe's measurement: recompute wins except for very long contexts; ServerlessLLM's token-migration argument).
- [ ] Freeze the differentiation table vs SpotServe, ShuntServe, SkyServe, SkyNomad, Pallas, ctHO, Llumnix, Petals/Parallax. Re-run an arXiv sweep for late-2026 preprints before freezing.
- [ ] Pick the paper's *one figure*: the cost decomposition *E = T + L* on a decreasing-hazard vs increasing-hazard node.

Exit artifact: 6–8 page design note (`paper/design-note.md`), notebook deriving the trigger.

## Phase 1 — Simulator and policy (weeks 3–10)

Goal: a simulator others will reuse even if they ignore our policy.

- [x] Discrete-time churn-driven simulator with laptop / spot / server archetypes.
- [x] Kaplan-Meier conditional survival per node, pooled prior for newcomers.
- [x] Unified expected-cost placement; hazard-motivated pre-emptive migration; KV-transfer vs recompute.
- [x] Baselines: random, reactive-fastest (SpotServe-style recovery), oracle upper bound.
- [ ] Add baselines: load/queue-aware (Llumnix-style), replica hedging (SkyServe-style), prefix-cache-aware placement (llm-d default).
- [ ] Tune the migration trigger: it barely fires in v0. Sweep hysteresis, check interval, `min_remaining`; report the Pareto curve of planned vs unplanned migrations.
- [ ] Hazard estimators beyond KM: Weibull MLE, hierarchical (archetype prior + per-node update), gradient-boosted survival with features (uptime, hour-of-day, node type). Ablate.
- [ ] Batching in the simulator (currently one request per node). Continuous batching changes the service-time model; add it before Phase 2 numbers are final.
- [ ] Output-length estimator noise sweep (the policy consumes an *estimate*; show robustness).
- [ ] Simulator validation plan: which real quantities will we compare against in Phase 4.

Exit artifact: `pip install hazardserve`, `examples/` reproducing every table, ≥ 80 % test coverage of `policy.py` and `hazard.py`.

## Phase 2 — Trace-driven evaluation (weeks 8–16)

Goal: numbers on public data that a reviewer can re-run.

- [ ] Trace loaders (`traces/`): SpotLake (AWS spot), Google 2019 cluster (evictions), Failure Trace Archive, SETI@home/BOINC host availability; workloads from Azure LLM Inference 2023, BurstGPT, Mooncake. Respect licences; loaders download, never redistribute.
- [ ] Cross availability × workload traces into scenario files; commit scenario *definitions*, not data.
- [ ] Metrics: goodput, TTFT, TPOT/ITL, P50/P99, SLO attainment, wasted GPU-seconds, $/token, migration count and downtime, fraction of requests hit by unplanned loss.
- [ ] Confidence intervals over seeds; plots via `examples/plot_results.py`.
- [ ] Ablation: hazard estimator family × migration trigger × workload.

Exit artifact: `results/` JSON for tagged release, figures for the paper.

**Pivot threshold:** if hazard_aware gains < 5 % goodput or waste reduction over reactive across *all* spot traces, shift the paper's centre of gravity to the volunteer/decentralized regime (heavier churn, prediction pays more) and position the spot result as secondary.

## Phase 3 — Reference implementation (weeks 14–22)

Goal: the algorithm lives where people already run inference.

- [ ] **Placement:** a hazard-aware *Scorer* plugin for the llm-d Inference Scheduler (Gateway API Inference Extension Endpoint Picker; Filter → Score → Pick pipeline, YAML-configured, no core changes needed). Node uptime/history come from endpoint metadata or a small sidecar.
- [ ] **Migration mechanics:** a vLLM KV-connector-backed path (LMCache / NIXL connectors) for planned migration, reusing append-only KV pipelining (Llumnix) and incremental per-token checkpointing (ConServe) so transfer-vs-recompute is a real choice, not a simulated one.
- [ ] **Secondary demo:** the same policy inside Parallax (or Petals) for the volunteer story.
- [ ] Open an upstream discussion in llm-d / GIE early; upstreaming is the distribution channel.

Exit artifact: installable plugin, config examples, upstream PR or RFC link.

## Phase 4 — Real hardware validation (weeks 20–26)

Goal: show the simulator is not lying.

- [ ] Small AWS spot cluster (g5 / g6 / g6e, mirroring ShuntServe) over a multi-day window; record real interruption times.
- [ ] A handful of consumer GPUs / Apple-silicon machines with real owner-activity churn for the volunteer regime.
- [ ] Replay the recorded churn through the simulator; plot simulator-vs-real fidelity.
- [ ] Ablations that only make sense on hardware: actual KV-transfer vs recompute crossover per context length.

Exit artifact: run logs, fidelity plot, hardware ablation tables.

## Phase 5 — Paper, Pages, release (weeks 24–30)

- [ ] Paper (MLSys / EuroSys style, ~10 pages): problem → cost function → algorithm → simulator results → real-hardware validation → artifact. Target MLSys 2027 (submission ≈ end of Oct 2026, verify on mlsys.org) or EuroSys / SoCC; workshops (ES-FoMo, MLArchSys) for early signal.
- [ ] arXiv: cs.DC primary, cs.LG cross-list.
- [ ] GitHub Pages live (MkDocs Material, `docs/`), CITATION.cff validated in CI, `.zenodo.json` → DOI on first tag, Apache-2.0.
- [ ] Artifact-evaluation submission (Available / Functional / Reproduced badges), Docker image for reproducibility.
- [ ] Launch: short blog post + repo + arXiv + 60-second demo; announce in llm-d / vLLM community channels.

**Pivot threshold:** if a preprint ships predictive hazard + unified placement/migration + transfer-vs-recompute before Phase 3 lands, reposition around (a) the survival-model formalization, (b) the open simulator and trace suite, (c) a head-to-head benchmark. The reference implementation remains the moat.

---

## Risks

| Risk | Mitigation |
|---|---|
| Field converges first (SkyNomad, Pallas, ShuntServe lineages are close) | Speed; publish arXiv early with simulator results; keep the scope small |
| Per-node history too sparse for survival fits | Hierarchical / pooled hazard (archetype prior + per-node update); itself a contribution |
| Gains on spot traces are small | Volunteer/decentralized regime as primary story (see Phase 2 pivot) |
| Simulator fidelity questioned | Phase 4 replay validation; publish fidelity plot |
| Reference implementation drifts with host APIs | Target plugin interfaces (llm-d scorers, vLLM KV connectors), pin versions, CI against them |
