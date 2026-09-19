# Prior art and novelty

Status as of September 2026. Re-run an arXiv sweep before freezing the paper's related-work section; several entries below are 2026 preprints and the area is moving fast.

## Verdict

No published system combines all three of:

1. a **predictive per-node survival/hazard model** estimated from that node's session history and conditioned on current uptime;
2. a **single expected-completion-cost function** driving both new-request placement and pre-emptive migration of running stateful requests *while the source is still alive*;
3. an explicit **KV-transfer vs recompute-from-tokens** choice per migration.

The three ingredients exist separately. The nearest neighbours each hold roughly two.

## Scorecard

| Work | (1) per-node hazard | (2) unified placement + pre-emptive migration | (3) transfer vs recompute | Domain |
|---|---|---|---|---|
| SpotServe, ASPLOS'24, arXiv 2311.15566 | no; lists "instance availability prediction" as future work | no; reactive migration + stateful recovery in the grace period | recompute-oriented recovery | LLM on preemptible instances |
| ShuntServe, 2026, arXiv 2606.18600 | no | no; reactive + on-demand fallback | measured both on g6/g6e; per-request hybrid selection named as future work | heterogeneous spot clusters |
| SkyServe (SpotHedge), EuroSys'25, arXiv 2411.01438 | no; replica-level hedging across failure domains | no; provisioning + abort/retry | no (aborts and re-sends) | online serving |
| SkyNomad, 2026, arXiv 2601.06520 | **yes**: survival on instance age, hazard rate, conditional remaining lifetime | partial: unified monetary + migration cost, but batch jobs, no request-level migration | no | AI **batch** jobs |
| Pallas, 2026, arXiv 2608.16477 | no; mobility/handover prediction | no; migration only | **yes**: prefix prefill + suffix KV stream | AI-RAN LLM under mobility |
| ctHO, 2026, arXiv 2603.28018 | no | no; migration only, single delay objective | **yes**: joint prefill amount and KV backhaul rate | edge LLM handover (simulation only) |
| Llumnix, OSDI'24, arXiv 2406.03243 | no | no; reactive live migration for load balance / de-frag / priority | KV transfer (append-only pipelining) | multi-instance vLLM |
| ServerlessLLM, OSDI'24, arXiv 2401.14351 | no | no | token-based migration; recompute at destination | serverless inference |
| DéjàVu, ICML'24 | no | no; KV streaming replication for fault tolerance | KV streaming | disaggregated serving |
| ConServe, ICML'26, arXiv 2410.01228 | no | no; preemption-tolerant harvesting | per-token incremental KV checkpoint to host | GPU harvesting |
| Petals, ACL'23, arXiv 2209.01188 | no | no; DHT rebalancing, reroute after disconnect | recompute | volunteer / internet-scale |
| Parallax (Gradient), 2025, arXiv 2509.26182 | no; selects on availability, compute, latency at request time | no | – | decentralized heterogeneous nodes |
| Helix, ASPLOS'25, arXiv 2406.01566; HexGen, ICML'24 | no; static heterogeneous placement | no | – | heterogeneous / geo-distributed |
| Bamboo NSDI'23, Parcae NSDI'24, Oobleck SOSP'23 | some proactive redundancy | – | – | spot **training**, not stateful serving |
| Mooncake, DistServe OSDI'24, Splitwise ISCA'24, llm-d P2P KV | – | – | transport substrate we reuse | disaggregated serving |

## What we must differentiate against

- **SpotServe / ShuntServe:** we are predictive and unify placement with migration; ShuntServe's own future-work paragraph describes our per-request transfer-vs-recompute decision.
- **SkyNomad:** we target stateful interactive decoding with request-level KV migration; we learn the hazard per node from session history rather than region-level lifetime for batch jobs.
- **Pallas / ctHO:** our trigger is a per-node survival hazard, not a mobility prediction, and we cover placement, not just the handover.
- **Llumnix:** we reuse its migration mechanism; our contribution is *when* and *where*, driven by hazard.

## Borrowable prediction literature

- Desktop grids / volunteer computing: Javadi, Kondo, Vincent, Anderson, "Discovering statistical models of availability in large distributed systems: an empirical study of SETI@home," IEEE TPDS 22(11), 2011; Kondo, Andrzejak, Anderson, "On correlated availability in Internet-distributed systems," Grid 2008; Heien, Kondo, Anderson, IEEE TPDS 23(6), 2012. Weibull / hyperexponential fits and semi-Markov host models are direct precedent for per-node survival estimation.
- Spot interruption prediction: SpotLake (IISWC'22, arXiv 2202.02973) archives AWS placement scores and interruption ratios and shows Kaplan-Meier lifetime curves; Cast AI and Spot by NetApp productise survival-style rebalancing (NetApp patent US11915053B2 describes gradient-boosted trees).
- Failure Trace Archive: Javadi, Kondo, Iosup, Epema, JPDC 73(8), 2013.

## Host systems for the reference implementation

- **llm-d Inference Scheduler** (Gateway API Inference Extension Endpoint Picker): Filter → Score → Pick pipeline with YAML-configured scorer plugins; adding a scorer needs no core changes. Best home for the placement rule.
- **vLLM KV-connector API** (`kv_transfer/kv_connector/v1`, LMCache and NIXL connectors, dynamic loading, layer-wise async save/load): where transfer-vs-recompute is actually executed.
- **Llumnix** for a migration-heavy prototype; **Parallax / Petals** for the volunteer demo; SGLang, Ray Serve LLM, Dynamo, SkyPilot as secondary targets.

## The adoption model

Kazemi & Sullivan, "One Millisecond Face Alignment with an Ensemble of Regression Trees," CVPR 2014 (DOI 10.1109/CVPR.2014.241), became a standard because the method was simple, fast, and shipped as a reference implementation in dlib (Davis King), later wrapped by OpenCV. The paper alone did not do it; the drop-in implementation did. Hence Phase 3.
