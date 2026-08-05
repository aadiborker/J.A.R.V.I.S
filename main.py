from __future__ import annotations

import sys
import datetime
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
from ui.console_ui import (
    Style,
    THEME,
    clear_status,
    log_error,
    log_system,
    log_thinking,
    log_user,
    maybe_bell,
    set_status,
)


def type_out(text: str, *, delay_s: float = 0.015) -> None:
    """Console-friendly type-out effect (keeps console readable, not slow)."""
    # Color the typed output so replies look like "Jarvis" instead of plain text.
    if THEME.jarvis:
        print(THEME.jarvis, end="", flush=True)
    for ch in text:
        print(ch, end="", flush=True)
        # Keep the delay small; if speech is long, this still should feel quick.
        time.sleep(delay_s)
    if THEME.jarvis:
        print(Style.RESET_ALL, end="", flush=True)
    print()


def jarvis_typed(text: str) -> None:
    """Print the Jarvis prefix and run the type-out effect consistently."""
    if THEME.jarvis:
        print(f"{THEME.jarvis}Jarvis:{Style.RESET_ALL} ", end="", flush=True)
    else:
        print("Jarvis: ", end="", flush=True)
    type_out(text)


def make_jarvis_greeting(
    *, now_ist: datetime.datetime | None = None
) -> tuple[str, str]:
    """Create a JARVIS-style greeting in IST.

    Returns: (print_text, speech_text)
    """
    # Avoid zoneinfo tz database dependency (tzdata) by using a fixed IST offset.
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30), name="IST")
    now = now_ist or datetime.datetime.now(datetime.timezone.utc).astimezone(ist_tz)

    hour = now.hour
    if 5 <= hour < 12:
        part = "Morning"
    elif 12 <= hour < 17:
        part = "Afternoon"
    elif 17 <= hour < 22:
        part = "Evening"
    else:
        part = "Night"

    date_str = now.strftime("%d-%m-%Y")
    time_str = now.strftime("%I:%M %p").lstrip("0")

    dd, mm, yyyy = date_str.split("-")
    # Speak the date with spaces instead of hyphens to avoid TTS pause artifacts.
    speech_date = f"{dd} {mm} {yyyy}"

    print_text = (
        f"Good {part} Sir. Today is {date_str}. Time is {time_str}."
    )
    speech_text = (
        f"Good {part} Sir. Today is {speech_date}. Time is {time_str}."
    )
    return print_text, speech_text


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
        log_user(text)
        farewell = "Alright, I'll be here when you need me."
        jarvis_typed(farewell)
        try:
            speak(farewell)
        except Exception as exc:  # noqa: BLE001
            log_error(f"TTS error: {exc}")
        return False

    log_user(text)
    messages.append({"role": "user", "content": text})

    # Regex/local fast-path for simple actions (saves LLM round-trips).
    simple_reply = try_handle_simple(text, timer_manager)
    if simple_reply is not None:
        messages.append({"role": "assistant", "content": simple_reply})
        jarvis_typed(simple_reply)
        if simple_reply:
            try:
                set_status("[SPEAK] Speaking...")
                speak(simple_reply)
            except Exception as exc:  # noqa: BLE001
                log_error(f"TTS error: {exc}")
            finally:
                clear_status()
        return True

    set_status("[THINK] Thinking...")
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
        clear_status()
        log_error(f"Groq error: {exc}")
        messages.pop()
        return True

    messages.append({"role": "assistant", "content": reply})
    clear_status()
    jarvis_typed(reply)

    if reply:
        try:
            set_status("[SPEAK] Speaking...")
            speak(reply)
        except Exception as exc:  # noqa: BLE001
            log_error(f"TTS error: {exc}")
        finally:
            clear_status()
    return True


def run_conversation_session(
    messages: list[dict[str, str]],
    *,
    timer_manager: TimerManager,
) -> None:
    """Multi-turn chat without wake word until goodbye or silence timeout."""
    log_system(
        f"Conversation open — speak normally. Say goodbye, or stay quiet ~{SESSION_SILENCE_SECONDS}s to end."
    )
    silence_started: float | None = None

    while True:
        set_status("[SESSION] Listening for your next request...")
        try:
            text = transcribe_microphone()
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001
            clear_status()
            log_error(f"Error: {exc}")
            continue

        clear_status()
        if not text:
            log_user("(no speech detected)")
            now = time.monotonic()
            if silence_started is None:
                silence_started = now
            elapsed = now - silence_started + float(RECORD_SECONDS)
            log_system(f"Silence ~{elapsed:.0f}s / {SESSION_SILENCE_SECONDS}s")
            if elapsed >= SESSION_SILENCE_SECONDS:
                log_system("Silence timeout — back to wake word.")
                try:
                    speak("I'll go quiet for now. Say hey jarvis when you need me.")
                except Exception as exc:  # noqa: BLE001
                    log_error(f"TTS error: {exc}")
                return
            continue

        silence_started = None
        keep_going = handle_turn(messages, text, timer_manager=timer_manager)
        if not keep_going:
            log_system("Session ended — back to wake word.")
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

    greeting_print, greeting_speech = make_jarvis_greeting()
    print(greeting_print)
    try:
        speak(greeting_speech)
    except Exception as exc:  # noqa: BLE001
        log_error(f"TTS error (greeting): {exc}")

    log_system("Ready. Say 'hey jarvis' to start talking (Ctrl+C to quit).")

    while True:
        try:
            set_status("[IDLE] Listening for 'hey jarvis'...")
            score = wait_for_wake_word(
                wakeword_pause_event=wakeword_pause_event,
                show_scores=False,
            )
            clear_status()
            maybe_bell("wake")
            log_system(f"[WAKE] Wake word detected (score={score:.2f}).")
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
