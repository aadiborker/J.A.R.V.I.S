# Network Mode (Lower Modules) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect internet loss/restore with a background probe, announce JARVIS-style transitions, and run full local stack (Piper + wake/Whisper + time/timer) while offline.

**Architecture:** A thread-safe online flag plus `NetworkMonitor` polls TCP probes; on debounced transitions it speaks fixed cues and emits a HUD `network` event. `speak()` skips Edge when offline; `handle_turn` skips Groq when offline and the utterance is not a local fast-path.

**Tech Stack:** Python 3 stdlib (`socket`, `threading`), existing Piper/Edge TTS, pytest, Electron HUD WebSocket.

## Global Constraints

- Offline cue (exact): `Network offline. Switching to lower modules.`
- Online cue (exact): `Network restored. Full systems online.`
- Offline stack: Piper only; wake word + Whisper; local time/timer via `try_handle_simple`; no Groq; no Edge.
- Probe: TCP to hosts like `1.1.1.1:443` / `8.8.8.8:443` with short timeout — not “Edge succeeded.”
- Announce **once per debounced transition** only.
- Keep `speak(text)` as the single TTS API.
- No offline generative LLM.
- Do not change HUD bridge Connected/Offline semantics; WAN is a separate `network` event.

## File map

| File | Responsibility |
|------|----------------|
| `net/__init__.py` | Re-export public API |
| `net/connectivity.py` | `check_internet`, mode flag, `NetworkMonitor`, announcement strings |
| `config.py` | Probe interval/timeout/hosts/debounce |
| `tts/speak.py` | Skip Edge when `is_online()` is False |
| `main.py` | Boot probe, start monitor, offline turn gate |
| `desktop/renderer/app.js` (+ HTML/CSS if needed) | Show WAN status from `network` events |
| `tests/test_connectivity.py` | Probe, flag, monitor debounce |
| `tests/test_speak.py` | Offline forces Piper |
| `tests/test_offline_turn.py` | Offline skips Groq |

---

### Task 1: Connectivity probe + mode flag

**Files:**
- Create: `net/__init__.py`
- Create: `net/connectivity.py`
- Modify: `config.py` (append network settings)
- Test: `tests/test_connectivity.py`

**Interfaces:**
- Consumes: `config.NETWORK_*` constants
- Produces:
  - `OFFLINE_ANNOUNCE: str`
  - `ONLINE_ANNOUNCE: str`
  - `check_internet() -> bool`
  - `is_online() -> bool`
  - `set_online(value: bool) -> None`
  - `get_online_lock() -> threading.Lock` (optional; internal lock is fine if `is_online`/`set_online` are the only public accessors)

- [x] **Step 1: Write the failing tests**

Create `tests/test_connectivity.py`:

```python
from __future__ import annotations

import net.connectivity as conn


def test_announcement_strings():
    assert conn.OFFLINE_ANNOUNCE == "Network offline. Switching to lower modules."
    assert conn.ONLINE_ANNOUNCE == "Network restored. Full systems online."


def test_set_online_is_threadsafe_readable(monkeypatch):
    conn.set_online(True)
    assert conn.is_online() is True
    conn.set_online(False)
    assert conn.is_online() is False


def test_check_internet_true_when_connect_ok(monkeypatch):
    class FakeSock:
        def settimeout(self, t):
            self.t = t

        def connect(self, addr):
            self.addr = addr

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(conn.socket, "socket", lambda *a, **k: FakeSock())
    monkeypatch.setattr(conn, "NETWORK_PROBE_HOSTS", (("1.1.1.1", 443),))
    assert conn.check_internet() is True


def test_check_internet_false_when_all_hosts_fail(monkeypatch):
    class BadSock:
        def settimeout(self, t):
            pass

        def connect(self, addr):
            raise OSError("no route")

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(conn.socket, "socket", lambda *a, **k: BadSock())
    monkeypatch.setattr(conn, "NETWORK_PROBE_HOSTS", (("1.1.1.1", 443), ("8.8.8.8", 443)))
    assert conn.check_internet() is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_connectivity.py -v`  
