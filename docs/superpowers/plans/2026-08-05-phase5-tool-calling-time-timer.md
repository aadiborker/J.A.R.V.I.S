# Phase 5 Tool Calling (Time + Timer) Implementation Plan
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable Groq native tool-calling for `get_time` and `set_timer`, with regex/local fast paths for clear time/timer requests.

**Architecture:** Add a small tool execution layer (`llm/tool_loop.py`) that repeatedly calls Groq with `tools=[...]` until the model returns final `message.content`. Add Python tool implementations for time and timers. Timer reminders run in the background and pause wake-word scoring while speaking the reminder.

**Tech Stack:** Python 3.10+, `groq` SDK, existing whisper.cpp + Piper, `threading`, unit tests via `pytest`.

## Global Constraints
- Use **Groq native tools / function calls** (not JSON scraping).
- Support simple **regex/local fast paths** for clear “what time is it” and “set a timer for X …” requests.
- Timer reminders **speak immediately when due** and must **pause wake-word scoring while speaking** (avoid self-trigger).

---

### Task 1: Wake-word pause hook (so timer reminders don’t re-trigger)

**Files:**
- Modify: `wakeword/listen.py`
- Modify: `tests/test_wakeword.py`

**Interfaces:**
- Consumes: `openwakeword.model.Model` and current `wait_for_wake_word()` behavior.
- Produces:
  - `wait_for_wake_word(..., wakeword_pause_event: threading.Event | None = None) -> float`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_wakeword.py`:

```python
import threading
import numpy as np

from wakeword import listen as listen_mod


def test_wait_for_wake_word_skips_scoring_while_paused():
    class FakeModel:
        def __init__(self):
            self.calls = 0

        def predict(self, frame):
            self.calls += 1
            # Always below threshold; we control the score via the call count
            return {"hey jarvis": 0.9 if self.calls >= 2 else 0.1}

    paused = threading.Event()
    paused.set()
    model = FakeModel()

    def fake_read_chunk():
        # Unpause after the first read so predict is skipped once,
        # then runs again and triggers detection.
        paused.clear()
        return np.zeros(1280, dtype=np.int16)

    detected_scores = []
    score = listen_mod.wait_for_wake_word(
        model=model,
        threshold=0.5,
        read_chunk=fake_read_chunk,
        on_detect=lambda: detected_scores.append(True),
        wakeword_pause_event=paused,
        show_scores=False,
    )

    assert score >= 0.5
    assert detected_scores == [True]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_wakeword.py -v
```

Expected: FAIL because `wait_for_wake_word` does not yet accept `wakeword_pause_event`.

- [ ] **Step 3: Write minimal implementation**

Update `wakeword/listen.py`:

```python
import threading

# ... keep existing imports ...

def wait_for_wake_word(
    *,
    model: Model | None = None,
    threshold: float | None = None,
    read_chunk: Callable[[], np.ndarray] | None = None,
    on_detect: Callable[[], None] | None = play_wakeup_chime,
    show_scores: bool = True,
    wakeword_pause_event: threading.Event | None = None,
) -> float:
    oww = model if model is not None else get_model()
    reset_model(oww)
    limit = WAKEWORD_THRESHOLD if threshold is None else float(threshold)

    if read_chunk is not None:
        while True:
            frame = _to_int16_mono(read_chunk())
            if wakeword_pause_event is not None and wakeword_pause_event.is_set():
                continue
            prediction = oww.predict(frame)
            score = _score_for_wakeword(prediction)
            if score >= limit:
                if on_detect is not None:
                    on_detect()
                reset_model(oww)
                return score

    # streaming path
    chunk = WAKEWORD_CHUNK_SAMPLES
    frames_since_log = 0
    best = 0.0

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=chunk,
        device=INPUT_DEVICE,
    ) as stream:
        while True:
            raw, overflowed = stream.read(chunk)
            if overflowed and show_scores:
                print("Wake-word mic overflow (audio glitch); continuing...")
            frame = _to_int16_mono(raw)

            if wakeword_pause_event is not None and wakeword_pause_event.is_set():
                continue

            prediction = oww.predict(frame)
            score = _score_for_wakeword(prediction)
            best = max(best, score)
            frames_since_log += 1

            if show_scores and frames_since_log >= 25:
                print(f"  listening… peak score={best:.3f} (need ≥ {limit:.2f})")
                frames_since_log = 0
                best = 0.0

            if score >= limit:
                if on_detect is not None:
                    on_detect()
                reset_model(oww)
                return score
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/test_wakeword.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add wakeword/listen.py tests/test_wakeword.py
git commit -m "feat: pause wakeword scoring during speaking"
```

---

### Task 2: Implement TimerManager (background timers + speak + wakeword pause)

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/timer_tools.py`
- Create: `tests/test_timer_tools.py`

