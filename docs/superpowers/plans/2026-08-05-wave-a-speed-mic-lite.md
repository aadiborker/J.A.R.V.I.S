# Wave A — Speed + Mic + Lite Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut conversation dead air with VAD, improve laptop-mic pickup, and make no-HUD Lite mode a first-class low-RAM path with optional idle sleep.

**Architecture:** Add energy-based VAD recording for session/mic capture; resolve `MIC_PROFILE` into silence thresholds and optional device hints; treat absence of `--ui-ws` as Lite (defer Piper load, document as low-RAM entry); after long idle, pause network/power monitors while wake-word stays armed. Keep existing `whisper-cli` for STT; boot warm-up transcribes a tiny WAV once to heat disk cache (full in-process Whisper deferred if still slow).

**Tech Stack:** Python 3.10+, `sounddevice`, `numpy`, existing `whisper-cli` + `ggml-base.en`, pytest.

**Spec:** `docs/superpowers/specs/2026-08-05-jarvis-y-feel-speed-lite-design.md` (Wave A only).

## Global Constraints

- Windows-first; do not reintroduce hotkeys/PTT
- Wake-word path (openWakeWord) stays as-is
- Retain `clean_transcript` / spurious filters
- Waves B–D are out of scope for this plan
- Prefer config knobs over hard-coding magic numbers

## Resolved decisions (from spec open items)

| Item | Decision |
|------|----------|
| STT warm | Keep `whisper-cli`; add boot `warmup_whisper()` (one tiny WAV). No faster-whisper in Wave A. |
| VAD | Speech RMS ≥ threshold → speech started; after start, stop after `VAD_SILENCE_MS` (800) of below-threshold frames; max `VAD_MAX_SECONDS` (10); min `VAD_MIN_SECONDS` (0.4) |
| Idle sleep | Default `IDLE_SLEEP_SECONDS = 900`; pause NetworkMonitor + PowerMonitor only; wake word continues |

## File map

| File | Role |
|------|------|
| `config.py` | VAD, mic profile, idle-sleep, silence RMS per profile |
| `stt/vad_record.py` | Chunked mic capture until end-of-speech |
| `stt/transcribe.py` | Use VAD; boot warm-up helper |
| `stt/mic_profile.py` | Resolve profile → RMS / device |
| `main.py` | Lite piper deferral; idle sleep around wake loop |
| `README.md` | Lite vs HUD; mic profile tip |
| `tests/test_vad_record.py` | VAD unit tests with fake audio |
| `tests/test_mic_profile.py` | Profile resolution tests |

---

### Task 1: Config + mic profile helpers

**Files:**
- Modify: `config.py`
- Create: `stt/mic_profile.py`
- Create: `tests/test_mic_profile.py`

**Interfaces:**
- Produces: `resolve_mic_settings() -> MicSettings(device, silence_rms)`
- Consumes: `config.MIC_PROFILE`, `INPUT_DEVICE`, `STT_SILENCE_RMS`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_mic_profile.py
from stt.mic_profile import resolve_mic_settings

def test_laptop_profile_more_permissive(monkeypatch):
    import config as cfg
    monkeypatch.setattr(cfg, "MIC_PROFILE", "laptop")
    monkeypatch.setattr(cfg, "STT_SILENCE_RMS", 0.012)
    monkeypatch.setattr(cfg, "STT_SILENCE_RMS_LAPTOP", 0.006)
    monkeypatch.setattr(cfg, "INPUT_DEVICE", None)
    s = resolve_mic_settings()
    assert s.silence_rms == 0.006
    assert s.device is None

def test_headset_uses_default_rms(monkeypatch):
    import config as cfg
    monkeypatch.setattr(cfg, "MIC_PROFILE", "headset")
    monkeypatch.setattr(cfg, "STT_SILENCE_RMS", 0.012)
    monkeypatch.setattr(cfg, "INPUT_DEVICE", 1)
    s = resolve_mic_settings()
    assert s.silence_rms == 0.012
    assert s.device == 1
```

- [ ] **Step 2: Run tests — expect FAIL (import / missing)**

Run: `pytest tests/test_mic_profile.py -q`

- [ ] **Step 3: Add config knobs**

Append to `config.py` (keep existing `STT_SILENCE_RMS`):

```python
# Mic: "laptop" = quieter array (more permissive silence gate); "headset" = default
MIC_PROFILE = "laptop"  # laptop | headset
STT_SILENCE_RMS_LAPTOP = 0.006

# VAD conversation capture (replaces fixed RECORD_SECONDS for session listen)
VAD_CHUNK_MS = 80
VAD_SILENCE_MS = 800
VAD_MIN_SECONDS = 0.4
VAD_MAX_SECONDS = 10.0
VAD_SPEECH_RMS = None  # None → use resolve_mic_settings().silence_rms

