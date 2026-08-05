# J.A.R.V.I.S — Phase 1 (Local STT)

Records a short microphone clip, transcribes with whisper.cpp (`base.en`), prints the text.

## Prerequisites

- Windows x64
- Python 3.10+
- Working default microphone

## One-time setup

1. Create a virtualenv (optional) and install deps:

```powershell
pip install -r requirements.txt
```

2. Download [whisper-bin-x64.zip (v1.9.1)](https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.1/whisper-bin-x64.zip), extract, and copy `whisper-cli.exe` plus its DLLs into `vendor/whisper/`.

3. Download the model into `models/`:

```powershell
Invoke-WebRequest -Uri "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin" -OutFile "models\ggml-base.en.bin"
```

## Run

```powershell
python main.py
```

Press Enter, speak for ~5 seconds, wait for `You said: ...`.

## Tests

```powershell
python -m pytest tests/test_transcribe.py -v
```
