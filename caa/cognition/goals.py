"""Persistent goal stack + bounded autonomy loop.

Autonomy policy (enforced in code, not prompts):
  - only VERIFIED outcomes close a goal; unverifiable results stop for human review
  - high-risk goals wait for explicit approval
  - hard step budget and bounded retries; failures feed reflection
"""
from __future__ import annotations
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Callable
from ..core.schemas import Task
from ..core.schemas import new_id

TERMINAL = ("done", "failed", "awaiting_approval", "needs_review")


class GoalManager:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
        db.row_factory = sqlite3.Row
        db.execute("""CREATE TABLE IF NOT EXISTS goals(
            id TEXT PRIMARY KEY, parent TEXT, text TEXT, priority INTEGER, status TEXT,
            attempts INTEGER DEFAULT 0, result TEXT DEFAULT '', ts REAL)""")

    def add(self, text: str, priority: int = 5, parent: str | None = None) -> str:
        gid = new_id("goal")
        self.db.execute("INSERT INTO goals(id,parent,text,priority,status,ts) VALUES(?,?,?,?,'pending',?)",
                        (gid, parent, text, priority, time.time()))
        self.db.commit()
        return gid

    def get(self, gid: str) -> dict:
        return dict(self.db.execute("SELECT * FROM goals WHERE id=?", (gid,)).fetchone())

    def set_status(self, gid: str, status: str, result: str = "") -> None:
        self.db.execute("UPDATE goals SET status=?, result=? WHERE id=?", (status, result, gid))
        self.db.commit()

    def bump(self, gid: str) -> int:
        self.db.execute("UPDATE goals SET attempts=attempts+1 WHERE id=?", (gid,))
        self.db.commit()
        return self.get(gid)["attempts"]

    def _roll_up(self) -> None:
        """A parent with children closes when all children are done."""
        for p in self.db.execute("SELECT id FROM goals WHERE status='pending'").fetchall():
            kids = self.db.execute("SELECT status FROM goals WHERE parent=?", (p["id"],)).fetchall()
            if kids and all(k["status"] == "done" for k in kids):
                self.set_status(p["id"], "done", "all subgoals done")

    def next(self) -> dict | None:
        self._roll_up()
        for g in self.db.execute("SELECT * FROM goals WHERE status='pending' ORDER BY priority DESC, ts ASC"):
            if not self.db.execute("SELECT 1 FROM goals WHERE parent=? AND status IN ('pending')",
                                   (g["id"],)).fetchone():
                if not self.db.execute("SELECT 1 FROM goals WHERE parent=?", (g["id"],)).fetchone():
                    return dict(g)
        return None

    def all(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM goals ORDER BY ts")]


def decompose(agent, goals: GoalManager, goal_id: str) -> list[str]:
    """Ask the planner role for subgoals (one per line) and attach them as children."""
    g = goals.get(goal_id)
    raw = agent.slow.complete("planner", f"Decompose into 2-5 verifiable subgoals, one per line.\nGOAL: {g['text']}", "slow")
    lines = [ln.strip(" -0123456789.") for ln in raw.splitlines() if ln.strip(" -0123456789.")]
    return [goals.add(t, g["priority"], parent=goal_id) for t in lines]


@dataclass
class LoopReport:
    steps: int = 0
    done: list = field(default_factory=list)
    failed: list = field(default_factory=list)
    awaiting_approval: list = field(default_factory=list)
    needs_review: list = field(default_factory=list)
    stopped: str = ""

    @property
    def success_rate(self) -> float:
        n = len(self.done) + len(self.failed)
        return round(len(self.done) / n, 3) if n else 0.0


class AutonomyLoop:
    def __init__(self, agent, goals: GoalManager, task_factory: Callable[[dict], Task],
                 max_steps: int = 50, max_retries: int = 1, approved: set[str] | None = None) -> None:
        self.agent, self.goals, self.task_factory = agent, goals, task_factory
        self.max_steps, self.max_retries, self.approved = max_steps, max_retries, approved or set()

    def run(self) -> LoopReport:
        rep = LoopReport()
        while rep.steps < self.max_steps:
            g = self.goals.next()
            if g is None:
                rep.stopped = "no_pending_goals"
                break
            task = self.task_factory(g)
            if self.agent.router.route(task, []).risk_level == "high" and g["id"] not in self.approved:
                self.goals.set_status(g["id"], "awaiting_approval")
                rep.awaiting_approval.append(g["id"])
                continue
            res = self.agent.handle(task)
            rep.steps += 1
            if res.verifier == "pass":
                self.goals.set_status(g["id"], "done", res.content[:200])
                rep.done.append(g["id"])
            elif res.verifier == "unverifiable":
                self.goals.set_status(g["id"], "needs_review", res.content[:200])
                rep.needs_review.append(g["id"])
            else:
                self.agent.learn(task, res)
                if self.goals.bump(g["id"]) > self.max_retries:
                    self.goals.set_status(g["id"], "failed", res.note[:200])
                    rep.failed.append(g["id"])
        else:
            rep.stopped = "step_budget_exhausted"
        return rep