**Interfaces:**
- Produces:
  - `class TimerManager`
    - `set_timer(self, seconds: int, label: str = "") -> dict[str, str | int]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_timer_tools.py`:

```python
import threading
import time

import pytest

from tools.timer_tools import TimerManager


def test_timer_manager_speaks_and_pauses_wakeword():
    paused = threading.Event()
    spokens: list[str] = []

    def speak_fn(text: str) -> None:
        # While speaking, wakeword pause should be set
        assert paused.is_set()
        spokens.append(text)

    mgr = TimerManager(
        speak_fn=speak_fn,
        wakeword_pause_event=paused,
    )

    # Fire quickly
    mgr.set_timer(seconds=0.2, label="test")

    t0 = time.monotonic()
    while time.monotonic() - t0 < 2.0:
        if spokens:
            break
        time.sleep(0.05)

    assert spokens, "Timer did not fire in time"
    assert not paused.is_set(), "wakeword_pause_event should be cleared after speaking"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_timer_tools.py -v
```

Expected: FAIL because `tools.timer_tools` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `tools/timer_tools.py`:

```python
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class _TimerSpec:
    seconds: int
    label: str
    timer_id: str


class TimerManager:
    def __init__(
        self,
        *,
        speak_fn: Callable[[str], None],
        wakeword_pause_event: threading.Event,
    ) -> None:
        self._speak_fn = speak_fn
        self._wakeword_pause_event = wakeword_pause_event
        self._lock = threading.Lock()

    def set_timer(self, seconds: int | float, label: str = "") -> dict[str, str | int]:
        seconds_f = float(seconds)
        # Accept float in scheduling; schema is “int seconds” later, but we keep it robust.
        timer_id = str(uuid.uuid4())
        spec = _TimerSpec(seconds=seconds_f, label=label, timer_id=timer_id)  # type: ignore[arg-type]

        thread = threading.Thread(
            target=self._worker,
            args=(spec,),
            daemon=True,
        )
        thread.start()

        return {"timer_id": timer_id, "seconds": int(seconds_f), "label": label}

    def _worker(self, spec: _TimerSpec) -> None:
        time.sleep(float(spec.seconds))
        reminder = f"Timer done{': ' + spec.label if spec.label else '.'}"

        # Pause wakeword scoring while we speak the reminder
        self._wakeword_pause_event.set()
        try:
            self._speak_fn(reminder)
        finally:
            self._wakeword_pause_event.clear()
```

Create `tools/__init__.py`:

```python
\"\"\"Local tool implementations (time, timers, etc.).\"\"\"
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/test_timer_tools.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tools/timer_tools.py tools/__init__.py tests/test_timer_tools.py
git commit -m "feat: add TimerManager for background spoken reminders"
```

---

### Task 3: Implement time tool + regex fast-path for time/timer

**Files:**
- Create: `tools/time_tools.py`
- Create: `tools/simple_commands.py`
- Create/Modify: `tests/test_simple_commands.py`

**Interfaces:**
- Produces:
  - `tools.time_tools.get_time() -> dict[str, str]`
  - `tools.simple_commands.try_handle_simple(text: str, timer_manager: TimerManager) -> str | None`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_simple_commands.py`:

```python
import datetime

from tools.simple_commands import try_handle_simple


class FakeTimerManager:
    def __init__(self):
        self.calls = []

    def set_timer(self, seconds: int, label: str = ""):
        self.calls.append((seconds, label))
        return {"timer_id": "t1", "seconds": seconds, "label": label}


def test_try_handle_simple_time_returns_string(monkeypatch):
    class FakeDT(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 1, 15, 5)

    monkeypatch.setattr(datetime, "datetime", FakeDT)
    reply = try_handle_simple("what time is it right now", timer_manager=FakeTimerManager())
    assert "3:" in reply or "03:" in reply


def test_try_handle_simple_timer_parses_digits():
    tm = FakeTimerManager()
    reply = try_handle_simple("set a timer for 10 minutes", timer_manager=tm)
    assert tm.calls == [(600, "")]
    assert "10" in reply.lower()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/test_simple_commands.py -v
