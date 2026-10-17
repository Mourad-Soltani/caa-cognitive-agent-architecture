"""Domain registry: each domain = tasks with a verifier path. Verification styles differ on purpose:
rules -> exact answer, code -> executed tests, planning -> property checker (any valid order)."""
from __future__ import annotations
import heapq
import random
import re
from caa.core.schemas import Task
from .code_tasks import _SPECS, build_code_tasks
from .sql_domain import BROKEN as SQL_BAD, REFERENCE as SQL_REF, SCHEMA as SQL_SCHEMA, SPECS as SQL_SPECS, build_sql_tasks
from .scripted import ScriptedCoder
from .tasks import build_tasks
from caa.models.client import MockModel

PLAN_MARK = "comes after its prerequisites"


def build_planning_tasks(seed: int = 3, n: int = 8) -> list[Task]:
    rng = random.Random(seed)
    tasks = []
    for _ in range(n):
        nodes = list("abcdefg"[: rng.randint(4, 7)])
        deps = {}
        for j, node in enumerate(nodes):
            deps[node] = sorted(rng.sample(nodes[:j], k=min(j, rng.randint(0, 2))))
        if not deps[nodes[-1]]:
            deps[nodes[-1]] = [nodes[0]]  # guarantee an ordering constraint
        desc = "; ".join(f"{k} needs {','.join(v) or 'nothing'}" for k, v in deps.items())
        intent = (f"Order these tasks so every task {PLAN_MARK}: {desc}. "
                  "Reply with comma-separated task names only.")

        def check(output: str, deps=deps):
            order = [x.strip() for x in output.split(",") if x.strip()]
            if sorted(order) != sorted(deps):
                return "fail", "output must list every task exactly once"
            pos = {t: i for i, t in enumerate(order)}
            for t, ps in deps.items():
                for p in ps:
                    if pos[p] > pos[t]:
                        return "fail", f"violation: {t} listed before its prerequisite {p}"
            return "pass", "valid order"

        tasks.append(Task(intent=intent, task_type="planning", meta={"check": check}))
    return tasks


def build_domains() -> dict[str, list[Task]]:
    train, test, control = build_tasks()
    for t in train:
        t.task_type = "rules"
    return {"rules": train, "code": build_code_tasks(), "planning": build_planning_tasks(), "sql": build_sql_tasks(), "_control": control}


class MultiDomainStub:
    """Offline stand-in across all domains. Fails everywhere until a lesson ('RULE:') is in context.
    WIRING ONLY: with this stub any retrieved lesson 'fixes' a task, so transfer is inflated."""

    def __init__(self) -> None:
        self.calls = {"fast": 0, "slow": 0}
        self.code, self.rules = ScriptedCoder(), MockModel()

    def complete(self, role: str, prompt: str, tier: str = "fast") -> str:
        self.calls[tier] = self.calls.get(tier, 0) + 1
        if role in ("executor", "test_writer"):
            if PLAN_MARK in prompt:
                return self._plan(prompt)
            if SQL_SCHEMA in prompt:
                for name, question, *_ in SQL_SPECS:
                    if question in prompt:
                        return SQL_REF[name] if "RULE:" in prompt else SQL_BAD[name]
            if any(spec[1] in prompt for spec in _SPECS):
                return self.code.complete(role, prompt, tier)
        return self.rules.complete(role, prompt, tier)

    @staticmethod
    def _plan(prompt: str) -> str:
        deps = {m.group(1): [] if m.group(2) == "nothing" else m.group(2).split(",")
                for m in re.finditer(r"\b(\w) needs ([\w,]+)", prompt)}
        if "RULE:" not in prompt:
            return ",".join(sorted(deps, reverse=True))
        indeg = {n: len(p) for n, p in deps.items()}
        h = [n for n, d in indeg.items() if d == 0]
        heapq.heapify(h)
        out = []
        while h:
            n = heapq.heappop(h)
            out.append(n)
            for m, ps in deps.items():
                if n in ps:
                    indeg[m] -= 1
                    if indeg[m] == 0:
                        heapq.heappush(h, m)
        return ",".join(out)
