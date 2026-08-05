from __future__ import annotations

import re
from typing import Optional

from net.connectivity import is_online
from tools.app_tools import normalize_app_name, open_app
from tools.browser_tools import (
    BROWSER_OFFLINE_REPLY,
    open_url,
    open_youtube,
    youtube_play,
    youtube_search,
)
from tools.system_tools import (
    get_system_status,
    lock_pc,
    set_brightness,
    set_mute,
    set_volume,
    take_screenshot,
)
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

_OPEN_YOUTUBE = re.compile(
    r"^\s*open\s+you\s*tube\s*$",
    re.IGNORECASE,
)

_YOUTUBE_SEARCH = re.compile(
    r"^\s*(?:search\s+you\s*tube\s+for|you\s*tube\s+search)\s+(?P<query>.+?)\s*$",
    re.IGNORECASE,
)

_YOUTUBE_PLAY = re.compile(
    r"^\s*play\s+(?:the\s+)?(?P<query>.+?)(?:\s+on\s+you\s*tube)?\s*$",
    re.IGNORECASE,
)

_OPEN_URL = re.compile(
    r"^\s*open\s+(?P<target>(?:https?://\S+|(?:[\w-]+\.)+[a-z]{2,}(?:/\S*)?))\s*$",
    re.IGNORECASE,
)

_OPEN_APP = re.compile(
    r"^\s*(?:open|launch|start)\s+(?P<name>.+?)\s*$",
    re.IGNORECASE,
)

_SYSTEM_STATUS = re.compile(
    r"^\s*(?:"
    r"(?:(?:check|check\s+for|what(?:'s|\s+is)|show(?:\s+me)?)\s+(?:my\s+)?)?"
    r"(?:ram|memory)(?:\s+(?:usage|use|used|using|percent|load))?"
    r"(?:\s+(?:is\s+)?(?:the\s+)?(?:system\s+)?(?:using|used))?"
    r"|how\s+much\s+(?:ram|memory)(?:\s+(?:is\s+)?(?:the\s+)?(?:system\s+)?(?:using|used|usage))?"
    r"|system\s+status"
    r"|cpu\s+(?:usage|use|percent|load)"
    r"|how\s+(?:high|much)\s+is\s+(?:the\s+)?cpu"
    r"|what(?:'s|\s+is)\s+(?:my\s+)?(?:ram|memory|cpu)\s*(?:usage|use|percent)?"
    r")\s*[.!?]*\s*$",
    re.IGNORECASE,
)

_MUTE = re.compile(r"^\s*(?:mute|silence)(?:\s+(?:the\s+)?(?:pc|computer|audio|sound|volume))?\s*$", re.I)
_UNMUTE = re.compile(r"^\s*unmute(?:\s+(?:the\s+)?(?:pc|computer|audio|sound|volume))?\s*$", re.I)
_VOLUME = re.compile(
    r"^\s*(?:set\s+)?(?:the\s+)?volume\s+(?:to\s+)?(?P<level>\d{1,3})\s*(?:%|percent)?\s*$",
    re.I,
)
_BRIGHTNESS = re.compile(
    r"^\s*(?:set\s+)?(?:the\s+)?brightness\s+(?:to\s+)?(?P<level>\d{1,3})\s*(?:%|percent)?\s*$",
    re.I,
)
_LOCK = re.compile(
    r"^\s*(?:lock\s+(?:the\s+)?(?:pc|computer|workstation|screen)|lock\s+pc)\s*$",
    re.I,
)
_SCREENSHOT = re.compile(
    r"^\s*(?:take\s+(?:a\s+)?screenshot|screenshot|capture\s+(?:the\s+)?screen)\s*$",
    re.I,
)

# Apps that must not steal browser / youtube open phrases
_BROWSERISH_APP_NAMES = frozenset(
    {
        "youtube",
        "you tube",
        "yt",
    }
)


def _msg_reply(payload: dict) -> tuple[str, str]:
    msg = str(payload.get("message") or "").strip() or "Done."
    return msg, msg


def try_handle_simple(text: str, timer_manager) -> Optional[tuple[str, str]]:
    """Fast-path local handlers.

    Returns (print_text, speech_text) or None.
    """
    if not text or not text.strip():
        return None

    stripped = text.strip()
    lowered = stripped.lower()

    if any(p.search(lowered) for p in _TIME_PATTERNS):
        payload = get_time()
        print_text = f"It's {payload['time']} on {payload['date']}."
        speech_text = f"It's {payload['time']} on the {payload['date_spoken']}."
        return print_text, speech_text

    m = _TIMER_PATTERN.search(lowered)
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

    if _SYSTEM_STATUS.match(stripped):
        return _msg_reply(get_system_status())

    if _MUTE.match(stripped):
        return _msg_reply(set_mute(True))
    if _UNMUTE.match(stripped):
        return _msg_reply(set_mute(False))

    vol = _VOLUME.match(stripped)
    if vol:
        return _msg_reply(set_volume(int(vol.group("level"))))

    bri = _BRIGHTNESS.match(stripped)
    if bri:
        return _msg_reply(set_brightness(int(bri.group("level"))))

    if _LOCK.match(stripped):
        return _msg_reply(lock_pc())

    if _SCREENSHOT.match(stripped):
        return _msg_reply(take_screenshot())

    browser_hit = (
        _OPEN_YOUTUBE.match(stripped)
        or _YOUTUBE_SEARCH.match(stripped)
        or _YOUTUBE_PLAY.match(stripped)
        or _OPEN_URL.match(stripped)
    )
    if browser_hit and not is_online():
        return BROWSER_OFFLINE_REPLY, BROWSER_OFFLINE_REPLY

    if _OPEN_YOUTUBE.match(stripped):
        return _msg_reply(open_youtube())

    ys = _YOUTUBE_SEARCH.match(stripped)
    if ys:
        return _msg_reply(youtube_search(ys.group("query").strip()))

    yp = _YOUTUBE_PLAY.match(stripped)
    if yp:
        query = yp.group("query").strip()
        # Avoid stealing unrelated "play" phrases with no media intent.
        if query and not re.fullmatch(r"(?:a\s+)?(?:game|song)?", query, re.I):
            return _msg_reply(youtube_play(query))

    ou = _OPEN_URL.match(stripped)
    if ou:
        return _msg_reply(open_url(ou.group("target").strip()))

    # App open after URL / YouTube so "open https://…" stays browser.
    oa = _OPEN_APP.match(stripped)
    if oa:
        name = oa.group("name").strip()
        name_key = " ".join(name.lower().split())
        if name_key in _BROWSERISH_APP_NAMES:
            return None
        if "://" in name or ("." in name and " " not in name):
            return None
        # Only fast-path known allowlisted apps; leave other "open …" to Groq.
        if normalize_app_name(name) is None:
            return None
        return _msg_reply(open_app(name))

    return None
