from __future__ import annotations

import sys
import time

from dotenv import load_dotenv

from config import (
    RECORD_SECONDS,
    SESSION_END_PHRASES,
    SESSION_SILENCE_SECONDS,
    SYSTEM_PROMPT,
)
from llm.client import chat, ensure_api_key
from stt.transcribe import ensure_whisper_ready, transcribe_microphone
from tts.speak import ensure_piper_ready, speak
from wakeword.listen import ensure_wakeword_ready, wait_for_wake_word


def is_session_end(text: str) -> bool:
    lowered = text.lower().strip()
    return any(phrase in lowered for phrase in SESSION_END_PHRASES)


def handle_turn(messages: list[dict[str, str]], text: str) -> bool:
    """
    Run LLM + TTS for one user utterance.
    Returns False if the session should end (goodbye phrase).
    """
    if is_session_end(text):
        print(f"You said: {text}")
        farewell = "Alright, I'll be here when you need me."
        print(f"Jarvis: {farewell}")
        try:
            speak(farewell)
        except Exception as exc:  # noqa: BLE001
            print(f"TTS error: {exc}", file=sys.stderr)
        return False

    print(f"You said: {text}")
    messages.append({"role": "user", "content": text})

    print("Thinking...")
    try:
        reply = chat(messages)
    except Exception as exc:  # noqa: BLE001
        print(f"Groq error: {exc}", file=sys.stderr)
        messages.pop()
        return True

    messages.append({"role": "assistant", "content": reply})
    print(f"Jarvis: {reply}")

    if reply:
        print("Speaking...")
        try:
            speak(reply)
        except Exception as exc:  # noqa: BLE001
            print(f"TTS error: {exc}", file=sys.stderr)
    return True


def run_conversation_session(messages: list[dict[str, str]]) -> None:
    """Multi-turn chat without wake word until goodbye or silence timeout."""
    print(
        f"Conversation open — speak normally. "
        f"Say goodbye, or stay quiet ~{SESSION_SILENCE_SECONDS}s to end."
    )
    silence_started: float | None = None

    while True:
        print("Listening for your next request...")
        try:
            text = transcribe_microphone()
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}", file=sys.stderr)
            continue

        if not text:
            print("You said: (no speech detected)")
            now = time.monotonic()
            if silence_started is None:
                silence_started = now
            elapsed = now - silence_started + float(RECORD_SECONDS)
            print(f"  silence ~{elapsed:.0f}s / {SESSION_SILENCE_SECONDS}s")
            if elapsed >= SESSION_SILENCE_SECONDS:
                print("Silence timeout — back to wake word.")
                try:
                    speak("I'll go quiet for now. Say hey jarvis when you need me.")
                except Exception as exc:  # noqa: BLE001
                    print(f"TTS error: {exc}", file=sys.stderr)
                return
            continue

        silence_started = None
        keep_going = handle_turn(messages, text)
        if not keep_going:
            print("Session ended — back to wake word.")
            return


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

    print("Ready. Say 'hey jarvis' to start talking (Ctrl+C to quit).")

    while True:
        try:
            print("Listening for 'hey jarvis'...")
            score = wait_for_wake_word()
            print(f"Wake word detected (score={score:.2f}).")
        except KeyboardInterrupt:
            print("\nBye.")
            return 0

        try:
            run_conversation_session(messages)
        except KeyboardInterrupt:
            print("\nBye.")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
