"""Global workspace v0: planner -> executor -> critic, selector keeps the best unblocked action."""
from __future__ import annotations
from ..core.schemas import Proposal
from ..models.client import Model


class Workspace:
    def __init__(self, model: Model) -> None:
        self.model = model
        self.board: list[Proposal] = []

    def _post(self, author: str, ptype: str, content: str) -> Proposal:
        p = Proposal(author=author, type=ptype, content=content)
        self.board.append(p)
        return p

    def run(self, intent: str, ctx: str) -> str:
        plan = self._post("planner", "plan",
                          self.model.complete("planner", f"{ctx}\nTASK: {intent}", "slow"))
        act = self._post("executor", "action", self.model.complete(
            "executor", f"{ctx}\nPLAN: {plan.content}\nTASK: {intent}", "slow"))
        verdict = self.model.complete("critic", f"TASK: {intent}\nANSWER: {act.content}", "slow")
        if verdict.startswith("OBJECTION"):
            self._post("critic", "objection", verdict)
            act = self._post("executor", "action", self.model.complete(
                "executor", f"{ctx}\nPLAN: {plan.content}\n{verdict}\nTASK: {intent}", "slow"))
        return act.content
