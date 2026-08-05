# Hybrid TTS Design — Edge British Male + Piper Fallback

**Date:** 2026-08-05  
**Goal:** Make Jarvis sound more natural without breaking offline use.

## Non-goals / constraints

- Do **not** clone or impersonate Paul Bettany (or any real actor). Use licensed synthetic voices only.
- Keep the existing `speak(text)` API so `main.py`, timers, and wake-word pause behavior stay unchanged.
- Prefer free solutions; Edge neural voices are free; Piper remains the offline path.

## Approach (approved)

**Hybrid:** try Edge TTS (online) first; on failure or preference, use Piper (local).

| Mode | Engine | Voice |
|------|--------|--------|
| Online (preferred) | `edge-tts` | `en-GB-RyanNeural` (British male; swap to `en-GB-ThomasNeural` via config) |
| Offline / Edge error | Piper | existing `en_US-lessac-medium` |

## Architecture

1. Extend `tts/speak.py` (single entry point):
   - `speak(text)` → synthesize → `sounddevice` play → block until done.
   - Prefer Edge when `TTS_PREFER_EDGE` is true.
   - On any Edge failure (no network, timeout, empty audio): fall back to Piper and optionally log once.
2. Edge path:
   - Use `edge-tts` to synthesize MP3/WAV bytes (or stream to temp WAV).
   - Decode to float32 mono and play via existing `sounddevice` path (same as Piper).
3. Piper path: unchanged preload + `PiperVoice` synthesis.
4. Config (`config.py`):
   - `TTS_PREFER_EDGE = True`
   - `EDGE_VOICE = "en-GB-RyanNeural"`
   - `EDGE_TTS_TIMEOUT_SECONDS = 15` (or similar)
   - Existing Piper knobs unchanged.

## Error handling

- Missing `edge-tts` package → Piper only (clear message once at startup if prefer Edge).
- Network / Edge API errors → silent fallback to Piper for that utterance (or one-line console note).
- Empty text → no-op (current behavior).

## Verification

- Unit tests: mock Edge success, Edge failure→Piper, empty text.
- Manual: online reply should sound clearly more natural; airplane mode / kill network → Piper still speaks.

## Out of scope

- Celebrity / custom voice cloning.
- Streaming playback mid-sentence (keep full-utterance blocking play for Phase compatibility).
