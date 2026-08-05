# Network Mode Design — Online / Lower Modules

**Date:** 2026-08-05  
**Goal:** Detect internet loss and restore, announce transitions in JARVIS style, and run a full local stack while offline.

## Non-goals / constraints

- Do not require a new cloud service or paid uptime API.
- Keep `speak(text)` as the single TTS entry; timers and wake-word pause behavior stay intact.
- Do not invent an offline LLM — offline chat beyond local tools gets a short refusal/status line.
- HUD WebSocket “Connected/Offline” remains about the local Python bridge, not WAN; optionally add a separate network status event.

## Approach (approved)

**Background connectivity probe** with an explicit mode:

| Mode | Meaning | Behavior |
|------|---------|----------|
| Online | Internet reachable | Prefer Edge TTS + Groq LLM; full tools |
| Offline (“lower modules”) | Internet not reachable | Piper only; wake word + Whisper + local time/timer; skip Groq/Edge |

Spoken cues (once per transition):

- Offline: `Network offline. Switching to lower modules.`
- Online again: `Network restored. Full systems online.`

## Architecture

1. **Connectivity module** (`net/connectivity.py` or `system/network.py`):
   - `check_internet() -> bool` — short TCP connect (e.g. `1.1.1.1:443` and/or `8.8.8.8:443`) with ~2s timeout.
   - `NetworkMonitor` — background thread: poll every `NETWORK_CHECK_INTERVAL_SECONDS` (default 20–30).
   - On **state change only** (online↔offline), invoke a callback; debounce brief flaps (e.g. require 2 consecutive same results or ~5s stable before announcing).

2. **Mode flag** (process-wide, thread-safe):
   - `is_online() -> bool` / `set_online(bool)`.
   - `speak()`: if offline, skip Edge and use Piper (even when `TTS_PREFER_EDGE` is True).
   - `handle_turn` / tool loop: if offline and request is not a local fast-path, reply with a short offline line (e.g. that only lower modules are available) instead of calling Groq.

3. **Boot** (`main.py`):
   - After models warm, run an initial probe.
   - If online: keep existing `System Online.` then greeting.
   - If offline: speak offline cue (and still greet using Piper); do not imply cloud systems are up.
   - Start `NetworkMonitor` before the wake-word loop; announcements use `speak()` (Piper when offline).

4. **UI (optional, small)**:
   - Emit `{"type": "network", "online": true|false}` on transition so the HUD can show WAN status separately from bridge status.

5. **Config** (`config.py`):
   - `NETWORK_CHECK_INTERVAL_SECONDS = 20`
   - `NETWORK_PROBE_TIMEOUT_SECONDS = 2`
   - `NETWORK_PROBE_HOSTS = (("1.1.1.1", 443), ("8.8.8.8", 443))`
   - `NETWORK_DEBOUNCE_CHECKS = 2` (consecutive agreeing probes before transition)

## Error handling

- Probe exceptions → treat as offline for that sample.
- Announcement TTS failure → log; still flip mode so behavior stays correct.
- Flapping Wi‑Fi → debounce so cues are not repeated every few seconds.
- Offline → online while mid-utterance: next `speak()` may use Edge; no interrupt of current Piper play.

## Verification

- Unit tests: probe mock online/offline; monitor fires callback once per transition; debounce ignores single-flip; `speak` skips Edge when offline; simple turn offline skips Groq.
- Manual: disconnect Wi‑Fi → hear offline cue + Piper + local time still works; reconnect → hear restore cue + Edge/Groq resume.

## Out of scope

- Offline generative LLM / local GGUF.
- Changing HUD bridge Connected/Offline semantics (that stays local WS).
- Persistent “force offline” user toggle (can add later).
