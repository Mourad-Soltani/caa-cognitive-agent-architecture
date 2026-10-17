"""Provider-agnostic model client.

MockModel is deterministic and needs no network: it exists to test plumbing
(routing, memory, reflection, eval). It is NOT evidence of intelligence.
AnthropicModel is a thin stdlib client; it is untested in this repo's CI.
"""
from __future__ import annotations
import json
import os
import re
import urllib.request
from typing import Protocol


class Model(Protocol):
    def complete(self, role: str, prompt: str, tier: str = "fast") -> str: ...


class MockModel:
    """Follows 'RULE: 1 X = N Y' lines found in the prompt; fails otherwise."""

    def __init__(self) -> None:
        self.calls = {"fast": 0, "slow": 0}

    def complete(self, role: str, prompt: str, tier: str = "fast") -> str:
        self.calls[tier] = self.calls.get(tier, 0) + 1
        if role == "planner":
            return "1. find applicable rule 2. compute"
        if role == "critic":
            return "OBJECTION: no answer produced" if "unknown" in prompt.lower() else "OK"
        if role == "reflector":
            m = re.search(r"FEEDBACK: (.*)", prompt)
            return f"RULE: {m.group(1).strip()}" if m else ""
        return self._execute(prompt)

    @staticmethod
    def _execute(prompt: str) -> str:
        m = re.search(r"What is (\d+) plus (\d+)\?", prompt)
        if m:
            return str(int(m.group(1)) + int(m.group(2)))
        q = re.search(r"How many (\w+) in (\d+) (\w+)\?", prompt)
        if q:
            to_u, k, from_u = q.group(1), int(q.group(2)), q.group(3)
            for r in re.finditer(r"RULE: 1 (\w+) = (\d+) (\w+)", prompt):
                if r.group(1) == from_u and r.group(3) == to_u:
                    return str(k * int(r.group(2)))
        return "unknown"


class AnthropicModel:
    """Minimal Messages API client. Needs ANTHROPIC_API_KEY. Untested in this repo's CI.

    Default model IDs are placeholders — pass real provider IDs for your account.
    """

    def __init__(self, fast: str = "claude-3-5-haiku-latest", slow: str = "claude-sonnet-4-20250514") -> None:
        self.models = {"fast": fast, "slow": slow}
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.key = key

    def complete(self, role: str, prompt: str, tier: str = "fast") -> str:
        body = json.dumps({
            "model": self.models[tier],
            "max_tokens": 1000,
            "system": f"You are the {role} agent. Be concise and exact.",
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=body, method="POST",
            headers={"content-type": "application/json", "x-api-key": self.key,
                     "anthropic-version": "2023-06-01"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
        return "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
