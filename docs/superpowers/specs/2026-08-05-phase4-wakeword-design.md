# Phase 4: openWakeWord — Design

**Date:** 2026-08-05  
**Status:** Approved (option B: pretrained model)  
**Scope:** Replace Enter-to-record with continuous wake-word listening.

## Decisions

| Topic | Choice |
|-------|--------|
| Model | Pretrained `hey_jarvis` ("hey jarvis") via openWakeWord |
| Framework | ONNX on Windows |
| After detect | Short console ack + optional beep; then fixed-length record → STT → Groq → TTS |
| During reply | Do not run wake-word listening (avoid self-trigger from speakers) |

## Architecture

```
Listen (openWakeWord, 16 kHz frames)
  → score >= threshold for hey_jarvis
  → record N seconds → whisper → Groq → Piper speak
  → return to listen
```

## Files

- `wakeword/listen.py` — `ensure_wakeword_ready()`, `wait_for_wake_word()`
- `config.py` — model name, threshold, frame size
- `main.py` — replace Enter with `wait_for_wake_word()`
- `requirements.txt` — `openwakeword`
- tests with mocked Model
