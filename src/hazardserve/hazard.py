"""Per-node availability hazard estimation.

A *node* is anything that can disappear mid-request: a spot instance, a
volunteer laptop, an edge device. We model each node's session length
(time from join to leave) as a random variable and estimate its survival
function S(t) = P(session length > t) from that node's own history, falling
back to a pooled estimate when history is thin.

The quantity the scheduler actually needs is the *conditional* survival:

    S(t | a) = P(session lasts at least a + t | it has already lasted a)
             = S(a + t) / S(a)

which is what makes the difference between "this laptop just woke up" and
"this laptop has been idle for six hours" (for a decreasing-hazard node the
latter is *safer*, for an increasing-hazard node like a spot instance nearing
its typical reclaim time it is *riskier*).

Estimator: Kaplan-Meier over observed sessions (right-censoring the
currently-open session), with an exponential tail beyond the last
observation so S(t) never hits exactly zero.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class SurvivalCurve:
    """Step-function survival estimate with an exponential tail."""

    times: np.ndarray  # sorted event times
    surv: np.ndarray  # S(times[i]) after the drop at times[i]
    tail_rate: float  # hazard used beyond the last observed time

    def S(self, t: np.ndarray | float) -> np.ndarray | float:
        t = np.asarray(t, dtype=float)
        if self.times.size == 0:
            return np.exp(-self.tail_rate * t)
        idx = np.searchsorted(self.times, t, side="right") - 1
        base = np.where(idx >= 0, self.surv[np.clip(idx, 0, None)], 1.0)
        last_t = self.times[-1]
        beyond = t > last_t
        out = np.where(beyond, self.surv[-1] * np.exp(-self.tail_rate * (t - last_t)), base)
        out = np.maximum(out, 1e-9)  # never exactly zero: keeps conditional survival defined
        return out if out.ndim else float(out)

    def conditional_S(self, t: np.ndarray | float, age: float) -> np.ndarray | float:
        """P(survive t more | already survived age)."""
        s_age = max(float(self.S(age)), 1e-12)
        return np.asarray(self.S(age + np.asarray(t, dtype=float))) / s_age

    def conditional_fail_prob(self, dt: float, age: float) -> float:
        return float(1.0 - self.conditional_S(dt, age))


def kaplan_meier(durations: np.ndarray, observed: np.ndarray) -> SurvivalCurve:
    """Kaplan-Meier estimator.

    durations: session lengths.
    observed:  1 if the session ended (event), 0 if still running (censored).
    """
    durations = np.asarray(durations, dtype=float)
    observed = np.asarray(observed, dtype=bool)
    if durations.size == 0:
        return SurvivalCurve(np.array([]), np.array([]), tail_rate=1.0 / 3600.0)

    order = np.argsort(durations)
    durations, observed = durations[order], observed[order]
    uniq = np.unique(durations[observed])
    surv = []
    s = 1.0
    for t in uniq:
        at_risk = np.sum(durations >= t)
        events = np.sum((durations == t) & observed)
        if at_risk > 0:
            s *= 1.0 - events / at_risk
        surv.append(s)
    surv = np.asarray(surv)
    # Exponential tail: use mean observed session length as scale.
    ev = durations[observed]
    tail_rate = 1.0 / max(float(ev.mean()) if ev.size else 3600.0, 1e-6)
    return SurvivalCurve(uniq, surv, tail_rate)


@dataclass
class NodeHistory:
    sessions: list[float] = field(default_factory=list)  # completed session lengths
    current_start: float | None = None  # wall time this node joined, if up

    def record_join(self, now: float) -> None:
        self.current_start = now

    def record_leave(self, now: float) -> None:
        if self.current_start is not None:
            self.sessions.append(max(now - self.current_start, 1e-6))
            self.current_start = None

    def age(self, now: float) -> float:
        return 0.0 if self.current_start is None else now - self.current_start


class HazardModel:
    """Maintains a survival curve per node with pooled fallback.

    min_sessions: below this many completed sessions the node uses the pooled
    curve (all nodes' sessions), which is the right prior for a newcomer.
    """

    def __init__(self, min_sessions: int = 5):
        self.min_sessions = min_sessions
        self.history: dict[str, NodeHistory] = {}
        self._curves: dict[str, SurvivalCurve] = {}
        self._pooled: SurvivalCurve | None = None
        self._dirty = True

    # ---- bookkeeping -------------------------------------------------
    def _h(self, node: str) -> NodeHistory:
        return self.history.setdefault(node, NodeHistory())

    def on_join(self, node: str, now: float) -> None:
        self._h(node).record_join(now)

    def on_leave(self, node: str, now: float) -> None:
        self._h(node).record_leave(now)
        self._dirty = True

    def age(self, node: str, now: float) -> float:
        return self._h(node).age(now)

    # ---- estimation --------------------------------------------------
    def _refit(self, now: float) -> None:
        all_d, all_o = [], []
        for name, h in self.history.items():
            d = list(h.sessions)
            o = [1] * len(d)
            if h.current_start is not None:  # censor the live session
                d.append(now - h.current_start)
                o.append(0)
            all_d += d
            all_o += o
            if len(h.sessions) >= self.min_sessions:
                self._curves[name] = kaplan_meier(np.array(d), np.array(o))
            else:
                self._curves.pop(name, None)
        self._pooled = kaplan_meier(np.array(all_d), np.array(all_o))
        self._dirty = False

    def curve(self, node: str, now: float) -> SurvivalCurve:
        if self._dirty or self._pooled is None:
            self._refit(now)
        return self._curves.get(node) or self._pooled  # type: ignore[return-value]

    def fail_prob(self, node: str, now: float, horizon: float) -> float:
        """P(node leaves within `horizon` seconds | its current uptime)."""
        return self.curve(node, now).conditional_fail_prob(horizon, self.age(node, now))

    def expected_loss_integral(
        self, node: str, now: float, horizon: float, loss_at, steps: int = 32
    ) -> float:
        """E[loss] = ∫_0^T f(t|age) · loss_at(t) dt, discretised.

        loss_at(ts) maps an array of failure times to costs (vectorised).
        """
        if horizon <= 0:
            return 0.0
        curve = self.curve(node, now)
        age = self.age(node, now)
        grid = np.linspace(0.0, horizon, steps + 1)
        S = np.asarray(curve.conditional_S(grid, age))
        f_mass = S[:-1] - S[1:]  # probability of dying in each cell
        mids = 0.5 * (grid[:-1] + grid[1:])
        return float(np.sum(f_mass * np.asarray(loss_at(mids), dtype=float)))
