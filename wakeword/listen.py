from __future__ import annotations

from typing import Any, Callable
import threading

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
    """Short confirmation tone after wake-word detection (avoid sounddevice I/O)."""
    try:
        import winsound

        winsound.Beep(880, 120)
    except Exception:  # noqa: BLE001
        # Fallback: skip chime rather than risk stealing the mic stream.
        pass


def _to_int16_mono(frame: np.ndarray, *, gain: float = 1.0) -> np.ndarray:
    """Mix channels, apply gain, return PCM16 mono for openWakeWord."""
    from stt.mic_profile import apply_mic_gain

    audio = np.asarray(frame)
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32767.0
    else:
        audio = audio.astype(np.float32)
    mono = apply_mic_gain(audio, gain)
    return (np.clip(mono, -1.0, 1.0) * 32767.0).astype(np.int16)


def wait_for_wake_word(
    *,
    model: Model | None = None,
    threshold: float | None = None,
    read_chunk: Callable[[], np.ndarray] | None = None,
    on_detect: Callable[[], None] | None = play_wakeup_chime,
    show_scores: bool = True,
    wakeword_pause_event: threading.Event | None = None,
    abort_event: threading.Event | None = None,
) -> float | None:
    """
    Block until the wake word score exceeds threshold.

    Uses a continuous InputStream by default. Gappy per-chunk sd.rec() breaks
    openWakeWord's streaming feature pipeline and prevents detection.

    Returns the score that triggered detection, or None if abort_event was set.
    """
    oww = model if model is not None else get_model()
    reset_model(oww)
    limit = WAKEWORD_THRESHOLD if threshold is None else float(threshold)

    # Injected reader path (unit tests)
    if read_chunk is not None:
        while True:
            if abort_event is not None and abort_event.is_set():
                return None
            frame = _to_int16_mono(read_chunk())
            if wakeword_pause_event is not None and wakeword_pause_event.is_set():
                continue
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

    try:
        from stt.mic_profile import resolve_mic_settings

        settings = resolve_mic_settings()
        mic_device = settings.device if settings.device is not None else INPUT_DEVICE
        channels = max(1, int(settings.input_channels))
        gain = float(settings.gain)
    except Exception:  # noqa: BLE001
        mic_device = INPUT_DEVICE
        channels = 1
        gain = 1.0

    detected: float | None = None
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=channels,
        dtype="float32",
        blocksize=chunk,
        device=mic_device,
    ) as stream:
        while True:
            if abort_event is not None and abort_event.is_set():
                return None
            raw, overflowed = stream.read(chunk)
            if overflowed and show_scores:
                print("Wake-word mic overflow (audio glitch); continuing...")
            frame = _to_int16_mono(raw, gain=gain)
            if wakeword_pause_event is not None and wakeword_pause_event.is_set():
                continue
            prediction = oww.predict(frame)
            score = _score_for_wakeword(prediction)
            best = max(best, score)
            frames_since_log += 1

            # ~2s at 80ms chunks
            if show_scores and frames_since_log >= 25:
                print(f"  listening... peak score={best:.3f} (need >= {limit:.2f})")
                frames_since_log = 0
                best = 0.0

            if score >= limit:
                # Exit `with` so the InputStream fully releases before TTS/STT.
                detected = float(score)
                break

    if detected is None:
        return None
    try:
        sd.stop()
    except Exception:  # noqa: BLE001
        pass
    if on_detect is not None:
        on_detect()
    reset_model(oww)
    return detected
