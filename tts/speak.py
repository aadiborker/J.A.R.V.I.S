from __future__ import annotations

from pathlib import Path

import numpy as np
import sounddevice as sd
from piper import PiperVoice, SynthesisConfig

from config import (
    PIPER_LENGTH_SCALE,
    PIPER_MODEL_PATH,
    PIPER_NOISE_SCALE,
    PIPER_NOISE_W_SCALE,
    PIPER_VOLUME,
)

_voice: PiperVoice | None = None


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
    """Return mono float32 audio and sample rate for the given text."""
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


def speak(text: str, *, voice: PiperVoice | None = None) -> None:
    """Synthesize text and block until playback finishes."""
    audio, sample_rate = synthesize_audio(text, voice=voice)
    if audio.size == 0:
        return
    sd.play(audio, samplerate=sample_rate)
    sd.wait()
