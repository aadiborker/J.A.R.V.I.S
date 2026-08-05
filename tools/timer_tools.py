from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class _TimerSpec:
    seconds: float
    label: str
    timer_id: str


class TimerManager:
    def __init__(
        self,
        *,
        speak_fn: Callable[[str], None],
        wakeword_pause_event: threading.Event,
    ) -> None:
        self._speak_fn = speak_fn
        self._wakeword_pause_event = wakeword_pause_event

    def set_timer(self, seconds: int | float, label: str = "") -> dict[str, str | int]:
        seconds_f = float(seconds)
        timer_id = str(uuid.uuid4())
        spec = _TimerSpec(seconds=seconds_f, label=label, timer_id=timer_id)

        thread = threading.Thread(
            target=self._worker,
            args=(spec,),
            daemon=True,
        )
        thread.start()

        return {"timer_id": timer_id, "seconds": int(seconds_f), "label": label}

    def _worker(self, spec: _TimerSpec) -> None:
        time.sleep(float(spec.seconds))
        reminder = f"Timer done{': ' + spec.label if spec.label else '.'}"

        # Pause wakeword scoring while we speak the reminder
        self._wakeword_pause_event.set()
        try:
            self._speak_fn(reminder)
        finally:
            self._wakeword_pause_event.clear()

