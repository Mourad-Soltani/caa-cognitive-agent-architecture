"""Router decision log and threshold tuner (Phase 2).

LIMIT: logs only show the path actually taken, so estimates pool outcomes by word-count
bucket. Use explore_rate > 0 so long tasks sometimes run fast; without exploration the
tuner has no data on how fast performs on long tasks.
"""
from __future__ import annotations
import sqlite3
import time


class DecisionLog:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
        db.execute("""CREATE TABLE IF NOT EXISTS decisions(
            task_id TEXT, ts REAL, words INTEGER, routed TEXT, reason TEXT,
            escalated INTEGER, verdict TEXT)""")

    def log(self, task_id: str, words: int, routed: str, reason: str, escalated: bool, verdict: str) -> None:
        self.db.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?,?)",
                        (task_id, time.time(), words, routed, reason, int(escalated), verdict))
        self.db.commit()

    def rows(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM decisions")]


def tune_long_task_words(rows: list[dict], cost_fast: float = 1.0, cost_slow: float = 5.0,
                         detect_rate: float = 0.7, wrong_penalty: float = 20.0,
                         candidates: range = range(10, 130, 10)) -> dict:
    """Pick the word-count threshold minimising expected cost per task.

    Fast failure is caught with prob detect_rate (then escalated: pays cost_slow);
    undetected failures pay wrong_penalty. All four constants are assumptions: set them
    from your real pricing and the real cost of a wrong answer.
    """
    fast_rows = [r for r in rows if r["routed"] == "fast"]
    slow_final = [r for r in rows if r["routed"] == "slow" or r["escalated"]]
    if not fast_rows or not slow_final:
        return {"error": "need both fast and slow outcomes in the log"}
    p_slow = sum(r["verdict"] == "pass" for r in slow_final) / len(slow_final)
    best = None
    for T in candidates:
        total_cost = total_ok = 0.0
        for r in rows:
            w = r["words"]
            if w > T:
                total_cost += cost_slow
                total_ok += p_slow
            else:
                near = [x for x in fast_rows if abs(x["words"] - w) <= 5] or fast_rows
                pf = sum((not x["escalated"]) and x["verdict"] == "pass" for x in near) / len(near)
                fail = 1 - pf
                total_cost += cost_fast + fail * (detect_rate * cost_slow + (1 - detect_rate) * wrong_penalty)
                total_ok += pf + fail * detect_rate * p_slow
        n = len(rows)
        cand = {"threshold": T, "exp_cost": round(total_cost / n, 3), "exp_success": round(total_ok / n, 3)}
        if best is None or cand["exp_cost"] < best["exp_cost"]:
            best = cand
    return best