```

Expected: FAIL (missing tool modules).

- [ ] **Step 3: Write minimal implementation**

Create `tools/time_tools.py`:

```python
from __future__ import annotations

import datetime


def get_time() -> dict[str, str]:
    now = datetime.datetime.now()
    return {"time": now.strftime("%I:%M %p").lstrip("0")}
```

Create `tools/simple_commands.py`:

```python
from __future__ import annotations

import re
from typing import Optional

from tools.time_tools import get_time


_TIME_PATTERNS = (
    re.compile(r"\\bwhat\\s+time\\b", re.IGNORECASE),
    re.compile(r"\\bcurrent\\s+time\\b", re.IGNORECASE),
    re.compile(r"\\btime\\s+is\\s+it\\b", re.IGNORECASE),
)

_TIMER_PATTERN = re.compile(
    r"\\bset\\s+(?:a\\s+)?timer\\s+for\\s+(?P<num>\\d+)\\s*(?P<unit>seconds?|minutes?|hours?)\\b",
    re.IGNORECASE,
)


def try_handle_simple(text: str, timer_manager) -> Optional[str]:
    if not text or not text.strip():
        return None

    stripped = text.strip().lower()

    if any(p.search(stripped) for p in _TIME_PATTERNS):
        payload = get_time()
        return f\"It's {payload['time']}.\"

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

        timer_manager.set_timer(seconds=seconds, label=\"\")
        return f\"Timer set for {num} {unit}.\"

    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/test_simple_commands.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tools/time_tools.py tools/simple_commands.py tests/test_simple_commands.py
git commit -m "feat: add time tool and regex fast-path for time/timer"
```

---

### Task 4: Implement Groq tool-calling loop

**Files:**
- Create: `llm/tool_loop.py`
- Create: `tests/test_tool_loop.py`

**Interfaces:**
- Consumes: `tools` schema list and `tool_registry` mapping.
- Produces:
  - `chat_with_tools(messages: list[dict[str, str]], tools: list[dict], tool_registry: dict[str, Callable[..., Any]], *, client: Any | None=None) -> str`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tool_loop.py`:

```python
import json
from types import SimpleNamespace

import pytest

from llm.tool_loop import chat_with_tools


def test_chat_with_tools_executes_tool_calls_and_returns_final_content():
    # 1st Groq response asks for get_time tool
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="get_time", arguments="{}"),
    )
    msg1 = SimpleNamespace(content=None, tool_calls=[tool_call])
    choice1 = SimpleNamespace(message=msg1)
    resp1 = SimpleNamespace(choices=[choice1])

    # 2nd Groq response returns final text
    msg2 = SimpleNamespace(content="Jarvis: It's 3:05 PM.", tool_calls=None)
    choice2 = SimpleNamespace(message=msg2)
    resp2 = SimpleNamespace(choices=[choice2])

    class FakeChatCompletions:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            return resp1 if self.calls == 1 else resp2

    class FakeClient:
        chat = SimpleNamespace(completions=FakeChatCompletions())

    def get_time_tool():
        return {"time": "3:05 PM"}

    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "what time is it"}]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "Get current time",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    tool_registry = {"get_time": get_time_tool}

    reply = chat_with_tools(messages, tools, tool_registry, client=FakeClient())
    assert "3:05" in reply
```

- [ ] **Step 2: Run tests to verify failure**

```powershell
python -m pytest tests/test_tool_loop.py -v
```

Expected: FAIL (missing `llm.tool_loop`).

- [ ] **Step 3: Write minimal implementation**

Create `llm/tool_loop.py`:

```python
from __future__ import annotations

import json
from typing import Any, Callable

from llm.client import get_client
from config import GROQ_MODEL


def chat_with_tools(
    messages: list[dict[str, str]],
    tools: list[dict[str, Any]],
    tool_registry: dict[str, Callable[..., Any]],
    *,
    client: Any | None = None,
) -> str:
    groq_client = client if client is not None else get_client()

    while True:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=tools,
        )

        msg = response.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)

        if tool_calls:
            # Append the assistant tool-call message for context.
            tool_calls_payload = []
            for tc in tool_calls:
                tool_calls_payload.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                )
            messages.append({"role": "assistant", "content": "", "tool_calls": tool_calls_payload})  # type: ignore[arg-type]

            # Execute tools and feed tool results back.
            for tc in tool_calls:
                name = tc.function.name
                args_raw = tc.function.arguments or "{}"
                try:
                    args = json.loads(args_raw)
                except json.JSONDecodeError:
                    args = {}

                fn = tool_registry.get(name)
                if fn is None:
                    result = {"error": f"Unknown tool: {name}"}
                else:
                    result = fn(**args)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result),
                    }
                )

            continue

        content = getattr(msg, "content", None) or ""
        return str(content).strip()
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/test_tool_loop.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add llm/tool_loop.py tests/test_tool_loop.py
git commit -m "feat: add Groq tool-calling loop for function calls"
```

---

### Task 5: Wire tool calling into `main.py` (local fast path + tool loop)

**Files:**
- Modify: `main.py`
- Update: imports + create `wakeword_pause_event` + `TimerManager`

**Interfaces:**
- Consumes: existing `handle_turn()` and `run_conversation_session()` flow.
- Produces: tool calling for:
  - time requests
  - timer requests (digits via regex fast path; words via LLM tool-calls)

- [ ] **Step 1: Write failing routing tests**

Create `tests/test_main_tool_routing.py`:

```python
from types import SimpleNamespace

import pytest

import main as main_mod


def test_handle_turn_uses_simple_commands_when_available(monkeypatch):
    messages = [{"role": "system", "content": "sys"}]

    class FakeTimerManager:
        def set_timer(self, seconds: int, label: str = ""):
            return {"timer_id": "t1", "seconds": seconds, "label": label}

    # Force simple command handler to handle the utterance.
    monkeypatch.setattr(main_mod, "try_handle_simple", lambda text, timer_manager: "It's now.")
    monkeypatch.setattr(main_mod, "chat_with_tools", lambda *args, **kwargs: "SHOULD NOT BE CALLED")
    monkeypatch.setattr(main_mod, "speak", lambda text: None)

    keep_going = main_mod.handle_turn(messages, "what time is it", timer_manager=FakeTimerManager())
    assert keep_going is True
    assert messages[-1]["role"] == "assistant"
    assert "It's now." in messages[-1]["content"]
```

Expected to fail until `handle_turn` accepts `timer_manager` and routing is implemented.

- [ ] **Step 2: Run tests to verify failure**

```powershell
python -m pytest tests/test_main_tool_routing.py -v
```

- [ ] **Step 3: Minimal implementation**

Update `main.py` as follows (showing the essential changes only):

1. Import new modules:

```python
import threading

from tools.simple_commands import try_handle_simple
from tools.time_tools import get_time
from tools.timer_tools import TimerManager
from llm.tool_loop import chat_with_tools
```

2. Create a `wakeword_pause_event` in `main()` and pass it into `wait_for_wake_word()` and `TimerManager`.

3. Update `handle_turn` signature to accept `timer_manager`.

4. In `handle_turn`:
   - attempt regex fast path: `reply = try_handle_simple(text, timer_manager)`
   - if `reply` is not `None`, append assistant reply + speak it
   - else run `chat_with_tools` with tools schema and `tool_registry` mapping:
     - `get_time`: use `get_time`
     - `set_timer`: use `timer_manager.set_timer`

```python
# inside handle_turn after session-end check and before Groq call:
simple_reply = try_handle_simple(text, timer_manager)
if simple_reply is not None:
    messages.append({"role": "assistant", "content": simple_reply})
    print(f"Jarvis: {simple_reply}")
    speak(simple_reply)
    return True

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get current local time",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "Set a timer and remind the user when it ends",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {"type": "integer", "description": "Timer duration in seconds"},
                    "label": {"type": "string", "description": "Optional label for the timer"},
                },
                "required": ["seconds"],
            },
        },
    },
]

tool_registry = {
    "get_time": get_time,
    "set_timer": timer_manager.set_timer,
}

reply = chat_with_tools(messages, tools, tool_registry)
messages.append({"role": "assistant", "content": reply})
print(f"Jarvis: {reply}")
speak(reply)
return True
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest tests/test_main_tool_routing.py -v
python -m pytest tests -v
```

- [ ] **Step 5: Commit**

```powershell
git add main.py
git commit -m "feat: add time/timer tool calling and local fast paths"
```

---

## Execution Handoff

Plan complete. Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task with review between tasks
2. **Inline Execution** - Execute tasks in this session with checkpoints

Which approach?

