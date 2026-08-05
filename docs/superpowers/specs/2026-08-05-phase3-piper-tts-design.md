# Phase 3: Piper TTS — Design

**Date:** 2026-08-05  
**Status:** Approved  
**Scope:** Speak Groq replies aloud with local Piper TTS. No wake word or tools yet.

## Goal

After the LLM reply is printed, synthesize it with Piper (`en_US-ryan-medium`) and play it through the speakers/earphones, blocking until playback finishes.

## Decisions locked in

| Topic | Choice |
|-------|--------|
| Voice | `en_US-ryan-medium` |
| Playback | Blocking until speech finishes |
| Approach | `piper-tts` Python API + `sounddevice` playback |
| Next | After Phase 3 verified, add wake word (Phase 4) |

## Architecture

```
… Phase 2 → Groq reply text
  → print "Jarvis: …"
  → Piper synthesize (en_US-ryan-medium)
  → sounddevice play (blocking)
  → prompt Enter again
```

Voice model loaded once and reused. Still no wake word or tools.

## Files & components

| Path | Role |
|------|------|
| `tts/__init__.py` | Package marker |
| `tts/speak.py` | Load Piper once; `speak(text) -> None` + blocking playback |
| `config.py` | `PIPER_MODEL_PATH` → `models/piper/en_US-ryan-medium.onnx` |
| `main.py` | Call `speak(reply)` after print; TTS errors don't kill the loop |
| `requirements.txt` | Add `piper-tts` |
| `models/piper/` | `.onnx` + `.onnx.json` (under gitignored `models/`) |
| `tests/test_speak.py` | Mocked unit tests |
| `README.md` | Voice download + run notes |

## Error handling

- Missing model/json → clear download guidance; fail at startup check.
- TTS/playback failure → print error; keep loop alive.
- Empty reply → skip `speak()`.

## Verification

1. Hear spoken reply after `Jarvis: …`
2. Next Enter prompt only after playback ends
3. No wake-word/tool code yet

## Non-goals

- Wake word (Phase 4, immediately after this works)
- Streaming TTS, multiple voices UI, tools
