from stt.mic_profile import resolve_mic_settings


def test_laptop_profile_more_permissive(monkeypatch):
    import config as cfg

    monkeypatch.setattr(cfg, "MIC_PROFILE", "laptop")
    monkeypatch.setattr(cfg, "STT_SILENCE_RMS", 0.012)
    monkeypatch.setattr(cfg, "STT_SILENCE_RMS_LAPTOP", 0.006)
    monkeypatch.setattr(cfg, "INPUT_DEVICE", None)
    s = resolve_mic_settings()
    assert s.silence_rms == 0.006
    assert s.device is None


def test_headset_uses_default_rms(monkeypatch):
    import config as cfg

    monkeypatch.setattr(cfg, "MIC_PROFILE", "headset")
    monkeypatch.setattr(cfg, "STT_SILENCE_RMS", 0.012)
    monkeypatch.setattr(cfg, "INPUT_DEVICE", 1)
    s = resolve_mic_settings()
    assert s.silence_rms == 0.012
    assert s.device == 1
