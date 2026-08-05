# J.A.R.V.I.S — Phase 1–4 (Wake word + STT + Groq + Piper TTS)

Say **hey jarvis**, then speak your request. Local wake word + STT + TTS; Groq for replies.

## Prerequisites

- Windows x64
- Python 3.10+
- Working microphone and speakers/earphones
- Free Groq API key from https://console.groq.com/keys

## One-time setup

1. `pip install -r requirements.txt`
2. Whisper: put `whisper-cli.exe` + DLLs in `vendor/whisper/`, and `ggml-base.en.bin` in `models/`
3. Piper: `python -m piper.download_voices en_US-lessac-medium --download-dir models\piper`
4. Wake word models download automatically on first run (`openwakeword.utils.download_models`)
5. Copy `.env.example` → `.env` and set `GROQ_API_KEY`

## Run

```powershell
python main.py
```

Say **hey jarvis** (you'll hear a short chime), then speak for ~5 seconds.

Tune sensitivity with `WAKEWORD_THRESHOLD` in `config.py` (default `0.5`; lower = easier to trigger).

## Tests

```powershell
python -m pytest tests -v
```
