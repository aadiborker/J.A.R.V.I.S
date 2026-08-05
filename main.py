from __future__ import annotations

import sys
import time
import threading

from dotenv import load_dotenv

from config import (
    RECORD_SECONDS,
    SESSION_END_PHRASES,
    SESSION_SILENCE_SECONDS,
    SYSTEM_PROMPT,
)
from llm.client import ensure_api_key
from llm.tool_loop import chat_with_tools
from stt.transcribe import ensure_whisper_ready, transcribe_microphone
from tts.speak import ensure_piper_ready, speak
from wakeword.listen import ensure_wakeword_ready, wait_for_wake_word
from tools.simple_commands import try_handle_simple
from tools.time_tools import get_time
from tools.timer_tools import TimerManager


def is_session_end(text: str) -> bool:
    lowered = text.lower().strip()
    return any(phrase in lowered for phrase in SESSION_END_PHRASES)


def handle_turn(
    messages: list[dict[str, str]],
    text: str,
    *,
    timer_manager: TimerManager,
) -> bool:
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

    # Regex/local fast-path for simple actions (saves LLM round-trips).
    simple_reply = try_handle_simple(text, timer_manager)
    if simple_reply is not None:
        messages.append({"role": "assistant", "content": simple_reply})
        print(f"Jarvis: {simple_reply}")
        if simple_reply:
            print("Speaking...")
            try:
                speak(simple_reply)
            except Exception as exc:  # noqa: BLE001
                print(f"TTS error: {exc}", file=sys.stderr)
        return True

    print("Thinking...")
    try:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_time",
                    "description": "Get current local time",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "set_timer",
                    "description": "Set a timer and remind the user when it ends",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "seconds": {"type": "integer", "description": "Timer duration in seconds"},
                            "label": {"type": "string", "description": "Optional label for the timer"},
                        },
                        "required": ["seconds"],
                    },
                },
            },
        ]

        tool_registry = {
            "get_time": lambda: get_time(),
            "set_timer": timer_manager.set_timer,
        }

        reply = chat_with_tools(messages, tools, tool_registry)
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


def run_conversation_session(
    messages: list[dict[str, str]],
    *,
    timer_manager: TimerManager,
) -> None:
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
        keep_going = handle_turn(messages, text, timer_manager=timer_manager)
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

    wakeword_pause_event = threading.Event()
    timer_manager = TimerManager(
        speak_fn=speak,
        wakeword_pause_event=wakeword_pause_event,
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    print("Ready. Say 'hey jarvis' to start talking (Ctrl+C to quit).")

    while True:
        try:
            print("Listening for 'hey jarvis'...")
            score = wait_for_wake_word(wakeword_pause_event=wakeword_pause_event)
            print(f"Wake word detected (score={score:.2f}).")
        except KeyboardInterrupt:
            print("\nBye.")
            return 0

        try:
            run_conversation_session(messages, timer_manager=timer_manager)
        except KeyboardInterrupt:
            print("\nBye.")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
