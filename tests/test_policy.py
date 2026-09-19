from hazardserve import HazardAwarePolicy, HazardModel, NodeSpec, Request


def _nodes():
    return {
        "flaky": NodeSpec("flaky", 20, 400, 1e7, 131072, 50_000),
        "solid": NodeSpec("solid", 20, 400, 1e7, 131072, 50_000),
    }


def test_placement_prefers_safer_node_at_equal_speed():
    h = HazardModel(min_sessions=3)
    now = 0.0
    # flaky: 30 s sessions; solid: 10 h sessions
    for _ in range(6):
        h.on_join("flaky", now)
        now += 30
        h.on_leave("flaky", now)
        now += 5
        h.on_join("solid", now)
        now += 36000
        h.on_leave("solid", now)
        now += 5
    h.on_join("flaky", now)
    h.on_join("solid", now)
    p = HazardAwarePolicy(h)
    req = Request(1, 500, 600, 600, now)
    pl = p.place(req, _nodes(), {}, now)
    assert pl.node == "solid"


def test_no_migration_when_risk_is_negligible():
    h = HazardModel()
    now = 0.0
    h.on_join("flaky", now)
    h.on_join("solid", now)
    p = HazardAwarePolicy(h)
    req = Request(1, 500, 600, 600, now)
    assert p.should_migrate(req, "solid", 700, 200, _nodes(), {}, now) is None
