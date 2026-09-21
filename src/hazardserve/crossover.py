"""Transfer-vs-recompute crossover: when is moving the KV cache cheaper than rebuilding it?

Phase 0 deliverable (design note §4). A *planned* migration has two ways to
put a request's context on the destination node:

    transfer(c)   = O_t + c · kv_bytes_per_token / min(B_src, B_dst)
    recompute(c)  = O_r + c / prefill_tps_dst

Both are affine in the context length `c`, so they cross at most once. Solving
transfer(c) = recompute(c):

    c* = (O_t - O_r) / (1/p_dst - kv_bytes_per_token / B)

The denominator is the per-token saving of shipping a token's KV instead of
re-prefilling it. If it is negative the link is slower per token than the
destination's prefill engine and transfer *never* wins, however long the
context — which is the regime ShuntServe measures over WAN-class links and
the reason recompute is the default here. Over NVLink/RDMA the denominator is
positive and c* is a few thousand tokens.

The constants below are placeholders with stated provenance, not measurements.
Phase 4 replaces every one of them with a number from real hardware; until
then treat `crossover_tokens` as the shape of the answer, not the answer.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from .cost import MigrationCost, NodeSpec

__all__ = ["LinkClass", "LINK_CLASSES", "crossover_tokens", "crossover_table"]


@dataclass(frozen=True)
class LinkClass:
    """A bandwidth regime, with where its number came from.

    `provenance` exists so the paper can say which constants are measured and
    which are assumed. Phase 4 must retire every "assumed" entry.
    """

    name: str
    bandwidth_bps: float
    provenance: str

    def per_token_seconds(self, kv_bytes_per_token: float) -> float:
        return kv_bytes_per_token / self.bandwidth_bps


# Order matters only for display. All three are ASSUMED until Phase 4.
LINK_CLASSES: tuple[LinkClass, ...] = (
    LinkClass("wan", 100e6 / 8, "assumed: ~100 Mbit/s residential/volunteer uplink"),
    LinkClass("lan", 10e9 / 8, "assumed: 10 GbE inside one datacentre/rack"),
    LinkClass("rdma", 200e9 / 8, "assumed: 200 Gbit/s RDMA or NVLink-class fabric"),
)


def crossover_tokens(src: NodeSpec, dst: NodeSpec, mig: MigrationCost | None = None) -> float:
    """Context length (tokens) beyond which KV transfer beats recompute.

    Returns 0.0 when transfer wins at every context length, and `math.inf`
    when it never does. Consistent by construction with
    `MigrationCost.planned`, which is what the policy actually calls.
    """
    mig = mig or MigrationCost()
    bw = min(src.bandwidth_bps, dst.bandwidth_bps)
    per_token_saving = 1.0 / dst.prefill_tps - src.kv_bytes_per_token / bw
    if per_token_saving <= 0.0:
        return math.inf
    return max((mig.transfer_overhead - mig.recompute_overhead) / per_token_saving, 0.0)


def crossover_table(
    dst: NodeSpec,
    kv_bytes_per_token: float,
    mig: MigrationCost | None = None,
    links: tuple[LinkClass, ...] = LINK_CLASSES,
) -> dict[str, float]:
    """`crossover_tokens` for one destination across the bandwidth regimes.

    Feeds the design note's §4 table: one row per link class, the context
    length at which transfer starts winning, `inf` where it never does.
    The link class is applied to *both* ends of the hop, since the cost model
    takes min(B_src, B_dst) and `dst.bandwidth_bps` would otherwise silently
    cap every regime at the destination's own link.
    """
    mig = mig or MigrationCost()
    out: dict[str, float] = {}
    for link in links:
        src = NodeSpec(
            name=f"src@{link.name}",
            decode_tps=dst.decode_tps,
            prefill_tps=dst.prefill_tps,
            bandwidth_bps=link.bandwidth_bps,
            kv_bytes_per_token=kv_bytes_per_token,
            mem_tokens=dst.mem_tokens,
        )
        at_link = replace(dst, bandwidth_bps=link.bandwidth_bps)
        out[link.name] = crossover_tokens(src, at_link, mig)
    return out
