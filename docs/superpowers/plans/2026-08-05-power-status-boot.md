# Power Status Implementation Plan

> **For agentic workers:** Execute inline or via subagent-driven-development. Steps use checkbox syntax.

**Goal:** Boot announces power % + charging + joke; monitor announces plug/unplug; HUD power chip.

**Architecture:** `system/power.py` mirrors `net/connectivity.py` (status + PowerMonitor). Wired in `main.py` after network boot cue.

**Tech Stack:** Python ctypes `GetSystemPowerStatus`, pytest, Electron HUD WS.

## Tasks

1. `system/power.py` + config + unit tests (status, formatters, jokes, monitor debounce)
2. Wire boot + PowerMonitor in `main.py`
3. HUD `power` event chip
4. `pytest tests/ -q` green

See spec: `docs/superpowers/specs/2026-08-05-power-status-boot-design.md`