Expected: FAIL (module/import or missing attributes)

- [ ] **Step 3: Add config knobs**

Append to `config.py`:

```python
# WAN connectivity (lower-modules mode when offline)
NETWORK_CHECK_INTERVAL_SECONDS = 20
NETWORK_PROBE_TIMEOUT_SECONDS = 2.0
NETWORK_PROBE_HOSTS = (("1.1.1.1", 443), ("8.8.8.8", 443))
NETWORK_DEBOUNCE_CHECKS = 2
```

- [ ] **Step 4: Implement `net/connectivity.py` + `__init__.py`**

`net/__init__.py`:

```python
from net.connectivity import (
    OFFLINE_ANNOUNCE,
    ONLINE_ANNOUNCE,
    NetworkMonitor,
    check_internet,
    is_online,
    set_online,
)

__all__ = [
    "OFFLINE_ANNOUNCE",
    "ONLINE_ANNOUNCE",
    "NetworkMonitor",
    "check_internet",
    "is_online",
    "set_online",
]
```

`net/connectivity.py` (minimal for this task — include `NetworkMonitor` stub class body empty/`pass` only if Task 2 owns it; prefer implementing probe+flag fully here and leave monitor for Task 2):

```python
from __future__ import annotations

import socket
import threading

from config import (
    NETWORK_PROBE_HOSTS,
    NETWORK_PROBE_TIMEOUT_SECONDS,
)

OFFLINE_ANNOUNCE = "Network offline. Switching to lower modules."
ONLINE_ANNOUNCE = "Network restored. Full systems online."

_lock = threading.Lock()
_online = True


def is_online() -> bool:
    with _lock:
        return _online


def set_online(value: bool) -> None:
    with _lock:
        global _online
        _online = bool(value)


def check_internet(
    *,
    hosts: tuple[tuple[str, int], ...] | None = None,
    timeout: float | None = None,
) -> bool:
    """Return True if any probe host accepts a TCP connect."""
    probe_hosts = hosts if hosts is not None else NETWORK_PROBE_HOSTS
    probe_timeout = (
        NETWORK_PROBE_TIMEOUT_SECONDS if timeout is None else timeout
    )
    for host, port in probe_hosts:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(probe_timeout)
                sock.connect((host, port))
            return True
        except OSError:
            continue
    return False
```

Do **not** implement `NetworkMonitor` in this step if tests above do not require it; Task 2 adds it. If `__init__.py` imports `NetworkMonitor`, either omit it from `__init__` until Task 2 or add a placeholder — prefer updating `__init__.py` in Task 2 when the class exists.

For Task 1, use a thinner `__init__.py`:

```python
from net.connectivity import (
    OFFLINE_ANNOUNCE,
    ONLINE_ANNOUNCE,
    check_internet,
    is_online,
    set_online,
)

__all__ = [
    "OFFLINE_ANNOUNCE",
    "ONLINE_ANNOUNCE",
    "check_internet",
    "is_online",
    "set_online",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_connectivity.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add config.py net/__init__.py net/connectivity.py tests/test_connectivity.py
git commit -m "feat: add internet probe and online mode flag"
```

---

### Task 2: NetworkMonitor with debounce + transition callback

**Files:**
- Modify: `net/connectivity.py`
- Modify: `net/__init__.py` (export `NetworkMonitor`)
- Modify: `tests/test_connectivity.py`

**Interfaces:**
- Consumes: `check_internet`, `set_online`, `is_online`, `NETWORK_CHECK_INTERVAL_SECONDS`, `NETWORK_DEBOUNCE_CHECKS`
- Produces:
  - `class NetworkMonitor:`
    - `__init__(self, on_transition, *, check_fn=check_internet, interval_s=..., debounce=..., speak_fn=None) -> None`
    - `start(self) -> None`
    - `stop(self) -> None`
  - `on_transition(online: bool) -> None` called only after debounce confirms a change from the last **announced/committed** state

