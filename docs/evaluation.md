# Evaluation plan

## Baselines

| Baseline | Stands in for |
|---|---|
| `random` | sanity floor |
| `reactive_fastest` | SpotServe / Petals style: fastest feasible node, recover after failure |
| load-aware (todo) | Llumnix-style queue balancing |
| replica hedging (todo) | SkyServe SpotHedge |
| prefix-cache-aware (todo) | llm-d default scorer |
| `oracle` | upper bound: knows true remaining session length |

## Metrics

Goodput under SLO; TTFT; TPOT / ITL; P50, P90, P99 latency; SLO attainment; wasted GPU-seconds (recompute + lost work); $/token relative to on-demand; planned and unplanned migration counts and downtime; fraction of requests hit by unplanned loss.

## Traces

Cross one **availability** trace with one **workload** trace. See `traces/README.md` for sources and licences (SpotLake, Google 2019, Failure Trace Archive, SETI@home/BOINC; Azure LLM Inference 2023, BurstGPT, Mooncake).

## Ablations

Hazard estimator family (KM / Weibull / hierarchical / boosted with features) × migration trigger parameters × output-length estimate noise × workload mix.

## Simulator validation

Record real churn on a small spot cluster and a few consumer machines (Phase 4), replay it through the simulator, and publish the fidelity plot. Prior art did the same on 12× g4dn (SpotServe) and g6/g6e (ShuntServe).
