# Wow UI Design — Electron HUD Phases A–C

**Date:** 2026-08-05  
**Goal:** Make the Electron HUD feel cinematic and always-present, without changing Python voice/AI logic.

## Phases (approved)

| Phase | Focus |
|-------|--------|
| A | Cinematic HUD chrome + stronger state animations |
| B | Reactive waveform/energy look tied to UI state |
| C | Tray icon, hide-to-tray, autostart/shortcut → HUD |

## Non-goals

- New tools / memory / TTS engine changes
- WebGL / Three.js (keep CSS + canvas 2D)
- Purple “AI slop” palette — stay steel/cyan

## Phase A

- Corner brackets, subtle scanline, faint grid
- State badge under brand
- Stronger ring/core motion per `idle|listening|thinking|speaking|error`
- Transcript as clearer HUD cards

## Phase B

- Canvas under/near the ring: bars or circular energy ticks
- Amplitude/speed driven by `state` (not real mic FFT in v1)
- Speaking = higher motion; idle = slow breathe

## Phase C

- Electron Tray with Show / Quit
- Window close (X) hides to tray by default; Quit from tray exits Python + app
- `install_autostart.ps1` + desktop shortcut target HUD launcher

## Verification

- Visual: states visibly different; waveform moves on speaking
- Tray: hide/show works; Quit stops Python
- Autostart script points at `start_jarvis_ui.bat`
