# Phase 1: Local Speech-to-Text Loop — Design

**Date:** 2026-08-05  
**Status:** Approved  
**Scope:** Phase 1 only (record → whisper.cpp → print). No LLM, TTS, wake word, or tools.

## Goal

Build a minimal voice loop that records a short microphone clip, transcribes it with whisper.cpp (`base.en`), and prints the text to the console. Verify STT works on this Windows machine before any later phases.

## Decisions locked in

| Topic | Choice |
|-------|--------|
| Whisper runtime | Prebuilt `whisper-cli.exe` + Python `subprocess` |
| Recording UX | Fixed length: press Enter → record N seconds → transcribe |
| Project root | This workspace (`J.A.R.V.I.S/`), not a nested `jarvis-assistant/` |
| Approach | Vendor binaries + WAV round-trip |

## System context

- Windows, ~15.5 GB RAM, ample disk
- Prefer local audio stack; Groq only from Phase 2 onward
- Python / terminal-first; no GUI

## Architecture

```
Microphone (sounddevice)
  → fixed-duration capture @ 16 kHz mono float32
  → write temp WAV (16-bit PCM)
  → whisper-cli.exe -m models/ggml-base.en.bin -f <wav> -nt -np
  → parse stdout transcript
  → print "You said: ..."
  → delete temp WAV
  → wait for Enter again (Ctrl+C to exit)
```

Config lives in `config.py` (paths, sample rate, record seconds, optional input device). No API keys required in Phase 1.

## Files & components

| Path | Role |
|------|------|
| `main.py` | Orchestration loop: prompt → record → transcribe → print |
| `config.py` | `WHISPER_BIN`, `WHISPER_MODEL`, `SAMPLE_RATE=16000`, `RECORD_SECONDS=5`, optional `INPUT_DEVICE` |
| `stt/transcribe.py` | `record_audio()` and `transcribe(wav_path) -> str` via subprocess |
| `stt/__init__.py` | Package marker |
| `requirements.txt` | Phase 1: `sounddevice`, `numpy`, `scipy`, `python-dotenv` |
| `vendor/whisper/` | Prebuilt Windows `whisper-cli.exe` (+ required DLLs) |
| `models/ggml-base.en.bin` | Whisper `base.en` model weights |
| `.gitignore` | `.env`, `vendor/`, `models/`, `__pycache__/`, temp audio |
| `README.md` | Download binary/model, install deps, run `python main.py` |

**Out of scope (later phases):** `tts/`, `wakeword/`, `llm/`, `tools/`, `memory/`, Groq, Piper, openWakeWord.

## Data flow

1. User presses Enter.
2. `sounddevice.rec` captures `RECORD_SECONDS` at `SAMPLE_RATE` mono.
3. Audio written to a temp `.wav` (16-bit PCM).
4. `subprocess.run` invokes whisper-cli with model path and WAV path; flags include `-nt` (no timestamps) and `-np` (no prints beyond transcript where supported).
5. Stdout parsed into a clean transcript string.
6. Print `You said: <transcript>` (or `(no speech detected)` if empty).
7. Delete temp WAV; loop until Ctrl+C.

## Error handling

- Missing binary or model → print expected paths and download guidance; exit non-zero.
- Mic / device errors → catch and print actionable message.
- Non-zero whisper exit → surface stderr; keep the loop usable where possible.
- Empty transcript → print `(no speech detected)` and continue.

## Setup (manual, one-time)

1. Download a Windows prebuilt whisper.cpp release containing `whisper-cli.exe` into `vendor/whisper/`.
2. Download `ggml-base.en.bin` into `models/`.
3. `pip install -r requirements.txt`
4. `python main.py`

Exact download URLs will be confirmed during implementation against current ggml-org/whisper.cpp releases.

## Verification criteria

Phase 1 is done when:

1. Speaking a short phrase after Enter yields matching text in the console.
2. Latency with `base.en` is acceptable on this machine.
3. Codebase contains no LLM, TTS, or wake-word integration.

## Non-goals for this phase

- Silence detection / VAD
- Continuous listening or wake word
- Streaming transcription
- Model upgrades beyond `base.en` (can revisit after Phase 1 works)

## Later phases (reference only)

2. Groq chat (text in → text out)  
3. Piper TTS  
4. openWakeWord  
5. Tool-calling loop  
6. Real tools (time/timer → SSH/email/tasks)  
7. Optional persistent memory  
