from __future__ import annotations
from .core.schemas import Result, Task
from .deliberation.verifier import Verifier
from .memory.store import MemoryStore
from .metacognition.confidence import ESCALATE_BELOW, confidence
from .models.client import Model
from .reflection.reflect import reflect
from .router.router import Router
from .router.tuning import DecisionLog
from .deliberation.plan_search import SearchExecutor
from .cognition.world_model import WorldModel
from .workspace.board import Workspace


class Agent:
    def __init__(self, fast: Model, slow: Model, memory: MemoryStore, router: Router | None = None,
                 verifier: Verifier | None = None, use_memory: bool = True,
                 write_episodes: bool = True, learn: bool = True, log_decisions: bool = True,
                 search_n: int = 0) -> None:
        self.fast, self.slow, self.memory = fast, slow, memory
        self.router = router or Router()
        self.verifier = verifier or Verifier()
        self.use_memory, self.write_episodes, self.learn_enabled = use_memory, write_episodes, learn
        self.decisions = DecisionLog(memory.db) if log_decisions else None
        self.search_n, self.last_search, self.search_log = search_n, None, []
        self.world = WorldModel(memory)
        self.lesson_tasks: dict = {}  # fact id -> Task that produced it (in-process)
        self.canaries: list = []  # regression tasks guarding lesson promotion (continual-learning guard)

    @staticmethod
    def _ctx(hits: list[dict]) -> str:
        return "\n".join(f"- {h['text']}" for h in hits)

    def _run(self, path: str, task: Task, hits: list[dict]) -> str:
        ctx = self._ctx(hits)
        if path == "fast":
            return self.fast.complete("executor", f"{ctx}\nTASK: {task.intent}", "fast")
        if self.search_n > 1 and task.meta.get("lang") == "python":
            out, self.last_search = SearchExecutor(self.slow, n=self.search_n).run(task.intent, ctx)
            self.search_log.append(self.last_search)
            return out
        # tool_first has no tools yet in v0: falls through to the slow workspace
        return Workspace(self.slow).run(task.intent, ctx)

    def replay_with(self, task: Task, extra_hits: list[dict]) -> str:
        hits = self.memory.recall(task.intent) if self.use_memory else []
        return self._run(self.router.route(task, extra_hits + hits).path, task, extra_hits + hits)

    def handle(self, task: Task) -> Result:
        hits = self.memory.recall(task.intent) if self.use_memory else []
        decision = self.router.route(task, hits)
        pred = self.world.predict(task, hits)
        path, escalated = decision.path, False
        out = self._run(path, task, hits)
        verdict, note = self.verifier.check(task, out)
        conf = confidence(out, verdict)
        if conf < ESCALATE_BELOW and path == "fast":
            path, escalated = "slow", True
            out = self._run("slow", task, hits)
            verdict, note = self.verifier.check(task, out)
            conf = confidence(out, verdict)
        surprise = self.world.surprise(pred, verdict)
        eid = None
        if self.write_episodes:
            eid = self.memory.write_episode({
                "intent": task.intent, "task_type": task.task_type, "path": path,
                "output": out, "predicted": pred, "surprise": surprise, "status": "success" if verdict == "pass" else
                ("fail" if verdict == "fail" else "unverified"), "confidence": conf})
        if self.decisions:
            self.decisions.log(task.id, len(task.intent.split()), decision.path, decision.reason,
                               escalated, verdict)
        return Result(task.id, out, conf, verdict, path, eid, escalated, note, pred, surprise)

    def learn(self, task: Task, result: Result) -> str | None:
        return reflect(self, task, result) if self.learn_enabled else None
