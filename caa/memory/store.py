"""SQLite-backed memory: episodic log + versioned facts/skills with rollback.

Retrieval v0: hashed bag-of-words cosine + keyword overlap, weighted by trust.
Swap in pgvector / real embeddings later behind the same recall() signature.
"""
from __future__ import annotations
import hashlib
import json
import math
import sqlite3
import time
from ..core.schemas import new_id
from ..core.text import tokens
from .retrieval import HybridRetriever

DIM = 256


def _vec(toks: list[str]) -> list[float]:
    v = [0.0] * DIM
    for t in toks:
        v[int(hashlib.md5(t.encode()).hexdigest(), 16) % DIM] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


class MemoryStore:
    def __init__(self, path: str = ":memory:", retriever: str = "v1", embedder=None,
                 min_score: float | None = None, rel_gate: float = 0.6) -> None:
        self.version = retriever
        self.retriever = HybridRetriever(embedder) if retriever == "v1" else None
        self.min_score = min_score if min_score is not None else (0.3 if retriever == "v1" else 0.1)
        self.rel_gate = rel_gate  # v1: drop hits scoring below rel_gate * top score
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS episodes(
            id TEXT PRIMARY KEY, ts REAL, intent TEXT, task_type TEXT, path TEXT,
            output TEXT, status TEXT, confidence REAL, data TEXT);
        CREATE TABLE IF NOT EXISTS facts(
            id TEXT PRIMARY KEY, ts REAL, text TEXT, kind TEXT, trust REAL,
            active INTEGER, uses INTEGER DEFAULT 0, evidence TEXT, retired_ts REAL, tags TEXT DEFAULT '');
        CREATE INDEX IF NOT EXISTS idx_facts_active ON facts(active);
        """)

    # ---- episodic ----
    def write_episode(self, ep: dict) -> str:
        eid = ep.get("episode_id") or new_id("ep")
        self.db.execute(
            "INSERT INTO episodes VALUES(?,?,?,?,?,?,?,?,?)",
            (eid, time.time(), ep.get("intent", ""), ep.get("task_type", ""), ep.get("path", ""),
             ep.get("output", ""), ep.get("status", ""), ep.get("confidence", 0.0), json.dumps(ep)))
        self.db.commit()
        return eid

    def episodes(self, status: str | None = None) -> list[dict]:
        q = "SELECT * FROM episodes" + (" WHERE status=?" if status else "") + " ORDER BY ts"
        return [dict(r) for r in self.db.execute(q, (status,) if status else ())]

    # ---- facts / skills ----
    def promote(self, text: str, evidence: list[str] | None = None,
                kind: str = "semantic", trust: float = 0.8, tags: str = "") -> str:
        """tags = situation text used for retrieval only (not shown in context)."""
        row = self.db.execute("SELECT id FROM facts WHERE text=? AND tags=? AND active=1", (text, tags)).fetchone()
        if row:
            return row["id"]
        fid = new_id("fact")
        self.db.execute(
            "INSERT INTO facts(id,ts,text,kind,trust,active,evidence,tags) VALUES(?,?,?,?,?,1,?,?)",
            (fid, time.time(), text, kind, trust, json.dumps(evidence or []), tags))
        self.db.commit()
        return fid

    def rollback(self, pointer: str) -> None:
        """Tombstone, never delete."""
        self.db.execute("UPDATE facts SET active=0, retired_ts=? WHERE id=?", (time.time(), pointer))
        self.db.commit()

    def reactivate(self, pointer: str) -> None:
        self.db.execute("UPDATE facts SET active=1, retired_ts=NULL WHERE id=?", (pointer,))
        self.db.commit()

    def recall(self, query: str, k: int = 8, min_score: float | None = None) -> list[dict]:
        floor = self.min_score if min_score is None else min_score
        if self.retriever is None:
            return self._recall_v0(query, k, floor)
        rows = {r["id"]: r for r in self.db.execute("SELECT * FROM facts WHERE active=1")}
        if not rows:
            return []
        docs = {i: r["text"] + " " + (r["tags"] or "") for i, r in rows.items()}
        raw = self.retriever.rank(query, docs)
        scored = sorted(((raw[i] * rows[i]["trust"], i) for i in rows), reverse=True)
        top = scored[0][0]
        out, seen = [], set()
        for sc, i in scored:   # collapse identical texts (one rule stored under many situations)
            if sc >= max(floor, self.rel_gate * top) and rows[i]["text"] not in seen:
                seen.add(rows[i]["text"])
                out.append({"id": i, "text": rows[i]["text"], "kind": rows[i]["kind"],
                            "score": round(sc, 4), "trust": rows[i]["trust"]})
        out = out[:k]
        for d in out:
            self.db.execute("UPDATE facts SET uses=uses+1 WHERE id=?", (d["id"],))
        self.db.commit()
        return out

    def _recall_v0(self, query: str, k: int, min_score: float) -> list[dict]:
        q = tokens(query)
        qs, qv = set(q), _vec(q)
        out = []
        for r in self.db.execute("SELECT * FROM facts WHERE active=1"):
            t = tokens(r["text"] + " " + (r["tags"] or ""))
            overlap = len(qs & set(t)) / max(len(qs), 1)
            cos = sum(a * b for a, b in zip(qv, _vec(t)))
            score = (0.6 * cos + 0.4 * overlap) * r["trust"]
            if score >= min_score:
                out.append({"id": r["id"], "text": r["text"], "kind": r["kind"],
                            "score": round(score, 4), "trust": r["trust"]})
        out.sort(key=lambda d: d["score"], reverse=True)
        top = out[:k]
        for d in top:
            self.db.execute("UPDATE facts SET uses=uses+1 WHERE id=?", (d["id"],))
        self.db.commit()
        return top

    def prune(self, decay: float = 0.9, floor: float = 0.2) -> list[str]:
        """Decay trust of never-used facts; retire those under the floor. Returns retired ids."""
        self.db.execute("UPDATE facts SET trust=trust*? WHERE active=1 AND uses=0", (decay,))
        retired = [r["id"] for r in self.db.execute(
            "SELECT id FROM facts WHERE active=1 AND trust<?", (floor,))]
        for fid in retired:
            self.rollback(fid)
        return retired
