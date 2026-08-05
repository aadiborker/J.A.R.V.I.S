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

    # Fire quickly without startup announcement (tested separately via format_t_minus).
    mgr.set_timer(seconds=0.2, label="test", announce=False)

    t0 = time.monotonic()
    while time.monotonic() - t0 < 2.0:
        if spokens:
            break
        time.sleep(0.05)

    assert spokens, "Timer did not fire in time"
    assert not paused.is_set(), "wakeword_pause_event should be cleared after speaking"


def test_format_t_minus():
    from tools.timer_tools import format_t_minus

    assert format_t_minus(90) == "T minus 1 minute 30 seconds"
    assert format_t_minus(60) == "T minus 1 minute"
    assert format_t_minus(5) == "T minus 5 seconds"

