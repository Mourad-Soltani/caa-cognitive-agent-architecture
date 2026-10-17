"""Skill consolidation: many case-specific lessons of one task type -> one general procedural rule.

Safety (this is the risky step: it rewrites memory):
  1. candidate rule comes from a 'consolidator' model call over the member lessons
  2. members are tombstoned and the rule is installed under every member's situation
  3. member tasks are re-run through the REAL retrieval path; if the pass count drops
     below the pre-consolidation count, everything is rolled back (members reactivated)
Clustering v0 groups by task_type (in-process; needs agent.lesson_tasks). Semantic clustering is future work."""
from __future__ import annotations
from collections import defaultdict
from ..core.schemas import Task


def _passes(agent, tasks: list[Task]) -> int:
    return sum(agent.verifier.check(t, agent.replay_with(t, []))[0] == "pass" for t in tasks)


def consolidate(agent, min_cluster: int = 3) -> dict:
    active = {r["id"]: r["text"] for r in agent.memory.db.execute(
        "SELECT id, text FROM facts WHERE active=1 AND kind='semantic'")}
    groups: dict[str, list[str]] = defaultdict(list)
    for fid, task in agent.lesson_tasks.items():
        if fid in active:
            groups[task.task_type].append(fid)
    report = {"promoted": [], "rejected": [], "skipped": []}
    for ttype, ids in groups.items():
        if len(ids) < min_cluster:
            report["skipped"].append(ttype)
            continue
        tasks = [agent.lesson_tasks[i] for i in ids]
        before = _passes(agent, tasks)
        lessons = "\n".join(f"- {active[i]}" for i in ids)
        rule = agent.slow.complete(
            "consolidator",
            f"These lessons all came from '{ttype}' tasks:\n{lessons}\n"
            "Write ONE general rule covering all of them. Keep every concrete fact needed to apply it.",
            "slow").strip()
        if not rule:
            report["rejected"].append(ttype)
            continue
        for i in ids:
            agent.memory.rollback(i)
        new_ids = [agent.memory.promote(rule, evidence=ids, kind="procedural", trust=0.9, tags=t.intent)
                   for t in tasks]
        after = _passes(agent, tasks)
        if after >= before:
            report["promoted"].append({"type": ttype, "members": len(ids), "before": before, "after": after})
            for n_id, t in zip(new_ids, tasks):
                agent.lesson_tasks[n_id] = t
            for i in ids:
                agent.lesson_tasks.pop(i, None)
        else:  # regression: undo everything
            for n_id in new_ids:
                agent.memory.rollback(n_id)
            for i in ids:
                agent.memory.reactivate(i)
            report["rejected"].append({"type": ttype, "before": before, "after": after})
    return report
