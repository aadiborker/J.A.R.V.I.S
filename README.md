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
4. Wake word models download automatically on first run
5. Copy `.env.example` → `.env` and set `GROQ_API_KEY`

## Easy launch (no typing `python main.py`)

### HUD (Electron UI)

```bat
scripts\start_jarvis_ui.bat
```

First run installs Electron (`npm install` in `desktop/`). The HUD starts Python with `--ui-ws` and shows status + transcript animations.

Terminal-only (no HUD): `python main.py` or `scripts\start_jarvis.bat`.

### Desktop shortcut

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\create_desktop_shortcut.ps1"
```

Then double-click **J.A.R.V.I.S** on your Desktop.

### Start on Windows login (optional)

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\install_autostart.ps1"
```

Disable later:

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\uninstall_autostart.ps1"
```

HUD mode: closing the window hides to the **system tray** (right-click tray → Quit to fully stop). A Python console may also appear while the backend runs.

Terminal-only: close that console or Ctrl+C to stop.

## Manual run

```powershell
python main.py
```

Or:

```powershell
.\scripts\start_jarvis.bat
```

## Usage

1. Say **hey jarvis** (chime)
2. Keep talking turn-by-turn without repeating the wake word
3. Say **goodbye** / **stop listening**, or stay quiet ~30s, to end the session

Tune `WAKEWORD_THRESHOLD` and `SESSION_SILENCE_SECONDS` in `config.py`.

## Tests

```powershell
python -m pytest tests -v
```
