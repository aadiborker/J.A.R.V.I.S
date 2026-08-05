from __future__ import annotations

from dataclasses import dataclass
import datetime
import re
import sys

from config import (
    CONSOLE_BELL_ON_TIMER,
    CONSOLE_BELL_ON_WAKE,
    CONSOLE_NO_COLOR,
    CONSOLE_SHOW_TIMESTAMPS,
)
from ui.ws_bridge import emit_ui

_HAS_COLORAMA = False
if not CONSOLE_NO_COLOR:
    try:
        from colorama import Fore, Style, init as colorama_init

        colorama_init()
        _HAS_COLORAMA = True
    except Exception:  # noqa: BLE001
        _HAS_COLORAMA = False

if not _HAS_COLORAMA:
    class _Dummy:  # simple stand-in for Fore/Style constants
        def __getattr__(self, _name: str) -> str:
            return ""

    Fore = _Dummy()  # type: ignore[assignment]
    Style = _Dummy()  # type: ignore[assignment]


@dataclass(frozen=True)
class Theme:
    user: str = Fore.CYAN if _HAS_COLORAMA else ""
    jarvis: str = Fore.GREEN if _HAS_COLORAMA else ""
    system: str = Fore.YELLOW if _HAS_COLORAMA else ""
    thinking: str = Fore.MAGENTA if _HAS_COLORAMA else ""
    error: str = Fore.RED if _HAS_COLORAMA else ""
    timer: str = Fore.BLUE if _HAS_COLORAMA else ""


THEME = Theme()


def _clear_line() -> str:
    # ANSI clear line + carriage return. If colorama is off, this still works in most terminals.
    return "\r\033[2K"


_IST_TZ = datetime.timezone(datetime.timedelta(hours=5, minutes=30), name="IST")


def _status_prefix() -> str:
    if not CONSOLE_SHOW_TIMESTAMPS:
        return ""
    now = datetime.datetime.now(datetime.timezone.utc).astimezone(_IST_TZ)
    return now.strftime("[%H:%M:%S] ")


def _infer_state(text: str) -> str:
    lowered = text.lower()
    if "error" in lowered:
        return "error"
    if "[speak]" in lowered or "speaking" in lowered:
        return "speaking"
    if "[think]" in lowered or "thinking" in lowered:
        return "thinking"
    if "[idle]" in lowered or "hey jarvis" in lowered:
        return "idle"
    if "[session]" in lowered or "listening" in lowered or "[boot]" in lowered:
        return "listening"
    if "[wake]" in lowered:
        return "listening"
    return "listening"


def set_status(text: str) -> None:
    """Update a single-line status (overwrites the current line)."""
    print(f"{_clear_line()}{_status_prefix()}{text}", end="", flush=True)
    emit_ui({"type": "status", "state": _infer_state(text), "detail": text})


def clear_status() -> None:
    print(_clear_line(), end="", flush=True)


def _bell() -> None:
    # ASCII bell (works in most terminals). It's safe if the terminal ignores it.
    sys.stdout.write("\a")
    sys.stdout.flush()


def maybe_bell(kind: str) -> None:
    if kind == "wake" and CONSOLE_BELL_ON_WAKE:
        _bell()
    elif kind == "timer" and CONSOLE_BELL_ON_TIMER:
        _bell()


def cprefix(prefix: str, color: str) -> str:
    if not prefix:
        return ""
    return f"{color}{prefix}{Style.RESET_ALL if _HAS_COLORAMA else ''} "


def log_user(text: str) -> None:
    print(f"{cprefix('You:', THEME.user)}{text}")
    emit_ui({"type": "transcript", "role": "user", "text": text})


def log_jarvis(text: str) -> None:
    print(f"{cprefix('Jarvis:', THEME.jarvis)}{text}")
    emit_ui({"type": "transcript", "role": "jarvis", "text": text})


def log_system(text: str) -> None:
    if _HAS_COLORAMA:
        print(f"{THEME.system}{text}{Style.RESET_ALL}")
    else:
        print(text)
    emit_ui({"type": "transcript", "role": "system", "text": text})
    if "[WAKE]" in text:
        match = re.search(r"score=([0-9.]+)", text)
        score = float(match.group(1)) if match else 0.0
        emit_ui({"type": "wake", "score": score})


def log_thinking(text: str = "Thinking...") -> None:
    if _HAS_COLORAMA:
        print(f"{THEME.thinking}{text}{Style.RESET_ALL}")
    else:
        print(text)
    emit_ui({"type": "status", "state": "thinking", "detail": text})


def log_error(text: str) -> None:
    print(f"{cprefix('Error:', THEME.error)}{text}")
    emit_ui({"type": "error", "message": text})
    emit_ui({"type": "status", "state": "error", "detail": text})


def log_timer(text: str) -> None:
    maybe_bell("timer")
    print(f"{cprefix('Timer:', THEME.timer)}[TIMER] {text}")
    emit_ui({"type": "transcript", "role": "system", "text": f"[TIMER] {text}"})
