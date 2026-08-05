from __future__ import annotations

import re
from typing import Optional

from tools.time_tools import get_time


_TIME_PATTERNS = (
    re.compile(r"\bwhat\s+time\b", re.IGNORECASE),
    re.compile(r"\bcurrent\s+time\b", re.IGNORECASE),
    re.compile(r"\btime\s+is\s+it\b", re.IGNORECASE),
)

_TIMER_PATTERN = re.compile(
    r"\bset\s+(?:a\s+)?timer\s+for\s+(?P<num>\d+)\s*(?P<unit>seconds?|minutes?|hours?)\b",
    re.IGNORECASE,
)


def try_handle_simple(text: str, timer_manager) -> Optional[str]:
    if not text or not text.strip():
        return None

    stripped = text.strip().lower()

    if any(p.search(stripped) for p in _TIME_PATTERNS):
        payload = get_time()
        return f"It's {payload['time']}."

    m = _TIMER_PATTERN.search(stripped)
    if m:
        num = int(m.group("num"))
        unit = m.group("unit").lower()
        if unit.startswith("second"):
            seconds = num
        elif unit.startswith("minute"):
            seconds = num * 60
        else:
            seconds = num * 3600

        timer_manager.set_timer(seconds=seconds, label="")
        return f"Timer set for {num} {unit}."

    return None

