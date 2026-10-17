"""Candidate search with an EXECUTING critic (Phase 3).

N candidate solutions are generated under different strategies; the model also writes its
OWN tests from the spec. Candidates are scored by actually running those tests. The hidden
verifier never leaks into selection.

Known failure modes (by design, reported in SearchInfo):
  - model-written tests can be wrong or weak -> a wrong candidate may win (not discriminative)
  - invalid/empty tests or all-zero scores -> falls back to candidate 0
"""
from __future__ import annotations
from dataclasses import dataclass, field
from ..models.client import Model
from .code_verifier import CodeVerifier, extract_code

STRATEGIES = [
    "Prefer the simplest correct approach.",
    "Enumerate edge cases first (empty input, duplicates, boundaries), then implement.",
    "Think about worst-case complexity and input limits, then implement and re-check edge cases.",
]

TEST_PROMPT = (
    "TASK: {intent}\nWrite 5 to 8 python assert statements that check this spec, including edge cases. "
    "The function or class is already in scope. Reply with only one ```python block."
)


@dataclass
class SearchInfo:
    n: int
    scores: list[float] = field(default_factory=list)
    chosen: int = 0
    tests_total: int = 0
    discriminative: bool = False
    repaired: bool = False
    fallback: str = ""


class SearchExecutor:
    def __init__(self, model: Model, n: int = 3, repair_rounds: int = 1,
                 runner: CodeVerifier | None = None) -> None:
        self.model, self.n, self.repair_rounds = model, n, repair_rounds
        self.runner = runner or CodeVerifier()

    @staticmethod
    def _frac(s: dict) -> float:
        return s["passed"] / s["total"] if s["total"] else 0.0

    def run(self, intent: str, ctx: str) -> tuple[str, SearchInfo]:
        tests_src = extract_code(self.model.complete("test_writer", TEST_PROMPT.format(intent=intent), "slow"))
        cands = [self.model.complete(
            "executor", f"{ctx}\nSTRATEGY:{k + 1} {STRATEGIES[k % len(STRATEGIES)]}\nTASK: {intent}", "slow")
            for k in range(self.n)]
        scored = [self.runner.score_tests(c, tests_src) for c in cands]
        fr = [self._frac(s) for s in scored]
        info = SearchInfo(n=self.n, tests_total=scored[0]["total"])
        info.discriminative = info.tests_total > 0 and len(set(fr)) > 1
        best = max(range(self.n), key=lambda i: (fr[i], -i))
        if info.tests_total > 0 and fr[best] < 1.0:
            for _ in range(self.repair_rounds):
                fails = "; ".join(scored[best]["fails"][:3])
                rep = self.model.complete(
                    "executor", f"{ctx}\nREPAIR: this solution failed your own tests: {fails}\n"
                                f"PREVIOUS:\n{cands[best]}\nTASK: {intent}", "slow")
                rs = self.runner.score_tests(rep, tests_src)
                if self._frac(rs) > fr[best]:
                    cands[best], scored[best], fr[best] = rep, rs, self._frac(rs)
                    info.repaired = True
                else:
                    break
        if info.tests_total == 0:
            best, info.fallback = 0, "invalid or empty self-tests"
        elif max(fr) == 0.0:
            best, info.fallback = 0, "all candidates failed self-tests (tests or candidates wrong)"
        info.scores, info.chosen = [round(x, 3) for x in fr], best
        return cands[best], info
