# Phase 2 Groq Chat Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After microphone transcription, send text to Groq (`llama-3.1-8b-instant`), print the reply, and keep in-session multi-turn history until process exit.

**Architecture:** Thin `llm/client.py` wraps the official `groq` SDK. `main.py` loads dotenv, builds a messages list starting with `SYSTEM_PROMPT`, and after each non-empty transcript calls `chat(messages)`, prints `Jarvis: ...`, and appends the assistant turn. No TTS, wake word, or tools.

**Tech Stack:** Python 3.10+, `groq`, `python-dotenv`, existing Phase 1 STT stack.

## Global Constraints

- Windows / PowerShell-compatible commands (no bash heredocs).
- Phase 2 only: no Piper, openWakeWord, tool-calling, or `memory/history.json`.
- Model: `llama-3.1-8b-instant` (config-driven for later upgrade).
- In-memory multi-turn only; lost on restart.
- Never commit `.env` or real API keys; provide `.env.example` only.
- Voice output remains text-only in the console.
- Continue on branch `phase1-stt` (or create `phase2-groq` from it); do not put secrets in commits.

## File Structure

| Path | Responsibility |
|------|----------------|
| `.env.example` | Documents `GROQ_API_KEY=` without a real value |
| `.env` | Local secret file created by user (gitignored already) |
| `config.py` | Add `GROQ_MODEL`, `SYSTEM_PROMPT` |
| `llm/__init__.py` | Package marker |
| `llm/client.py` | `ensure_api_key()`, `get_client()`, `chat(messages) -> str` |
| `main.py` | Wire STT → chat → print; session messages |
| `requirements.txt` | Add `groq` |
| `tests/test_llm_client.py` | Mocked unit tests for client helpers |
| `README.md` | Phase 2 `.env` + run instructions |

---

### Task 1: Config, deps, and env example

**Files:**
- Modify: `config.py`
- Modify: `requirements.txt`
- Create: `.env.example`
- Modify: `README.md` (Phase 2 setup section)

**Interfaces:**
- Consumes: existing `config.py` paths
- Produces: `config.GROQ_MODEL: str`, `config.SYSTEM_PROMPT: str`

- [ ] **Step 1: Update `config.py`**

Append after existing constants:

```python
GROQ_MODEL = "llama-3.1-8b-instant"
SYSTEM_PROMPT = (
    "You are Jarvis, a helpful personal voice assistant. "
    "Keep answers concise and conversational so they work well when spoken aloud later. "
    "Do not mention that you are an AI model unless asked."
)
```

- [ ] **Step 2: Add `groq` to `requirements.txt`**

Final file:

```text
sounddevice>=0.5.0
numpy>=1.26.0
scipy>=1.11.0
python-dotenv>=1.0.0
pytest>=8.0.0
groq>=0.11.0
```

- [ ] **Step 3: Create `.env.example`**

```text
GROQ_API_KEY=your_groq_api_key_here
```

- [ ] **Step 4: Update `README.md` to include Phase 2**

Replace contents with:

```markdown
# J.A.R.V.I.S — Phase 1–2 (Local STT + Groq Chat)

Records a short microphone clip, transcribes with whisper.cpp (`base.en`), sends text to Groq, prints the reply.

## Prerequisites

- Windows x64
- Python 3.10+
- Working microphone
- Free Groq API key from https://console.groq.com/keys

## One-time setup

1. Install deps:

```powershell
pip install -r requirements.txt
```

2. Whisper binary: download [whisper-bin-x64.zip (v1.9.1)](https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.1/whisper-bin-x64.zip), copy `whisper-cli.exe` + DLLs into `vendor/whisper/`.

3. Model:

```powershell
Invoke-WebRequest -Uri "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin" -OutFile "models\ggml-base.en.bin"
```

4. Create `.env` in the project root (copy from `.env.example`):

```powershell
Copy-Item .env.example .env
# Then edit .env and set GROQ_API_KEY to your real key
```

## Run

```powershell
python main.py
```

Press Enter, speak, wait for `You said:` and `Jarvis:`.

## Tests

```powershell
python -m pytest tests -v
```
```

- [ ] **Step 5: Install groq and commit**

```powershell
pip install "groq>=0.11.0"
git add config.py requirements.txt .env.example README.md
git commit -m "Add Phase 2 Groq config and env example."
```

Verify `.env` is not staged (`git status` must not list `.env` with a real key).

---

### Task 2: LLM client (TDD)

**Files:**
- Create: `llm/__init__.py`
- Create: `llm/client.py`
- Create: `tests/test_llm_client.py`

**Interfaces:**
- Consumes: `config.GROQ_MODEL`, env `GROQ_API_KEY`
- Produces:
  - `ensure_api_key() -> str` (raises `RuntimeError` if missing/blank)
  - `get_client() -> groq.Groq`
  - `chat(messages: list[dict[str, str]], *, client: groq.Groq | None = None) -> str`

- [ ] **Step 1: Write failing tests**

Create `tests/test_llm_client.py`:

