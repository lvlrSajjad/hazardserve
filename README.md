# hazardserve

**Hazard-aware placement and pre-emptive migration for stateful LLM inference requests on nodes that can disappear.**

> Status: v0.1 research scaffold. The algorithm, simulator, baselines and tests work; the numbers below are from synthetic churn traces and are not yet a result. See [`PLAN.md`](PLAN.md) for what happens next.

## The problem in one paragraph

Autoregressive decoding is stateful: every generated token grows a KV cache that lives on one node. Spot instances get reclaimed, volunteer laptops get their owners back, edge devices lose battery or signal. Today's serving systems (SpotServe, ShuntServe, SkyServe, Llumnix, Petals, Parallax) treat that departure as a *surprise* and recover after the fact. But node departure is not random: each node has a **hazard function** that can be estimated from its own session history, and the hazard changes with how long the node has already been up. hazardserve makes that hazard a first-class scheduling input.

## The idea in one equation

For request *r* on node *i*, with remaining service time *T<sub>i</sub>* and conditional session-length density *f<sub>i</sub>(t | age<sub>i</sub>)*:

```
E_i(r) = T_i  +  ∫₀^{T_i} f_i(t | age_i) · U_i(t) dt
         ─┬─     ────────────┬──────────────
       time            expected unplanned loss
```

*U<sub>i</sub>(t)* is what a failure at time *t* costs: re-prefilling the context accumulated by then on the best fallback node, plus an SLO penalty for the visible stall.

One function, two decisions:

| Decision | Rule |
|---|---|
| **Place** new request | `argmin_i E_i(r)` over feasible nodes |
| **Pre-emptively migrate** running request *i → j* | move iff the risk removed pays for the move and the request does not get materially slower: `L_i − (C_planned(i→j) + L_j) > h` and `(T_j + C_planned) − T_i < h` |
| **How** to migrate | `C_planned = min(KV transfer, recompute-from-tokens)`; when the source is already gone only recompute is possible |

Because the same *E* drives both decisions, the policy never migrates into a node it would not have placed on, and it migrates *early*, while the source is still alive and cheap KV transfer is an option.

Hazard estimation is deliberately simple (Kaplan-Meier per node, conditioned on current uptime, pooled prior for newcomers). The paper is the decision rule, not the estimator; better estimators plug in.

## Quickstart

```bash
pip install -e ".[dev]"
pytest -q
python examples/compare_policies.py --seeds 3 --hours 2      # mixed fleet: laptops + spot + servers
python examples/volunteer_fleet.py  --seeds 3 --hours 2      # 45 laptops, churn dominates
```

## Current (synthetic) numbers

Three seeds, 2 simulated hours, warm-up excluded. Policies see identical churn and arrivals. `oracle` knows every node's true remaining session length and is an upper bound on what *any* predictor could achieve.

**Mixed fleet** (30 laptops, 10 spot, 3 servers, 0.6 req/s):

| policy | mean lat (s) | p99 lat (s) | unplanned migrations | wasted s |
|---|---|---|---|---|
| random | 384.7 | 2394.4 | 518.7 | 1200.2 |
| reactive_fastest | 38.2 | 143.3 | 39.0 | 90.9 |
| **hazard_aware** | 38.1 | 148.9 | 35.3 | 70.9 |
| oracle | 38.5 | 151.5 | 22.3 | 61.7 |

**Volunteer fleet** (45 laptops, 0.15 req/s):

| policy | mean lat (s) | p99 lat (s) | unplanned migrations | planned | wasted s |
|---|---|---|---|---|---|
| reactive_fastest | 88.0 | 466.4 | 77.3 | 0 | 586.3 |
| **hazard_aware** | 82.8 | 466.0 | 74.3 | 10.0 | 691.3 |
| oracle | 87.8 | 514.0 | 32.7 | 0 | 253.7 |

What this says, honestly: the v0 placement rule already reduces unplanned failures and waste versus the reactive baseline at equal latency, and the oracle shows there is a further 2× reduction available to better prediction. The pre-emptive migration trigger is conservative and barely fires; tuning it is Phase 1 work. None of this is a claim until it runs on real traces (Phase 2).

## What is new here

Prior work holds at most two of the three ingredients:

| | per-node survival hazard | one cost for placement **and** pre-emptive migration | KV-transfer vs recompute choice |
|---|:-:|:-:|:-:|
| SpotServe (ASPLOS'24) | – | – | recompute-oriented |
| ShuntServe (2026) | – | – | measured, per-request choice left as future work |
| SkyServe (EuroSys'25) | – | – | – (abort and retry) |
| SkyNomad (2026) | ✓ (batch jobs) | partial (no request migration) | – |
| Pallas / ctHO (2026) | – (mobility prediction) | – (migration only) | ✓ |
| Llumnix (OSDI'24) | – | – (reactive live migration) | KV transfer |
| **hazardserve** | ✓ | ✓ | ✓ |

Full comparison and citations: [`docs/related-work.md`](docs/related-work.md).

## Layout

```
src/hazardserve/   hazard.py (survival)  cost.py (time/migration)  crossover.py (transfer vs recompute)  policy.py (the algorithm + baselines)  simulator.py
examples/          runnable experiments
notebooks/         derive-trigger.ipynb — the Phase 0 derivation
tests/             pytest
docs/              GitHub Pages (MkDocs Material)
paper/             paper skeleton + bib + design note
traces/            notes on public availability and workload traces
PLAN.md            phases, milestones, pivot thresholds
```

## Roadmap

Phase 0 formalize → Phase 1 simulator and policy → Phase 2 trace-driven evaluation → Phase 3 reference implementation as an llm-d scorer plus vLLM KV-connector migration → Phase 4 real spot/consumer hardware → Phase 5 paper, Pages, release. Details and checklists in [`PLAN.md`](PLAN.md).

## Citing

See [`CITATION.cff`](CITATION.cff). A Zenodo DOI is minted on the first tagged release.

## License

Apache-2.0.
