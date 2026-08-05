from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Canonical name -> (display label, executable candidates / PATH names)
_APP_SPECS: dict[str, tuple[str, list[str]]] = {
    "notepad": ("Notepad", ["notepad.exe", "notepad"]),
    "calculator": ("Calculator", ["calc.exe", "calc"]),
    "paint": ("Paint", ["mspaint.exe", "mspaint"]),
    "cmd": ("Command Prompt", ["cmd.exe", "cmd"]),
    "powershell": ("PowerShell", ["powershell.exe", "powershell"]),
    "explorer": ("File Explorer", ["explorer.exe", "explorer"]),
    "chrome": (
        "Chrome",
        [
            "chrome.exe",
            "chrome",
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
            r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
        ],
    ),
    "edge": (
        "Microsoft Edge",
        [
            "msedge.exe",
            "msedge",
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
            r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
        ],
    ),
    "spotify": (
        "Spotify",
        [
            "spotify.exe",
            "Spotify.exe",
            r"%AppData%\Spotify\Spotify.exe",
            r"%LocalAppData%\Microsoft\WindowsApps\Spotify.exe",
        ],
    ),
}

# Spoken / typed aliases -> canonical name
_ALIASES: dict[str, str] = {
    "notepad": "notepad",
    "note pad": "notepad",
    "calculator": "calculator",
    "calc": "calculator",
    "paint": "paint",
    "mspaint": "paint",
    "cmd": "cmd",
    "command prompt": "cmd",
    "terminal": "cmd",
    "powershell": "powershell",
    "power shell": "powershell",
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "edge",
    "microsoft edge": "edge",
    "spotify": "spotify",
}


def list_allowlisted_apps() -> list[str]:
    return sorted(_APP_SPECS.keys())


def normalize_app_name(name: str) -> str | None:
    key = " ".join((name or "").strip().lower().split())
    if not key:
        return None
    if key in _ALIASES:
        return _ALIASES[key]
    # Strip trailing .exe
    if key.endswith(".exe"):
        key = key[:-4]
        if key in _ALIASES:
            return _ALIASES[key]
    return None


def _expand(path: str) -> str:
    return os.path.expandvars(path)


def resolve_app_path(canonical: str) -> str | None:
    spec = _APP_SPECS.get(canonical)
    if not spec:
        return None
    _, candidates = spec
    for candidate in candidates:
        expanded = _expand(candidate)
        if os.path.sep in expanded or (sys.platform == "win32" and "\\" in expanded):
            p = Path(expanded)
            if p.is_file():
                return str(p)
            continue
        found = shutil.which(candidate)
        if found:
            return found
    return None


def open_app(name: str = "", **_kwargs) -> dict:
    """Launch an allowlisted desktop app. Returns status message dict."""
    canonical = normalize_app_name(name)
    if canonical is None:
        allowed = ", ".join(list_allowlisted_apps())
        return {
            "ok": False,
            "message": f"I can only open these apps: {allowed}.",
        }

    label = _APP_SPECS[canonical][0]
    path = resolve_app_path(canonical)
    if not path:
        return {
            "ok": False,
            "app": canonical,
            "message": f"I couldn't find {label} on this PC.",
        }

    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen([path], start_new_session=True)
    except OSError as exc:
        return {
            "ok": False,
            "app": canonical,
            "path": path,
            "message": f"Couldn't open {label}: {exc}",
        }

    return {
        "ok": True,
        "app": canonical,
        "path": path,
        "message": f"Opening {label}.",
    }
