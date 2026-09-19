"""Cost model: how long things take, and how much a failure wastes.

Units are seconds throughout. Everything here is deliberately simple and
overridable; the point of the paper is the *decision rule*, not the
calibration constants.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NodeSpec:
    name: str
    decode_tps: float  # tokens/s during decode
    prefill_tps: float  # tokens/s during prefill
    bandwidth_bps: float  # bytes/s to/from other nodes (WAN-ish)
    kv_bytes_per_token: float  # KV cache footprint per token (all layers)
    mem_tokens: int  # KV capacity in tokens


@dataclass
class Request:
    rid: int
    prompt_tokens: int
    expected_output_tokens: int  # scheduler's estimate (may be wrong)
    true_output_tokens: int  # ground truth, only the simulator sees this
    arrival: float


@dataclass
class MigrationCost:
    """Cost in seconds of moving a request with `ctx` tokens of context."""

    transfer_overhead: float = 0.5  # connection setup etc.
    recompute_overhead: float = 0.2

    def kv_transfer(self, ctx: int, src: NodeSpec, dst: NodeSpec) -> float:
        bw = min(src.bandwidth_bps, dst.bandwidth_bps)
        return self.transfer_overhead + ctx * src.kv_bytes_per_token / bw

    def recompute(self, ctx: int, dst: NodeSpec) -> float:
        # Tokens are tiny; cost is re-prefilling the whole context on dst.
        return self.recompute_overhead + ctx / dst.prefill_tps

    def planned(self, ctx: int, src: NodeSpec, dst: NodeSpec) -> tuple[float, str]:
        """Cheapest *planned* migration (source still alive → both options)."""
        a, b = self.kv_transfer(ctx, src, dst), self.recompute(ctx, dst)
        return (a, "kv_transfer") if a < b else (b, "recompute")

    def unplanned(self, ctx: int, dst: NodeSpec) -> float:
        """Source is gone: only recompute-from-tokens is possible."""
        return self.recompute(ctx, dst)


def service_time(req: Request, node: NodeSpec, done_tokens: int = 0) -> float:
    """Remaining time to finish `req` on `node`, from the scheduler's estimate."""
    remaining = max(req.expected_output_tokens - done_tokens, 0)
    prefill = 0.0 if done_tokens > 0 else req.prompt_tokens / node.prefill_tps
    return prefill + remaining / node.decode_tps
