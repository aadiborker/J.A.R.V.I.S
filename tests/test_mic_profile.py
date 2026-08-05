from stt.mic_profile import resolve_mic_settings


def test_laptop_profile_more_permissive(monkeypatch):
    import config as cfg

    monkeypatch.setattr(cfg, "MIC_PROFILE", "laptop")
    monkeypatch.setattr(cfg, "STT_SILENCE_RMS", 0.012)
    monkeypatch.setattr(cfg, "STT_SILENCE_RMS_LAPTOP", 0.003)
    monkeypatch.setattr(cfg, "MIC_GAIN_LAPTOP", 4.0)
    monkeypatch.setattr(cfg, "INPUT_DEVICE", None)
    s = resolve_mic_settings()
    assert s.silence_rms == 0.003
    assert s.gain == 4.0
    assert s.device is None


def test_headset_uses_default_rms(monkeypatch):
    import config as cfg

    monkeypatch.setattr(cfg, "MIC_PROFILE", "headset")
    monkeypatch.setattr(cfg, "STT_SILENCE_RMS", 0.012)
    monkeypatch.setattr(cfg, "MIC_GAIN_HEADSET", 1.0)
    monkeypatch.setattr(cfg, "INPUT_DEVICE", 1)
    s = resolve_mic_settings()
    assert s.silence_rms == 0.012
    assert s.gain == 1.0
    assert s.device == 1


def test_apply_mic_gain_picks_loudest_channel():
    import numpy as np
    from stt.mic_profile import apply_mic_gain

    stereo = np.zeros((100, 2), dtype=np.float32)
    stereo[:, 0] = 0.1
    stereo[:, 1] = 0.3
    out = apply_mic_gain(stereo, 2.0)
    assert out.ndim == 1
    # Loudest channel (0.3) * gain 2.0
    assert abs(float(out.mean()) - 0.6) < 0.01
