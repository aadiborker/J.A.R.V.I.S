from __future__ import annotations

import sys
import datetime
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv

from config import (
    MEDIA_SESSION_END,
    MEDIA_WAKEWORD_PAUSE_SECONDS,
    IDLE_SLEEP_SECONDS,
    SESSION_END_PHRASES,
    SESSION_SILENCE_SECONDS,
    STT_LISTEN_SECONDS,
    SYSTEM_PROMPT,
    UI_WS_HOST,
    UI_WS_PORT,
    WORKING_ACK,
)
from llm.client import ensure_api_key
from llm.tool_loop import chat_with_tools
from stt.transcribe import ensure_whisper_ready, transcribe_microphone, warmup_whisper
from tts.speak import ensure_piper_ready, get_voice, speak
from wakeword.listen import ensure_wakeword_ready, wait_for_wake_word
from tools.offline_gate import handle_offline_or_simple
from tools.time_tools import get_time
from tools.timer_tools import TimerManager
from tools.app_tools import open_app
from tools.browser_tools import (
    consume_session_end_after_media,
    open_url,
    open_youtube,
    youtube_play,
    youtube_search,
)
from tools.memory_store import build_system_prompt, list_memories, recall, remember
from tools.system_tools import (
    get_system_status,
    lock_pc,
    set_brightness,
    set_mute,
    set_volume,
    take_screenshot,
)
from net.connectivity import (
    OFFLINE_ANNOUNCE,
    ONLINE_ANNOUNCE,
    NetworkMonitor,
    boot_status_line,
    check_internet,
    set_online,
)
from system.power import (
    PowerMonitor,
    emit_power_ui_payload,
    format_boot_power_line,
    format_power_transition_line,
    get_power_status,
)
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
from ui.ws_bridge import enable_bridge, emit_ui, get_bridge


def warmup_models(*, lite: bool = False) -> None:
    """Load wake-word (+ optional Piper) in parallel; warm Whisper disk cache."""
    ensure_whisper_ready()
    ensure_api_key()
    warmup_whisper()

    def _piper() -> None:
        ensure_piper_ready()
        if not lite:
            get_voice()  # preload so first speak is instant (HUD / full mode)

    with ThreadPoolExecutor(max_workers=2) as pool:
        piper_f = pool.submit(_piper)
        wake_f = pool.submit(ensure_wakeword_ready)
        piper_f.result()
        wake_f.result()


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
    emit_ui({"type": "transcript", "role": "jarvis", "text": text})


def make_jarvis_greeting(
    *, now_ist: datetime.datetime | None = None
) -> tuple[str, str]:
    """Create a JARVIS-style greeting in IST.

    Returns: (print_text, speech_text)
    Print shows numeric date (05-08-2026); speech says the full date aloud.
    """
    from tools.time_tools import (
        format_date_display,
        format_date_spoken,
        format_time_display,
        _now_ist,
    )

    now = _now_ist(now_ist)
    hour = now.hour
    if 5 <= hour < 12:
        part = "Morning"
    elif 12 <= hour < 17:
        part = "Afternoon"
    elif 17 <= hour < 22:
        part = "Evening"
    else:
        part = "Night"

    date_str = format_date_display(now)
    spoken_long = format_date_spoken(now)
    time_str = format_time_display(now)

    print_text = f"Good {part.lower()}. {date_str}, {time_str}."
    speech_text = (
        f"Good {part.lower()}. Today is the {spoken_long}. It's {time_str}."
    )
    return print_text, speech_text


def is_session_end(text: str) -> bool:
    lowered = text.lower().strip()
    return any(phrase in lowered for phrase in SESSION_END_PHRASES)


def _finish_turn_after_media(timer_manager: TimerManager) -> bool:
    """Return False to end the conversation session after media starts."""
    if not MEDIA_SESSION_END or not consume_session_end_after_media():
        return True
    log_system(
        "Media playing — leaving conversation mode so the mic won't hear the video."
    )
    if MEDIA_WAKEWORD_PAUSE_SECONDS > 0:
        timer_manager.pause_wakeword_for(MEDIA_WAKEWORD_PAUSE_SECONDS)
        log_system(
            f"Wake word paused ~{int(MEDIA_WAKEWORD_PAUSE_SECONDS)}s "
            "(say hey jarvis after that)."
        )
    return False


