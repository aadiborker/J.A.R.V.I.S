from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

from config import (
    CHANNELS,
    INPUT_DEVICE,
    RECORD_SECONDS,
    SAMPLE_RATE,
    WHISPER_BIN,
    WHISPER_MODEL,
)

_NOISE_PREFIXES = (
    "whisper_",
    "system_info",
    "main:",
    "ggml_",
    "operator():",
)


def parse_whisper_stdout(stdout: str) -> str:
    lines: list[str] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if any(lower.startswith(prefix) for prefix in _NOISE_PREFIXES):
            continue
        if lower.startswith("[") and "]" in line[:32]:
            after = line.split("]", 1)[-1].strip()
            if after:
                lines.append(after)
            continue
        lines.append(line)
    return " ".join(lines).strip()


def ensure_whisper_ready() -> None:
    if not Path(WHISPER_BIN).is_file():
        raise FileNotFoundError(
            f"whisper-cli not found at {WHISPER_BIN}. "
            "Download whisper-bin-x64.zip from "
            "https://github.com/ggml-org/whisper.cpp/releases/tag/v1.9.1 "
            "and place whisper-cli.exe (and its DLLs) in vendor/whisper/."
        )
    if not Path(WHISPER_MODEL).is_file():
        raise FileNotFoundError(
            f"Whisper model not found at {WHISPER_MODEL}. "
            "Download ggml-base.en.bin from "
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin "
            "into the models/ folder."
        )


def write_wav(path: Path | str, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(audio, -1.0, 1.0)
    pcm_i16 = (pcm * 32767.0).astype(np.int16)
    if pcm_i16.ndim > 1:
        pcm_i16 = pcm_i16.reshape(-1, pcm_i16.shape[-1])
    wavfile.write(str(path), sample_rate, pcm_i16)


def record_audio(seconds: float | None = None) -> Path:
    duration = float(RECORD_SECONDS if seconds is None else seconds)
    frames = int(duration * SAMPLE_RATE)
    audio = sd.rec(
        frames,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        device=INPUT_DEVICE,
    )
    sd.wait()
    audio = np.squeeze(audio)
    tmp = tempfile.NamedTemporaryFile(prefix="jarvis_", suffix=".wav", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()
    write_wav(tmp_path, audio, sample_rate=SAMPLE_RATE)
    return tmp_path


def transcribe(wav_path: Path | str) -> str:
    ensure_whisper_ready()
    wav_path = Path(wav_path)
    if not wav_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {wav_path}")

    cmd = [
        str(WHISPER_BIN),
        "-m",
        str(WHISPER_MODEL),
        "-f",
        str(wav_path),
        "-nt",
        "-l",
        "en",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(WHISPER_BIN.parent),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"whisper-cli failed ({result.returncode}):\n{result.stderr.strip()}"
        )
    return parse_whisper_stdout(result.stdout)


def transcribe_microphone(seconds: float | None = None) -> str:
    wav_path = record_audio(seconds=seconds)
    try:
        return transcribe(wav_path)
    finally:
        wav_path.unlink(missing_ok=True)
