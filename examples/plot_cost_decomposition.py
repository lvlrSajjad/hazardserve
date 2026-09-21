"""The paper's one figure: E = T + L on a decreasing-hazard vs an increasing-hazard node.

Phase 0 deliverable (design note §6). The two nodes are given *identical*
speed, capacity and link, so everything that separates the curves is the
hazard. Read left to right: a laptop that just woke up is the risky place for
a request and a freshly started spot instance is the safe one; twenty minutes
later that has reversed and the same request should go the other way. No
other scheduler input changed.

The left panel is the honest scale — L is a single-digit percentage of E, and
the paper should not pretend otherwise. The right panel is the part the
scheduler can actually act on: T is the same on both nodes, so the placement
decision is entirely L.

This is a Phase 0 sketch drawn from the archetypes, not a result: the session
distributions are synthetic Weibulls. Phase 2 re-cuts the same figure from
trace data, and the claim only becomes evidence there.

Usage:
    python examples/plot_cost_decomposition.py [--out paper/figures/cost-decomposition.png]
"""
from __future__ import annotations

import argparse
from math import gamma
from pathlib import Path

import numpy as np

from hazardserve.cost import NodeSpec, Request
from hazardserve.hazard import HazardModel, NodeHistory
from hazardserve.policy import HazardAwarePolicy

MEAN_SESSION_S = 20 * 60.0
# Weibull shape < 1 → hazard falls with uptime (the laptop that stayed up all
# morning will probably keep staying up). Shape > 1 → hazard rises with uptime
# (the spot instance approaching its typical reclaim age). Same mean, so the
# shape is the only thing that differs.
LAPTOP, SPOT = "laptop  (decreasing hazard)", "spot  (increasing hazard)"
ARCHETYPES = {LAPTOP: 0.6, SPOT: 3.0}
N_SESSIONS = 1200
MAX_AGE_S = 32 * 60.0  # beyond this the Kaplan-Meier tail is carrying the curve, not the data


def sample_sessions(rng: np.random.Generator, shape: float, n: int = N_SESSIONS) -> np.ndarray:
    """Weibull session lengths with a fixed mean, so only the *shape* differs."""
    scale = MEAN_SESSION_S / gamma(1.0 + 1.0 / shape)
    return scale * rng.weibull(shape, n)


def spec(name: str) -> NodeSpec:
    """Identical hardware for both archetypes: the figure isolates hazard."""
    return NodeSpec(
        name=name,
        decode_tps=12.0,
        prefill_tps=250.0,
        bandwidth_bps=100e6 / 8,
        kv_bytes_per_token=128e3,
        mem_tokens=200_000,
    )


def decompose(ages_s: np.ndarray, seed: int = 0) -> tuple[float, dict[str, np.ndarray]]:
    """Return (T, {archetype: L(age)}) — the deterministic time and the risk term."""
    rng = np.random.default_rng(seed)
    history = {name: sample_sessions(rng, shape) for name, shape in ARCHETYPES.items()}
    nodes = {name: spec(name) for name in ARCHETYPES}
    loads = dict.fromkeys(nodes, 0.0)
    req = Request(rid=0, prompt_tokens=4000, expected_output_tokens=2500, true_output_tokens=2500, arrival=0.0)

    now = float(ages_s.max()) + 1.0
    losses = {name: np.zeros_like(ages_s, dtype=float) for name in ARCHETYPES}
    service = 0.0
    for k, age in enumerate(ages_s):
        # A fresh model per age keeps the Kaplan-Meier refit honest: the live
        # session is censored at exactly `age`, which is what the scheduler sees.
        model = HazardModel(min_sessions=5)
        for name, sessions in history.items():
            model.history[name] = NodeHistory(sessions=list(sessions), current_start=now - float(age))
        policy = HazardAwarePolicy(model, slo_penalty=10.0)
        for name in ARCHETYPES:
            service, losses[name][k] = policy.cost_components(req, name, req.prompt_tokens, 0, nodes, loads, now)
    return service, losses


def _crossing(ages_min: np.ndarray, a: np.ndarray, b: np.ndarray) -> float | None:
    """First uptime at which the cheaper node changes."""
    diff = a - b
    idx = np.flatnonzero(np.sign(diff[:-1]) != np.sign(diff[1:]))
    return float(ages_min[idx[0]]) if idx.size else None


def plot(out: Path, seed: int = 0) -> Path:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise SystemExit("matplotlib is required: pip install -e '.[dev]'") from exc

    ages_s = np.linspace(60.0, MAX_AGE_S, 150)
    ages_min = ages_s / 60.0
    service, losses = decompose(ages_s, seed)
    # Greyscale and linestyle only: the figure has to survive a black-and-white
    # print and a reader who skips the caption.
    styles = {LAPTOP: ("-", "//"), SPOT: ("--", "\\\\")}

    fig, (ax_e, ax_l) = plt.subplots(1, 2, figsize=(9.5, 4.0))

    ax_e.axhline(service, color="black", lw=1.0)
    ax_e.text(ages_min[3], service * 0.45, "T   service time,\nidentical on both nodes", fontsize=9)
    for name, L in losses.items():
        line, hatch = styles[name]
        ax_e.plot(ages_min, service + L, line, color="black", lw=1.5)
        ax_e.fill_between(ages_min, service, service + L, facecolor="none", edgecolor="0.45", hatch=hatch, lw=0.0)
    ax_e.set_ylim(0, (service + max(L.max() for L in losses.values())) * 1.25)
    ax_e.set_title("E = T + L", fontsize=11)
    ax_e.set_ylabel("expected completion cost (s)")

    # No hatching on the right: two lines crossing is the whole message, and
    # overlapping fills only muddy it.
    anchor = int(0.62 * len(ages_min))
    for name, L in losses.items():
        line, _ = styles[name]
        ax_l.plot(ages_min, L, line, color="black", lw=1.8)
        ax_l.annotate(name, (ages_min[anchor], L[anchor]), textcoords="offset points",
                      xytext=(8, 10 if name == SPOT else -20), fontsize=9)
    cross = _crossing(ages_min, losses[LAPTOP], losses[SPOT])
    if cross is not None:
        ax_l.axvline(cross, color="black", lw=0.8, ls=":")
        ax_l.annotate("same request,\nbest node flips here", (cross, ax_l.get_ylim()[1]), textcoords="offset points",
                      xytext=(-4, -32), ha="right", fontsize=9)
    ax_l.set_title("L alone — the whole placement decision", fontsize=11)
    ax_l.set_ylabel("expected unplanned loss (s)")

    for ax in (ax_e, ax_l):
        ax.set_xlabel("node uptime so far (minutes)")
        ax.margins(x=0.02)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    fig.tight_layout()

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("paper/figures/cost-decomposition.png"))
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    path = plot(args.out, args.seed)
    print(f"wrote {path} and {path.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
