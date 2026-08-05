# Feature F: Ctrl+Alt+J Launch + Push-to-Talk — Design

**Date:** 2026-08-05  
**Goal:** `Ctrl+Alt+J` launches J.A.R.V.I.S if it is not running; if it is running, hold the combo to talk and release to send (push-to-talk).

## Non-goals / constraints

- Do not replace “hey jarvis” wake word (both remain available).
- Rare combo only: default `Ctrl+Alt+J` (configurable in `config.py` / Electron env).
- No accidental one-tap YouTube play from the hotkey alone — PTT only records/sends speech after release.
- Out of scope: VAD (Feature D), HUD polish beyond PTT status (Feature E can extend), memory/apps/vision.

## Approach (approved)

**Tray app owns PTT when running; login watchdog launches when closed.**

| State | Ctrl+Alt+J |
|-------|------------|
| Process not running | Watchdog starts HUD / Electron |
| Running, window hidden | Show window; treat as PTT if held |
| Running | Key down → start capture; key up → stop, STT, handle turn |

## Architecture

1. **`scripts/jarvis_hotkey_watchdog.py`** (started with Windows login / optional with HUD)
   - Polls whether Electron/Jarvis UI process is running.
   - When **not** running: detect `Ctrl+Alt+J` (GetAsyncKeyState edge) → spawn `scripts/start_jarvis_ui.bat` (or `desktop/start.bat`) once (debounce).
   - When **running**: do not steal the hotkey (Electron handles PTT).

2. **Electron (`desktop/main.js`)**
   - Global keyboard hook (e.g. `uiohook-napi` or equivalent) for Ctrl+Alt+J keydown/keyup.
   - keydown → show window if needed; send WS `{type:"ptt","action":"start"}` to Python.
   - keyup → WS `{type:"ptt","action":"stop"}`.
   - Ignore repeats while TTS/`speaking`; optional ignore if already in PTT.

3. **Python WS bridge + main**
   - Accept client→server PTT events on the UI WebSocket.
   - `ptt start`: pause wake-word; begin rolling mic capture (no fixed 5s clip).
   - `ptt stop`: end capture → Whisper → `handle_turn` (or open session if idle).
   - Status/HUD: `Listening (PTT)…` / `Got it — transcribing…`.

4. **Install**
   - Extend `scripts/install_autostart.ps1` to also start the watchdog at login (or start watchdog from Electron on boot).
   - Prefer: Electron starts watchdog child only if not present; autostart still launches Electron.

## Safety

- Debounce launch (ignore further launches for N seconds).
- Single-instance Electron lock unchanged.
- After YouTube play, existing media session-end still applies; PTT can re-open a session deliberately (user held the key).

## Verification

- Quit Jarvis fully → Ctrl+Alt+J launches HUD.
- With Jarvis open → hold Ctrl+Alt+J, speak, release → transcript + reply.
- Tap without hold (instant up) → no spurious long listen / no auto play.
- Unit tests for PTT state machine (start/stop/cancel) with mocked audio.

## Out of scope

- Customizable hotkey UI (config constant is enough for F).
- Push-to-talk over Bluetooth headsets special keys.
