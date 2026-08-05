from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable

from ui.console_ui import log_timer
from ui.ws_bridge import emit_ui


@dataclass(frozen=True)
class _TimerSpec:
    seconds: float
    label: str
    timer_id: str


def format_t_minus(seconds: float | int) -> str:
    """Human/TTS countdown phrase, e.g. 'T minus 90 seconds'."""
    total = max(0, int(round(float(seconds))))
    if total >= 3600:
        hours = total // 3600
        minutes = (total % 3600) // 60
        secs = total % 60
        parts: list[str] = []
        parts.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
        if minutes:
            parts.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")
        if secs and not minutes:
            parts.append(f"{secs} {'second' if secs == 1 else 'seconds'}")
        return "T minus " + " ".join(parts)
    if total >= 60:
        minutes = total // 60
        secs = total % 60
        if secs == 0:
            return f"T minus {minutes} {'minute' if minutes == 1 else 'minutes'}"
        return (
            f"T minus {minutes} {'minute' if minutes == 1 else 'minutes'} "
            f"{secs} {'second' if secs == 1 else 'seconds'}"
        )
    return f"T minus {total} {'second' if total == 1 else 'seconds'}"


class TimerManager:
    def __init__(
        self,
        *,
        speak_fn: Callable[[str], None],
        wakeword_pause_event: threading.Event,
    ) -> None:
        self._speak_fn = speak_fn
        self._wakeword_pause_event = wakeword_pause_event

    @property
    def wakeword_pause_event(self) -> threading.Event:
        return self._wakeword_pause_event

    def pause_wakeword_for(self, seconds: float) -> None:
        """Temporarily ignore wake-word hits (e.g. while YouTube audio is loud)."""
        seconds_f = max(0.0, float(seconds))
        if seconds_f <= 0:
            return
        self._wakeword_pause_event.set()

        def _clear() -> None:
            time.sleep(seconds_f)
            self._wakeword_pause_event.clear()

        threading.Thread(
            target=_clear, name="wakeword-pause-media", daemon=True
        ).start()

    def set_timer(
        self,
        seconds: int | float,
        label: str = "",
        *,
        announce: bool = True,
    ) -> dict[str, str | int]:
        seconds_f = float(seconds)
        timer_id = str(uuid.uuid4())
        spec = _TimerSpec(seconds=seconds_f, label=label or "", timer_id=timer_id)
        announcement = format_t_minus(seconds_f)
        ends_at = time.time() + seconds_f

        emit_ui(
            {
                "type": "timer",
                "action": "start",
                "timer_id": timer_id,
                "seconds": int(seconds_f),
                "label": spec.label,
                "ends_at": ends_at,
                "announcement": announcement,
            }
        )

        thread = threading.Thread(
            target=self._worker,
            args=(spec,),
            daemon=True,
        )
        thread.start()

        if announce:
            self._wakeword_pause_event.set()
            try:
                log_timer(announcement)
                self._speak_fn(announcement)
            finally:
                self._wakeword_pause_event.clear()

        return {
            "timer_id": timer_id,
            "seconds": int(seconds_f),
            "label": spec.label,
            "announcement": announcement,
        }

    def _worker(self, spec: _TimerSpec) -> None:
        time.sleep(float(spec.seconds))
        reminder = f"Timer done{': ' + spec.label if spec.label else '.'}"

        emit_ui(
            {
                "type": "timer",
                "action": "done",
                "timer_id": spec.timer_id,
                "label": spec.label,
            }
        )

        # Pause wakeword scoring while we speak the reminder
        self._wakeword_pause_event.set()
        try:
            log_timer(reminder)
            self._speak_fn(reminder)
        finally:
            self._wakeword_pause_event.clear()
