from __future__ import annotations

import ctypes
import random
import threading
from dataclasses import dataclass
from typing import Callable

from config import POWER_CHECK_INTERVAL_SECONDS, POWER_DEBOUNCE_CHECKS

POWER_UNAVAILABLE = "Power status unavailable."

_POWER_JOKES = (
    "Why did the computer go to the doctor? It had a virus.",
    "I would tell you a UDP joke, but you might not get it.",
    "There are only 10 kinds of people: those who understand binary and those who don't.",
    "My battery and I have commitment issues — it keeps leaving me at 1 percent.",
    "I asked the charger how it was doing. It said it was feeling very positive.",
    "Why was the keyboard locked? Because it had a shift key and trust issues.",
)


@dataclass(frozen=True)
class PowerStatus:
    percent: int | None
    charging: bool | None
    available: bool


class _SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("SystemStatusFlag", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def _status_from_win(raw) -> PowerStatus:
    """Map a SYSTEM_POWER_STATUS-like object to PowerStatus."""
    if raw.BatteryFlag & 0x80:
        return PowerStatus(percent=None, charging=None, available=False)

    percent_raw = raw.BatteryLifePercent & 0xFF
    percent = None if percent_raw > 100 else int(percent_raw)

    ac = raw.ACLineStatus & 0xFF
    if ac == 0:
        charging = False
    elif ac == 1:
        charging = True
    else:
        charging = None

    if percent is None and charging is None:
        return PowerStatus(percent=None, charging=None, available=False)

    return PowerStatus(percent=percent, charging=charging, available=True)


def get_power_status() -> PowerStatus:
    """Read Windows system power status via GetSystemPowerStatus."""
    try:
        status = _SYSTEM_POWER_STATUS()
        ok = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
        if not ok:
            return PowerStatus(percent=None, charging=None, available=False)
        return _status_from_win(status)
    except Exception:  # noqa: BLE001
        return PowerStatus(percent=None, charging=None, available=False)


def pick_power_joke(*, rng: random.Random | None = None) -> str:
    picker = rng.choice if rng is not None else random.choice
    return picker(_POWER_JOKES)


def format_boot_power_line(status: PowerStatus, joke: str) -> str:
    if not status.available:
        return POWER_UNAVAILABLE

    parts: list[str] = []
    if status.percent is not None:
        parts.append(f"Power at {status.percent} percent.")
    else:
        parts.append("Power level unknown.")

    if status.charging is True:
        parts.append("Charging.")
    elif status.charging is False:
        parts.append("Not charging.")

    cleaned = (joke or "").strip()
    if cleaned:
        parts.append(f"Here's a quick one: {cleaned}")
    return " ".join(parts)


def format_power_transition_line(*, charging: bool, percent: int | None) -> str:
    if charging:
        head = "Power connected."
    else:
        head = "Running on battery."
    if percent is not None:
        return f"{head} Power at {percent} percent."
    return head


def emit_power_ui_payload(status: PowerStatus) -> dict:
    if not status.available:
        return {"type": "power", "available": False}
    return {
        "type": "power",
        "available": True,
        "percent": status.percent,
        "charging": status.charging,
    }


class PowerMonitor:
    """Poll charge state; call on_transition after debounce when AC plug state flips."""

    def __init__(
        self,
        on_transition: Callable[[bool, PowerStatus], None],
        *,
        status_fn: Callable[[], PowerStatus] | None = None,
        interval_s: float | None = None,
        debounce: int | None = None,
    ) -> None:
        self._on_transition = on_transition
        self._status_fn = status_fn or get_power_status
        self._interval_s = (
            POWER_CHECK_INTERVAL_SECONDS if interval_s is None else interval_s
        )
        self._debounce = POWER_DEBOUNCE_CHECKS if debounce is None else debounce
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._committed_charging: bool | None = None

    def seed(self, status: PowerStatus) -> None:
        if status.available and status.charging is not None:
            self._committed_charging = status.charging

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="PowerMonitor", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval_s + 1.0)
            self._thread = None

    def _run(self) -> None:
        committed = self._committed_charging
        streak = 0
        while not self._stop.is_set():
            status = self._status_fn()
            if (
                not status.available
                or status.charging is None
                or committed is None
            ):
                streak = 0
                self._stop.wait(self._interval_s)
                continue

            if status.charging == committed:
                streak = 0
            else:
                streak += 1
                if streak >= self._debounce:
                    committed = status.charging
                    streak = 0
                    self._committed_charging = committed
                    try:
                        self._on_transition(committed, status)
                    except Exception as exc:  # noqa: BLE001
                        print(f"Power transition handler error: {exc}")
            self._stop.wait(self._interval_s)
