from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

Path = Literal["fast", "slow", "tool_first"]
Verdict = Literal["pass", "fail", "unverifiable"]


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@dataclass
class Task:
    intent: str
    task_type: str = "general"
    risk_level: str = "low"
    constraints: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)  # eval-only: expected, feedback
    id: str = field(default_factory=lambda: new_id("task"))


@dataclass
class Proposal:
    author: str
    type: str  # plan | evidence | action | objection
    content: str
    confidence: float = 0.5
    id: str = field(default_factory=lambda: new_id("prop"))


@dataclass
class Result:
    task_id: str
    content: str
    confidence: float
    verifier: Verdict
    path: Path
    episode_id: str | None = None
    escalated: bool = False
    note: str = ""
    predicted: float | None = None
    surprise: float | None = None
