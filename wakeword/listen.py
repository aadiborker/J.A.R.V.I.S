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


def reset_model(model: Model | None = None) -> None:
    oww = model if model is not None else _model
    if oww is None:
        return
    if hasattr(oww, "reset"):
        oww.reset()


def _score_for_wakeword(prediction: dict[str, Any]) -> float:
    if WAKEWORD_MODEL in prediction:
        return float(prediction[WAKEWORD_MODEL])
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


def _to_int16_mono(frame: np.ndarray) -> np.ndarray:
    audio = np.asarray(frame)
    if audio.ndim > 1:
        audio = audio[:, 0]
    audio = np.squeeze(audio)
    if audio.dtype != np.int16:
        # sounddevice may deliver float; convert to PCM16
        clipped = np.clip(audio.astype(np.float32), -1.0, 1.0)
        audio = (clipped * 32767.0).astype(np.int16)
    return audio


def wait_for_wake_word(
    *,
    model: Model | None = None,
    threshold: float | None = None,
    read_chunk: Callable[[], np.ndarray] | None = None,
    on_detect: Callable[[], None] | None = play_wakeup_chime,
    show_scores: bool = True,
) -> float:
    """
    Block until the wake word score exceeds threshold.

    Uses a continuous InputStream by default. Gappy per-chunk sd.rec() breaks
    openWakeWord's streaming feature pipeline and prevents detection.

    Returns the score that triggered detection.
    """
    oww = model if model is not None else get_model()
    reset_model(oww)
    limit = WAKEWORD_THRESHOLD if threshold is None else float(threshold)

    # Injected reader path (unit tests)
    if read_chunk is not None:
        while True:
            frame = _to_int16_mono(read_chunk())
            prediction = oww.predict(frame)
            score = _score_for_wakeword(prediction)
            if score >= limit:
                if on_detect is not None:
                    on_detect()
                reset_model(oww)
                return score

    chunk = WAKEWORD_CHUNK_SAMPLES
    frames_since_log = 0
    best = 0.0

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=chunk,
        device=INPUT_DEVICE,
    ) as stream:
        while True:
            raw, overflowed = stream.read(chunk)
            if overflowed and show_scores:
                print("Wake-word mic overflow (audio glitch); continuing...")
            frame = _to_int16_mono(raw)
            prediction = oww.predict(frame)
            score = _score_for_wakeword(prediction)
            best = max(best, score)
            frames_since_log += 1

            # ~2s at 80ms chunks
            if show_scores and frames_since_log >= 25:
                print(f"  listening… peak score={best:.3f} (need ≥ {limit:.2f})")
                frames_since_log = 0
                best = 0.0

            if score >= limit:
                if on_detect is not None:
                    on_detect()
                reset_model(oww)
                return score
