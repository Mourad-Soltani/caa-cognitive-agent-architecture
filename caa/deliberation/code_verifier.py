"""Executable verification: run candidate code + asserts in a subprocess.

Isolation here = temp dir, python -I style flags, CPU/memory rlimits, wall timeout.
It does NOT block network or the filesystem: run untrusted model code inside a
container with no network before using this on anything real.
"""
from __future__ import annotations
import ast
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from ..core.schemas import Task, Verdict

_SAFE_ENV = {"PATH": "/usr/bin:/bin"}  # never pass API keys or other secrets to model-written code

_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)


def extract_code(output: str) -> str:
    m = _FENCE.search(output)
    return m.group(1) if m else output


def _limits(mem_mb: int, cpu_s: int):
    def apply():
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (mem_mb * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
    return apply


class CodeVerifier:
    def __init__(self, timeout: float = 5.0, mem_mb: int = 512) -> None:
        self.timeout, self.mem_mb = timeout, mem_mb

    def check(self, task: Task, output: str) -> tuple[Verdict, str]:
        code = extract_code(output)
        with tempfile.TemporaryDirectory() as d:
            Path(d, "solution.py").write_text(code)
            Path(d, "run_tests.py").write_text(
                "import sys; sys.path.insert(0, '.')\nfrom solution import *\n" + task.meta["tests"])
            try:
                p = subprocess.run([sys.executable, "-I", "-E", "-s", "run_tests.py"], cwd=d,
                                   capture_output=True, text=True, timeout=self.timeout,
                                   preexec_fn=_limits(self.mem_mb, int(self.timeout) + 1), env=_SAFE_ENV)
            except subprocess.TimeoutExpired:
                return "fail", "timeout: solution exceeded time limit"
        if p.returncode == 0:
            return "pass", "all tests passed"
        return "fail", (p.stderr or p.stdout).strip()[-600:]


_SCORER = """import sys, ast, json
sys.path.insert(0, '.')
from solution import *
g = dict(globals())
tree = ast.parse(open('tests_src.py').read())
res = {"passed": 0, "total": len(tree.body), "fails": []}
for node in tree.body:
    try:
        exec(compile(ast.Module([node], []), 'tests', 'exec'), g)
        res["passed"] += 1
    except BaseException as e:
        res["fails"].append(repr(e)[:160])
print(json.dumps(res))
"""


def _score_tests(self, output: str, tests_src: str) -> dict:
    """Partial-credit run of model-written tests (one result per top-level statement).
    total == 0 means the tests were invalid or empty, i.e. they cannot discriminate."""
    try:
        total = len(ast.parse(tests_src).body)
    except SyntaxError as e:
        return {"passed": 0, "total": 0, "fails": [f"invalid tests: {e}"]}
    if total == 0:
        return {"passed": 0, "total": 0, "fails": ["no tests"]}
    with tempfile.TemporaryDirectory() as d:
        Path(d, "solution.py").write_text(extract_code(output))
        Path(d, "tests_src.py").write_text(tests_src)
        Path(d, "scorer.py").write_text(_SCORER)
        try:
            p = subprocess.run([sys.executable, "-I", "-E", "-s", "scorer.py"], cwd=d, capture_output=True,
                               text=True, timeout=self.timeout,
                               preexec_fn=_limits(self.mem_mb, int(self.timeout) + 1), env=_SAFE_ENV)
        except subprocess.TimeoutExpired:
            return {"passed": 0, "total": total, "fails": ["timeout"]}
    if p.returncode != 0:
        return {"passed": 0, "total": total, "fails": [(p.stderr or "error").strip()[-200:]]}
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"passed": 0, "total": total, "fails": ["unparseable scorer output"]}


CodeVerifier.score_tests = _score_tests