def _refresh_system_prompt(messages: list[dict[str, str]]) -> None:
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] = build_system_prompt(SYSTEM_PROMPT)


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
        farewell = "Standing by."
        jarvis_typed(farewell)
        try:
            speak(farewell)
        except Exception as exc:  # noqa: BLE001
            log_error(f"TTS error: {exc}")
        return False

    log_user(text)
    messages.append({"role": "user", "content": text})

    # Local fast-path and offline lower-modules gate (skips Groq when offline).
    gated = handle_offline_or_simple(text, timer_manager)
    if gated is not None:
        print_text, speech_text = gated
        messages.append({"role": "assistant", "content": print_text})
        # Memory fast-paths may have changed stored facts.
        _refresh_system_prompt(messages)
        jarvis_typed(print_text)
        if speech_text:
            try:
                set_status("[SPEAK] Speaking...")
                speak(speech_text)
            except Exception as exc:  # noqa: BLE001
                log_error(f"TTS error: {exc}")
            finally:
                clear_status()
        return _finish_turn_after_media(timer_manager)

    ack = (WORKING_ACK or "").strip()
    if ack:
        try:
            set_status("[SPEAK] Ack...")
            speak(ack)
        except Exception as exc:  # noqa: BLE001
            log_error(f"TTS error (ack): {exc}")
        finally:
            clear_status()

    set_status("[THINK] Thinking...")
    try:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_time",
                    "description": (
                        "Get current IST time and date. Returns time, date as DD-MM-YYYY "
                        "(e.g. 05-08-2026), and date_spoken. In your reply, show the numeric "
                        "date and say the date_spoken form aloud."
                    ),
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
            {
                "type": "function",
                "function": {
                    "name": "open_youtube",
                    "description": "Open YouTube in the default browser",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "youtube_search",
                    "description": (
                        "Open YouTube search results in the browser. "
                        "Use only when the user wants to browse results, not play a specific video."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for YouTube",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "youtube_play",
                    "description": (
                        "Find the top YouTube match for a query and open the watch page so it can play. "
                        "Use when the user says play, watch, or put on a video/trailer/song."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "What to play, e.g. Ramayana trailer",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "open_url",
                    "description": (
                        "Open an http or https URL in the default browser. "
                        "Use for websites other than a plain YouTube home/search/play request."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "Full URL or domain (e.g. https://example.com)",
                            },
                        },
                        "required": ["url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "open_app",
                    "description": (
                        "Open an allowlisted desktop app. Supported names: notepad, calculator, "
                        "chrome, edge, explorer, spotify, cmd, powershell, paint."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "App name, e.g. chrome, notepad, calculator",
                            },
                        },
                        "required": ["name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_system_status",
                    "description": (
                        "Get live RAM and CPU usage for this PC. Use when the user asks about "
                        "memory, RAM, CPU, or system load."
                    ),
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "set_volume",
                    "description": "Set master speaker volume from 0 to 100.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "level": {
                                "type": "integer",
                                "description": "Volume percent 0-100",
                            },
                        },
                        "required": ["level"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "set_mute",
                    "description": "Mute or unmute system audio.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "muted": {
                                "type": "boolean",
                                "description": "True to mute, false to unmute",
                            },
                        },
                        "required": ["muted"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "lock_pc",
                    "description": "Lock the Windows workstation / screen.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "take_screenshot",
                    "description": "Capture the primary screen and save a PNG on the Desktop.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "set_brightness",
                    "description": (
                        "Set display brightness 0-100 when supported (often laptops only)."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "level": {
                                "type": "integer",
                                "description": "Brightness percent 0-100",
                            },
                        },
                        "required": ["level"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "remember",
                    "description": (
                        "Save a short lasting fact about the user (name, city, preference). "
                        "Use a simple snake_case key."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string", "description": "e.g. name, city"},
                            "value": {"type": "string", "description": "Fact to store"},
                        },
                        "required": ["key", "value"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "recall",
                    "description": "Look up one saved user fact by key.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                        },
                        "required": ["key"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_memories",
                    "description": "List all saved user facts.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

        def _remember_and_refresh(**kwargs):
            out = remember(**kwargs)
            _refresh_system_prompt(messages)
            return out

        tool_registry = {
            "get_time": lambda **_kwargs: get_time(),
            "set_timer": timer_manager.set_timer,
            "open_youtube": lambda **_kwargs: open_youtube(),
            "youtube_search": youtube_search,
            "youtube_play": youtube_play,
            "open_url": open_url,
            "open_app": open_app,
            "get_system_status": lambda **_kwargs: get_system_status(),
            "set_volume": set_volume,
            "set_mute": set_mute,
            "lock_pc": lambda **_kwargs: lock_pc(),
            "take_screenshot": lambda **_kwargs: take_screenshot(),
            "set_brightness": set_brightness,
            "remember": _remember_and_refresh,
            "recall": recall,
            "list_memories": lambda **_kwargs: list_memories(),
        }

        reply = chat_with_tools(messages, tools, tool_registry)
        _refresh_system_prompt(messages)
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
    return _finish_turn_after_media(timer_manager)


def _on_mic_recording_done() -> None:
    """Immediate feedback that the listen window finished (before Whisper text)."""
    set_status("[STT] Got it — transcribing...")


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
        set_status(
            f"[SESSION] Listening — speak now (about {STT_LISTEN_SECONDS:.0f} seconds)..."
        )
        try:
            text = transcribe_microphone(on_recording_done=_on_mic_recording_done)
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
            elapsed = now - silence_started + float(STT_LISTEN_SECONDS)
            log_system(f"Silence ~{elapsed:.0f}s / {SESSION_SILENCE_SECONDS}s")
            if elapsed >= SESSION_SILENCE_SECONDS:
                log_system("Silence timeout — back to wake word.")
                try:
                    speak("Going quiet. Say hey jarvis when you need me.")
                except Exception as exc:  # noqa: BLE001
                    log_error(f"TTS error: {exc}")
                return
            continue

        silence_started = None
        keep_going = handle_turn(messages, text, timer_manager=timer_manager)
        if not keep_going:
            log_system("Session ended — back to wake word.")
            return


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    ui_ws = "--ui-ws" in args

    load_dotenv()
    if ui_ws:
        try:
            bridge = enable_bridge(host=UI_WS_HOST, port=UI_WS_PORT)
            log_system(f"UI bridge on ws://{UI_WS_HOST}:{UI_WS_PORT}")
        except Exception as exc:  # noqa: BLE001
            print(f"UI bridge failed: {exc}", file=sys.stderr)
            return 1

    print("J.A.R.V.I.S booting...", flush=True)
    if not ui_ws:
        log_system("Lite mode (no HUD) — lower RAM. Use scripts\\start_jarvis_ui.bat for the HUD.")
    set_status("[BOOT] Loading models...")

    try:
        warmup_models(lite=not ui_ws)
    except (FileNotFoundError, RuntimeError, OSError, ValueError) as exc:
        clear_status()
        print(exc, file=sys.stderr)
        emit_ui({"type": "error", "message": str(exc)})
        return 1

    clear_status()
    emit_ui({"type": "ready"})
    wakeword_pause_event = threading.Event()
    timer_manager = TimerManager(
        speak_fn=speak,
        wakeword_pause_event=wakeword_pause_event,
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": build_system_prompt(SYSTEM_PROMPT)},
    ]

    def on_network_transition(online: bool) -> None:
        line = ONLINE_ANNOUNCE if online else OFFLINE_ANNOUNCE
        log_system(line)
        emit_ui({"type": "network", "online": online})
        emit_ui({"type": "transcript", "role": "system", "text": line})
        wakeword_pause_event.set()
        try:
            set_status("[SPEAK] Network...")
            speak(line)
        except Exception as exc:  # noqa: BLE001
            log_error(f"TTS error (network): {exc}")
        finally:
            clear_status()
            wakeword_pause_event.clear()

    initial_online = check_internet()
    set_online(initial_online)
    emit_ui({"type": "network", "online": initial_online})

    monitor = NetworkMonitor(on_transition=on_network_transition)
    monitor.start()

    power_monitor: PowerMonitor | None = None

    # First boot / launch cue before the daily greeting.
    boot_line = boot_status_line(initial_online)
    print(boot_line, flush=True)
    emit_ui({"type": "transcript", "role": "system", "text": boot_line})
    wakeword_pause_event.set()
    try:
        set_status("[SPEAK] Boot...")
        speak(boot_line)
    except Exception as exc:  # noqa: BLE001
        log_error(f"TTS error (boot): {exc}")
    finally:
        clear_status()
        wakeword_pause_event.clear()

    def on_power_transition(charging: bool, status) -> None:
        line = format_power_transition_line(
            charging=charging, percent=status.percent
        )
        log_system(line)
        emit_ui(emit_power_ui_payload(status))
        emit_ui({"type": "transcript", "role": "system", "text": line})
        wakeword_pause_event.set()
        try:
            set_status("[SPEAK] Power...")
            speak(line)
        except Exception as exc:  # noqa: BLE001
            log_error(f"TTS error (power): {exc}")
        finally:
            clear_status()
            wakeword_pause_event.clear()

    power_status = get_power_status()
    emit_ui(emit_power_ui_payload(power_status))
    power_line = format_boot_power_line(power_status)
    print(power_line, flush=True)
    emit_ui({"type": "transcript", "role": "system", "text": power_line})
    wakeword_pause_event.set()
    try:
        set_status("[SPEAK] Power...")
        speak(power_line)
    except Exception as exc:  # noqa: BLE001
        log_error(f"TTS error (power boot): {exc}")
    finally:
        clear_status()
        wakeword_pause_event.clear()

    if power_status.available and power_status.charging is not None:
        power_monitor = PowerMonitor(on_transition=on_power_transition)
        power_monitor.seed(power_status)
        power_monitor.start()

    greeting_print, greeting_speech = make_jarvis_greeting()
    print(greeting_print, flush=True)
    emit_ui({"type": "transcript", "role": "jarvis", "text": greeting_print})
    log_system(
        "Ready. Say 'hey jarvis' to talk (Ctrl+C to quit)."
    )

    # Speak greeting before wake-word loop so desktop launch always greets aloud.
    wakeword_pause_event.set()
    try:
        set_status("[SPEAK] Greeting...")
        speak(greeting_speech)
    except Exception as exc:  # noqa: BLE001
        log_error(f"TTS error (greeting): {exc}")
    finally:
        clear_status()
        wakeword_pause_event.clear()

    last_activity = time.monotonic()
    idle_sleeping = False
    idle_lock = threading.Lock()

    def _enter_idle_sleep() -> None:
        nonlocal idle_sleeping, monitor, power_monitor
        with idle_lock:
            if idle_sleeping:
                return
            idle_sleeping = True
            log_system(
                f"Idle sleep — pausing network/power monitors "
                f"(~{int(IDLE_SLEEP_SECONDS)}s quiet). Wake word still on."
            )
            monitor.stop()
            if power_monitor is not None:
                power_monitor.stop()

    def _leave_idle_sleep() -> None:
        nonlocal idle_sleeping, monitor, power_monitor, last_activity
        with idle_lock:
            last_activity = time.monotonic()
            if not idle_sleeping:
                return
            idle_sleeping = False
            log_system("Leaving idle sleep — resuming monitors.")
            monitor = NetworkMonitor(on_transition=on_network_transition)
            monitor.start()
            status = get_power_status()
            if status.available and status.charging is not None:
                power_monitor = PowerMonitor(on_transition=on_power_transition)
                power_monitor.seed(status)
                power_monitor.start()
            else:
                power_monitor = None

    def _idle_watchdog() -> None:
        while True:
            time.sleep(30)
            if float(IDLE_SLEEP_SECONDS) <= 0:
                continue
            with idle_lock:
                sleeping = idle_sleeping
                inactive = (time.monotonic() - last_activity) >= float(IDLE_SLEEP_SECONDS)
            if inactive and not sleeping:
                _enter_idle_sleep()

    if float(IDLE_SLEEP_SECONDS) > 0:
        threading.Thread(target=_idle_watchdog, daemon=True, name="idle-sleep").start()

    while True:
        try:
            set_status("[IDLE] Listening for 'hey jarvis'...")
            score = wait_for_wake_word(
                wakeword_pause_event=wakeword_pause_event,
                show_scores=True,
            )
            clear_status()
            _leave_idle_sleep()
            maybe_bell("wake")
            log_system(f"[WAKE] Wake word detected (score={score:.2f}).")
        except KeyboardInterrupt:
            print("\nBye.")
            monitor.stop()
            if power_monitor is not None:
                power_monitor.stop()
            return 0

        try:
            run_conversation_session(messages, timer_manager=timer_manager)
            with idle_lock:
                last_activity = time.monotonic()
        except KeyboardInterrupt:
            print("\nBye.")
            monitor.stop()
            if power_monitor is not None:
                power_monitor.stop()
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
