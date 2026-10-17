"""Offline stand-in coder for WIRING tests, not capability.

- no lesson in context: emits a broken solution (except under plan search, where exactly
  candidate 2 of 3 is correct, so selection mechanics can be exercised)
- lesson ('RULE:') in context: emits the reference
- test_writer: returns up to 3 single-line asserts from the hidden tests (deliberately weak),
  or 'assert True' when none exist, which exercises the fallback path
"""
import re
from .code_tasks import BROKEN, REFERENCE, _SPECS


class ScriptedCoder:
    def __init__(self) -> None:
        self.calls = {"fast": 0, "slow": 0}

    @staticmethod
    def _spec(prompt: str):
        for spec in _SPECS:
            if spec[1] in prompt:
                return spec
        return None

    def complete(self, role: str, prompt: str, tier: str = "fast") -> str:
        self.calls[tier] = self.calls.get(tier, 0) + 1
        if role == "planner":
            return "plan"
        if role == "critic":
            return "OK"
        if role == "reflector":
            m = re.search(r"FEEDBACK: (.*?)\nPropose", prompt, re.S)
            return "RULE: " + (m.group(1).strip().splitlines()[-1] if m else "check edge cases")
        spec = self._spec(prompt)
        if spec is None:
            return ""
        name, _, tests, *_ = spec
        if role == "test_writer":
            asserts = [ln for ln in tests.splitlines() if ln.startswith("assert ")][:3]
            return "```python\n" + ("\n".join(asserts) or "assert True") + "\n```"
        if "REPAIR:" in prompt:
            return BROKEN[name]  # neutral: scripted repair never fixes anything
        if "RULE:" in prompt:
            return REFERENCE[name]
        m = re.search(r"STRATEGY:(\d)", prompt)
        if m:
            return REFERENCE[name] if m.group(1) == "2" else BROKEN[name]
        return BROKEN[name]
