"""Hazard-aware placement and pre-emptive migration.

One expected-cost function drives both decisions.

For a request r currently holding `ctx` tokens of context, with remaining
service time T on node i, define the *expected completion cost*

    E_i(r) = T_i                                         (service time)
           + ∫_0^{T_i} f_i(t | age_i) · U_i(t) dt          (expected unplanned loss)

where f_i(· | age) is the node's conditional session-length density and
U_i(t) is what a failure t seconds from now costs: the unplanned migration
(recompute the context accumulated by then on the best fallback node) plus
a fixed SLO penalty for the visible stall.

    Placement:  argmin_i  E_i(r)                     over feasible nodes
    Migration:  move r from i to j iff
                E_i(r) - ( C_planned(i→j) + E_j(r) ) > hysteresis

Because the same E is used for both, the policy never migrates *into* a node
it would not have placed on, and it migrates *early*, while the source is
still alive and cheap KV transfer is an option, instead of after the fact
when only recompute is left.

Baselines (Reactive, Random) share the interface so the simulator can swap
them in.
"""
from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .cost import MigrationCost, NodeSpec, Request, service_time
from .hazard import HazardModel


@dataclass
class Placement:
    node: str
    expected_cost: float


class Policy:
    name = "base"

    def place(self, req: Request, nodes: dict[str, NodeSpec], loads: dict[str, float], now: float) -> Placement | None:
        raise NotImplementedError

    def should_migrate(
        self,
        req: Request,
        current: str,
        ctx: int,
        done: int,
        nodes: dict[str, NodeSpec],
        loads: dict[str, float],
        now: float,
        own_load: float = 0.0,
        hops: int = 0,
    ) -> tuple[str, str, float] | None:
        """Return (destination, method, cost) or None to stay."""
        return None


