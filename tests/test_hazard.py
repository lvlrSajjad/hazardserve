import numpy as np

from hazardserve.hazard import HazardModel, kaplan_meier


def test_km_monotone_and_bounded():
    d = np.array([10, 20, 30, 40, 50], dtype=float)
    c = kaplan_meier(d, np.ones(5, dtype=bool))
    s = np.asarray(c.S(np.linspace(0, 100, 50)))
    assert np.all(np.diff(s) <= 1e-12)
    assert 0 <= s.min() and s.max() <= 1.0


def test_conditional_survival_uses_age():
    # Decreasing-hazard node: the longer it has survived, the safer the next 60 s.
    d = np.random.default_rng(0).weibull(0.6, 400) * 600
    c = kaplan_meier(d, np.ones_like(d, dtype=bool))
    assert c.conditional_fail_prob(60, age=1800) < c.conditional_fail_prob(60, age=1)


def test_pooled_fallback_for_new_node():
    h = HazardModel(min_sessions=3)
    for t, length in enumerate([20.0, 45.0, 70.0, 130.0, 300.0]):
        h.on_join("a", t * 1000.0)
        h.on_leave("a", t * 1000.0 + length)
    h.on_join("newcomer", 1000.0)
    p = h.fail_prob("newcomer", 1010.0, horizon=30.0)
    assert 0.0 < p < 1.0