# Lite / idle
IDLE_SLEEP_SECONDS = 900  # 15 min; 0 disables
```

- [ ] **Step 4: Implement `stt/mic_profile.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
import config as cfg

@dataclass(frozen=True)
class MicSettings:
    device: int | None
    silence_rms: float

def resolve_mic_settings() -> MicSettings:
    profile = (getattr(cfg, "MIC_PROFILE", "headset") or "headset").strip().lower()
    device = cfg.INPUT_DEVICE
    if profile == "laptop":
        rms = float(getattr(cfg, "STT_SILENCE_RMS_LAPTOP", cfg.STT_SILENCE_RMS))
    else:
        rms = float(cfg.STT_SILENCE_RMS)
    return MicSettings(device=device, silence_rms=rms)
```

- [ ] **Step 5: Run tests — expect PASS**

Run: `pytest tests/test_mic_profile.py -q`

- [ ] **Step 6: Commit** (only if user asked to commit)

---

### Task 2: VAD recorder

**Files:**
- Create: `stt/vad_record.py`
- Create: `tests/test_vad_record.py`

**Interfaces:**
- Consumes: `MicSettings`, config VAD_* , `SAMPLE_RATE`, `CHANNELS`
- Produces: `record_until_silence(...) -> tuple[Path, float]` (path, overall rms)

- [ ] **Step 1: Write failing tests with synthetic chunks**

```python
# tests/test_vad_record.py
import numpy as np
from stt.vad_record import decide_vad_action

def test_vad_waits_before_speech():
    # below threshold, never started → continue
    assert decide_vad_action(rms=0.001, speech_started=False, silence_ms=0,
                             speech_rms=0.01, silence_needed_ms=800) == "continue"

def test_vad_starts_on_speech():
    assert decide_vad_action(rms=0.05, speech_started=False, silence_ms=0,
                             speech_rms=0.01, silence_needed_ms=800) == "speech"

def test_vad_stops_after_silence():
    assert decide_vad_action(rms=0.001, speech_started=True, silence_ms=800,
                             speech_rms=0.01, silence_needed_ms=800) == "stop"
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement decide + recorder**

```python
# stt/vad_record.py (core logic)
from __future__ import annotations
import tempfile
from pathlib import Path
import numpy as np
import sounddevice as sd
from config import CHANNELS, SAMPLE_RATE, VAD_CHUNK_MS, VAD_MAX_SECONDS, VAD_MIN_SECONDS, VAD_SILENCE_MS
from stt.mic_profile import resolve_mic_settings
from stt.transcribe import audio_rms, write_wav

def decide_vad_action(*, rms: float, speech_started: bool, silence_ms: float,
                      speech_rms: float, silence_needed_ms: float) -> str:
    if not speech_started:
        return "speech" if rms >= speech_rms else "continue"
    if rms < speech_rms:
        return "stop" if silence_ms >= silence_needed_ms else "continue"
    return "speech"  # reset silence accumulation in caller

def record_until_silence(*, on_recording_done=None) -> tuple[Path, float]:
    settings = resolve_mic_settings()
    speech_rms = float(settings.silence_rms)
    chunk = max(1, int(SAMPLE_RATE * (VAD_CHUNK_MS / 1000.0)))
    max_frames = int(SAMPLE_RATE * float(VAD_MAX_SECONDS))
    min_frames = int(SAMPLE_RATE * float(VAD_MIN_SECONDS))
    chunks: list[np.ndarray] = []
    total = 0
    speech_started = False
    silence_ms = 0.0
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                        dtype="float32", device=settings.device, blocksize=chunk) as stream:
        while total < max_frames:
            data, _ = stream.read(chunk)
            data = np.squeeze(data)
            chunks.append(np.array(data, copy=True))
            total += data.size
            rms = audio_rms(data)
            action = decide_vad_action(
                rms=rms, speech_started=speech_started, silence_ms=silence_ms,
                speech_rms=speech_rms, silence_needed_ms=float(VAD_SILENCE_MS),
            )
            if action == "speech":
                speech_started = True
                silence_ms = 0.0
            elif action == "continue" and speech_started and rms < speech_rms:
                silence_ms += VAD_CHUNK_MS
            elif action == "stop" and total >= min_frames:
                break
            elif action == "stop":
                silence_ms = float(VAD_SILENCE_MS)  # keep waiting for min length
    if on_recording_done is not None:
        on_recording_done()
    audio = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
    energy = audio_rms(audio)
    tmp = tempfile.NamedTemporaryFile(prefix="jarvis_", suffix=".wav", delete=False)
    path = Path(tmp.name); tmp.close()
    write_wav(path, audio, sample_rate=SAMPLE_RATE)
    return path, energy
```

