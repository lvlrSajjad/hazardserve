from hazardserve import HazardAwarePolicy, HazardModel, ReactivePolicy, Simulator


def test_simulator_runs_and_completes_requests():
    for policy_cls in (ReactivePolicy, HazardAwarePolicy):
        h = HazardModel()
        pol = policy_cls(h) if policy_cls is HazardAwarePolicy else policy_cls()
        sim = Simulator(pol, h, n_laptop=6, n_spot=2, n_server=1, arrival_rate=0.2, duration=600, warmup=120, seed=1)
        r = sim.run()
        assert r["completed"] > 0
        assert r["p99_latency_s"] >= r["p50_latency_s"]
