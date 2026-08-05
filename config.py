from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

WHISPER_BIN = ROOT_DIR / "vendor" / "whisper" / "whisper-cli.exe"
WHISPER_MODEL = ROOT_DIR / "models" / "ggml-base.en.bin"

SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 5
INPUT_DEVICE = None  # default system input; set to an int device id to override

GROQ_MODEL = "llama-3.1-8b-instant"
SYSTEM_PROMPT = (
    "You are Jarvis, a helpful personal voice assistant. "
    "Keep answers concise and conversational so they work well when spoken aloud later. "
    "Do not mention that you are an AI model unless asked."
)
