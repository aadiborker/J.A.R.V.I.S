# Jarvis-y Feel — Speed Spine + Lite Mode — Design

**Date:** 2026-08-05  
**Goal:** Make J.A.R.V.I.S feel less like a slow chatbot-with-mic and more like a present assistant: snappy first, then personality, presence, and light memory. Optional **Lite mode** cuts RAM when the HUD is not needed.

## Motivation

User feedback:
1. Takes too long to “understand”
2. Feels slow overall
3. ~10% RAM while running in background is painful
4. Without earphones, speech is often missed
5. Doesn’t feel “Jarvis-y” (presence / confidence / immediacy)

Priority locked: **all of the above, speed first.** RAM approach: **Lite mode** (optional no-Electron; idle sleep).

## Approach

**Speed spine first, then polish in waves** (not prompt-only, not full local-LLM rewrite).

| Wave | Theme | Outcome |
|------|--------|---------|
| **A** | Speed + mic + Lite | Less dead air; better laptop mic; lower RAM option |
| **B** | Personality | Concise, confident spoken style |
| **C** | Presence | HUD/SFX when HUD is on |
| **D** | Anticipation | Small persistent prefs/memory |

## Wave A — Speed, mic, Lite (implement first)

### A1. VAD / end-of-speech listening
- Replace fixed `RECORD_SECONDS = 5` conversation capture with energy-based VAD:
  - Start recording on session listen
  - Stop after ~N ms of low energy (e.g. 600–900 ms) once speech was detected
  - Hard cap ~8–10 s
- Keep a short minimum so clicks aren’t cut off
- Idle wake-word path unchanged (openWakeWord)

### A2. Faster STT path
- Prefer keeping Whisper warm across turns (persistent process or in-process library) so each utterance doesn’t cold-load `ggml-base.en`
- If warm process is too heavy for Lite, document trade-off: warm = faster, more RAM; cold = slower, lighter
- Retain hallucination / silence filters from recent STT hardening

### A3. Mic profile (no earphones)
- Default remains system default device, but add:
  - Documented way to set `INPUT_DEVICE` to laptop **Microphone Array**
  - Slightly more permissive silence RMS for array mics (or a `MIC_PROFILE=laptop|headset` config)
- Goal: desk-volume speech without headset is usable

### A4. Lite mode
- **Lite = no Electron HUD:** `python main.py` / `scripts/start_jarvis.bat` as first-class “low RAM” entry
- HUD remains `scripts/start_jarvis_ui.bat` when user wants presence UI
- **Idle sleep (optional config):** after quiet period (e.g. 10–15 min with no wake), reduce work (pause nonessential monitors / avoid spawning STT); wake word still required to resume full loop where feasible
- Do not force-unload wake word if that breaks “hey jarvis” (prefer pausing HUD-related and deferring Piper load until first speak)

## Wave B — Personality

- Tighten `SYSTEM_PROMPT` toward Iron Man–adjacent Jarvis: short, dry, confident, spoken English
- Optional address style later (e.g. name from memory); default no forced “Sir”
- Brief working acks when a turn will take noticeable time (“On it.”) — only if latency still warrants it after Wave A

## Wave C — Presence

- When HUD is running: clearer idle / listening / thinking / speaking states
- Keep light SFX on wake and “got it” (already partially present)
- Out of scope for first cut: full cinematic redesign

## Wave D — Anticipation

- Small JSON memory file (e.g. `data/memory.json`): display name, a few prefs
- Load into system prompt or tool `remember` / `recall` — details in a follow-on plan
- Not a full RAG brain

## Non-goals (this initiative)

- Reintroducing hotkeys / PTT
- Local LLM (Feature G) as the primary brain
- Screen vision (Feature H)
- Removing the HUD permanently

## Success criteria

- After wake + short command, spoken reply begins in a few seconds in typical online conditions (noticeably faster than fixed 5s + cold Whisper)
- Laptop mic array at normal desk volume works without earphones for clear speech
- Lite mode (no Electron) uses clearly less RAM than full HUD stack
- Replies feel more Jarvis-like (Wave B) without long essays
- Optional: prefs survive restart (Wave D)

## Suggested build order

1. Spec + plan for Wave A only → implement & verify  
2. Wave B (prompt + light acks)  
3. Wave C (HUD polish if still using UI)  
4. Wave D (memory)

## Open decisions (resolve in Wave A plan)

- Warm Whisper vs faster-whisper / other in-process STT
- Exact VAD thresholds and max utterance length
- Idle-sleep duration default and what exactly pauses
