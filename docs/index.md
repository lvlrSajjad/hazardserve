# hazardserve

**Hazard-aware placement and pre-emptive migration for stateful LLM inference on unreliable nodes.**

Spot instances get reclaimed. Volunteer laptops get their owners back. Edge devices lose battery. Every one of those events destroys a KV cache mid-generation, and every current serving system treats it as a surprise.

It is not a surprise. Each node has a hazard function you can estimate from its own history, and it depends on how long the node has already been up. hazardserve turns that hazard into one expected-completion-cost function that decides **where to place** a request and **when and how to move** it before the node disappears.

$$
E_i(r) \;=\; T_i \;+\; \int_0^{T_i} f_i(t \mid \text{age}_i)\, U_i(t)\, dt
$$

- [The problem](problem.md): nodes, hazards, requests, state, objective
- [The algorithm](algorithm.md): the cost function and the two decisions it drives
- [Prior art and novelty](related-work.md): what exists, what is new
- [Evaluation plan](evaluation.md): traces, baselines, metrics
- [Roadmap](roadmap.md): phases and pivot thresholds

Code: [github.com/lvlrSajjad/hazardserve](https://github.com/lvlrSajjad/hazardserve). Apache-2.0.
