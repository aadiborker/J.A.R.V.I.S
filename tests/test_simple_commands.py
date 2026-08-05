import datetime

from tools.simple_commands import try_handle_simple


class FakeTimerManager:
    def __init__(self):
        self.calls = []

    def set_timer(self, seconds: int, label: str = "", *, announce: bool = True):
        self.calls.append((seconds, label, announce))
        return {
            "timer_id": "t1",
            "seconds": seconds,
            "label": label,
            "announcement": f"T minus {seconds} seconds",
        }


def test_try_handle_simple_time_returns_string(monkeypatch):
    fixed = datetime.datetime(
        2026, 8, 5, 15, 5, tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    )

    import tools.time_tools as time_tools

    monkeypatch.setattr(time_tools, "_now_ist", lambda now=None: fixed if now is None else now)
    print_text, speech_text = try_handle_simple(
        "what time is it right now",
        timer_manager=FakeTimerManager(),
    )
    assert "3:" in print_text or "03:" in print_text
    assert "05-08-2026" in print_text
    assert "fifth of August twenty twenty six" in speech_text
    assert "05-08-2026" not in speech_text


def test_try_handle_simple_timer_parses_digits():
    tm = FakeTimerManager()
    print_text, speech_text = try_handle_simple("set a timer for 10 minutes", timer_manager=tm)
    assert tm.calls == [(600, "", False)]
    assert "t minus" in print_text.lower()
    assert "10" in print_text.lower() or "minute" in print_text.lower()
    assert print_text == speech_text

