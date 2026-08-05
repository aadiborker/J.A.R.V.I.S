# Electron HUD + Python Bridge Implementation Plan

> **For agentic workers:** Implement task-by-task. Steps use checkbox syntax.

**Goal:** Add a local WebSocket bridge from Python Jarvis and an Electron HUD that shows status, transcripts, and state animations.

**Architecture:** Python emits JSON events on `ws://127.0.0.1:8765`. Electron is a frameless HUD client that optionally spawns `python -u main.py --ui-ws`. Terminal mode without the flag stays unchanged.

**Tech Stack:** Python `websockets`, Electron (vanilla HTML/CSS/JS), existing Jarvis stack.

## Global Constraints

- Do not rewrite STT/TTS/wake-word/tools in Node.
- Keep `speak()` blocking behavior and wake-word pause semantics.
- Dual output: console UI still works when `--ui-ws` is set.
- Cool steel/cyan HUD; avoid purple AI aesthetic.
- Windows-first launch scripts.

---

### Task 1: Python WebSocket bridge + tests

**Files:**
- Create: `ui/ws_bridge.py`
- Create: `tests/test_ws_bridge.py`
- Modify: `config.py`, `requirements.txt`

- [ ] Add `UI_WS_HOST`, `UI_WS_PORT` to config
- [ ] Implement thread-safe `UiBridge` with `start()`, `stop()`, `emit(dict)`
- [ ] Unit test: emit queues/sends JSON; emit is no-op when not started
- [ ] Add `websockets` to requirements

### Task 2: Hook console UI + main CLI flag

**Files:**
- Modify: `ui/console_ui.py`, `main.py`

- [ ] `set_status` / `log_*` also emit bridge events when bridge enabled
- [ ] `main.py --ui-ws` starts bridge before warmup; emit `ready` after models load
- [ ] Map statuses to `idle|listening|thinking|speaking|error`

### Task 3: Electron HUD shell

**Files:**
- Create: `desktop/package.json`, `desktop/main.js`, `desktop/preload.js`, `desktop/renderer/index.html`, `desktop/renderer/styles.css`, `desktop/renderer/app.js`

- [ ] Frameless always-on-top window
- [ ] Connect WebSocket; show Connected/Offline
- [ ] Render status + transcript; ring animation by state
- [ ] Spawn Python with `--ui-ws` from Electron; kill on quit

### Task 4: Launch scripts + verify

**Files:**
- Create: `scripts/start_jarvis_ui.bat`
- Modify: `README.md` (brief UI section)

- [ ] `npm install` in `desktop/`
- [ ] Manual smoke: HUD connects and shows events
- [ ] `python -m pytest` green