```python
from types import SimpleNamespace

import pytest

from llm.client import chat, ensure_api_key


def test_ensure_api_key_missing(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        ensure_api_key()


def test_ensure_api_key_blank(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "   ")
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        ensure_api_key()


def test_ensure_api_key_ok(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    assert ensure_api_key() == "gsk_test"


def test_chat_returns_assistant_text(monkeypatch):
    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["model"] == "llama-3.1-8b-instant"
            assert kwargs["messages"][0]["role"] == "system"
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="  hello there  "))]
            )

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]
    assert chat(messages, client=FakeClient()) == "hello there"
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest tests/test_llm_client.py -v
```

Expected: FAIL with `ModuleNotFoundError` for `llm.client`.

- [ ] **Step 3: Implement `llm/__init__.py` and `llm/client.py`**

`llm/__init__.py`:

```python
"""Groq LLM client helpers."""
```

`llm/client.py`:

```python
from __future__ import annotations

import os
from typing import Any

from groq import Groq

from config import GROQ_MODEL


def ensure_api_key() -> str:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Copy .env.example to .env and set your Groq API key."
        )
    return key


def get_client() -> Groq:
    return Groq(api_key=ensure_api_key())


def chat(messages: list[dict[str, str]], *, client: Any | None = None) -> str:
    groq_client = client if client is not None else get_client()
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
    )
    content = response.choices[0].message.content
    if content is None:
        return ""
    return str(content).strip()
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/test_llm_client.py -v
```

Expected: all four tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add llm/__init__.py llm/client.py tests/test_llm_client.py
git commit -m "Add Groq chat client with mocked unit tests."
```

---

### Task 3: Wire `main.py` chat loop

**Files:**
- Modify: `main.py`

**Interfaces:**
- Consumes: `ensure_whisper_ready`, `transcribe_microphone`, `ensure_api_key`, `chat`, `SYSTEM_PROMPT`
- Produces: interactive loop printing `You said:` and `Jarvis:`

- [ ] **Step 1: Replace `main.py` with Phase 2 loop**

```python
from __future__ import annotations

import sys

from dotenv import load_dotenv

from config import SYSTEM_PROMPT
from llm.client import chat, ensure_api_key
from stt.transcribe import ensure_whisper_ready, transcribe_microphone


def main() -> int:
    load_dotenv()

    try:
        ensure_whisper_ready()
        ensure_api_key()
    except (FileNotFoundError, RuntimeError) as exc:
        print(exc, file=sys.stderr)
        return 1

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    print("Phase 2 STT + Groq ready.")
    print("Press Enter to record, or Ctrl+C to quit.")

    while True:
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0

        print("Recording...")
        try:
            text = transcribe_microphone()
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}", file=sys.stderr)
            continue

        if not text:
            print("You said: (no speech detected)")
            print("Press Enter to record again, or Ctrl+C to quit.")
            continue

        print(f"You said: {text}")
        messages.append({"role": "user", "content": text})

        print("Thinking...")
        try:
            reply = chat(messages)
        except Exception as exc:  # noqa: BLE001
            print(f"Groq error: {exc}", file=sys.stderr)
            messages.pop()  # remove failed user turn so history stays consistent
            print("Press Enter to record again, or Ctrl+C to quit.")
            continue

        messages.append({"role": "assistant", "content": reply})
        print(f"Jarvis: {reply}")
        print("Press Enter to record again, or Ctrl+C to quit.")


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run full unit test suite**

```powershell
python -m pytest tests -v
```

Expected: all existing STT tests + LLM tests PASS.

- [ ] **Step 3: Commit**

```powershell
git add main.py
git commit -m "Wire Groq multi-turn chat into main STT loop."
```

---

### Task 4: Local `.env` and manual verification

**Files:**
- Create locally (not committed): `.env`

**Interfaces:**
- Consumes: user Groq API key
- Produces: verified end-to-end voice → Groq → console

- [ ] **Step 1: Create `.env` without printing the key**

Instruct the user (or run interactively) to create `.env`:

```powershell
Copy-Item .env.example .env
notepad .env
```

User pastes `GROQ_API_KEY=...` themselves. Do **not** echo the key in terminal logs or chat.

- [ ] **Step 2: Confirm git ignores `.env`**

```powershell
git status
git check-ignore -v .env
```

Expected: `.env` is ignored; not listed as untracked for commit.

- [ ] **Step 3: Manual end-to-end verification**

```powershell
python main.py
```

1. Press Enter, ask a factual question → see `You said:` and `Jarvis:`.
2. Press Enter again, ask a follow-up that needs prior context → reply should reference it.
3. Ctrl+C exits cleanly.
4. Confirm no TTS/wake-word/tool modules were added beyond `llm/`.

- [ ] **Step 4: No commit of secrets**

If any change remains, commit only code/docs — never `.env`.

---

## Plan Self-Review

1. **Spec coverage:** Architecture, `llama-3.1-8b-instant`, in-session multi-turn, `.env` / `.env.example`, `llm/client.py`, main loop print labels, empty-transcript skip, Groq error survival, mocked tests, README — covered in Tasks 1–4. TTS explicitly out of scope.
2. **Placeholders:** None; full code and commands included.
3. **Type consistency:** `ensure_api_key() -> str`, `get_client() -> Groq`, `chat(messages, *, client=None) -> str` match across Task 2 tests, implementation, and Task 3 `main.py`.
