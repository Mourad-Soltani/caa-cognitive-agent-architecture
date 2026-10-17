from __future__ import annotations
from ..core.schemas import Task, Verdict
from .code_verifier import CodeVerifier


class Verifier:
    """Strongest ground truth first: domain checker > executable tests > expected answer > unverifiable."""

    def __init__(self) -> None:
        self.code = CodeVerifier()

    def check(self, task: Task, output: str) -> tuple[Verdict, str]:
        chk = task.meta.get("check")  # domain-supplied property checker: output -> (verdict, note)
        if callable(chk):
            return chk(output)
        if task.meta.get("tests"):
            return self.code.check(task, output)
        expected = task.meta.get("expected")
        if expected is not None:
            ok = output.strip() == str(expected).strip()
            return ("pass" if ok else "fail"), "expected-answer match"
        return "unverifiable", "no ground truth available"