Fix stop-branch carefully in implementation so `silence_ms` accumulates on quiet frames after speech.

- [ ] **Step 4: Tests PASS for `decide_vad_action`**

- [ ] **Step 5: Commit** (if requested)

---

### Task 3: Wire VAD into `transcribe_microphone` + Whisper warm-up

**Files:**
- Modify: `stt/transcribe.py`
- Modify: `tests/test_transcribe.py` (mock VAD path if needed)
- Modify: `main.py` (`warmup_models`)

**Interfaces:**
- Produces: `warmup_whisper() -> None`; `transcribe_microphone` uses VAD by default

- [ ] **Step 1: Change `transcribe_microphone` to call `record_until_silence` instead of fixed `record_audio`**

Keep `record_audio(seconds=...)` for callers that pass explicit seconds (if any); session path uses VAD when `seconds is None`.

```python
def transcribe_microphone(seconds: float | None = None, *, on_recording_done=None) -> str:
    if seconds is None:
        from stt.vad_record import record_until_silence
        wav_path, energy = record_until_silence(on_recording_done=on_recording_done)
    else:
        wav_path, energy = record_audio(seconds=seconds)
        if on_recording_done is not None:
            on_recording_done()
    try:
        settings = resolve_mic_settings()  # from stt.mic_profile
        if energy < float(settings.silence_rms):
            return ""
        return transcribe(wav_path)
    finally:
        wav_path.unlink(missing_ok=True)
```

- [ ] **Step 2: Add `warmup_whisper()`**

Write ~0.3s of near-silence WAV to temp, call `transcribe`, delete; catch/log errors so boot never dies.

- [ ] **Step 3: Call `warmup_whisper()` from `warmup_models()` in `main.py` after `ensure_whisper_ready()`**

- [ ] **Step 4: `pytest tests/test_transcribe.py tests/test_vad_record.py -q` PASS**

---

### Task 4: Lite mode + idle sleep

**Files:**
- Modify: `main.py`
- Modify: `README.md`
- Modify: `scripts/start_jarvis.bat` (echo Lite tip)

**Interfaces:**
- Lite when `--ui-ws` absent: do not preload Piper in `warmup_models` (only `ensure_piper_ready` file check optional; skip `get_voice()`)
- Idle: track `last_activity = monotonic()`; update on wake and after each conversation session; if `IDLE_SLEEP_SECONDS > 0` and idle exceeded, stop network/power monitors; restart them on next wake

- [ ] **Step 1: Split warmup**

```python
def warmup_models(*, lite: bool) -> None:
    ensure_whisper_ready()
    from stt.transcribe import warmup_whisper
    warmup_whisper()
    def _piper():
        ensure_piper_ready()
        if not lite:
            get_voice()
    ...
```

- [ ] **Step 2: Idle sleep helpers in `main.py`**

```python
def _pause_background(monitors: list) -> None:
    for m in monitors:
        if m is not None and hasattr(m, "stop"):
            m.stop()

def _resume_background(factory_list) -> list:
    # re-create NetworkMonitor / PowerMonitor like boot
    ...
```

Use existing `NetworkMonitor.start/stop` and `PowerMonitor.start/stop` APIs (inspect and match).

- [ ] **Step 3: In wake loop, if slept, resume monitors once before conversation**

- [ ] **Step 4: README — “Lite (low RAM)” vs “HUD” section; set `MIC_PROFILE = \"laptop\"`; list devices tip: `python -c \"import sounddevice as sd; print(sd.query_devices())\"`**

- [ ] **Step 5: `pytest tests/ -q` green**

---

### Task 5: Manual verification checklist

- [ ] Lite: `scripts\start_jarvis.bat` — Task Manager shows no Electron; wake + short command feels shorter than before
- [ ] Without earphones, desk voice: “what time is it” works with `MIC_PROFILE=laptop`
- [ ] HUD still works via `scripts\start_jarvis_ui.bat`
- [ ] After 15 min idle (or temp `IDLE_SLEEP_SECONDS=30` for test), log shows sleep; “hey jarvis” still wakes

---

## Spec coverage

| Spec Wave A item | Task |
|------------------|------|
| A1 VAD | Task 2–3 |
| A2 Faster STT (warm) | Task 3 warm-up (cli cache); full in-process deferred |
| A3 Mic profile | Task 1 |
| A4 Lite + idle sleep | Task 4 |

## Out of plan

- Wave B/C/D
- faster-whisper / whisper-server persistent model
- Changing wake-word engine
