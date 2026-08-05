import threading
import time

from tools.timer_tools import TimerManager


def test_timer_manager_speaks_and_pauses_wakeword():
    paused = threading.Event()
    spokens: list[str] = []

    def speak_fn(text: str) -> None:
        # While speaking, wakeword pause should be set
        assert paused.is_set()
        spokens.append(text)

    mgr = TimerManager(
        speak_fn=speak_fn,
        wakeword_pause_event=paused,
    )

    # Fire quickly
    mgr.set_timer(seconds=0.2, label="test")

    t0 = time.monotonic()
    while time.monotonic() - t0 < 2.0:
        if spokens:
            break
        time.sleep(0.05)

    assert spokens, "Timer did not fire in time"
    assert not paused.is_set(), "wakeword_pause_event should be cleared after speaking"

