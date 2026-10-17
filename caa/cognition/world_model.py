"""Predictive layer (predictive processing): predict P(success) BEFORE acting, compare with the
verified outcome AFTER. Surprise = |outcome - prediction| drives what reflection studies first;
Brier score measures whether the system's expectations are calibrated.

v0 predictor: Laplace-smoothed historical pass rate for the task type, raised when a strong
relevant lesson was retrieved. It is a baseline to beat, not a learned world model."""
from __future__ import annotations
import json
from ..core.schemas import Task, Verdict
from ..memory.store import MemoryStore


class WorldModel:
    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory

    def predict(self, task: Task, hits: list[dict]) -> float:
        rows = self.memory.db.execute(
            "SELECT status FROM episodes WHERE task_type=? AND status IN ('success','fail')",
            (task.task_type,)).fetchall()
        s = sum(r["status"] == "success" for r in rows)
        p = (s + 1) / (len(rows) + 2)
        if hits and hits[0]["score"] >= 0.5:
            p = min(0.95, p + 0.3)
        return round(p, 3)

    @staticmethod
    def surprise(pred: float, verdict: Verdict) -> float | None:
        if verdict == "unverifiable":
            return None
        return round(abs((1.0 if verdict == "pass" else 0.0) - pred), 3)

    def brier(self) -> float | None:
        """Mean squared error of predictions vs verified outcomes (0 = perfect, 0.25 = coin flip)."""
        errs = []
        for r in self.memory.db.execute("SELECT status, data FROM episodes WHERE status IN ('success','fail')"):
            pred = json.loads(r["data"]).get("predicted")
            if pred is not None:
                errs.append((pred - (1.0 if r["status"] == "success" else 0.0)) ** 2)
        return round(sum(errs) / len(errs), 4) if errs else None