class HazardAwarePolicy(Policy):
    name = "hazard_aware"

    def __init__(
        self,
        hazard: HazardModel,
        migration: MigrationCost | None = None,
        slo_penalty: float = 2.0,
        hysteresis: float = 2.0,
        check_interval: float = 5.0,
        integral_steps: int = 16,
        max_hops: int = 3,
        min_remaining: float = 5.0,
    ):
        self.max_hops = max_hops
        self.min_remaining = min_remaining
        self.hazard = hazard
        self.mig = migration or MigrationCost()
        self.slo_penalty = slo_penalty
        self.hysteresis = hysteresis
        self.check_interval = check_interval
        self.steps = integral_steps

    # ---- the one cost function -------------------------------------
    def expected_cost(
        self,
        req: Request,
        node: str,
        ctx: int,
        done: int,
        nodes: dict[str, NodeSpec],
        loads: dict[str, float],
        now: float,
        fallback: NodeSpec | None = None,
        own_load: float = 0.0,
    ) -> float:
        """E = queue wait + service time + expected unplanned loss.

        own_load: work of this very request already counted in loads[node]
        (non-zero when evaluating the node the request is currently on).
        """
        spec = nodes[node]
        wait = max(loads.get(node, 0.0) - own_load, 0.0)
        svc = service_time(req, spec, done)
        T = wait + svc
        fb = fallback or self._fallback(node, nodes)
        remaining_out = max(req.expected_output_tokens - done, 0)

        def unplanned_loss(ts: np.ndarray) -> np.ndarray:
            # Context accumulated if the node dies at time t (decode starts after wait).
            gained = np.clip((ts - wait) * spec.decode_tps, 0, remaining_out)
            ctx_t = ctx + gained
            if fb is None:
                return np.full_like(ts, T + self.slo_penalty)
            return self.mig.recompute_overhead + ctx_t / fb.prefill_tps + self.slo_penalty

        loss = self.hazard.expected_loss_integral(node, now, T, unplanned_loss, self.steps)
        return T + loss

    def cost_components(self, req, node, ctx, done, nodes, loads, now, own_load=0.0) -> tuple[float, float]:
        """(deterministic time T, expected unplanned loss L) with E = T + L."""
        spec = nodes[node]
        wait = max(loads.get(node, 0.0) - own_load, 0.0)
        T = wait + service_time(req, spec, done)
        E = self.expected_cost(req, node, ctx, done, nodes, loads, now, own_load=own_load)
        return T, E - T

    def _fallback(self, exclude: str, nodes: dict[str, NodeSpec]) -> NodeSpec | None:
        others = [n for k, n in nodes.items() if k != exclude]
        return max(others, key=lambda n: n.prefill_tps) if others else None

    # ---- decisions ---------------------------------------------------
    def place(self, req, nodes, loads, now):
        feasible = [k for k, n in nodes.items() if n.mem_tokens >= req.prompt_tokens + req.expected_output_tokens]
        if not feasible:
            return None
        costs = {k: self.expected_cost(req, k, req.prompt_tokens, 0, nodes, loads, now) for k in feasible}
        best = min(costs, key=costs.get)
        return Placement(best, costs[best])

    def should_migrate(self, req, current, ctx, done, nodes, loads, now, own_load=0.0, hops=0):
        if current not in nodes or hops >= self.max_hops:
            return None
        if service_time(req, nodes[current], done) < self.min_remaining:
            return None
        t_stay, l_stay = self.cost_components(req, current, ctx, done, nodes, loads, now, own_load=own_load)
        best = None
        for k, spec in nodes.items():
            if k == current or spec.mem_tokens < ctx + (req.expected_output_tokens - done):
                continue
            c_mig, method = self.mig.planned(ctx, nodes[current], spec)
            t_dest, l_dest = self.cost_components(req, k, ctx, done, nodes, loads, now)
            # Migration must be *hazard-motivated*: the risk it removes must pay
            # for the move, and it must not make the request materially slower.
            risk_gain = l_stay - (c_mig + l_dest)
            time_delta = (t_dest + c_mig) - t_stay
            if risk_gain > self.hysteresis and time_delta < self.hysteresis:
                score = risk_gain - max(time_delta, 0.0)
                if best is None or score > best[0]:
                    best = (score, k, method, c_mig)
        if best:
            return best[1], best[2], best[3]
        return None


class ReactivePolicy(Policy):
    """SpotServe/Petals-style: pick the fastest node, recover only after failure."""

    name = "reactive_fastest"

    def place(self, req, nodes, loads, now):
        feasible = [k for k, n in nodes.items() if n.mem_tokens >= req.prompt_tokens + req.expected_output_tokens]
        if not feasible:
            return None
        best = min(feasible, key=lambda k: service_time(req, nodes[k]) + loads.get(k, 0.0))
        return Placement(best, service_time(req, nodes[best]))


class RandomPolicy(Policy):
    name = "random"

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def place(self, req, nodes, loads, now):
        feasible = [k for k, n in nodes.items() if n.mem_tokens >= req.prompt_tokens + req.expected_output_tokens]
        if not feasible:
            return None
        k = self.rng.choice(feasible)
        return Placement(k, service_time(req, nodes[k]))


class OraclePolicy(Policy):
    """Upper bound: knows each node's true remaining session length.

    Not implementable in practice; shows how much headroom hazard estimation
    leaves on the table.
    """

    name = "oracle"

    def __init__(self, remaining_fn: Callable[[str, float], float]):
        self.remaining = remaining_fn

    def place(self, req, nodes, loads, now):
        feasible = [k for k, n in nodes.items() if n.mem_tokens >= req.prompt_tokens + req.expected_output_tokens]
        if not feasible:
            return None
        safe = [k for k in feasible if self.remaining(k, now) > service_time(req, nodes[k]) + loads.get(k, 0.0)]
        pool = safe or feasible
        best = min(pool, key=lambda k: service_time(req, nodes[k]) + loads.get(k, 0.0))
        return Placement(best, service_time(req, nodes[best]))
