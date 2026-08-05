from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

WHISPER_BIN = ROOT_DIR / "vendor" / "whisper" / "whisper-cli.exe"
WHISPER_MODEL = ROOT_DIR / "models" / "ggml-base.en.bin"

SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 5
INPUT_DEVICE = None  # default system input; set to an int device id to override
