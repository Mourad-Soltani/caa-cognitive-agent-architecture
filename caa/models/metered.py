"""Cost/latency accounting wrapper. Token counts are estimated (chars/4).

PRICES are PLACEHOLDER USD per 1M tokens (in, out). Replace with real pricing before
trusting any cost number.
"""
from __future__ import annotations
import time
from .client import Model

PRICES = {"fast": (1.0, 5.0), "slow": (3.0, 15.0)}


class Metered:
    def __init__(self, inner: Model, prices: dict | None = None) -> None:
        self.inner, self.prices = inner, prices or PRICES
        self.calls = {"fast": 0, "slow": 0}
        self.tokens_in = self.tokens_out = 0
        self.latency = 0.0
        self.cost = 0.0

    def complete(self, role: str, prompt: str, tier: str = "fast") -> str:
        t0 = time.perf_counter()
        out = self.inner.complete(role, prompt, tier)
        self.latency += time.perf_counter() - t0
        ti, to = len(prompt) // 4, len(out) // 4
        self.calls[tier] = self.calls.get(tier, 0) + 1
        self.tokens_in += ti
        self.tokens_out += to
        pin, pout = self.prices[tier]
        self.cost += ti / 1e6 * pin + to / 1e6 * pout
        return out