Behavior:
1. Seed internal `committed` state from current `is_online()` (caller sets flag from boot probe first).
2. Each tick: `ok = check_fn()`.
3. If `ok == committed`, reset streak counter to 0.
4. If `ok != committed`, increment streak; when streak >= debounce, `set_online(ok)`, `committed = ok`, streak = 0, call `on_transition(ok)`.
5. Daemon thread; `stop()` sets an Event and joins with timeout.

- [x] **Step 1: Write the failing tests**

Append to `tests/test_connectivity.py`:

```python
import time


def test_monitor_debounces_single_blip(monkeypatch):
    transitions: list[bool] = []
    results = iter([True, False, True, True, True])  # single offline blip

    def fake_check():
        return next(results)

    conn.set_online(True)
    mon = conn.NetworkMonitor(
        on_transition=lambda online: transitions.append(online),
        check_fn=fake_check,
        interval_s=0.01,
        debounce=2,
    )
    mon.start()
    time.sleep(0.12)
    mon.stop()
    assert transitions == []


def test_monitor_announces_after_debounce(monkeypatch):
    transitions: list[bool] = []
    # committed online; then two offline readings -> transition
    results = iter([False, False, False, False])

    def fake_check():
        try:
            return next(results)
        except StopIteration:
            return False

    conn.set_online(True)
    mon = conn.NetworkMonitor(
        on_transition=lambda online: transitions.append(online),
        check_fn=fake_check,
        interval_s=0.01,
        debounce=2,
    )
    mon.start()
    time.sleep(0.12)
    mon.stop()
    assert transitions == [False]
    assert conn.is_online() is False
```

- [ ] **Step 2: Run new tests to verify they fail**

Run: `pytest tests/test_connectivity.py::test_monitor_debounces_single_blip tests/test_connectivity.py::test_monitor_announces_after_debounce -v`  
Expected: FAIL (`NetworkMonitor` missing)

- [ ] **Step 3: Implement `NetworkMonitor`**

Add to `net/connectivity.py`:

```python
from config import (
    NETWORK_CHECK_INTERVAL_SECONDS,
    NETWORK_DEBOUNCE_CHECKS,
    NETWORK_PROBE_HOSTS,
    NETWORK_PROBE_TIMEOUT_SECONDS,
)


class NetworkMonitor:
    def __init__(
        self,
        on_transition,
        *,
        check_fn=None,
        interval_s: float | None = None,
        debounce: int | None = None,
    ) -> None:
        self._on_transition = on_transition
        self._check_fn = check_fn or check_internet
        self._interval_s = (
            NETWORK_CHECK_INTERVAL_SECONDS if interval_s is None else interval_s
        )
        self._debounce = (
            NETWORK_DEBOUNCE_CHECKS if debounce is None else debounce
        )
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="NetworkMonitor", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval_s + 1.0)
            self._thread = None

    def _run(self) -> None:
        committed = is_online()
        streak = 0
        while not self._stop.is_set():
            ok = bool(self._check_fn())
            if ok == committed:
                streak = 0
            else:
                streak += 1
                if streak >= self._debounce:
                    committed = ok
                    streak = 0
                    set_online(ok)
                    try:
                        self._on_transition(ok)
                    except Exception as exc:  # noqa: BLE001
                        print(f"Network transition handler error: {exc}")
            self._stop.wait(self._interval_s)
```

Update `net/__init__.py` to export `NetworkMonitor`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_connectivity.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add net/connectivity.py net/__init__.py tests/test_connectivity.py
git commit -m "feat: add debounced NetworkMonitor transitions"
```

---

### Task 3: Force Piper when offline in `speak()`

**Files:**
- Modify: `tts/speak.py`
- Modify: `tests/test_speak.py`

**Interfaces:**
- Consumes: `net.connectivity.is_online`
- Produces: `speak()` tries Edge only when `TTS_PREFER_EDGE and is_online()`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_speak.py`:

