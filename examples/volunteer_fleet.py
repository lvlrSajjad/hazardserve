"""Volunteer-only fleet: 45 laptops, no servers. Churn dominates.

    python examples/volunteer_fleet.py --seeds 3 --hours 2
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402

from hazardserve import HazardAwarePolicy, HazardModel, OraclePolicy, ReactivePolicy, Simulator  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--hours", type=float, default=2.0)
    ap.add_argument("--json", type=str, default="")
    args = ap.parse_args()
    keys = [
        "mean_latency_s", "p99_latency_s", "unplanned_migrations",
        "planned_migrations", "wasted_seconds", "completed",
    ]
    results = {}
    for name in ["reactive_fastest", "hazard_aware", "oracle"]:
        runs = []
        for seed in range(args.seeds):
            h = HazardModel()
            pol = {
                "reactive_fastest": ReactivePolicy(),
                "hazard_aware": HazardAwarePolicy(h, hysteresis=1.0),
                "oracle": None,
            }[name]
            sim = Simulator(pol, h, n_laptop=45, n_spot=0, n_server=0, arrival_rate=0.15,
                            duration=args.hours * 3600, warmup=min(2400, args.hours * 1800), seed=seed)
            if name == "oracle":
                sim.policy = OraclePolicy(sim.true_remaining)
            runs.append(sim.run())
        results[name] = {k: float(np.mean([r[k] for r in runs])) for k in keys}
    hdr = f"{'policy':<18}" + "".join(f"{k:>22}" for k in keys)
    print(hdr)
    print("-" * len(hdr))
    for p, r in results.items():
        print(f"{p:<18}" + "".join(f"{r[k]:>22.1f}" for k in keys))
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
