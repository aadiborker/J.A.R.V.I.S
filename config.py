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
    "You are Jarvis, a warm personal voice assistant speaking out loud. "
    "Reply in short, natural spoken English: use contractions (I'm, you'll, that's), "
    "everyday wording, and light personality. Prefer 1-3 short sentences. "
    "Avoid bullet lists, markdown, URLs, and stiff formal phrasing unless asked. "
    "Do not mention that you are an AI model unless asked."
)

# Lessac tends to sound more natural than Ryan for conversational replies.
PIPER_MODEL_PATH = ROOT_DIR / "models" / "piper" / "en_US-lessac-medium.onnx"

# Piper expressiveness (higher noise ≈ less flat; length_scale > 1 ≈ slightly slower)
PIPER_LENGTH_SCALE = 1.1
PIPER_NOISE_SCALE = 0.8
PIPER_NOISE_W_SCALE = 0.9
PIPER_VOLUME = 1.0

# openWakeWord (pretrained "hey jarvis")
# Speak clearly: "hey jarvis" then pause. Lower threshold if it rarely triggers.
WAKEWORD_MODEL = "hey jarvis"
WAKEWORD_THRESHOLD = 0.4
WAKEWORD_CHUNK_SAMPLES = 1280  # 80 ms at 16 kHz
WAKEWORD_INFERENCE_FRAMEWORK = "onnx"

# After wake word: keep chatting without re-waking until goodbye or silence timeout
SESSION_SILENCE_SECONDS = 30
SESSION_END_PHRASES = (
    "goodbye",
    "good bye",
    "bye jarvis",
    "stop listening",
    "that's all",
    "thats all",
    "go to sleep",
    "never mind",
    "nevermind",
)

# ---- Console UI options ----
#
# These affect only terminal presentation (colors/status/timestamps/bell),
# not any audio, STT, LLM, or tool-calling behavior.
CONSOLE_NO_COLOR = False
CONSOLE_SHOW_TIMESTAMPS = True
CONSOLE_BELL_ON_WAKE = True
CONSOLE_BELL_ON_TIMER = True