```python
def test_speak_skips_edge_when_offline(monkeypatch):
    edge_calls: list[str] = []
    piper_calls: list[str] = []

    monkeypatch.setattr(speak_mod, "TTS_PREFER_EDGE", True)
    monkeypatch.setattr(speak_mod, "is_online", lambda: False)
    monkeypatch.setattr(
        speak_mod, "_speak_edge", lambda text: edge_calls.append(text)
    )
    monkeypatch.setattr(
        speak_mod,
        "_speak_piper",
        lambda text, voice=None: piper_calls.append(text),
    )

    speak_mod.speak("offline line")
    assert edge_calls == []
    assert piper_calls == ["offline line"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_speak.py::test_speak_skips_edge_when_offline -v`  
Expected: FAIL (`is_online` not defined on module, or Edge still called)

- [ ] **Step 3: Wire `is_online` into `speak()`**

In `tts/speak.py`, import:

```python
from net.connectivity import is_online
```

Change the Edge gate to:

```python
    if TTS_PREFER_EDGE and is_online():
        try:
            _speak_edge(cleaned)
            return
        except Exception as exc:  # noqa: BLE001
            if not _edge_fail_logged:
                print(f"Edge TTS unavailable ({exc}); using Piper fallback.")
                _edge_fail_logged = True

    _speak_piper(cleaned, voice=voice)
```

- [ ] **Step 4: Run speak tests**

Run: `pytest tests/test_speak.py -v`  
Expected: PASS (including existing Edge preference tests — they leave `is_online` real or monkeypatch online; if real probe might be offline in CI, **monkeypatch `is_online` to True** in `test_speak_prefers_edge_when_enabled`):

```python
monkeypatch.setattr(speak_mod, "is_online", lambda: True)
```

Apply the same online monkeypatch to any test that expects Edge.

- [ ] **Step 5: Commit**

```bash
git add tts/speak.py tests/test_speak.py
git commit -m "feat: skip Edge TTS when network mode is offline"
```

---

### Task 4: Offline turn gate in `main.py` (skip Groq)

**Files:**
- Modify: `main.py` (`handle_turn`)
- Create: `tests/test_offline_turn.py`

**Interfaces:**
- Consumes: `is_online`, `try_handle_simple`, `OFFLINE_ANNOUNCE` (or a dedicated short reply)
- Produces: when offline and no simple handler, reply/speak: `I'm on lower modules only right now — time and timers still work.`

Use this exact offline chat line (distinct from the transition cue):

`I'm on lower modules only right now — time and timers still work.`

- [ ] **Step 1: Write the failing test**

Create `tests/test_offline_turn.py`. Prefer extracting a small helper to avoid importing full `main` with heavy deps — add `reply_if_offline(text, timer_manager) -> tuple[str, str] | None` in `tools/offline_gate.py` **or** test via a thin function in `main`.

Preferred: create `tools/offline_gate.py`:

```python
from __future__ import annotations

from typing import Optional

from net.connectivity import is_online
from tools.simple_commands import try_handle_simple

OFFLINE_CHAT_REPLY = (
    "I'm on lower modules only right now — time and timers still work."
)


def handle_offline_or_simple(text: str, timer_manager) -> Optional[tuple[str, str]]:
    """Return (print, speech) for local/offline handling, else None to use Groq."""
    simple = try_handle_simple(text, timer_manager)
    if simple is not None:
        return simple
    if not is_online():
        return OFFLINE_CHAT_REPLY, OFFLINE_CHAT_REPLY
    return None
```

Test:

