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
        def synthesize(self, text, syn_config=None):
            assert text == "hello"
            assert syn_config is not None
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

    monkeypatch.setattr(speak_mod, "TTS_PREFER_EDGE", False)
    monkeypatch.setattr(
        speak_mod,
        "synthesize_audio",
        lambda text, voice=None: (np.array([0.1, 0.0], dtype=np.float32), 22050),
    )
    monkeypatch.setattr(speak_mod.sd, "play", lambda audio, samplerate: calls.append(("play", len(audio), samplerate)))
    monkeypatch.setattr(speak_mod.sd, "wait", lambda: calls.append(("wait",)))

    speak_mod.speak("hi")
    assert calls == [("play", 2, 22050), ("wait",)]


def test_speak_prefers_edge_when_enabled(monkeypatch):
    edge_calls: list[str] = []
    piper_calls: list[str] = []

    monkeypatch.setattr(speak_mod, "TTS_PREFER_EDGE", True)
    monkeypatch.setattr(speak_mod, "is_online", lambda: True)
    monkeypatch.setattr(
        speak_mod,
        "_speak_edge",
        lambda text: edge_calls.append(text),
    )
    monkeypatch.setattr(
        speak_mod,
        "_speak_piper",
        lambda text, voice=None: piper_calls.append(text),
    )

    speak_mod.speak("hello sir")
    assert edge_calls == ["hello sir"]
    assert piper_calls == []


def test_speak_falls_back_to_piper_when_edge_fails(monkeypatch):
    piper_calls: list[str] = []

    monkeypatch.setattr(speak_mod, "TTS_PREFER_EDGE", True)
    monkeypatch.setattr(speak_mod, "is_online", lambda: True)
    monkeypatch.setattr(
        speak_mod,
        "_speak_edge",
        lambda text: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    monkeypatch.setattr(
        speak_mod,
        "_speak_piper",
        lambda text, voice=None: piper_calls.append(text),
    )

    speak_mod.speak("fallback please")
    assert piper_calls == ["fallback please"]


def test_speak_skips_edge_when_offline(monkeypatch):
    edge_calls: list[str] = []
    piper_calls: list[str] = []

    monkeypatch.setattr(speak_mod, "TTS_PREFER_EDGE", True)
    monkeypatch.setattr(speak_mod, "is_online", lambda: False)
    monkeypatch.setattr(
        speak_mod, "_speak_edge", lambda text: edge_calls.append(text)
    )
    monkeypatch.setattr(
        speak_mod,
        "_speak_piper",
        lambda text, voice=None: piper_calls.append(text),
    )

    speak_mod.speak("offline line")
    assert edge_calls == []
    assert piper_calls == ["offline line"]


def test_speak_empty_text_is_noop(monkeypatch):
    called = {"edge": False, "piper": False}
    monkeypatch.setattr(speak_mod, "TTS_PREFER_EDGE", True)
    monkeypatch.setattr(speak_mod, "is_online", lambda: True)
    monkeypatch.setattr(speak_mod, "_speak_edge", lambda text: called.__setitem__("edge", True))
    monkeypatch.setattr(speak_mod, "_speak_piper", lambda text, voice=None: called.__setitem__("piper", True))

    speak_mod.speak("   ")
    assert called == {"edge": False, "piper": False}
