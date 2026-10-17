"""Reflection: failed episode + environment feedback -> candidate lesson -> replay-validated promotion."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..core.schemas import Result, Task

if TYPE_CHECKING:
    from ..agent import Agent


def reflect(agent: "Agent", task: Task, result: Result) -> str | None:
    if result.verifier != "fail":
        return None
    # Real environments supply feedback (test output); eval tasks may also supply a teacher hint.
    feedback = task.meta.get("feedback") or result.note
    if not feedback:
        return None
    lesson = agent.slow.complete(
        "reflector",
        f"TASK: {task.intent}\nOUTPUT: {result.content}\nFEEDBACK: {feedback}\n"
        "Propose one specific, falsifiable lesson (what to do differently next time).", "slow").strip()
    if not lesson:
        return None
    # Validation gate: the lesson must fix the failing task on replay before it is promoted.
    out = agent.replay_with(task, [{"text": lesson, "kind": "semantic", "score": 1.0}])
    verdict, _ = agent.verifier.check(task, out)
    if verdict != "pass":
        return None
    if not _no_interference(agent, lesson):
        return None
    fid = agent.memory.promote(lesson, evidence=[result.episode_id or ""], tags=task.intent)
    agent.lesson_tasks[fid] = task
    return fid


def _no_interference(agent: "Agent", lesson: str) -> bool:
    """Continual-learning guard: a lesson must not reduce the pass count on canary tasks."""
    if not agent.canaries:
        return True
    hit = [{"text": lesson, "kind": "semantic", "score": 1.0}]

    def passes(extra):
        return sum(agent.verifier.check(c, agent.replay_with(c, extra))[0] == "pass" for c in agent.canaries)

    return passes(hit) >= passes([])


def reflect_batch(agent: "Agent", pairs: list[tuple[Task, Result]]) -> list[str]:
    """Consolidation pass: study the most surprising failures first."""
    ordered = sorted(pairs, key=lambda p: p[1].surprise or 0.0, reverse=True)
    return [fid for t, r in ordered if (fid := reflect(agent, t, r))]
