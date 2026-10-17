"""Eval harness: 3 conditions on fixed tasks. Run: python -m eval.run_eval

A = single model, no memory   B = memory of raw episodes, no reflection   C = full CAA loop
NOTE: with MockModel this validates the PLUMBING (memory -> reflection -> retrieval -> transfer).
It says nothing about real model capability. Swap in AnthropicModel for real numbers.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path
from caa.agent import Agent
from caa.memory.store import MemoryStore
from caa.models.client import MockModel
from .tasks import TASKSET_VERSION, build_tasks

CONDITIONS = {
    "A_no_memory": dict(use_memory=False, write_episodes=False, learn=False),
    "B_memory_no_reflection": dict(use_memory=True, write_episodes=True, learn=False),
    "C_full_caa": dict(use_memory=True, write_episodes=True, learn=True),
}


def rate(results):
    return round(sum(r.verifier == "pass" for r in results) / max(len(results), 1), 3)


def run_condition(name: str, flags: dict, model_factory=MockModel) -> dict:
    fast, slow = model_factory(), model_factory()
    agent = Agent(fast, slow, MemoryStore(), **flags)
    train, test, control = build_tasks()
    first = []
    for t in train:
        r = agent.handle(t)
        first.append(r)
        agent.learn(t, r)
    retry = [agent.handle(t) for t in train]
    transfer = [agent.handle(t) for t in test]
    ctrl = [agent.handle(t) for t in control]
    allr = first + retry + transfer + ctrl
    return {
        "condition": name,
        "train_first_pass": rate(first),
        "retry_success": rate(retry),
        "transfer_success": rate(transfer),
        "control_success": rate(ctrl),
        "escalation_rate": round(sum(r.escalated for r in allr) / len(allr), 3),
        "fast_calls": getattr(fast, "calls", {}).get("fast", 0),
        "slow_calls": getattr(slow, "calls", {}).get("slow", 0),
    }


def main() -> list[dict]:
    rows = [run_condition(n, f) for n, f in CONDITIONS.items()]
    hdr = ["condition", "train_first_pass", "retry_success", "transfer_success",
           "control_success", "escalation_rate", "slow_calls"]
    print(" | ".join(hdr))
    for r in rows:
        print(" | ".join(str(r[h]) for h in hdr))
    out = Path(__file__).parent / "reports" / f"report_{TASKSET_VERSION}_{int(time.time())}.json"
    out.write_text(json.dumps({"taskset": TASKSET_VERSION, "rows": rows}, indent=2))
    print(f"\nreport: {out}", file=sys.stderr)
    return rows


if __name__ == "__main__":
    main()
