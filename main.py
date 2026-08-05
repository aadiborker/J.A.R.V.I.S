from __future__ import annotations

import sys

from dotenv import load_dotenv

from config import SYSTEM_PROMPT
from llm.client import chat, ensure_api_key
from stt.transcribe import ensure_whisper_ready, transcribe_microphone


def main() -> int:
    load_dotenv()

    try:
        ensure_whisper_ready()
        ensure_api_key()
    except (FileNotFoundError, RuntimeError) as exc:
        print(exc, file=sys.stderr)
        return 1

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    print("Phase 2 STT + Groq ready.")
    print("Press Enter to record, or Ctrl+C to quit.")

    while True:
        try:
            input()
        except (EOFError, KeyboardInterrupt):
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
            print("Press Enter to record again, or Ctrl+C to quit.")
            continue

        print(f"You said: {text}")
        messages.append({"role": "user", "content": text})

        print("Thinking...")
        try:
            reply = chat(messages)
        except Exception as exc:  # noqa: BLE001
            print(f"Groq error: {exc}", file=sys.stderr)
            messages.pop()  # remove failed user turn so history stays consistent
            print("Press Enter to record again, or Ctrl+C to quit.")
            continue

        messages.append({"role": "assistant", "content": reply})
        print(f"Jarvis: {reply}")
        print("Press Enter to record again, or Ctrl+C to quit.")


if __name__ == "__main__":
    raise SystemExit(main())
