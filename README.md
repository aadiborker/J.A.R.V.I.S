# J.A.R.V.I.S

Local Windows voice assistant: say **hey jarvis**, speak a request, get a spoken reply.

- **Local:** wake word (openWakeWord), STT (whisper.cpp), TTS (Edge neural online / Piper offline)
- **Cloud:** Groq LLM (free tier)
- **Tools:** time/timers, browser/YouTube, allowlisted apps, system status (RAM/CPU/volume/lock/screenshot), simple memory

## Prerequisites

- Windows x64
- Python 3.10+
- Microphone + speakers (earphones/headset mic recommended)
- Free Groq API key: https://console.groq.com/keys
- Optional for HUD: Node.js 18+ and npm

Large binaries (`vendor/whisper`, `models/`) are **not** in git — download them after clone (steps below).

## Clone and setup

```powershell
git clone https://github.com/aadiborker/J.A.R.V.I.S.git
cd J.A.R.V.I.S
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 1. Environment

```powershell
copy .env.example .env
```

Edit `.env` and set:

```
GROQ_API_KEY=gsk_your_key_here
```

### 2. Whisper STT (required)

1. Download [whisper.cpp Windows x64 release](https://github.com/ggml-org/whisper.cpp/releases) (`whisper-bin-x64.zip`).
2. Extract so you have:
   - `vendor/whisper/whisper-cli.exe`
   - matching DLLs in the same folder
3. Download the English model into `models/`:

```powershell
mkdir models -Force
curl.exe -L -o models\ggml-small.en.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin"
```

(`ggml-base.en.bin` also works if you point `WHISPER_MODEL` in `config.py` at it.)

### 3. Piper TTS fallback (required)

```powershell
python -m piper.download_voices en_US-lessac-medium --download-dir models\piper
```

### 4. Wake word

No manual download — openWakeWord fetches pretrained **hey jarvis** on first run (needs network once).

### 5. Microphone

Earphones / USB headset generally work best. Built-in laptop arrays are quieter and less reliable.

```powershell
python -c "import sounddevice as sd; print(sd.query_devices())"
```

In `config.py`:

- `MIC_PROFILE = "headset"` — earphones / external mic (default)
- `MIC_PROFILE = "laptop"` — built-in array (higher gain)
- `INPUT_DEVICE = None` — Windows default mic (recommended after clone)
- Or set `INPUT_DEVICE = <id>` to force a device from the list above

Optional mic check:

```powershell
python scripts\test_mic.py
```

### 6. Optional Electron HUD

```powershell
cd desktop
npm install
cd ..
```

## Run

**Lite (terminal only — recommended):**

```powershell
.\scripts\start_jarvis.bat
```

or:

```powershell
python main.py
```

**With HUD:**

```powershell
.\scripts\start_jarvis_ui.bat
```

Stop with `Ctrl+C` in the console (HUD: tray → Quit).

There is **no** Windows login autostart in this repo. Launch only when you want it.

## Usage

1. Say **hey jarvis** clearly, then pause
2. After the cue, speak your request
3. Keep talking turn-by-turn without the wake word
4. Say **goodbye** / **stop listening**, or stay quiet ~30s, to return to wake-word mode

Useful `config.py` knobs:

| Setting | Purpose |
|---------|---------|
| `WAKEWORD_THRESHOLD` | Lower if wake misses; raise if false wakes |
| `STT_LISTEN_SECONDS` | How long each turn records |
| `MIC_GAIN_LAPTOP` / `MIC_GAIN_HEADSET` | Amplify quiet mics |
| `EDGE_VOICE` | Online TTS voice (default British male) |

## Tests

```powershell
python -m pytest tests -v
```

## Project layout (high level)

```
main.py           # entrypoint
config.py         # all tunables
stt/              # mic + Whisper
wakeword/         # hey jarvis
tts/              # Edge + Piper
llm/              # Groq
tools/            # timers, browser, apps, system, memory
desktop/          # optional Electron HUD
scripts/          # start_jarvis.bat, start_jarvis_ui.bat, test_mic.py
```

## License / notes

Personal project. Keep `.env` private — never commit API keys.