```python
from tools import offline_gate as og


class FakeTimer:
    def set_timer(self, seconds, label="", *, announce=True):
        return {}


def test_offline_gate_allows_time(monkeypatch):
    monkeypatch.setattr(og, "is_online", lambda: False)
    monkeypatch.setattr(
        og,
        "try_handle_simple",
        lambda text, tm: ("It's 1:00 PM on 05-08-2026.", "It's 1:00 PM on the fifth of August twenty twenty six."),
    )
    out = og.handle_offline_or_simple("what time is it", FakeTimer())
    assert out is not None
    assert "05-08-2026" in out[0]


def test_offline_gate_blocks_general_chat(monkeypatch):
    monkeypatch.setattr(og, "is_online", lambda: False)
    monkeypatch.setattr(og, "try_handle_simple", lambda text, tm: None)
    out = og.handle_offline_or_simple("tell me a joke", FakeTimer())
    assert out == (og.OFFLINE_CHAT_REPLY, og.OFFLINE_CHAT_REPLY)


def test_online_gate_passes_through(monkeypatch):
    monkeypatch.setattr(og, "is_online", lambda: True)
    monkeypatch.setattr(og, "try_handle_simple", lambda text, tm: None)
    assert og.handle_offline_or_simple("hello", FakeTimer()) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_offline_turn.py -v`  
Expected: FAIL (module missing)

- [ ] **Step 3: Implement `tools/offline_gate.py` and wire `main.handle_turn`**

Implement file as above. In `main.py`, replace the simple-only block with:

```python
    from tools.offline_gate import handle_offline_or_simple

    gated = handle_offline_or_simple(text, timer_manager)
    if gated is not None:
        print_text, speech_text = gated
        messages.append({"role": "assistant", "content": print_text})
        jarvis_typed(print_text)
        if speech_text:
            try:
                set_status("[SPEAK] Speaking...")
                speak(speech_text)
            except Exception as exc:  # noqa: BLE001
                log_error(f"TTS error: {exc}")
            finally:
                clear_status()
        return True
```

Remove the old direct `try_handle_simple` block (gate already calls it). Keep import of `try_handle_simple` removed if unused.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_offline_turn.py tests/test_simple_commands.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/offline_gate.py main.py tests/test_offline_turn.py
git commit -m "feat: skip Groq and use lower-modules reply when offline"
```

---

### Task 5: Boot probe, transition announcements, start monitor

**Files:**
- Modify: `main.py` (`main()` boot path)

**Interfaces:**
- Consumes: `check_internet`, `set_online`, `is_online`, `NetworkMonitor`, `OFFLINE_ANNOUNCE`, `ONLINE_ANNOUNCE`, `speak`, `emit_ui`, `log_system`
- Produces: boot sets mode from probe; monitor announces transitions with wakeword pause

- [ ] **Step 1: Add transition handler + boot probe (implementation)**

Near top of `main` after `timer_manager` / `wakeword_pause_event` exist:

```python
    from net.connectivity import (
        OFFLINE_ANNOUNCE,
        ONLINE_ANNOUNCE,
        NetworkMonitor,
        check_internet,
        is_online,
        set_online,
    )

    def on_network_transition(online: bool) -> None:
        line = ONLINE_ANNOUNCE if online else OFFLINE_ANNOUNCE
        log_system(line)
        emit_ui({"type": "network", "online": online})
        emit_ui({"type": "transcript", "role": "system", "text": line})
        wakeword_pause_event.set()
        try:
            set_status("[SPEAK] Network...")
            speak(line)
        except Exception as exc:  # noqa: BLE001
            log_error(f"TTS error (network): {exc}")
        finally:
            clear_status()
            wakeword_pause_event.clear()

    initial_online = check_internet()
    set_online(initial_online)
    emit_ui({"type": "network", "online": initial_online})

    monitor = NetworkMonitor(on_transition=on_network_transition)
    monitor.start()
```

Replace the fixed boot cue:

```python
    if initial_online:
        boot_line = "System Online."
    else:
        boot_line = OFFLINE_ANNOUNCE

    print(boot_line, flush=True)
    emit_ui({"type": "transcript", "role": "system", "text": boot_line})
    wakeword_pause_event.set()
    try:
        set_status("[SPEAK] Boot...")
        speak(boot_line)
    except Exception as exc:  # noqa: BLE001
        log_error(f"TTS error (boot): {exc}")
    finally:
        clear_status()
        wakeword_pause_event.clear()
