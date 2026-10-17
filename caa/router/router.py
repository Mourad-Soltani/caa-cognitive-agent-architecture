from __future__ import annotations
import random
from dataclasses import dataclass, field
from ..core.schemas import Path, Task

RISKY = ("delete", "drop", "publish", "send", "pay", "transfer", "refund", "deploy")
FRESH = ("latest", "today", "current price", "search")


@dataclass
class RouterConfig:
    fast_skill_threshold: float = 0.85
    long_task_words: int = 40
    explore_rate: float = 0.0  # share of length-routed slow tasks sent fast to gather tuning data
    seed: int = 0


@dataclass
class RouteDecision:
    path: Path
    risk_level: str
    reason: str
    budget: dict = field(default_factory=dict)


class Router:
    def __init__(self, cfg: RouterConfig | None = None) -> None:
        self.cfg = cfg or RouterConfig()
        self._rng = random.Random(self.cfg.seed)

    def route(self, task: Task, hits: list[dict]) -> RouteDecision:
        text = task.intent.lower()
        risk = "high" if any(w in text for w in RISKY) else task.risk_level
        if risk == "high":
            return RouteDecision("slow", risk, "risky action: slow path + verifier", {"tokens": 8000})
        if hits and hits[0]["kind"] == "procedural" and hits[0]["score"] >= self.cfg.fast_skill_threshold:
            return RouteDecision("fast", risk, "cached skill match", {"tokens": 1000})
        if any(w in text for w in FRESH):
            return RouteDecision("tool_first", risk, "needs fresh data", {"tokens": 4000})
        if len(text.split()) > self.cfg.long_task_words or task.task_type == "plan":
            if self._rng.random() < self.cfg.explore_rate:
                return RouteDecision("fast", risk, "explore", {"tokens": 1000})
            return RouteDecision("slow", risk, "multi-step estimate", {"tokens": 6000})
        return RouteDecision("fast", risk, "default routine", {"tokens": 1000})
