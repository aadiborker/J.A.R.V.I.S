from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

WHISPER_BIN = ROOT_DIR / "vendor" / "whisper" / "whisper-cli.exe"
WHISPER_MODEL = ROOT_DIR / "models" / "ggml-base.en.bin"

SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 5
INPUT_DEVICE = None  # default system input; set to an int device id to override

# Ignore near-silent clips before Whisper (RMS of float32 samples).
# Raise if real soft speech is dropped; lower if ambient noise still triggers STT.
STT_SILENCE_RMS = 0.012

# Mic: "laptop" = quieter array (more permissive silence gate); "headset" = default
MIC_PROFILE = "laptop"  # laptop | headset
STT_SILENCE_RMS_LAPTOP = 0.006

# VAD conversation capture (replaces fixed RECORD_SECONDS for session listen)
VAD_CHUNK_MS = 80
VAD_SILENCE_MS = 800
VAD_MIN_SECONDS = 0.4
VAD_MAX_SECONDS = 10.0
# Give up if no speech detected within this window (avoid 10s silent waits)
VAD_NO_SPEECH_SECONDS = 3.0
# None → use resolve_mic_settings().silence_rms as speech threshold
VAD_SPEECH_RMS = None

# Lite / idle: pause network+power monitors after quiet period (0 disables)
IDLE_SLEEP_SECONDS = 900

GROQ_MODEL = "llama-3.1-8b-instant"
SYSTEM_PROMPT = (
    "You are Jarvis, a warm personal voice assistant speaking out loud. "
    "Reply in short, natural spoken English: use contractions (I'm, you'll, that's), "
    "everyday wording, and light personality. Prefer 1-3 short sentences. "
    "Avoid bullet lists, markdown, URLs, and stiff formal phrasing unless asked. "
    "Do not mention that you are an AI model unless asked. "
    "When a timer tool returns an announcement, the user already heard the T-minus "
    "countdown aloud — give only a brief acknowledgment, don't repeat the countdown. "
    "For RAM, memory, or CPU questions, call get_system_status and use those numbers. "
    "For opening desktop apps, use open_app with an allowlisted name only."
)

# Lessac tends to sound more natural than Ryan for conversational replies.
PIPER_MODEL_PATH = ROOT_DIR / "models" / "piper" / "en_US-lessac-medium.onnx"

# Piper expressiveness (higher noise ≈ less flat; length_scale > 1 ≈ slightly slower)
PIPER_LENGTH_SCALE = 1.1
PIPER_NOISE_SCALE = 0.8
PIPER_NOISE_W_SCALE = 0.9
PIPER_VOLUME = 1.0

# Hybrid TTS: Edge neural (online) preferred; Piper is offline fallback.
# Swap EDGE_VOICE to "en-GB-ThomasNeural" if you prefer a different British male.
TTS_PREFER_EDGE = True
EDGE_VOICE = "en-GB-RyanNeural"
EDGE_TTS_TIMEOUT_SECONDS = 15

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

# Electron HUD WebSocket bridge (enabled via `python main.py --ui-ws`)
UI_WS_HOST = "127.0.0.1"
UI_WS_PORT = 8765

# WAN connectivity (lower-modules mode when offline)
NETWORK_CHECK_INTERVAL_SECONDS = 20
NETWORK_PROBE_TIMEOUT_SECONDS = 2.0
NETWORK_PROBE_HOSTS = (("1.1.1.1", 443), ("8.8.8.8", 443))
NETWORK_DEBOUNCE_CHECKS = 2

# Power / charge status (boot report + plug/unplug announcements)
POWER_CHECK_INTERVAL_SECONDS = 15
POWER_DEBOUNCE_CHECKS = 2

# After YouTube play, leave conversation mode so speaker audio isn't transcribed.
# Also pause wake-word briefly so the video soundtrack is less likely to false-trigger.
MEDIA_SESSION_END = True
MEDIA_WAKEWORD_PAUSE_SECONDS = 45

