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
