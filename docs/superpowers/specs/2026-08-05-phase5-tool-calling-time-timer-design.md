# Phase 5: Tool Calling (Time + Timer) — Design

**Date:** 2026-08-05  
**Status:** Pending user review  
**Scope:** Add Groq tool-calling support for simple “time” and “timer” actions. Start with a minimal tool set; expand later.

---

## Goal

When you say things like:
- “what time is it?”
- “set a timer for 5 minutes”

the assistant should:
1. Prefer **regex/local fast paths** for time/timer when it’s unambiguous (to save latency/cost).
2. Otherwise use **Groq tool-calling** so the model can request tool executions in a structured way.
3. Speak a response using the existing Piper flow.

Timer reminders must **speak immediately when due** (your choice **A**) while preventing accidental wake-word triggers.

---

## Locked decisions

- Tool-calling approach: **Groq native tools/function-calls** (not JSON scraping).
- Simple commands approach: **C (both)**  
  - regex/local for clear “time” and “timer” requests
  - Groq tool-calling for everything else (including unclear durations that the model must interpret)
- Timer behavior: **speak reminder immediately when timer fires**, and **pause wake-word scoring** while speaking the reminder.
- Wake-word behavior: existing flow stays:
  - wake-word triggers a session
  - session continues without re-wake until “goodbye”/silence timeout

---

## Current architecture (what we will change)

Today:
- `main.py` runs:
  - `wait_for_wake_word()` (openWakeWord)
  - `run_conversation_session()` (mic → whisper → Groq → Piper)
- `llm/client.py` has only `chat(messages) -> str` (no tools)

Phase 5 adds:
- a tool-calling loop that:
  1. sends tool definitions to Groq
  2. executes model-requested tool calls in Python
  3. sends tool results back to Groq
  4. gets a final natural-language reply
- a TimerManager that runs reminders in the background and coordinates with wake-word scoring.

---

## Proposed file structure (Phase 5)

### New: tools
- `tools/__init__.py`
- `tools/simple_commands.py`  
  - Regex/local fast path handlers for:
    - “what time is it?”
    - “set a timer for X …”
  - If it handles the utterance, it returns assistant reply text (no Groq call).
- `tools/time_tools.py`  
  - `get_time() -> dict[str, str]` (tool output payload)
- `tools/timer_tools.py`  
  - `TimerManager` class
  - `set_timer(seconds: int, label: str = \"\") -> dict[str, str]` (tool output payload)
  - Uses a background worker thread per timer
  - Uses a `wakeword_pause_event` to pause wake-word scoring during reminders

### New: LLM tool loop
- `llm/tool_loop.py`
  - `chat_with_tools(messages, tools, tool_registry, *, client=None) -> str`
  - Executes tool calls requested by Groq until a final assistant message is returned.

### Updated:
- `main.py`
  - add wakeword_pause_event creation
  - pass pause event into wakeword listener / TimerManager
  - before tool-calling:
    - try `tools.simple_commands.try_handle_simple(text, ...)`
    - if handled, reply directly
    - else use `chat_with_tools(...)`
- `wakeword/listen.py`
  - extend `wait_for_wake_word(...)` with an optional `wakeword_pause_event`
  - while pause is set: continue mic capture (to keep stream stable) but **skip prediction / scoring** so wake-word can’t fire on reminder audio

---

## Tool schema (minimal set)

Tool names exposed to Groq (Phase 5 initial set):

1. `get_time`
   - Parameters: none
   - Output payload: `{ \"time\": \"<string>\" }`

2. `set_timer`
   - Parameters:
     - `seconds` (integer, required)
     - `label` (string, optional, for the user-facing reminder)
   - Output payload:
     - `{ \"timer_id\": \"<id>\", \"seconds\": <int>, \"label\": \"<label>\" }`

Regex fast-path still handles:
- “what time is it”
- “set a timer for five minutes”

even if the LLM tool-calling loop is implemented.

---

## Data flow (what happens on each user utterance)

1. User speaks during an active session.
2. `transcribe_microphone()` produces `text`.
3. **Local fast path (regex)**:
   - call `tools.simple_commands.try_handle_simple(text, timer_manager, ...)`
   - if it returns a reply: speak it and append to chat history
   - if it returns `None`: proceed to Groq tool-calling
4. **Groq tool-calling loop**:
   - call `llm.tool_loop.chat_with_tools(messages, tools=[...], tool_registry={...})`
   - execute requested tool calls
   - append tool results into the conversation so Groq can finalize
   - return assistant reply text
5. Speak reply with existing Piper code.

---

## TimerManager behavior (your choice A)

`TimerManager` responsibilities:
- `set_timer(seconds, label)`:
  - create a new timer worker thread
  - return a `timer_id` immediately to the model (so it can confirm)
  - worker thread sleeps for `seconds`
  - when due:
    - sets `wakeword_pause_event` to prevent wake-word triggers
    - calls the provided `speak_fn` with a reminder message
    - clears `wakeword_pause_event`

Wake-word safety:
- `wakeword/listen.py` will observe `wakeword_pause_event`
- while it’s set, it will not evaluate predictions / wakeword scores

---

## Error handling

- Regex fast path:
  - if it can’t confidently parse a duration, it returns `None` so Groq can handle it.
- Tool execution:
  - if Python tool execution fails, return a tool result payload with an `"error"` string so Groq can respond gracefully.
- Timer thread:
  - if `speak_fn` fails, log to stderr and clear the pause event so wake-word works again.

---

## Testing strategy (Phase 5)

### Unit tests (no live mic / no live Groq)
- `tools/simple_commands.py`
  - test time parsing triggers reply generation
  - test timer parsing converts “five minutes”, “30 seconds”, etc. into seconds
- `tools/time_tools.py`
  - test `get_time()` returns a payload with a non-empty `"time"`
- `tools/timer_tools.py`
  - test `TimerManager.set_timer(seconds=1, ...)` schedules a callback:
    - use a fake `speak_fn` that records calls
    - use `wakeword_pause_event` and assert it is set/cleared around the speak call
- `llm/tool_loop.py`
  - test tool loop behavior using mocked Groq responses that include tool call requests
  - test that tool results are fed back and the final assistant text is returned

### Manual verification
- “what time is it?” returns quickly (regex fast path)
- “set a timer for 10 seconds”:
  - assistant confirms immediately
  - after ~10 seconds, reminder speaks once
  - wake-word doesn’t self-trigger during the reminder

---

## Phase boundaries

This design covers:
- Phase 5 tool calling infrastructure
- minimal tools: `get_time`, `set_timer`

Out of scope for Phase 5 (later):
- SSH/server status tools
- email tools
- task creation / logging tools
- persistent memory

