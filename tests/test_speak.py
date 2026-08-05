from types import SimpleNamespace

import numpy as np
import pytest

from tts import speak as speak_mod


def test_ensure_piper_ready_missing_model(monkeypatch, tmp_path):
    missing = tmp_path / "missing.onnx"
    monkeypatch.setattr(speak_mod, "PIPER_MODEL_PATH", missing)
    with pytest.raises(FileNotFoundError, match="Piper voice model"):
        speak_mod.ensure_piper_ready()


def test_synthesize_audio_empty_text():
    audio, rate = speak_mod.synthesize_audio("   ", voice=object())
    assert audio.size == 0
    assert rate > 0


def test_synthesize_audio_concatenates_chunks():
    class FakeVoice:
        def synthesize(self, text):
            assert text == "hello"
            yield SimpleNamespace(
                sample_rate=22050,
                audio_float_array=np.array([0.1, 0.2], dtype=np.float32),
            )
            yield SimpleNamespace(
                sample_rate=22050,
                audio_float_array=np.array([0.3], dtype=np.float32),
            )

    audio, rate = speak_mod.synthesize_audio("hello", voice=FakeVoice())
    assert rate == 22050
    np.testing.assert_allclose(audio, np.array([0.1, 0.2, 0.3], dtype=np.float32))


def test_speak_plays_and_waits(monkeypatch):
    calls: list[tuple] = []

    monkeypatch.setattr(
        speak_mod,
        "synthesize_audio",
        lambda text, voice=None: (np.array([0.1, 0.0], dtype=np.float32), 22050),
    )
    monkeypatch.setattr(speak_mod.sd, "play", lambda audio, samplerate: calls.append(("play", len(audio), samplerate)))
    monkeypatch.setattr(speak_mod.sd, "wait", lambda: calls.append(("wait",)))

    speak_mod.speak("hi")
    assert calls == [("play", 2, 22050), ("wait",)]
