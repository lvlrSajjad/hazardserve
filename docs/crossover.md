# Transfer vs recompute

!!! note "Phase 0 deliverable"
    Design note §4. The constants on this page are **assumed**, not measured. Phase 4 replaces every one of them with a number from real hardware.

A *planned* migration (source still alive) has two ways to put a request's context on the destination:

$$
\text{transfer}(c) = O_t + \frac{c \cdot \text{kv\_bytes}}{\min(B_i, B_j)},
\qquad
\text{recompute}(c) = O_r + \frac{c}{p_j}.
$$

Both are affine in the context length $c$, so they cross at most once:

$$
c^\star = \frac{O_t - O_r}{\dfrac{1}{p_j} - \dfrac{\text{kv\_bytes}}{\min(B_i, B_j)}}.
$$

The denominator is the per-token saving from shipping a token's KV instead of re-prefilling it. **If it is negative, transfer never wins** — no context is long enough — which is the WAN regime and the reason recompute is the default here. That matches ShuntServe's measurement (recompute wins except for very long contexts) and is the same argument ServerlessLLM makes for token-based migration.

## What the model says

`hazardserve.crossover.crossover_table` evaluates $c^\star$ per bandwidth class:

| destination prefill | WAN (100 Mbit/s) | LAN (10 GbE) | RDMA (200 Gbit/s) |
|---|---|---|---|
| datacentre GPU, 3000 tok/s | never | ≈ 1 300 tokens | ≈ 900 tokens |
| edge / consumer GPU, 250 tok/s | never | ≈ 80 tokens | ≈ 75 tokens |

(128 KB of KV per token; $O_t = 0.5$ s, $O_r = 0.2$ s.)

Two things to carry into the paper:

1. **Bandwidth is not the only axis.** The crossover moves with the destination's *prefill rate* just as much. A slow prefill engine makes shipping KV attractive at short contexts; a fast one pushes the crossover out by an order of magnitude. Prior work states the crossover as a function of context length alone.
2. **The bottleneck end decides.** The cost model uses $\min(B_i, B_j)$, so a fast source cannot rescue a slow destination — the relevant regime for volunteer and edge fleets, where transfer effectively never wins and the policy degenerates to recompute-only.

## What Phase 4 must measure

- $O_t$ and $O_r$ on a real KV connector (LMCache / NIXL), not assumed constants.
- Effective inter-node bandwidth under load, not link rate.
- Per-token KV footprint for the models actually served.
- Whether the destination can prefill *while* the source keeps decoding. If it can, the planned-migration cost charged to $\Delta T$ in [the algorithm](algorithm.md) is too pessimistic — see the open question in `notebooks/derive-trigger.ipynb` §3.

## Reference

`src/hazardserve/crossover.py`; tests in `tests/test_crossover.py` pin the model to `MigrationCost`, which is what the policy actually calls.
