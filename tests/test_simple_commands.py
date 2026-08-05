import datetime

from tools.simple_commands import try_handle_simple


class FakeTimerManager:
    def __init__(self):
        self.calls = []

    def set_timer(self, seconds: int, label: str = ""):
        self.calls.append((seconds, label))
        return {"timer_id": "t1", "seconds": seconds, "label": label}


def test_try_handle_simple_time_returns_string(monkeypatch):
    class FakeDT(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 1, 15, 5)

    monkeypatch.setattr(datetime, "datetime", FakeDT)
    reply = try_handle_simple(
        "what time is it right now",
        timer_manager=FakeTimerManager(),
    )
    assert "3:" in reply or "03:" in reply


def test_try_handle_simple_timer_parses_digits():
    tm = FakeTimerManager()
    reply = try_handle_simple("set a timer for 10 minutes", timer_manager=tm)
    assert tm.calls == [(600, "")]
    assert "10" in reply.lower()

