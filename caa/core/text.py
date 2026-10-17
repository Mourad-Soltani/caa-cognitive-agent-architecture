import re

_STOP = {"the", "a", "an", "of", "in", "is", "to", "and", "how", "many", "what", "are", "for",
         "reply", "only", "one", "python", "code", "block", "write", "returning", "that"}


def tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in _STOP and not t.isdigit()]
