# The problem

!!! note "Phase 0 deliverable"
    This page is the formal statement the paper will open with. Edit freely; keep it short.

## Setting

A set of nodes $\mathcal{N}$ serve autoregressive LLM requests. Node $i$ has decode rate $d_i$ (tok/s), prefill rate $p_i$ (tok/s), bandwidth $B_i$ and KV capacity. Node $i$ is *up* for a session of random length $S_i$, then *down* for a gap, then up again. We do not assume sessions are exponential: laptops have decreasing hazard (the longer idle, the safer), spot instances often have increasing hazard (reclaims cluster around a typical age).

A request $r$ arrives with prompt length $P_r$, unknown true output length, and a (noisy) estimate $\hat{L}_r$. While decoding on node $i$ it accumulates context $c_r(t) = P_r + \text{tokens generated}$ and an equally large KV cache that exists **only on node $i$**. Generated tokens are streamed to the client, so they are never lost; the KV cache is.

## Two kinds of migration

- **Unplanned** (node gone): the only option is to re-prefill $c_r$ on another node. Cost $\approx c_r / p_j$ plus a fixed stall penalty $\sigma$.
- **Planned** (source alive): choose the cheaper of KV transfer ($c_r \cdot \text{kv\_bytes} / \min(B_i,B_j)$) or recompute ($c_r/p_j$), each with a fixed overhead.

## Hazard

Let $S_i$ have survival $\bar F_i(t)$. The scheduler needs the **conditional** survival given the node's current uptime $a_i$:

$$
\bar F_i(t \mid a_i) = \frac{\bar F_i(a_i + t)}{\bar F_i(a_i)}, \qquad f_i(t \mid a_i) = -\frac{d}{dt}\bar F_i(t \mid a_i).
$$

Estimated per node from its own completed sessions (Kaplan-Meier, censoring the live session), with a pooled estimate as the prior for nodes with little history.

## Objective

Minimise expected request completion time (equivalently: maximise goodput under an SLO) subject to capacity, where completion time includes queueing, service, planned migration cost, and unplanned recovery cost. We do **not** assume we can observe the true remaining session length; the `oracle` baseline that can is an upper bound, not a competitor.

## Non-goals

Model training resilience (Bamboo, Parcae, Oobleck), disaggregated prefill/decode transport (Mooncake, DistServe), and incentive or trust layers for volunteer nodes are all out of scope.
