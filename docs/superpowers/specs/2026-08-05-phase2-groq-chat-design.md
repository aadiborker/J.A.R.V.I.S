# Phase 2: Groq Chat Loop — Design

**Date:** 2026-08-05  
**Status:** Approved  
**Scope:** Phase 2 only (STT → Groq → print reply). No TTS, wake word, or tool-calling.

## Goal

Take transcribed microphone text, send it to Groq’s free-tier chat API, and print the model’s plain-text reply. Confirm API auth and basic multi-turn chat work on this machine before Piper TTS (Phase 3).

## Decisions locked in

| Topic | Choice |
|-------|--------|
| Groq access | User has API key; stored in local `.env` as `GROQ_API_KEY` (never commit) |
| Model | Start with `llama-3.1-8b-instant`; upgrade to `llama-3.3-70b-versatile` later for tools |
| Session context | In-memory multi-turn until process exits; no disk persistence yet |
| Approach | Thin `llm/client.py` + extend `main.py` |
| Voice output | Deferred to Phase 3 (Piper). Phase 2 prints text only; mic input unchanged from Phase 1 |

## Architecture

```
Enter → mic (5s) → whisper.cpp → transcript text
  → append {role: "user", content: transcript} to in-memory messages
  → Groq chat.completions (llama-3.1-8b-instant)
  → print assistant reply
  → append {role: "assistant", content: reply}
  → loop (history lives until Ctrl+C / process exit)
```

Startup loads `.env` via `python-dotenv`. Missing `GROQ_API_KEY` fails fast with a clear message. A short system prompt frames the assistant as a helpful voice assistant that keeps answers concise (ready for later TTS).

## Files & components

| Path | Role |
|------|------|
| `.env` | `GROQ_API_KEY=...` (local only; gitignored) |
| `.env.example` | Documents required keys without secrets |
| `config.py` | Add `GROQ_MODEL`, `SYSTEM_PROMPT` |
| `llm/__init__.py` | Package marker |
| `llm/client.py` | `get_client()`, `chat(messages: list[dict]) -> str` using official `groq` SDK |
| `main.py` | After transcript: call `chat`, print reply, maintain session `messages` |
| `requirements.txt` | Add `groq` |
| `tests/test_llm_client.py` | Unit tests with mocked Groq client (no live API required) |
| `README.md` | Document `.env` setup and Phase 2 run |

**Unchanged:** `stt/`, `vendor/whisper/`, `models/ggml-base.en.bin`.

**Out of scope:** Piper TTS, openWakeWord, tool schemas, persistent `memory/history.json`.

## Data flow

1. User presses Enter; Phase 1 recording + transcription runs.
2. If transcript is empty → print `(no speech detected)`; do not call Groq.
3. Else append user message; call `chat(messages)` including the system message once at session start.
4. Print `You said: ...` and `Jarvis: ...`.
5. Append assistant message; wait for Enter again.

## Error handling

- Missing `GROQ_API_KEY` → message pointing to `.env` / `.env.example`; exit non-zero at startup.
- Groq API / network errors → print error to stderr; keep the Enter-loop alive.
- Empty transcript → skip LLM; continue loop.
- Phase 1 whisper/mic errors → unchanged behavior from Phase 1.

## Verification criteria

Phase 2 is done when:

1. `.env` with a valid key allows `python main.py` to start without auth errors.
2. Speaking a question yields a printed LLM reply.
3. A follow-up that depends on prior context is answered using in-session memory.
4. No TTS, wake-word, or tool-calling code is present yet.

## Non-goals for this phase

- Spoken replies (Phase 3)
- Streaming token output
- Tool / function calling (Phase 5)
- Persistent memory across restarts (Phase 7)
- Switching to the 70B model (optional later)

## Later phases (reference only)

3. Piper TTS  
4. openWakeWord  
5. Tool-calling loop  
6. Real tools  
7. Optional persistent memory  
