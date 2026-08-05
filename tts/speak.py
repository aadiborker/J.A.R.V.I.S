from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import miniaudio
import numpy as np
import sounddevice as sd
from piper import PiperVoice, SynthesisConfig

from config import (
    EDGE_TTS_TIMEOUT_SECONDS,
    EDGE_VOICE,
    PIPER_LENGTH_SCALE,
    PIPER_MODEL_PATH,
    PIPER_NOISE_SCALE,
    PIPER_NOISE_W_SCALE,
    PIPER_VOLUME,
    TTS_PREFER_EDGE,
)
from net.connectivity import is_online

_voice: PiperVoice | None = None
_edge_fail_logged = False


def ensure_piper_ready() -> None:
    model = Path(PIPER_MODEL_PATH)
    config = Path(str(model) + ".json")
    if not model.is_file():
        raise FileNotFoundError(
            f"Piper voice model not found at {model}. "
            "Download with: python -m piper.download_voices en_US-lessac-medium "
            "--download-dir models/piper"
        )
    if not config.is_file():
        raise FileNotFoundError(
            f"Piper voice config not found at {config}. "
            "Re-download en_US-lessac-medium into models/piper."
        )


def get_voice() -> PiperVoice:
    global _voice
    ensure_piper_ready()
    if _voice is None:
        _voice = PiperVoice.load(PIPER_MODEL_PATH)
    return _voice


def _synthesis_config() -> SynthesisConfig:
    return SynthesisConfig(
        length_scale=PIPER_LENGTH_SCALE,
        noise_scale=PIPER_NOISE_SCALE,
        noise_w_scale=PIPER_NOISE_W_SCALE,
        normalize_audio=True,
        volume=PIPER_VOLUME,
    )


def synthesize_audio(text: str, *, voice: PiperVoice | None = None) -> tuple[np.ndarray, int]:
    """Return mono float32 audio and sample rate for the given text (Piper)."""
    cleaned = (text or "").strip()
    if not cleaned:
        return np.zeros(0, dtype=np.float32), 22050

    piper_voice = voice if voice is not None else get_voice()
    chunks: list[np.ndarray] = []
    sample_rate = 22050
    for chunk in piper_voice.synthesize(cleaned, syn_config=_synthesis_config()):
        sample_rate = int(chunk.sample_rate)
        audio = np.asarray(chunk.audio_float_array, dtype=np.float32).reshape(-1)
        if audio.size:
            chunks.append(audio)

    if not chunks:
        return np.zeros(0, dtype=np.float32), sample_rate
    return np.concatenate(chunks), sample_rate


def _play_float_audio(audio: np.ndarray, sample_rate: int) -> None:
    if audio.size == 0:
        return
    sd.play(audio, samplerate=sample_rate)
    sd.wait()


def _speak_piper(text: str, *, voice: PiperVoice | None = None) -> None:
    audio, sample_rate = synthesize_audio(text, voice=voice)
    _play_float_audio(audio, sample_rate)


async def _edge_save_mp3(text: str, path: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, EDGE_VOICE)
    await asyncio.wait_for(communicate.save(path), timeout=float(EDGE_TTS_TIMEOUT_SECONDS))


def _mp3_to_float32(path: str) -> tuple[np.ndarray, int]:
    decoded = miniaudio.decode_file(path)
    samples = np.asarray(decoded.samples, dtype=np.float32)
    # miniaudio may return interleaved stereo int16-ish floats in -1..1 already,
    # or int16 depending on version — normalize if needed.
    if samples.dtype != np.float32:
        samples = samples.astype(np.float32)
    if np.max(np.abs(samples), initial=0.0) > 1.5:
        samples = samples / 32768.0

    channels = int(getattr(decoded, "nchannels", 1) or 1)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)

    rate = int(decoded.sample_rate)
    return samples.astype(np.float32, copy=False), rate


def _speak_edge(text: str) -> None:
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        asyncio.run(_edge_save_mp3(text, path))
        audio, sample_rate = _mp3_to_float32(path)
        if audio.size == 0:
            raise RuntimeError("Edge TTS returned empty audio")
        _play_float_audio(audio, sample_rate)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def speak(text: str, *, voice: PiperVoice | None = None) -> None:
    """Synthesize text and block until playback finishes.

    Prefers Edge neural TTS when enabled; falls back to Piper offline/on error.
    """
    global _edge_fail_logged
    cleaned = (text or "").strip()
    if not cleaned:
        return

    if TTS_PREFER_EDGE and is_online():
        try:
            _speak_edge(cleaned)
            return
        except Exception as exc:  # noqa: BLE001
            if not _edge_fail_logged:
                print(f"Edge TTS unavailable ({exc}); using Piper fallback.")
                _edge_fail_logged = True

    _speak_piper(cleaned, voice=voice)
