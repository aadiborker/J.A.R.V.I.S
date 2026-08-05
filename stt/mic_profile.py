from __future__ import annotations

from dataclasses import dataclass

import config as cfg


@dataclass(frozen=True)
class MicSettings:
    device: int | None
    silence_rms: float
    gain: float
    input_channels: int


def resolve_mic_settings() -> MicSettings:
    profile = (getattr(cfg, "MIC_PROFILE", "headset") or "headset").strip().lower()
    device = cfg.INPUT_DEVICE
    if profile == "laptop":
        rms = float(getattr(cfg, "STT_SILENCE_RMS_LAPTOP", cfg.STT_SILENCE_RMS))
        gain = float(getattr(cfg, "MIC_GAIN_LAPTOP", 1.0))
        wanted = 4
    else:
        rms = float(cfg.STT_SILENCE_RMS)
        gain = float(getattr(cfg, "MIC_GAIN_HEADSET", 1.0))
        wanted = int(getattr(cfg, "CHANNELS", 1) or 1)

    channels = wanted
    try:
        import sounddevice as sd

        info = sd.query_devices(device)  # None → default
        max_ch = int(info.get("max_input_channels") or 1)
        channels = max(1, min(wanted, max_ch))
    except Exception:  # noqa: BLE001
        channels = max(1, min(wanted, 2))

    return MicSettings(device=device, silence_rms=rms, gain=gain, input_channels=channels)


def apply_mic_gain(audio, gain: float):
    """Mix multi-channel → mono and apply gain. Returns float32 mono."""
    import numpy as np

    arr = np.asarray(audio, dtype=np.float32)
    if arr.ndim > 1 and arr.shape[-1] > 1:
        # Laptop arrays: speech is often strong on one beam — mean dilutes it.
        ch_rms = np.sqrt(np.mean(np.square(arr), axis=0))
        arr = arr[:, int(np.argmax(ch_rms))]
    arr = np.squeeze(arr)
    g = float(gain) if gain is not None else 1.0
    if g != 1.0:
        arr = arr * g
    return np.clip(arr, -1.0, 1.0).astype(np.float32)
