# The algorithm

One expected-cost function, two decisions.

## Expected completion cost

For request $r$ currently holding context $c$ on node $i$ with remaining (estimated) service time $T_i$ including queue wait:

$$
E_i(r) \;=\; \underbrace{T_i}_{\text{time}} \;+\; \underbrace{\int_0^{T_i} f_i(t\mid a_i)\, U_i(t)\, dt}_{L_i,\ \text{expected unplanned loss}}
$$

with

$$
U_i(t) \;=\; \frac{c + \min\!\big(d_i\,(t-w_i)^+,\ \hat L_r - \text{done}\big)}{p_{\text{fb}}} + \text{overhead} + \sigma
$$

the recompute cost of the context that will have accumulated by time $t$ on the best fallback node $\text{fb}$, plus stall penalty $\sigma$. The integral is a 16-cell Riemann sum over the conditional survival curve; it costs microseconds.

## Decision 1: placement

$$
i^\star = \arg\min_{i\ \text{feasible}} E_i(r).
$$

At equal speed this prefers the node with the lower conditional hazard over the request's horizon. It automatically prefers a laptop that has been idle for six hours over one that woke up a minute ago, and a fresh spot instance over one approaching its typical reclaim age.

## Decision 2: pre-emptive migration

Every `check_interval` seconds, for the running request on node $i$, and for each candidate $j$:

$$
\text{risk\_gain} = L_i - \big(C_{\text{planned}}(i\to j) + L_j\big), \qquad
\Delta T = (T_j + C_{\text{planned}}) - T_i .
$$

Migrate to the best $j$ iff $\text{risk\_gain} > h$ **and** $\Delta T < h$, with hysteresis $h$. Guards: at most `max_hops` planned moves per request; never move a request with less than `min_remaining` seconds of work left.

!!! tip "Why hazard-motivated only"
    An earlier version migrated whenever $E_j + C < E_i$. That turns the migration path into a load balancer with noisy inputs and it thrashed. Restricting the trigger to *risk removal* keeps migrations rare and makes each one attributable to the hazard model, which is the claim we want to test.

## Decision 3: how to migrate

$C_{\text{planned}} = \min(\text{KV transfer}, \text{recompute})$. Over WAN-class bandwidth recompute almost always wins; over NVLink/RDMA transfer wins for long contexts. The crossover is a hardware measurement (Phase 4), not a modelling choice.

## Reference

`src/hazardserve/policy.py`, class `HazardAwarePolicy`. Everything else in the repo exists to test this class.
