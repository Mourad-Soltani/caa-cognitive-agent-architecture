"""Retrieval precision: one lesson per code task (lesson text = the failing assert line, tags =
task intent), then query with (a) the exact intent and (b) a short paraphrase-ish prefix.
Metrics: p@1 (own lesson ranked first), own_recall (own lesson returned at all),
leakage (mean foreign lessons returned per query, lower is better).
Synthetic and offline: it measures lexical discrimination, not true semantic quality."""
from __future__ import annotations
from caa.memory.store import MemoryStore
from .code_tasks import build_code_tasks


def run(version: str, **kw) -> dict:
    tasks = build_code_tasks()
    m = MemoryStore(retriever=version, **kw)
    own = {}
    for t in tasks:
        first_assert = t.meta["tests"].splitlines()[0]
        own[m.promote(f"fix: {first_assert}", tags=t.intent)] = t
    stats = {}
    for qname, qf in (("exact", lambda t: t.intent),
                      ("short", lambda t: " ".join(t.intent.split()[:8])),
                      ("no_name", lambda t: t.intent.replace(t.meta["name"], "it").replace("LRUCache", "it"))):
        p1 = rec = leak = 0
        for t in tasks:
            hits = m.recall(qf(t))
            ids = [h["id"] for h in hits]
            mine = [i for i in ids if own[i] is t]
            p1 += bool(ids) and own[ids[0]] is t
            rec += bool(mine)
            leak += len(ids) - len(mine)
        n = len(tasks)
        stats[qname] = {"p@1": round(p1 / n, 3), "own_recall": round(rec / n, 3), "leakage": round(leak / n, 3)}
    return stats


def run_novel(version: str, **kw) -> dict:
    """Novel-task leakage: query each task against a memory holding every OTHER task's lesson.
    Any hit is noise or (for genuinely related tasks) possible transfer."""
    tasks = build_code_tasks()
    queries_with_hit = hits = 0
    for held in tasks:
        m = MemoryStore(retriever=version, **kw)
        for t in tasks:
            if t is not held:
                m.promote("RULE: AssertionError", tags=t.intent)
        h = m.recall(held.intent)
        queries_with_hit += bool(h)
        hits += len(h)
    n = len(tasks)
    return {"novel_queries_with_any_hit": f"{queries_with_hit}/{n}", "mean_hits": round(hits / n, 2)}


if __name__ == "__main__":
    for v in ("v0", "v1"):
        print(v, run(v), run_novel(v))
