from __future__ import annotations

import sys

from dotenv import load_dotenv

from config import SYSTEM_PROMPT
from llm.client import chat, ensure_api_key
from stt.transcribe import ensure_whisper_ready, transcribe_microphone
from tts.speak import ensure_piper_ready, speak
from wakeword.listen import ensure_wakeword_ready, wait_for_wake_word


def main() -> int:
    load_dotenv()

    try:
        ensure_whisper_ready()
        ensure_api_key()
        ensure_piper_ready()
        ensure_wakeword_ready()
    except (FileNotFoundError, RuntimeError, OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    print("Phase 4 ready. Say 'hey jarvis' to talk (Ctrl+C to quit).")

    while True:
        try:
            print("Listening for 'hey jarvis'...")
            score = wait_for_wake_word()
            print(f"Wake word detected (score={score:.2f}).")
        except KeyboardInterrupt:
            print("\nBye.")
            return 0

        print("Recording...")
        try:
            text = transcribe_microphone()
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}", file=sys.stderr)
            continue

        if not text:
            print("You said: (no speech detected)")
            continue

        print(f"You said: {text}")
        messages.append({"role": "user", "content": text})

        print("Thinking...")
        try:
            reply = chat(messages)
        except Exception as exc:  # noqa: BLE001
            print(f"Groq error: {exc}", file=sys.stderr)
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": reply})
        print(f"Jarvis: {reply}")

        if reply:
            print("Speaking...")
            try:
                speak(reply)
            except Exception as exc:  # noqa: BLE001
                print(f"TTS error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
