from ..core.schemas import Verdict


def confidence(output: str, verdict: Verdict) -> float:
    if not output.strip() or "unknown" in output.lower():
        return 0.1
    return {"pass": 0.95, "fail": 0.2, "unverifiable": 0.5}[verdict]


ESCALATE_BELOW = 0.6
