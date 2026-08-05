# Features B + C — Implementation Plan

> **For agentic workers:** Execute task-by-task.

**Goal:** Allowlisted desktop app launch + system controls (RAM/CPU, volume, mute, lock, screenshot, brightness).

## Tasks

1. `tools/app_tools.py` + tests
2. `tools/system_tools.py` + tests  
3. Fast-paths in `simple_commands.py`; offline reply update
4. Register Groq tools in `main.py`; deps in `requirements.txt`
5. `pytest tests/ -q` green

See: `docs/superpowers/specs/2026-08-05-features-b-c-apps-system-design.md`
