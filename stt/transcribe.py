from __future__ import annotations

import re
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
from stt.mic_profile import resolve_mic_settings


_NOISE_PREFIXES = (
    "whisper_",
    "system_info",
    "main:",
    "ggml_",
    "operator():",
)

# Whisper often invents these on silence / hiss (classic base.en hallucinations).
_SPURIOUS_TRANSCRIPTS = frozenset(
    {
        "you",
        "thank you",
        "thanks",
        "thanks for watching",
        "thank you for watching",
        "thanks for watching.",
        "subtitle",
        "subtitles",
        "subtitles by",
        "music",
        "applause",
        "blank audio",
        "[blank_audio]",
        "silence",
        "uh",
        "um",
        "ah",
        "hmm",
        "mm",
        "mhm",
        "the",
        "a",
        "i",
        ".",
        "...",
    }
)

# Only treat as silence-hallucinations when the clip is quiet. Loud "goodbye" is
# usually real (or TTS echo — settle time handles that); dropping loud ones made
# Jarvis look like it wasn't listening.
_SOFT_SPURIOUS_TRANSCRIPTS = frozenset(
    {
        "bye",
        "goodbye",
        "good bye",
        "good night",
        "goodnight",
    }
)
_SOFT_SPURIOUS_MAX_RMS = 0.02

_WHISPER_PROMPT = (
    "Voice commands to Jarvis: system status, what time is it, "
    "open notepad, set a timer, remember my name."
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


def normalize_transcript_key(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"^[\s\"'`]+|[\s\"'`.!?…,;:]+$", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def is_spurious_transcript(text: str, *, energy: float | None = None) -> bool:
    """True for empty / known Whisper silence hallucinations."""
    key = normalize_transcript_key(text)
    if not key:
        return True
    if key in _SPURIOUS_TRANSCRIPTS:
        return True
    if key in _SOFT_SPURIOUS_TRANSCRIPTS:
        # Quiet clip → likely hallucination; louder → keep (session can end on goodbye).
        if energy is None or float(energy) < _SOFT_SPURIOUS_MAX_RMS:
            return True
    # Very short single tokens that aren't useful commands
    if len(key) <= 2 and key.isalpha():
        return True
    return False


def clean_transcript(text: str, *, energy: float | None = None) -> str:
    if is_spurious_transcript(text, energy=energy):
        return ""
    return (text or "").strip()


def audio_rms(audio: np.ndarray) -> float:
    arr = np.asarray(audio, dtype=np.float32).reshape(-1)
    if arr.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(arr))))


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
            "Download ggml-small.en.bin from "
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin "
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


def record_audio(seconds: float | None = None) -> tuple[Path, float]:
    """Record mic audio for a fixed duration. Returns (wav_path, rms_energy)."""
    from stt.mic_profile import apply_mic_gain

    settings = resolve_mic_settings()
    duration = float(RECORD_SECONDS if seconds is None else seconds)
    frames = int(duration * SAMPLE_RATE)
    channels = max(1, int(settings.input_channels))
    device = settings.device if settings.device is not None else INPUT_DEVICE

    def _capture_once() -> tuple[np.ndarray, float]:
        # Ensure no leftover InputStream (wake word) owns the device.
        try:
            sd.stop()
        except Exception:  # noqa: BLE001
            pass
        sd.sleep(80)
        audio = sd.rec(
            frames,
            samplerate=SAMPLE_RATE,
            channels=channels,
            dtype="float32",
            device=device,
        )
        sd.wait()
        audio = apply_mic_gain(audio, settings.gain)
        return audio, audio_rms(audio)

    audio, energy = _capture_once()
    # Windows/Intel array sometimes returns a dead/near-dead buffer after wake/TTS.
    if energy < max(1e-4, float(settings.silence_rms) * 0.25):
        print("[MIC] weak/dead buffer — retrying capture once...", flush=True)
        sd.sleep(300)
        audio, energy = _capture_once()

    print(
        f"[MIC] recorded {duration:.1f}s rms={energy:.4f} "
        f"gate={settings.silence_rms:.4f} device={device} ch={channels} gain={settings.gain}",
        flush=True,
    )
    tmp = tempfile.NamedTemporaryFile(prefix="jarvis_", suffix=".wav", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()
    write_wav(tmp_path, audio, sample_rate=SAMPLE_RATE)
    return tmp_path, energy


def warmup_whisper() -> None:
    """One tiny transcription to warm disk/OS caches for whisper-cli."""
    ensure_whisper_ready()
    tmp = tempfile.NamedTemporaryFile(prefix="jarvis_warm_", suffix=".wav", delete=False)
    path = Path(tmp.name)
    tmp.close()
    try:
        # ~0.3s near-silence
        audio = np.zeros(int(SAMPLE_RATE * 0.3), dtype=np.float32)
        write_wav(path, audio, sample_rate=SAMPLE_RATE)
        transcribe(path)
    except Exception:  # noqa: BLE001
        # Boot must not fail on warm-up
        pass
    finally:
        path.unlink(missing_ok=True)


def transcribe(wav_path: Path | str, *, energy: float | None = None) -> str:
    ensure_whisper_ready()
    wav_path = Path(wav_path).resolve()
    if not wav_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {wav_path}")

    cmd = [
        str(WHISPER_BIN),
        "-m",
        str(WHISPER_MODEL.resolve()),
        "-f",
        str(wav_path),
        "-nt",
        "-np",
        "-l",
        "en",
        "-tp",
        "0",
        "-nf",
        "-sns",
        "-nth",
        "0.75",
        "--prompt",
        _WHISPER_PROMPT,
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
    raw = parse_whisper_stdout(result.stdout)
    cleaned = clean_transcript(raw, energy=energy)
    if raw and not cleaned:
        print(f"[MIC] dropped spurious transcript: {raw!r}", flush=True)
    return cleaned


def transcribe_microphone(
    seconds: float | None = None,
    *,
    on_recording_done=None,
) -> str:
    from config import MIC_SETTLE_MS, STT_LISTEN_SECONDS, STT_USE_VAD

    settings = resolve_mic_settings()
    # Give Windows time to unduck the mic after TTS / wake chime.
    settle = max(0, int(MIC_SETTLE_MS))
    if settle:
        sd.sleep(settle)

    if seconds is not None:
        wav_path, energy = record_audio(seconds=seconds)
        if on_recording_done is not None:
            on_recording_done()
    elif STT_USE_VAD:
        from stt.vad_record import record_until_silence

        wav_path, energy = record_until_silence(on_recording_done=on_recording_done)
    else:
        wav_path, energy = record_audio(seconds=float(STT_LISTEN_SECONDS))
        if on_recording_done is not None:
            on_recording_done()
    try:
        # Soft gate: still try Whisper if we have any real energy (arrays vary).
        gate = float(settings.silence_rms) * 0.5
        if energy < gate:
            print(f"[MIC] below energy gate ({energy:.4f} < {gate:.4f})", flush=True)
            return ""
        return transcribe(wav_path, energy=energy)
    finally:
        wav_path.unlink(missing_ok=True)
