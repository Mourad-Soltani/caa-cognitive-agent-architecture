"""Real-run harness: repeated trials, bootstrap CIs, budget cap, resumable checkpoints,
held-out transfer. Designed so a published number can be defended.

  python -m eval.real_run --model stub --trials 2 --per-domain 6          # offline wiring check
  python -m eval.real_run --model anthropic --dry-run                      # plan + cost bound, no calls
  ANTHROPIC_API_KEY=... python -m eval.real_run --model anthropic --trials 3 --budget-usd 20 \
        --price-fast 1,5 --price-slow 3,15                                 # REAL run (set real prices!)

Per (condition, trial) a fresh agent runs domains in sequence. Per domain the shuffled tasks are split
into a LEARN half and a HELD-OUT half:
  held_before -> learn (pass1, reflect) -> learn_retry -> held_after;  learn_final after ALL domains (forgetting).
Held-out uplift (held_after - held_before) is the generalisation metric; retry on learned tasks is only memory.
A trial that hits the budget is marked truncated and excluded; truncated runs cannot certify any stage."""
from __future__ import annotations
import argparse
import json
import random
import sys
import time
from pathlib import Path
from caa.agent import Agent
from caa.memory.store import MemoryStore
from caa.models.metered import PRICES, Metered
from .code_tasks import build_code_tasks
from .domains import MultiDomainStub, build_planning_tasks
from .sql_domain import build_sql_tasks
from .stats import bootstrap_ci, paired_diff_ci
from .tasks import build_tasks

CONDITIONS = {
    "A": dict(use_memory=False, write_episodes=False, learn=False),
    "B": dict(use_memory=True, write_episodes=True, learn=False),
    "C": dict(use_memory=True, write_episodes=True, learn=True),
    "D": dict(use_memory=True, write_episodes=True, learn=True, search_n=3),
}
DOMAIN_ORDER = ["rules", "code", "planning", "sql"]
KEYS = ["held_before", "learn_pass1", "learn_retry", "held_after", "learn_final"]


def domain_tasks():
    train, test, control = build_tasks()
    for t in train + test:
        t.task_type = "rules"
    return {"rules": train + test, "code": build_code_tasks(),
            "planning": build_planning_tasks(n=12), "sql": build_sql_tasks()}, control


def split(tasks, trial: int, dom: str, per_domain: int | None):
    rng = random.Random(f"{trial}-{dom}")          # identical across conditions -> paired comparisons
    ts = tasks[:]
    rng.shuffle(ts)
    if per_domain:
        ts = ts[:per_domain]
    h = len(ts) // 2
    return ts[:h], ts[h:]                           # learn, held-out


def run_trial(cond: str, trial: int, make_model, prices, budget: float, per_domain: int | None) -> dict:
    fast, slow = Metered(make_model(), prices), Metered(make_model(), prices)
    agent = Agent(fast, slow, MemoryStore(), **CONDITIONS[cond])
    doms, control = domain_tasks()
    agent.canaries = control[:5]
    rec = {"condition": cond, "trial": trial, "truncated": False, "domains": {}, "control_before": [], "control_after": []}

    def run(tasks, learn=False):
        out = []
        for t in tasks:
            if fast.cost + slow.cost >= budget:
                rec["truncated"] = True
                return out
            r = agent.handle(t)
            out.append(int(r.verifier == "pass"))
            if learn:
                agent.learn(t, r)
        return out

    rec["control_before"] = run(control)
    splits = {}
    for d in DOMAIN_ORDER:
        learn_set, held = split(doms[d], trial, d, per_domain)
        splits[d] = learn_set
        rec["domains"][d] = {"held_before": run(held), "learn_pass1": run(learn_set, learn=True)}
        rec["domains"][d]["learn_retry"] = run(learn_set)
        rec["domains"][d]["held_after"] = run(held)
    for d in DOMAIN_ORDER:
        rec["domains"][d]["learn_final"] = run(splits[d])
    rec["control_after"] = run(control)
    rec["cost"] = round(fast.cost + slow.cost, 6)
    rec["calls"] = {"fast": fast.calls["fast"], "slow": slow.calls["slow"]}
    return rec