```

Then greeting as today. Do not speak `ONLINE_ANNOUNCE` on boot if already online (boot uses `System Online.` only).

- [ ] **Step 2: Manual smoke checklist (document in commit body / skip automated)**

No unit test required for full `main()`; verify logic by reading the boot branch once.

Optional tiny test of boot-line selection if extracted:

```python
def boot_status_line(online: bool) -> str:
    return "System Online." if online else OFFLINE_ANNOUNCE
```

If extracted to `net/connectivity.py`, add:

```python
def boot_status_line(online: bool | None = None) -> str:
    ok = is_online() if online is None else online
    return "System Online." if ok else OFFLINE_ANNOUNCE
```

Test:

```python
assert conn.boot_status_line(True) == "System Online."
assert conn.boot_status_line(False) == conn.OFFLINE_ANNOUNCE
```

- [ ] **Step 3: Run full unit suite**

Run: `pytest tests/ -q`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add main.py net/connectivity.py tests/test_connectivity.py
git commit -m "feat: boot probe and announce network mode transitions"
```

---

### Task 6: HUD WAN status from `network` events

**Files:**
- Modify: `desktop/renderer/index.html` (add a small WAN label if none)
- Modify: `desktop/renderer/styles.css` (minimal styling)
- Modify: `desktop/renderer/app.js` (handle `network` message)

**Interfaces:**
- Consumes: WS event `{ type: "network", online: boolean }`
- Produces: UI shows e.g. `WAN: Online` / `WAN: Lower modules` without renaming bridge `Connected`/`Offline`

- [ ] **Step 1: Inspect current chrome**

Open `desktop/renderer/index.html` and locate the connection chip (`#conn` or similar). Add a sibling element:

```html
<span id="wan" class="wan" title="Internet">WAN —</span>
```

- [ ] **Step 2: Handle event in `app.js`**

```javascript
function setWan(online) {
  const el = document.getElementById("wan");
  if (!el) return;
  el.textContent = online ? "WAN Online" : "WAN Lower modules";
  el.dataset.state = online ? "online" : "offline";
}

// inside message switch:
case "network":
  setWan(!!msg.online);
  break;
```

Style `#wan[data-state="offline"]` with a muted/warning color distinct from bridge offline.

- [ ] **Step 3: Manual verify**

With HUD + `python main.py --ui-ws`, confirm initial `network` event updates the chip; (optional) force `emit_ui` via a one-liner only if easy.

- [ ] **Step 4: Commit**

```bash
git add desktop/renderer/index.html desktop/renderer/styles.css desktop/renderer/app.js
git commit -m "feat: show WAN / lower-modules status on HUD"
```

---

### Task 7: End-to-end verification

**Files:** none required (manual + suite)

- [ ] **Step 1: Run full tests**

Run: `pytest tests/ -q`  
Expected: all PASS

- [ ] **Step 2: Manual offline path**

1. Start JARVIS (HUD optional).
2. Disable Wi‑Fi / unplug ethernet.
3. Within ~40s (interval × debounce), hear: `Network offline. Switching to lower modules.`
4. Ask time → numeric date + spoken date via Piper.
5. Ask something needing Groq → lower-modules chat line.
6. Re-enable network → hear: `Network restored. Full systems online.`
7. Confirm Edge/Groq resume on next turn.

- [ ] **Step 3: Final commit only if leftover fixes**

```bash
git status
# commit any small fixes from manual test
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Background TCP probe | 1, 2 |
| Debounced transitions | 2 |
| Offline / online exact cues | 1, 5 |
| Piper-only when offline | 3 |
| Skip Groq; local tools only | 4 |
| Boot probe + appropriate boot line | 5 |
| HUD `network` event | 5, 6 |
| Config knobs | 1 |
| Tests + manual verify | 1–4, 7 |

## Placeholder / consistency self-review

- Announcement strings match spec verbatim.
- `is_online` / `set_online` / `check_internet` / `NetworkMonitor` names consistent across tasks.
- Offline chat line is separate from transition cues (intentional).
- No TBD / “add error handling later” left in steps.
