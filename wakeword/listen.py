from __future__ import annotations

from typing import Any, Callable

import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from openwakeword.utils import download_models

from config import (
    INPUT_DEVICE,
    SAMPLE_RATE,
    WAKEWORD_CHUNK_SAMPLES,
    WAKEWORD_INFERENCE_FRAMEWORK,
    WAKEWORD_MODEL,
    WAKEWORD_THRESHOLD,
)

_model: Model | None = None


def ensure_wakeword_ready() -> None:
    """Download pretrained models if needed and verify hey jarvis loads."""
    download_models()
    get_model()


def get_model() -> Model:
    global _model
    if _model is None:
        _model = Model(
            wakeword_models=[WAKEWORD_MODEL],
            inference_framework=WAKEWORD_INFERENCE_FRAMEWORK,
        )
    return _model


def _score_for_wakeword(prediction: dict[str, Any]) -> float:
    if WAKEWORD_MODEL in prediction:
        return float(prediction[WAKEWORD_MODEL])
    # Fallback: any key containing "jarvis"
    for key, value in prediction.items():
        if "jarvis" in str(key).lower():
            return float(value)
    if prediction:
        return float(next(iter(prediction.values())))
    return 0.0


def play_wakeup_chime() -> None:
    """Short confirmation tone after wake-word detection."""
    duration = 0.12
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    tone = 0.2 * np.sin(2 * np.pi * 880 * t).astype(np.float32)
    sd.play(tone, samplerate=SAMPLE_RATE)
    sd.wait()


def wait_for_wake_word(
    *,
    model: Model | None = None,
    threshold: float | None = None,
    read_chunk: Callable[[], np.ndarray] | None = None,
    on_detect: Callable[[], None] | None = play_wakeup_chime,
) -> float:
    """
    Block until the wake word score exceeds threshold.

    Returns the score that triggered detection.
    """
    oww = model if model is not None else get_model()
    limit = WAKEWORD_THRESHOLD if threshold is None else float(threshold)

    def _default_read() -> np.ndarray:
        audio = sd.rec(
            WAKEWORD_CHUNK_SAMPLES,
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            device=INPUT_DEVICE,
        )
        sd.wait()
        return np.squeeze(audio)

    reader = read_chunk if read_chunk is not None else _default_read

    while True:
        frame = reader()
        if frame.dtype != np.int16:
            frame = frame.astype(np.int16)
        prediction = oww.predict(frame)
        score = _score_for_wakeword(prediction)
        if score >= limit:
            if on_detect is not None:
                on_detect()
            return score
