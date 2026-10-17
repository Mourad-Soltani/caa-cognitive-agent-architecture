"""Code eval across conditions A/B/C with cost metering.

  python -m eval.run_code --model scripted     # offline wiring check
  python -m eval.run_code --model anthropic    # real run; needs ANTHROPIC_API_KEY

Conditions: A no memory | B memory, no reflection | C full loop | D = C + plan search (n=3, executing critic)
Protocol: pass 1 on all tasks (C reflects after each failure) -> pass 2 retry.
Real signal requires tasks the base model actually fails; if pass-1 is ~100% there is nothing to learn.
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from caa.agent import Agent
from caa.memory.store import MemoryStore
from caa.models.metered import Metered
from .code_tasks import build_code_tasks
from .run_eval import CONDITIONS, rate

CODE_CONDITIONS = dict(CONDITIONS, D_caa_plan_search=dict(use_memory=True, write_episodes=True, learn=True, search_n=3))


def make_model(kind: str):
    if kind == "anthropic":
        from caa.models.client import AnthropicModel
        return AnthropicModel()
    from .scripted import ScriptedCoder
    return ScriptedCoder()


def run(kind: str) -> list[dict]:
    rows = []
    for name, flags in CODE_CONDITIONS.items():
        fast, slow = Metered(make_model(kind)), Metered(make_model(kind))
        agent = Agent(fast, slow, MemoryStore(), **flags)
        tasks = build_code_tasks()
        p1 = []
        for t in tasks:
            r = agent.handle(t)
            p1.append(r)
            agent.learn(t, r)
        p2 = [agent.handle(t) for t in tasks]
        rows.append({
            "condition": name, "pass1": rate(p1), "pass2_retry": rate(p2),
            "escalation_rate": round(sum(r.escalated for r in p1 + p2) / len(p1 + p2), 3),
            "cost_usd_est": round(fast.cost + slow.cost, 6),
            "latency_s": round(fast.latency + slow.latency, 2),
            "calls": {"fast": fast.calls["fast"], "slow": slow.calls["slow"]},
            "searches": len(agent.search_log),
            "search_discriminative": sum(i.discriminative for i in agent.search_log),
            "search_fallbacks": sum(bool(i.fallback) for i in agent.search_log),
        })
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["scripted", "anthropic"], default="scripted")
    a = ap.parse_args()
    rows = run(a.model)
    for r in rows:
        print(r)
    out = Path(__file__).parent / "reports" / f"code_{a.model}_{int(time.time())}.json"
    out.write_text(json.dumps(rows, indent=2))
