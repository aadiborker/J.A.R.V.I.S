# J.A.R.V.I.S — Phase 1–3 (Local STT + Groq + Piper TTS)

Records a short microphone clip, transcribes with whisper.cpp, replies via Groq, speaks with Piper.

## Prerequisites

- Windows x64
- Python 3.10+
- Working microphone and speakers/earphones
- Free Groq API key from https://console.groq.com/keys

## One-time setup

1. Install deps:

```powershell
pip install -r requirements.txt
```

2. Whisper binary: download [whisper-bin-x64.zip (v1.9.1)](https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.1/whisper-bin-x64.zip), copy `whisper-cli.exe` + DLLs into `vendor/whisper/`.

3. Whisper model:

```powershell
Invoke-WebRequest -Uri "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin" -OutFile "models\ggml-base.en.bin"
```

4. Piper voice:

```powershell
python -m piper.download_voices en_US-lessac-medium --download-dir models\piper
```

Voice expressiveness is tunable in `config.py` via `PIPER_LENGTH_SCALE`, `PIPER_NOISE_SCALE`, and `PIPER_NOISE_W_SCALE`.

5. Create `.env` from `.env.example` and set `GROQ_API_KEY`.

## Run

```powershell
python main.py
```

Press Enter, speak, wait for printed `Jarvis:` and spoken reply.

## Tests

```powershell
python -m pytest tests -v
```