def run_all(make_model, conds, trials, prices, budget, per_domain, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    results, spent, resumed, executed = [], 0.0, 0, 0
    for trial in range(trials):
        for c in conds:
            ck = out_dir / f"ckpt_{c}_t{trial}.json"
            if ck.exists():
                rec = json.loads(ck.read_text())
                resumed += 1
            else:
                rec = run_trial(c, trial, make_model, prices, budget - spent, per_domain)
                executed += 1
                if not rec["truncated"]:
                    ck.write_text(json.dumps(rec))
            spent += rec.get("cost", 0.0)
            results.append(rec)
    return {"trials": results, "spent_usd_est": round(spent, 4), "resumed": resumed, "executed": executed}


def _pool(trials, cond, dom, key):
    return [x for t in sorted(trials, key=lambda t: t["trial"]) if t["condition"] == cond and not t["truncated"]
            for x in t["domains"][dom][key]]


def _ctrl(trials, cond, key):
    return [x for t in sorted(trials, key=lambda t: t["trial"]) if t["condition"] == cond and not t["truncated"] for x in t[key]]


def aggregate(trials: list[dict]) -> dict:
    conds = sorted({t["condition"] for t in trials})
    agg = {"conditions": {}, "vs_A": {}, "uplift_heldout": {}, "forgetting": {}, "controls": {}}
    for c in conds:
        agg["conditions"][c] = {d: {k: bootstrap_ci(_pool(trials, c, d, k)) for k in KEYS} for d in DOMAIN_ORDER}
        cb, ca = _ctrl(trials, c, "control_before"), _ctrl(trials, c, "control_after")
        agg["controls"][c] = {"before": bootstrap_ci(cb), "after": bootstrap_ci(ca)}
        agg["uplift_heldout"][c] = {d: paired_diff_ci(_pool(trials, c, d, "held_after"), _pool(trials, c, d, "held_before"))
                                    for d in DOMAIN_ORDER}
        agg["forgetting"][c] = {d: paired_diff_ci(_pool(trials, c, d, "learn_retry"), _pool(trials, c, d, "learn_final"))
                                for d in DOMAIN_ORDER}
        if c != "A" and "A" in conds:
            agg["vs_A"][c] = {d: {"learn_retry": paired_diff_ci(_pool(trials, c, d, "learn_retry"), _pool(trials, "A", d, "learn_retry")),
                                  "held_after": paired_diff_ci(_pool(trials, c, d, "held_after"), _pool(trials, "A", d, "held_after"))}
                              for d in DOMAIN_ORDER}
    return agg


def assess(agg: dict, real_model: bool, truncated: bool, n_tasks: int, autonomy: dict | None, cond: str = "C") -> dict:
    """CI-based stage gate. Stub or truncated runs can never exceed Stage 0."""
    vs = agg["vs_A"].get(cond, {})
    lo = lambda ci: ci[1] if ci and ci[1] is not None else -1.0
    met = {0: True}
    met[1] = n_tasks >= 30 and lo(vs.get("code", {}).get("learn_retry")) > 0
    up = agg["uplift_heldout"].get(cond, {})
    fg = agg["forgetting"].get(cond, {})
    ctrl = agg["controls"].get(cond, {})
    met[2] = (sum(lo(up[d]) > 0 for d in up) >= 3
              and all((fg[d][0] or 0) <= 0.05 for d in fg)
              and (ctrl.get("after", (0,))[0] or 0) >= (ctrl.get("before", (1,))[0] or 1))
    met[3] = bool(autonomy and autonomy["success_rate"] >= 0.8 and autonomy["awaiting_approval"] >= 1)
    met[4] = False
    q = 0
    for s in range(1, 5):
        if met[s] and real_model and not truncated and all(met[k] for k in range(s)):
            q = s
        else:
            break
    note = ("stub model: no stage above 0 can be certified" if not real_model else
            "budget-truncated run: no stage above 0 can be certified" if truncated else "")
    return {"qualified_stage": q, "criteria_met": [s for s, ok in met.items() if ok], "note": note}


def fmt(ci):
    return "n/a" if not ci or ci[0] is None else f"{ci[0]:.2f} [{ci[1]:.2f}, {ci[2]:.2f}]"


def render(cfg: dict, run: dict, agg: dict, stage: dict) -> str:
    L = [f"# CAA real-run report", "",
         f"- model: **{cfg['model']}** | trials: {cfg['trials']} | per-domain cap: {cfg['per_domain']} | conditions: {','.join(cfg['conds'])}",
         f"- estimated cost: ${run['spent_usd_est']} ({'PLACEHOLDER prices' if not cfg['prices_set'] else 'user-supplied prices'}; tokens estimated chars/4)",
         f"- truncated trials: {sum(t['truncated'] for t in run['trials'])} | resumed from checkpoint: {run['resumed']}",
         f"- qualified stage: **{stage['qualified_stage']}** (criteria met: {stage['criteria_met']}) {stage['note']}", "",
         "All intervals are 95% bootstrap CIs over tasks pooled across trials.", ""]
    for d in DOMAIN_ORDER:
        L += [f"## {d}", "", "| cond | held_before | learn_pass1 | learn_retry | held_after | held uplift | forgetting |", "|---|---|---|---|---|---|---|"]
        for c in agg["conditions"]:
            r = agg["conditions"][c][d]
            L.append(f"| {c} | {fmt(r['held_before'])} | {fmt(r['learn_pass1'])} | {fmt(r['learn_retry'])} | {fmt(r['held_after'])} | "
                     f"{fmt(agg['uplift_heldout'][c][d])} | {fmt(agg['forgetting'][c][d])} |")
        L.append("")
    L += ["## vs baseline A (paired differences)", "", "| cond | domain | learn_retry diff | held_after diff |", "|---|---|---|---|"]
    for c, doms in agg["vs_A"].items():
        for d, v in doms.items():
            L.append(f"| {c} | {d} | {fmt(v['learn_retry'])} | {fmt(v['held_after'])} |")
    L += ["", "## Controls (arithmetic, must not regress)", ""]
    for c, v in agg["controls"].items():
        L.append(f"- {c}: before {fmt(v['before'])} -> after {fmt(v['after'])}")
    L += ["", "Held-out uplift is the generalisation metric. Retry on learned tasks measures memory only."]
    return "\n".join(L)


def plan(per_domain, trials, conds, prices):
    doms, _ = domain_tasks()
    runs = 0
    for d in DOMAIN_ORDER:
        L, H = split(doms[d], 0, d, per_domain)
        runs += 2 * len(H) + 4 * len(L)
    calls = runs * 6 * trials * sum(2 if c == "D" else 1 for c in conds)
    tok = 700
    cost = calls * tok * (prices["slow"][0] + prices["slow"][1]) / 2 / 1e6
    return {"task_runs_per_trial_per_condition": runs, "model_calls_upper_bound": calls,
            "cost_upper_bound_usd_rough": round(cost, 2)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["stub", "anthropic"], default="stub")
    ap.add_argument("--conditions", default="A,B,C,D")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--per-domain", type=int, default=None)
    ap.add_argument("--budget-usd", type=float, default=20.0)
    ap.add_argument("--price-fast", default=None, help="in,out USD per 1M tokens")
    ap.add_argument("--price-slow", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--autonomy", action="store_true")
    a = ap.parse_args(argv)
    conds = a.conditions.split(",")
    prices, prices_set = dict(PRICES), bool(a.price_fast and a.price_slow)
    if a.price_fast:
        prices["fast"] = tuple(map(float, a.price_fast.split(",")))
    if a.price_slow:
        prices["slow"] = tuple(map(float, a.price_slow.split(",")))
    if a.model == "anthropic" and not prices_set:
        print("WARNING: using PLACEHOLDER prices; pass --price-fast/--price-slow for a real budget cap.", file=sys.stderr)
    p = plan(a.per_domain, a.trials, conds, prices)
    print("plan:", json.dumps(p))
    if a.dry_run:
        return p
    if a.model == "anthropic":
        from caa.models.client import AnthropicModel
        make = AnthropicModel
        m = make()
        for tier in ("fast", "slow"):
            print(f"preflight {tier}:", m.complete("executor", "Reply with the single word OK.", tier).strip()[:20])
    else:
        make = MultiDomainStub
    out = Path(a.out or f"eval/reports/real_{a.model}_{int(time.time())}")
    run = run_all(make, conds, a.trials, prices, a.budget_usd, a.per_domain, out)
    agg = aggregate(run["trials"])
    auto = None
    if a.autonomy:
        from .generality import autonomy_demo
        auto = autonomy_demo(make())
    n_tasks = sum(len(split(domain_tasks()[0][d], 0, d, a.per_domain)[0]) + len(split(domain_tasks()[0][d], 0, d, a.per_domain)[1]) for d in DOMAIN_ORDER)
    stage = assess(agg, a.model == "anthropic", any(t["truncated"] for t in run["trials"]), n_tasks, auto)
    cfg = {"model": a.model, "trials": a.trials, "per_domain": a.per_domain, "conds": conds, "prices_set": prices_set}
    md = render(cfg, run, agg, stage)
    (out / "report.md").write_text(md)
    (out / "aggregate.json").write_text(json.dumps({"agg": agg, "stage": stage, "autonomy": auto}, indent=1))
    print(md)
    print(f"\nreport: {out/'report.md'}", file=sys.stderr)
    return {"run": run, "agg": agg, "stage": stage}


if __name__ == "__main__":
    main()
