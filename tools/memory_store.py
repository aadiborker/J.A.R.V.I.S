from __future__ import annotations

import json
import re
import threading
from pathlib import Path

from config import MEMORY_PATH, ROOT_DIR

_lock = threading.Lock()
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


def _path() -> Path:
    p = Path(MEMORY_PATH)
    if not p.is_absolute():
        p = ROOT_DIR / p
    return p


def _default() -> dict:
    return {"facts": {}}


def load_memory() -> dict:
    path = _path()
    with _lock:
        if not path.is_file():
            return _default()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return _default()
        if not isinstance(data, dict):
            return _default()
        facts = data.get("facts")
        if not isinstance(facts, dict):
            facts = {}
        clean = {
            str(k): str(v)
            for k, v in facts.items()
            if isinstance(k, str) and isinstance(v, (str, int, float, bool))
        }
        return {"facts": clean}


def save_memory(data: dict) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"facts": dict((data or {}).get("facts") or {})}
    with _lock:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_key(key: str) -> str | None:
    k = re.sub(r"[^a-z0-9_]+", "_", (key or "").strip().lower()).strip("_")
    if not k or not _KEY_RE.match(k):
        return None
    return k


def remember(key: str = "", value: str = "", **_kwargs) -> dict:
    """Store a short fact. Keys like name, preference_city."""
    nk = normalize_key(key)
    val = " ".join(str(value or "").strip().split())
    if not nk:
        return {"ok": False, "message": "I need a simple key, like name or city."}
    if not val:
        return {"ok": False, "message": "I need a value to remember."}
    if len(val) > 200:
        return {"ok": False, "message": "That's too long to store as a single fact."}

    data = load_memory()
    data["facts"][nk] = val
    save_memory(data)
    return {
        "ok": True,
        "key": nk,
        "value": val,
        "message": f"Remembered {nk.replace('_', ' ')}: {val}.",
    }


def recall(key: str = "", **_kwargs) -> dict:
    nk = normalize_key(key)
    if not nk:
        return {"ok": False, "message": "Which fact should I recall?"}
    data = load_memory()
    if nk not in data["facts"]:
        return {"ok": False, "key": nk, "message": f"I don't have anything stored for {nk}."}
    val = data["facts"][nk]
    return {
        "ok": True,
        "key": nk,
        "value": val,
        "message": f"Your {nk.replace('_', ' ')} is {val}.",
    }


def list_memories(**_kwargs) -> dict:
    data = load_memory()
    facts = data["facts"]
    if not facts:
        return {"ok": True, "facts": {}, "message": "I don't have any saved facts yet."}
    lines = [f"{k.replace('_', ' ')}: {v}" for k, v in sorted(facts.items())]
    return {
        "ok": True,
        "facts": facts,
        "message": "Here's what I remember. " + "; ".join(lines) + ".",
    }


def format_memory_for_prompt() -> str:
    data = load_memory()
    facts = data.get("facts") or {}
    if not facts:
        return ""
    lines = [f"- {k}: {v}" for k, v in sorted(facts.items())]
    return (
        "Known user facts (use naturally; don't dump the list unless asked):\n"
        + "\n".join(lines)
    )


def build_system_prompt(base: str) -> str:
    extra = format_memory_for_prompt()
    if not extra:
        return base
    return f"{base}\n\n{extra}"
