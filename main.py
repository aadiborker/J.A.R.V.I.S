from __future__ import annotations

import sys

from stt.transcribe import ensure_whisper_ready, transcribe_microphone


def main() -> int:
    try:
        ensure_whisper_ready()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    print("Phase 1 STT ready.")
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
        except Exception as exc:  # noqa: BLE001 - surface mic/whisper errors to user
            print(f"Error: {exc}", file=sys.stderr)
            continue

        if text:
            print(f"You said: {text}")
        else:
            print("You said: (no speech detected)")

        print("Press Enter to record again, or Ctrl+C to quit.")


if __name__ == "__main__":
    raise SystemExit(main())
