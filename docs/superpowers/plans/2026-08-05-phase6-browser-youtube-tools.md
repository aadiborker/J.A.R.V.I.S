# Phase 6 Browser / YouTube Tools — Implementation Plan

> **For agentic workers:** Execute task-by-task. Checkbox steps for tracking.

**Goal:** Open YouTube, YouTube search, and http(s) URLs via `webbrowser` + allowlist, with local fast-paths and Groq tools.

**Architecture:** `tools/browser_tools.py` for validate/open; extend `simple_commands.py`; register tools in `main.py`; offline refusal for browser intents.

**Tech Stack:** Python stdlib `webbrowser`, `urllib.parse`; pytest.

## Tasks

1. `browser_tools.py` + unit tests (validate, open mocks, youtube search URL)
2. Extend `simple_commands.py` + offline browser refusal + tests
3. Wire Groq tools in `main.py`
4. `pytest tests/ -q` green; manual checklist in README note optional

See: `docs/superpowers/specs/2026-08-05-phase6-browser-youtube-tools-design.md`
