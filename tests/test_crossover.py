"""The crossover model must agree with the cost model the policy actually calls."""
import math

from hazardserve.cost import MigrationCost, NodeSpec
from hazardserve.crossover import LINK_CLASSES, crossover_table, crossover_tokens


def node(bandwidth_bps: float, prefill_tps: float = 3000.0, kv_bytes_per_token: float = 128e3) -> NodeSpec:
    return NodeSpec(
        name="n",
        decode_tps=40.0,
        prefill_tps=prefill_tps,
        bandwidth_bps=bandwidth_bps,
        kv_bytes_per_token=kv_bytes_per_token,
        mem_tokens=1_000_000,
    )


def test_crossover_matches_migration_cost():
    """Just below c* recompute must win; just above it, transfer."""
    mig = MigrationCost()
    src = dst = node(bandwidth_bps=10e9 / 8)
    c = crossover_tokens(src, dst, mig)
    assert math.isfinite(c) and c > 0
    assert mig.planned(int(c * 0.9), src, dst)[1] == "recompute"
    assert mig.planned(int(c * 1.1), src, dst)[1] == "kv_transfer"


def test_transfer_never_wins_over_a_slow_link():
    """WAN-class: the link is slower per token than prefill, so no context is long enough."""
    src = dst = node(bandwidth_bps=100e6 / 8)
    assert crossover_tokens(src, dst) == math.inf
    mig = MigrationCost()
    assert mig.planned(1_000_000, src, dst)[1] == "recompute"


def test_bandwidth_is_the_bottleneck_end():
    """A fast source cannot rescue a slow destination: min(B_src, B_dst) decides."""
    fast, slow = node(bandwidth_bps=200e9 / 8), node(bandwidth_bps=100e6 / 8)
    assert crossover_tokens(fast, slow) == math.inf


def test_table_covers_every_link_class_and_is_monotone():
    """More bandwidth can only move the crossover earlier."""
    table = crossover_table(node(bandwidth_bps=1e9), kv_bytes_per_token=128e3)
    assert set(table) == {link.name for link in LINK_CLASSES}
    assert table["wan"] == math.inf
    assert table["rdma"] <= table["lan"]
