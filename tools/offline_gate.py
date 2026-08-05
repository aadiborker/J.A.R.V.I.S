from __future__ import annotations

from typing import Optional

from net.connectivity import is_online
from tools.simple_commands import try_handle_simple

OFFLINE_CHAT_REPLY = (
    "Network's out — I'm on lower modules. Time, timers, apps, and system controls still work."
)


def handle_offline_or_simple(text: str, timer_manager) -> Optional[tuple[str, str]]:
    """Return (print, speech) for local/offline handling, else None to use Groq."""
    simple = try_handle_simple(text, timer_manager)
    if simple is not None:
        return simple
    if not is_online():
        return OFFLINE_CHAT_REPLY, OFFLINE_CHAT_REPLY
    return None
