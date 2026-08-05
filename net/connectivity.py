from __future__ import annotations

import socket
import threading

from config import (
    NETWORK_CHECK_INTERVAL_SECONDS,
    NETWORK_DEBOUNCE_CHECKS,
    NETWORK_PROBE_HOSTS,
    NETWORK_PROBE_TIMEOUT_SECONDS,
)

OFFLINE_ANNOUNCE = "Network offline. Switching to lower modules."
ONLINE_ANNOUNCE = "Network restored. Full systems online."

_lock = threading.Lock()
_online = True


def is_online() -> bool:
    with _lock:
        return _online


def set_online(value: bool) -> None:
    global _online
    with _lock:
        _online = bool(value)


def boot_status_line(online: bool | None = None) -> str:
    ok = is_online() if online is None else online
    return "System Online." if ok else OFFLINE_ANNOUNCE


def check_internet(
    *,
    hosts: tuple[tuple[str, int], ...] | None = None,
    timeout: float | None = None,
) -> bool:
    """Return True if any probe host accepts a TCP connect."""
    probe_hosts = hosts if hosts is not None else NETWORK_PROBE_HOSTS
    probe_timeout = (
        NETWORK_PROBE_TIMEOUT_SECONDS if timeout is None else timeout
    )
    for host, port in probe_hosts:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(probe_timeout)
                sock.connect((host, port))
            return True
        except OSError:
            continue
    return False


class NetworkMonitor:
    def __init__(
        self,
        on_transition,
        *,
        check_fn=None,
        interval_s: float | None = None,
        debounce: int | None = None,
    ) -> None:
        self._on_transition = on_transition
        self._check_fn = check_fn or check_internet
        self._interval_s = (
            NETWORK_CHECK_INTERVAL_SECONDS if interval_s is None else interval_s
        )
        self._debounce = (
            NETWORK_DEBOUNCE_CHECKS if debounce is None else debounce
        )
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="NetworkMonitor", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval_s + 1.0)
            self._thread = None

    def _run(self) -> None:
        committed = is_online()
        streak = 0
        while not self._stop.is_set():
            ok = bool(self._check_fn())
            if ok == committed:
                streak = 0
            else:
                streak += 1
                if streak >= self._debounce:
                    committed = ok
                    streak = 0
                    set_online(ok)
                    try:
                        self._on_transition(ok)
                    except Exception as exc:  # noqa: BLE001
                        print(f"Network transition handler error: {exc}")
            self._stop.wait(self._interval_s)
