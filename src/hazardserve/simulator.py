"""Trace-driven simulator: stateful LLM requests on nodes that come and go.

Time advances in fixed steps. Each node serves one request at a time (a
batching-free simplification; the decision rule does not depend on it).

Node availability is a renewal process: up for a session drawn from that
node's session distribution, down for a gap, repeat. Three node archetypes
give the hazard model something to learn:

  * ``laptop``  - short, highly variable sessions (Weibull shape < 1:
                  decreasing hazard, "the longer it's been idle the safer")
  * ``spot``    - sessions clustered around a typical reclaim time
                  (Weibull shape > 1: increasing hazard)
  * ``server``  - long, rarely interrupted sessions

When a node leaves, every request on it is orphaned: its tokens survive
(they were streamed to the client) but its KV cache does not, so it must be
re-placed and its whole context re-prefilled on the new node.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import numpy as np

from .cost import MigrationCost, NodeSpec, Request
from .hazard import HazardModel
from .policy import HazardAwarePolicy, Policy

ARCHETYPES = {
    #  name    : (decode_tps, prefill_tps, bandwidth B/s, kv B/tok, mem_tokens, session_scale_s, shape, gap_scale_s)
    "laptop": (12.0, 150.0, 4e6, 128 * 1024, 16_000, 600.0, 0.6, 600.0),
    "spot": (40.0, 900.0, 40e6, 128 * 1024, 64_000, 2400.0, 3.0, 300.0),
    "server": (60.0, 1500.0, 100e6, 128 * 1024, 128_000, 8 * 3600.0, 1.5, 120.0),
}


@dataclass
class SimNode:
    spec: NodeSpec
    kind: str
    session_scale: float
    shape: float
    gap_scale: float
    up: bool = False
    next_event: float = 0.0
    session_end: float = math.inf
    running: Active | None = None
    queue: list[Active] = field(default_factory=list)


@dataclass
class Active:
    req: Request
    node: str
    done: int = 0  # output tokens produced so far
    prefilled: bool = False
    prefill_left: float = 0.0  # seconds of prefill/recompute/migration delay remaining
    started: float = 0.0
    hops: int = 0
    unplanned: int = 0
    planned: int = 0
    wasted: float = 0.0  # seconds of work thrown away or spent moving
    last_check: float = -1e9


@dataclass
class Metrics:
    latencies: list[float] = field(default_factory=list)
    unplanned: int = 0
    planned: int = 0
    wasted: float = 0.0
    dropped: int = 0
    completed: int = 0

    def summary(self) -> dict:
        lat = np.array(self.latencies) if self.latencies else np.array([math.nan])
        return {
            "completed": self.completed,
            "dropped": self.dropped,
            "mean_latency_s": float(np.mean(lat)),
            "p50_latency_s": float(np.percentile(lat, 50)),
            "p99_latency_s": float(np.percentile(lat, 99)),
            "unplanned_migrations": self.unplanned,
            "planned_migrations": self.planned,
            "wasted_seconds": round(self.wasted, 1),
        }


class Simulator:
    def __init__(
        self,
        policy: Policy,
        hazard: HazardModel | None,
        n_laptop: int = 30,
        n_spot: int = 10,
        n_server: int = 3,
        arrival_rate: float = 0.6,  # requests / s
        duration: float = 6 * 3600.0,
        warmup: float = 2 * 3600.0,
        dt: float = 1.0,
        seed: int = 0,
        migration: MigrationCost | None = None,
    ):
        self.policy = policy
        self.hazard = hazard
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        self.dt, self.duration, self.warmup, self.lam = dt, duration, warmup, arrival_rate
        self.mig = migration or MigrationCost()
        self.nodes: dict[str, SimNode] = {}
        for kind, n in (("laptop", n_laptop), ("spot", n_spot), ("server", n_server)):
            d, p, bw, kv, mem, sc, sh, gap = ARCHETYPES[kind]
            for i in range(n):
                name = f"{kind}-{i}"
                # per-node jitter so nodes are not identical
                spec = NodeSpec(name, d * self.rng.uniform(0.7, 1.3), p * self.rng.uniform(0.7, 1.3), bw, kv, mem)
                self.nodes[name] = SimNode(spec, kind, sc * self.rng.uniform(0.6, 1.4), sh, gap)
        self.metrics = Metrics()
        self.pending: list[Active] = []  # orphaned, waiting for a node
        self._rid = 0

    # ---- churn --------------------------------------------------------
    def _draw_session(self, n: SimNode) -> float:
        return float(self.np_rng.weibull(n.shape) * n.session_scale) + 1.0

    def _draw_gap(self, n: SimNode) -> float:
        return float(self.np_rng.exponential(n.gap_scale)) + 1.0

    def true_remaining(self, name: str, now: float) -> float:
        n = self.nodes[name]
        return n.session_end - now if n.up else 0.0

    def _churn(self, now: float) -> None:
        for name, n in self.nodes.items():
            if now < n.next_event:
                continue
            if n.up:  # leave
                n.up = False
                n.next_event = now + self._draw_gap(n)
                n.session_end = math.inf
                if self.hazard:
                    self.hazard.on_leave(name, now)
                for a in ([n.running] if n.running else []) + n.queue:
                    a.unplanned += 1
                    # decode work since last prefill is kept (tokens streamed); the KV is lost.
                    a.prefilled = False
                    a.prefill_left = 0.0
                    self.pending.append(a)
                n.running, n.queue = None, []
            else:  # join
                n.up = True
                s = self._draw_session(n)
                n.next_event = now + s
                n.session_end = now + s
                if self.hazard:
                    self.hazard.on_join(name, now)

    # ---- helpers ------------------------------------------------------
    def _up_specs(self) -> dict[str, NodeSpec]:
        return {k: n.spec for k, n in self.nodes.items() if n.up}

    def _loads(self) -> dict[str, float]:
        out = {}
        for k, n in self.nodes.items():
            if not n.up:
                continue
            t = 0.0
            for a in ([n.running] if n.running else []) + n.queue:
                t += (a.req.expected_output_tokens - a.done) / n.spec.decode_tps + a.prefill_left
            out[k] = t
        return out

    def _ctx(self, a: Active) -> int:
        return a.req.prompt_tokens + a.done

    def _assign(self, a: Active, dest: str, delay: float, now: float) -> None:
        a.node = dest
        a.prefilled = False
        a.prefill_left = delay
        a.hops += 1
        n = self.nodes[dest]
        if n.running is None:
            n.running = a
        else:
            n.queue.append(a)

    # ---- arrivals -----------------------------------------------------
    def _arrivals(self, now: float) -> None:
        k = self.np_rng.poisson(self.lam * self.dt)
        for _ in range(k):
            self._rid += 1
            prompt = int(self.np_rng.lognormal(6.0, 0.8))  # ~400 tokens median
            out_true = int(self.np_rng.lognormal(6.3, 1.0)) + 1  # ~545 median, heavy tail (agentic/long-form)
            out_est = int(out_true * self.np_rng.lognormal(0.0, 0.4)) + 1  # noisy estimate
            req = Request(self._rid, prompt, out_est, out_true, now)
            a = Active(req, node="", started=now)
            self.pending.append(a)

    def _place_pending(self, now: float) -> None:
        specs, loads = self._up_specs(), self._loads()
        still = []
        for a in self.pending:
            if not specs:
                still.append(a)
                continue
            pl = self.policy.place(a.req, specs, loads, now)
            if pl is None:
                still.append(a)
                continue
            ctx = self._ctx(a)
            if a.hops == 0:
                delay = a.req.prompt_tokens / specs[pl.node].prefill_tps
            else:  # unplanned recovery: recompute whole context
                delay = self.mig.unplanned(ctx, specs[pl.node])
                a.wasted += delay
            self._assign(a, pl.node, delay, now)
            rem = (a.req.expected_output_tokens - a.done) / specs[pl.node].decode_tps
            loads[pl.node] = loads.get(pl.node, 0.0) + delay + rem
        self.pending = still

    # ---- pre-emptive migration ---------------------------------------
    def _maybe_migrate(self, now: float) -> None:
        if not isinstance(self.policy, HazardAwarePolicy):
            return
        specs, loads = self._up_specs(), self._loads()
        for name, n in self.nodes.items():
            a = n.running
            if not n.up or a is None or not a.prefilled:
                continue
            if now - a.last_check < self.policy.check_interval:
                continue
            a.last_check = now
            own = (a.req.expected_output_tokens - a.done) / n.spec.decode_tps
            dec = self.policy.should_migrate(
                a.req, name, self._ctx(a), a.done, specs, loads, now, own_load=own, hops=a.planned
            )
            if dec is None:
                continue
            dest, _method, cost = dec
            n.running = n.queue.pop(0) if n.queue else None
            a.planned += 1
            a.wasted += cost
            self._assign(a, dest, cost, now)
            loads[name] = max(loads.get(name, 0.0) - own, 0.0)
            loads[dest] = loads.get(dest, 0.0) + own + cost

    # ---- serving ------------------------------------------------------
    def _serve(self, now: float) -> None:
        for n in self.nodes.values():
            if not n.up or n.running is None:
                continue
            a = n.running
            if not a.prefilled:
                a.prefill_left -= self.dt
                if a.prefill_left <= 0:
                    a.prefilled = True
                continue
            a.done += max(int(n.spec.decode_tps * self.dt), 1)
            if a.done >= a.req.true_output_tokens:
                self._complete(a, now)
                n.running = n.queue.pop(0) if n.queue else None

    def _complete(self, a: Active, now: float) -> None:
        if a.started >= self.warmup:
            self.metrics.completed += 1
            self.metrics.latencies.append(now - a.started)
            self.metrics.unplanned += a.unplanned
            self.metrics.planned += a.planned
            self.metrics.wasted += a.wasted

    # ---- main loop ----------------------------------------------------
    def run(self) -> dict:
        now = 0.0
        # stagger initial node events
        for n in self.nodes.values():
            n.next_event = self.rng.uniform(0, 60)
        while now < self.duration:
            self._churn(now)
            self._arrivals(now)
            self._place_pending(now)
            self._maybe_migrate(now)
            self._serve(now)
            now += self.dt
        # requests still pending at the end are dropped from stats
        self.metrics.dropped = sum(1 for a in self.pending if a.started >= self.warmup)
        return self.metrics.summary()
