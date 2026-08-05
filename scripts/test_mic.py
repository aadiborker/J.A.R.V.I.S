"""Quick mic level check — speak for ~2 seconds, see RMS and pick a device.

Usage:
  python scripts/test_mic.py
  python scripts/test_mic.py 1
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import sounddevice as sd

from config import SAMPLE_RATE
from stt.mic_profile import apply_mic_gain, resolve_mic_settings
from stt.transcribe import audio_rms


def main() -> int:
    print("Input devices:")
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] <= 0:
            continue
        mark = "  ← default" if i == sd.default.device[0] else ""
        print(f"  {i:3d}  ch={d['max_input_channels']}  {d['name']}{mark}")

    settings = resolve_mic_settings()
    device = int(sys.argv[1]) if len(sys.argv) > 1 else settings.device
    info = sd.query_devices(device)
    max_ch = int(info.get("max_input_channels") or 1)
    channels = max(1, min(max_ch, max(1, int(settings.input_channels))))
    print(f"\nRecording 2.0s on device={device!r} ({info.get('name')}) channels={channels} gain={settings.gain}…")
    print("Speak clearly now.")
    try:
        audio = sd.rec(
            int(2.0 * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=channels,
            dtype="float32",
            device=device,
        )
        sd.wait()
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to open device {device}: {exc}")
        return 1
    raw = np.asarray(audio, dtype=np.float32)
    raw_rms = float(np.sqrt(np.mean(np.square(np.squeeze(raw)))))
    boosted = apply_mic_gain(raw, settings.gain)
    boosted_rms = audio_rms(boosted)
    print(f"raw RMS     = {raw_rms:.4f}")
    print(f"boosted RMS = {boosted_rms:.4f}  (silence gate ≈ {settings.silence_rms})")
    if boosted_rms < settings.silence_rms:
        print("→ Too quiet for Jarvis. Raise MIC_GAIN_LAPTOP or pick another INPUT_DEVICE.")
    else:
        print("→ Level looks usable. Keep INPUT_DEVICE =", device)
    print(f"\nIn config.py:  INPUT_DEVICE = {device}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
