# J.A.R.V.I.S — Phase 1–2 (Local STT + Groq Chat)

Records a short microphone clip, transcribes with whisper.cpp (`base.en`), sends text to Groq, prints the reply.

## Prerequisites

- Windows x64
- Python 3.10+
- Working microphone
- Free Groq API key from https://console.groq.com/keys

## One-time setup

1. Install deps:

```powershell
pip install -r requirements.txt
```

2. Whisper binary: download [whisper-bin-x64.zip (v1.9.1)](https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.1/whisper-bin-x64.zip), copy `whisper-cli.exe` + DLLs into `vendor/whisper/`.

3. Model:

```powershell
Invoke-WebRequest -Uri "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin" -OutFile "models\ggml-base.en.bin"
```

4. Create `.env` in the project root (copy from `.env.example`):

```powershell
Copy-Item .env.example .env
# Then edit .env and set GROQ_API_KEY to your real key
```

## Run

```powershell
python main.py
```

Press Enter, speak, wait for `You said:` and `Jarvis:`.

## Tests

```powershell
python -m pytest tests -v
```
