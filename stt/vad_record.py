from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import sounddevice as sd

from config import (
    SAMPLE_RATE,
    VAD_CHUNK_MS,
    VAD_MAX_SECONDS,
    VAD_MIN_SECONDS,
    VAD_NO_SPEECH_SECONDS,
    VAD_SILENCE_MS,
    VAD_SPEECH_RMS,
)
from stt.mic_profile import apply_mic_gain, resolve_mic_settings


def decide_vad_action(
    *,
    rms: float,
    speech_started: bool,
    silence_ms: float,
    speech_rms: float,
    silence_needed_ms: float,
) -> str:
    """Return 'speech' | 'continue' | 'stop' for one VAD frame."""
    if not speech_started:
        return "speech" if rms >= speech_rms else "continue"
    if rms >= speech_rms:
        return "speech"
    if silence_ms >= silence_needed_ms:
        return "stop"
    return "continue"


def record_until_silence(*, on_recording_done=None) -> tuple[Path, float]:
    """Record until end-of-speech (energy VAD). Returns (wav_path, overall_rms)."""
    from stt.transcribe import audio_rms, write_wav

    settings = resolve_mic_settings()
    speech_rms = (
        float(VAD_SPEECH_RMS) if VAD_SPEECH_RMS is not None else float(settings.silence_rms)
    )
    chunk = max(1, int(SAMPLE_RATE * (VAD_CHUNK_MS / 1000.0)))
    max_frames = int(SAMPLE_RATE * float(VAD_MAX_SECONDS))
    min_frames = int(SAMPLE_RATE * float(VAD_MIN_SECONDS))
    no_speech_frames = int(SAMPLE_RATE * float(VAD_NO_SPEECH_SECONDS))
    silence_needed = float(VAD_SILENCE_MS)
    channels = max(1, int(settings.input_channels))

    chunks: list[np.ndarray] = []
    total = 0
    speech_started = False
    silence_ms = 0.0

    # Let PortAudio release the wake-word stream before we reopen the mic.
    sd.sleep(200)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=channels,
        dtype="float32",
        device=settings.device,
        blocksize=chunk,
    ) as stream:
        # Discard ~160ms of startup junk / AGC settle.
        warmup = max(1, int(SAMPLE_RATE * 0.16) // chunk)
        for _ in range(warmup):
            stream.read(chunk)

        while total < max_frames:
            data, _overflowed = stream.read(chunk)
            mono = apply_mic_gain(data, settings.gain)
            chunks.append(mono)
            total += int(mono.size)
            rms = audio_rms(mono)
            action = decide_vad_action(
                rms=rms,
                speech_started=speech_started,
                silence_ms=silence_ms,
                speech_rms=speech_rms,
                silence_needed_ms=silence_needed,
            )
            if action == "speech":
                speech_started = True
                silence_ms = 0.0
            elif action == "continue":
                if speech_started and rms < speech_rms:
                    silence_ms += float(VAD_CHUNK_MS)
            elif action == "stop":
                if total >= min_frames:
                    break
                silence_ms = min(silence_ms, silence_needed - float(VAD_CHUNK_MS))

            if not speech_started and total >= no_speech_frames:
                break

    if on_recording_done is not None:
        on_recording_done()

    audio = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
    energy = audio_rms(audio)
    if not speech_started:
        print(
            f"[MIC] No speech detected (rms={energy:.4f}, gate={speech_rms:.4f}, "
            f"device={settings.device}, ch={channels}, gain={settings.gain})",
            flush=True,
        )
    tmp = tempfile.NamedTemporaryFile(prefix="jarvis_", suffix=".wav", delete=False)
    path = Path(tmp.name)
    tmp.close()
    write_wav(path, audio, sample_rate=SAMPLE_RATE)
    return path, energy
