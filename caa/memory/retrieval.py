"""Hybrid retriever v1: IDF-weighted lexical cosine + embedder cosine.

Embedder is pluggable. HashingEmbedder (char trigrams) is an offline stand-in, NOT a
semantic model. Plug a real one with CallableEmbedder(fn) where fn(text) -> list[float]
(e.g. a Voyage/OpenAI/local sentence-transformer call). Linear scan: fine to ~10^4 facts;
move to pgvector beyond that.
"""
from __future__ import annotations
import hashlib
import math
from collections import Counter
from typing import Callable, Protocol
from ..core.text import tokens


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class HashingEmbedder:
    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        t = " " + " ".join(tokens(text)) + " "
        v = [0.0] * self.dim
        for i in range(len(t) - 2):
            v[int(hashlib.md5(t[i:i + 3].encode()).hexdigest(), 16) % self.dim] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]


class CallableEmbedder:
    def __init__(self, fn: Callable[[str], list[float]]) -> None:
        self.fn = fn

    def embed(self, text: str) -> list[float]:
        v = self.fn(text)
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]


class HybridRetriever:
    def __init__(self, embedder: Embedder | None = None, w_lex: float = 0.7, w_sem: float = 0.3) -> None:
        self.embedder = embedder or HashingEmbedder()
        self.w_lex, self.w_sem = w_lex, w_sem
        self._cache: dict[str, list[float]] = {}

    def _emb(self, text: str) -> list[float]:
        if text not in self._cache:
            self._cache[text] = self.embedder.embed(text)
        return self._cache[text]

    def rank(self, query: str, docs: dict[str, str]) -> dict[str, float]:
        n = len(docs)
        counts = {i: Counter(tokens(t)) for i, t in docs.items()}
        df: Counter = Counter()
        for c in counts.values():
            df.update(c.keys())

        def idf(t: str) -> float:
            return math.log((n + 1) / (df.get(t, 0) + 1)) + 1.0

        q = {t: c * idf(t) for t, c in Counter(tokens(query)).items()}
        qn = math.sqrt(sum(v * v for v in q.values())) or 1.0
        qe = self._emb(query)
        out = {}
        for i, c in counts.items():
            d = {t: k * idf(t) for t, k in c.items()}
            dn = math.sqrt(sum(v * v for v in d.values())) or 1.0
            lex = sum(w * d.get(t, 0.0) for t, w in q.items()) / (qn * dn)
            sem = max(0.0, sum(a * b for a, b in zip(qe, self._emb(docs[i]))))
            out[i] = self.w_lex * lex + self.w_sem * sem
        return out
