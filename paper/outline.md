# Hazard-Aware Placement and Pre-emptive Migration for Stateful LLM Inference on Unreliable Nodes

## Abstract (150 words)
Claim: node departure is predictable per node; one expected-cost function unifies placement and pre-emptive migration; reduces unplanned failures and wasted work at equal latency on real spot and volunteer traces; ships as an llm-d scorer and a vLLM KV-connector migration path.

## 1 Introduction
- Stateful decoding + unreliable nodes (spot, volunteer, edge).
- Current systems react; departure is not random; hazard depends on uptime.
- Contributions: (i) formulation, (ii) algorithm, (iii) open simulator + trace suite, (iv) reference implementation, (v) evaluation.

## 2 Background and motivation
- KV cache lifecycle; unplanned vs planned migration; transfer vs recompute.
- Evidence that hazard is non-exponential and node-specific (SETI@home, SpotLake curves). **Figure 1.**

## 3 Problem formulation
- From `docs/problem.md`.

## 4 Algorithm
- Expected completion cost; placement; hazard-motivated migration trigger; transfer-vs-recompute.
- Hazard estimation (KM conditional survival, pooled prior; extensions).
- Complexity: O(nodes × integral cells) per decision.

## 5 Implementation
- Simulator; llm-d scorer plugin; vLLM KV-connector path; Parallax demo.

## 6 Evaluation
- Setup: traces × workloads; baselines; metrics.
- Main results; ablations (estimator, trigger, noise); simulator fidelity vs hardware.

## 7 Related work
- From `docs/related-work.md`, condensed to one page.

## 8 Limitations and future work
- Batching model; sparse-history nodes; adversarial nodes out of scope.

## 9 Conclusion

## Artifact appendix
