from __future__ import annotations

import re
import subprocess
import sys
import threading
import webbrowser
from urllib.parse import quote_plus, urlparse

BROWSER_OFFLINE_REPLY = "Browser tools need a network connection."
BROWSER_REJECT_REPLY = "I can only open web links."

_YOUTUBE_HOME = "https://www.youtube.com"
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

_media_lock = threading.Lock()
_end_session_after_media = False


def request_session_end_after_media() -> None:
    """Ask main loop to leave conversation mode (avoid mic picking up video audio)."""
    global _end_session_after_media
    with _media_lock:
        _end_session_after_media = True


def consume_session_end_after_media() -> bool:
    global _end_session_after_media
    with _media_lock:
        flagged = _end_session_after_media
        _end_session_after_media = False
        return flagged


def normalize_and_validate_url(raw: str) -> str | None:
    """Return a safe http(s) URL, or None if rejected."""
    text = (raw or "").strip()
    if not text:
        return None

    # Strip wrapping quotes/brackets often heard in speech-to-text.
    text = text.strip("\"'<>")

    lower = text.lower()
    if "://" in text:
        scheme_hint = text.split("://", 1)[0].lower()
        if scheme_hint not in ("http", "https"):
            return None
    elif re.match(r"^[a-z][a-z0-9+.-]*:", lower):
        # e.g. javascript:alert(1) — not a bare domain
        return None
    else:
        text = "https://" + text

    try:
        parsed = urlparse(text)
    except Exception:  # noqa: BLE001
        return None

    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return None
    if not parsed.netloc:
        return None
    # Disallow credentials in netloc for safety.
    if "@" in parsed.netloc:
        return None
    if " " in parsed.netloc:
        return None
    # Bare hostnames should look like a domain (have a dot) unless localhost.
    host = parsed.hostname or ""
    if host != "localhost" and "." not in host:
        return None

    return parsed.geturl()


def open_url(url: str = "", **_kwargs) -> dict:
    """Open an http(s) URL in the default browser."""
    validated = normalize_and_validate_url(url)
    if not validated:
        return {
            "ok": False,
            "url": "",
            "message": BROWSER_REJECT_REPLY,
        }
    try:
        opened = webbrowser.open(validated)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "url": validated,
            "message": f"Could not open the browser ({exc}).",
        }
    if not opened:
        return {
            "ok": False,
            "url": validated,
            "message": "Could not open the browser.",
        }
    return {
        "ok": True,
        "url": validated,
        "message": f"Opening {validated}.",
    }


def open_youtube(**_kwargs) -> dict:
    result = open_url(_YOUTUBE_HOME)
    if result.get("ok"):
        result["message"] = "Opening YouTube."
    return result


def youtube_search(query: str = "", **_kwargs) -> dict:
    q = (query or "").strip()
    if not q:
        return {
            "ok": False,
            "url": "",
            "message": "What should I search on YouTube?",
        }
    url = f"{_YOUTUBE_HOME}/results?search_query={quote_plus(q)}"
    result = open_url(url)
    if result.get("ok"):
        result["message"] = f"Searching YouTube for {q}."
        result["query"] = q
    return result


def resolve_youtube_video_id(query: str) -> str | None:
    """Resolve the top YouTube search hit to an 11-char video id via yt-dlp."""
    q = (query or "").strip()
    if not q:
        return None
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "yt_dlp",
                "--skip-download",
                "--no-playlist",
                "--print",
                "%(id)s",
                f"ytsearch1:{q}",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if completed.returncode != 0:
        return None

    for line in completed.stdout.splitlines():
        candidate = line.strip()
        if _VIDEO_ID_RE.match(candidate):
            return candidate
    return None


def youtube_play(query: str = "", **_kwargs) -> dict:
    """Open the top matching YouTube video (watch page) in the default browser."""
    q = (query or "").strip()
    if not q:
        return {
            "ok": False,
            "url": "",
            "message": "What should I play on YouTube?",
        }

    video_id = resolve_youtube_video_id(q)
    if not video_id:
        # Fall back to search results if resolution fails.
        fallback = youtube_search(q)
        if fallback.get("ok"):
            fallback["message"] = (
                f"I couldn't open a direct video for {q}, so I opened the search results."
            )
        return fallback

    url = f"{_YOUTUBE_HOME}/watch?v={video_id}"
    result = open_url(url)
    if result.get("ok"):
        request_session_end_after_media()
        result["message"] = (
            f"Playing {q} on YouTube. I'll go quiet so the video isn't picked up — "
            "say hey jarvis when you need me."
        )
        result["query"] = q
        result["video_id"] = video_id
        result["end_session"] = True
    return result
