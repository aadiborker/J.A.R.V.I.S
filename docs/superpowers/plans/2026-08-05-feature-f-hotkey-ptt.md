# Feature F Hotkey PTT — Implementation Plan

**Goal:** Ctrl+Alt+J launches if closed; hold-to-talk when running.

**Tasks:**
1. Bidirectional WS + PTT recorder start/stop
2. Python hotkey poller in main (PTT)
3. Watchdog script + autostart for launch-when-closed
4. HUD status for PTT; tests

See spec: `docs/superpowers/specs/2026-08-05-feature-f-hotkey-ptt-design.md`
