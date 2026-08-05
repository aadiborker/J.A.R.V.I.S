from __future__ import annotations

import re
from typing import Optional

from tools.time_tools import get_time
from tools.timer_tools import format_t_minus


_TIME_PATTERNS = (
    re.compile(r"\bwhat\s+time\b", re.IGNORECASE),
    re.compile(r"\bcurrent\s+time\b", re.IGNORECASE),
    re.compile(r"\btime\s+is\s+it\b", re.IGNORECASE),
)

_TIMER_PATTERN = re.compile(
    r"\bset\s+(?:a\s+)?timer\s+for\s+(?P<num>\d+)\s*(?P<unit>seconds?|minutes?|hours?)\b",
    re.IGNORECASE,
)


def try_handle_simple(text: str, timer_manager) -> Optional[tuple[str, str]]:
    """Fast-path local handlers.

    Returns (print_text, speech_text) or None.
    """
    if not text or not text.strip():
        return None

    stripped = text.strip().lower()

    if any(p.search(stripped) for p in _TIME_PATTERNS):
        payload = get_time()
        print_text = f"It's {payload['time']} on {payload['date']}."
        speech_text = f"It's {payload['time']} on the {payload['date_spoken']}."
        return print_text, speech_text

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

        timer_manager.set_timer(seconds=seconds, label="", announce=False)
        announcement = format_t_minus(seconds)
        return announcement, announcement

    return None

