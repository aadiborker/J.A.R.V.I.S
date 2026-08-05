from __future__ import annotations

from pathlib import Path

from config import WHISPER_BIN, WHISPER_MODEL

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
            # timestamped lines like [00:00:00.000 --> 00:00:05.000]
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
