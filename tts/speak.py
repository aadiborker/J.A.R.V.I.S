from __future__ import annotations

from pathlib import Path

import numpy as np
import sounddevice as sd
from piper import PiperVoice

from config import PIPER_MODEL_PATH

_voice: PiperVoice | None = None


def ensure_piper_ready() -> None:
    model = Path(PIPER_MODEL_PATH)
    config = Path(str(model) + ".json")
    if not model.is_file():
        raise FileNotFoundError(
            f"Piper voice model not found at {model}. "
            "Download with: python -m piper.download_voices en_US-ryan-medium "
            "--download-dir models/piper"
        )
    if not config.is_file():
        raise FileNotFoundError(
            f"Piper voice config not found at {config}. "
            "Re-download en_US-ryan-medium into models/piper."
        )


def get_voice() -> PiperVoice:
    global _voice
    ensure_piper_ready()
    if _voice is None:
        _voice = PiperVoice.load(PIPER_MODEL_PATH)
    return _voice


def synthesize_audio(text: str, *, voice: PiperVoice | None = None) -> tuple[np.ndarray, int]:
    """Return mono float32 audio and sample rate for the given text."""
    cleaned = (text or "").strip()
    if not cleaned:
        return np.zeros(0, dtype=np.float32), 22050

    piper_voice = voice if voice is not None else get_voice()
    chunks: list[np.ndarray] = []
    sample_rate = 22050
    for chunk in piper_voice.synthesize(cleaned):
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
