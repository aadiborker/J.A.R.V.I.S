# Electron HUD + Python Bridge Design

**Date:** 2026-08-05  
**Goal:** Replace the terminal as the primary UI with an Electron HUD that can show status and animations, while keeping all audio/STT/LLM/TTS/tools in Python.

## Decisions (approved)

| Choice | Decision |
|--------|----------|
| UI host | Electron desktop app |
| Backend | Existing Python Jarvis (`main.py` stack) |
| Link | Localhost WebSocket event bridge |
| Look (v1) | Iron Man–style HUD panel |
| Terminal | Optional / debug; not required for normal use |

## Non-goals (v1)

- Rewriting STT/TTS/wake-word/tools in Node
- Celebrity voice cloning
- Mobile / multi-machine remote control
- Fancy 3D WebGL scenes (can come later; v1 is 2D CSS/canvas)
- Shipping a signed installer (dev launch scripts are enough first)

## Architecture

```
┌─────────────────────┐     WebSocket (ws://127.0.0.1:PORT)
│  Electron (UI)      │◄──────────────────────────────────►┌──────────────────────┐
│  - HUD window       │     JSON events                     │  Python Jarvis        │
│  - animations       │     (status, transcripts)           │  - wake / STT / LLM   │
│  - start Python     │                                     │  - TTS / tools        │
└─────────────────────┘                                     │  - ui_bridge server   │
                                                            └──────────────────────┘
```

### Process model

1. User launches Electron (new primary entry), e.g. `npm start` or a `scripts/start_jarvis_ui.*` helper.
2. Electron spawns Python (`python -u main.py --ui-ws` or equivalent) with working directory = project root.
3. Python starts a small WebSocket server on a fixed local port (configurable; default `8765`).
4. Electron connects as a client and renders HUD from events.
5. On Electron quit: kill the Python child process.

If Python is already running with the bridge, Electron may connect without spawning (optional later).

### Event protocol (Python → Electron)

All messages are JSON objects:

```json
{ "type": "status", "state": "idle"|"listening"|"thinking"|"speaking"|"error", "detail": "..." }
{ "type": "transcript", "role": "user"|"jarvis"|"system", "text": "..." }
{ "type": "wake", "score": 0.87 }
{ "type": "ready" }
{ "type": "error", "message": "..." }
```

v1 is **one-way enough**: Python pushes UI state. Electron does not need to send mic audio. Optional later: Electron → Python `{ "type": "command", "name": "shutdown" }`.

### Python changes

- Add `ui/bridge.py` (or `ui/ws_bridge.py`): tiny WebSocket server + `emit(event)` helper.
- Thread-safe emit from main loop / timer threads.
- Hook existing console UI call sites (or a thin facade) so `log_user` / `set_status` / `jarvis_typed` also emit bridge events.
- Keep console output working when `--ui-ws` is set (dual output), unless `--ui-only` is added later.
- No change to STT/TTS/tool semantics.

### Electron layout (v1)

- Frameless, always-on-top window (~900×560), dark translucent HUD chrome.
- Regions:
  1. **Header** — brand “J.A.R.V.I.S” + connection pill (Connected / Booting / Offline)
  2. **Hero animation** — arc/ring that pulses by `state` (idle slow / listening breath / speaking stronger)
  3. **Status line** — human-readable state text from `detail`
  4. **Transcript** — scrolling You / Jarvis lines (last N messages)
- Visual direction: cool steel / cyan HUD (avoid generic purple AI aesthetic). Use a distinctive display font for the brand.
- Motion: at least 2–3 intentional CSS/canvas motions (ring pulse, status fade, transcript insert).

### Config

- `UI_WS_HOST = "127.0.0.1"`
- `UI_WS_PORT = 8765`
- `UI_WS_ENABLED` via CLI flag preferred over always-on (so terminal-only still works)

### Dependencies

- Python: `websockets` (or stdlib-only if we want zero deps — prefer `websockets` for clarity)
- Node: `electron` (dev), plain HTML/CSS/JS for v1 (no React required unless we want it)

### Launch / autostart

- New launcher starts Electron (which starts Python).
- Update Task Scheduler / desktop shortcut later to point at the Electron entry (phase after HUD works).
- Existing `start_jarvis.bat` remains valid for terminal-only mode.

## Error handling

| Case | Behavior |
|------|----------|
| Electron up, Python down | HUD shows Offline; retry connect with backoff |
| Python up, Electron down | Jarvis keeps working; emits are no-ops / dropped |
| Port in use | Fail with clear message; allow `UI_WS_PORT` override |
| Python crash | Electron shows error state; do not silently respawn loop in v1 |

## Verification

- Manual: launch Electron → see Connected → say “hey jarvis” → HUD state + transcript update while audio still works.
- Unit: Python emit helper buffers/sends JSON; no GUI unit tests required for v1 Electron.
- Regression: `python -m pytest` still passes; terminal mode without `--ui-ws` unchanged.

## Implementation order

1. Python WebSocket bridge + emit hooks (terminal still primary).
2. Minimal Electron window that displays raw events.
3. HUD styling + state animations.
4. Electron spawns Python; update launcher docs.
5. (Later) Point Windows autostart at Electron.

## Out of scope for first PR

- Custom animation editor
- Drag-to-resize polish / multiple monitor profiles
- Streaming partial STT tokens
- Replacing Edge/Piper TTS
