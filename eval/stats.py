"""Small, dependency-free statistics for eval reports (bootstrap over tasks)."""
from __future__ import annotations
import random


def bootstrap_ci(values: list[float], n_boot: int = 2000, alpha: float = 0.05, seed: int = 0):
    """Return (mean, lo, hi); (None, None, None) for empty input."""
    if not values:
        return None, None, None
    rng, n = random.Random(seed), len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    return (round(sum(values) / n, 4), round(means[int(alpha / 2 * n_boot)], 4),
            round(means[int((1 - alpha / 2) * n_boot) - 1], 4))


def paired_diff_ci(a: list[float], b: list[float], **kw):
    """CI of mean(a_i - b_i) over matched items. Lengths must match (same tasks, same order)."""
    if len(a) != len(b):
        raise ValueError("paired samples must have equal length")
    return bootstrap_ci([x - y for x, y in zip(a, b)], **kw)
