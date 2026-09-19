"""Run all policies on identical synthetic churn traces and print a table.

    python examples/compare_policies.py --seeds 3 --hours 6
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from hazardserve import (
    HazardAwarePolicy,
    HazardModel,
    OraclePolicy,
    RandomPolicy,
    ReactivePolicy,
    Simulator,
)


def run(policy_name: str, seed: int, hours: float, **kw) -> dict:
    hazard = HazardModel()
    if policy_name == "hazard_aware":
        policy = HazardAwarePolicy(hazard)
    elif policy_name == "reactive_fastest":
        policy = ReactivePolicy()
    elif policy_name == "random":
        policy = RandomPolicy(seed)
    elif policy_name == "oracle":
        policy = None  # needs the simulator handle
    else:
        raise ValueError(policy_name)
    sim = Simulator(policy, hazard, duration=hours * 3600, warmup=min(2 * 3600, hours * 1800), seed=seed, **kw)
    if policy_name == "oracle":
        sim.policy = OraclePolicy(sim.true_remaining)
    return sim.run()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--hours", type=float, default=4.0)
    ap.add_argument("--json", type=str, default="")
    args = ap.parse_args()

    policies = ["random", "reactive_fastest", "hazard_aware", "oracle"]
    keys = [
        "mean_latency_s", "p99_latency_s", "unplanned_migrations",
        "planned_migrations", "wasted_seconds", "completed",
    ]
    results = {}
    for p in policies:
        runs = [run(p, s, args.hours) for s in range(args.seeds)]
        results[p] = {k: float(np.mean([r[k] for r in runs])) for k in keys}

    hdr = f"{'policy':<18}" + "".join(f"{k:>22}" for k in keys)
    print(hdr)
    print("-" * len(hdr))
    for p in policies:
        print(f"{p:<18}" + "".join(f"{results[p][k]:>22.1f}" for k in keys))
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
