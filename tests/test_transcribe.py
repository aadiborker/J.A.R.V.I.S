from pathlib import Path

import numpy as np
import pytest

from stt.transcribe import (
    clean_transcript,
    ensure_whisper_ready,
    is_spurious_transcript,
    parse_whisper_stdout,
    write_wav,
)


def test_parse_whisper_stdout_strips_noise():
    raw = """
whisper_init_from_file_with_params_no_state: loading model
system_info: n_threads = 4
hello jarvis what time is it
"""
    assert parse_whisper_stdout(raw) == "hello jarvis what time is it"


def test_parse_whisper_stdout_empty():
    assert parse_whisper_stdout("whisper_init...\nsystem_info: x\n") == ""


def test_spurious_you_and_thank_you():
    assert is_spurious_transcript("you") is True
    assert is_spurious_transcript("You.") is True
    assert is_spurious_transcript("Thank you") is True
    assert is_spurious_transcript("  YOU  ") is True
    assert clean_transcript("you") == ""
    assert clean_transcript("what time is it") == "what time is it"
    assert is_spurious_transcript("open notepad") is False


def test_ensure_whisper_ready_missing_bin(monkeypatch, tmp_path):
    missing = tmp_path / "nope.exe"
    model = tmp_path / "model.bin"
    model.write_bytes(b"x")
    monkeypatch.setattr("stt.transcribe.WHISPER_BIN", missing)
    monkeypatch.setattr("stt.transcribe.WHISPER_MODEL", model)
    with pytest.raises(FileNotFoundError, match="whisper-cli"):
        ensure_whisper_ready()


def test_ensure_whisper_ready_missing_model(monkeypatch, tmp_path):
    binary = tmp_path / "whisper-cli.exe"
    binary.write_bytes(b"x")
    missing = tmp_path / "missing.bin"
    monkeypatch.setattr("stt.transcribe.WHISPER_BIN", binary)
    monkeypatch.setattr("stt.transcribe.WHISPER_MODEL", missing)
    with pytest.raises(FileNotFoundError, match="model"):
        ensure_whisper_ready()


def test_write_wav_creates_file(tmp_path):
    path = tmp_path / "sample.wav"
    audio = np.zeros(16000, dtype=np.float32)  # 1 second silence
    write_wav(path, audio, sample_rate=16000)
    assert path.is_file()
    assert path.stat().st_size > 44  # header + data
