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


def test_open_youtube_fast_path(monkeypatch):
    import tools.browser_tools as bt
    import tools.simple_commands as sc

    monkeypatch.setattr(sc, "is_online", lambda: True)
    monkeypatch.setattr(bt.webbrowser, "open", lambda url: True)
    print_text, speech_text = try_handle_simple("open youtube", FakeTimerManager())
    assert print_text == "Opening YouTube."
    assert speech_text == print_text


def test_youtube_search_fast_path(monkeypatch):
    import tools.browser_tools as bt
    import tools.simple_commands as sc

    monkeypatch.setattr(sc, "is_online", lambda: True)
    monkeypatch.setattr(bt.webbrowser, "open", lambda url: True)
    print_text, _ = try_handle_simple("search youtube for lo-fi beats", FakeTimerManager())
    assert "Searching YouTube for lo-fi beats." == print_text


def test_open_url_fast_path(monkeypatch):
    import tools.browser_tools as bt
    import tools.simple_commands as sc

    monkeypatch.setattr(sc, "is_online", lambda: True)
    monkeypatch.setattr(bt.webbrowser, "open", lambda url: True)
    print_text, _ = try_handle_simple("open https://example.com", FakeTimerManager())
    assert "Opening https://example.com." == print_text


def test_browser_fast_path_offline(monkeypatch):
    import tools.simple_commands as sc
    from tools.browser_tools import BROWSER_OFFLINE_REPLY

    monkeypatch.setattr(sc, "is_online", lambda: False)
    print_text, speech_text = try_handle_simple("open youtube", FakeTimerManager())
    assert print_text == BROWSER_OFFLINE_REPLY
    assert speech_text == BROWSER_OFFLINE_REPLY


def test_play_youtube_fast_path(monkeypatch):
    import tools.browser_tools as bt
    import tools.simple_commands as sc

    monkeypatch.setattr(sc, "is_online", lambda: True)
    monkeypatch.setattr(bt, "resolve_youtube_video_id", lambda q: "abcdefghijk")
    monkeypatch.setattr(bt.webbrowser, "open", lambda url: True)
    bt.consume_session_end_after_media()
    print_text, _ = try_handle_simple("play the ramayana trailer", FakeTimerManager())
    assert print_text.startswith("Playing ramayana trailer on YouTube.")
    assert bt.consume_session_end_after_media() is True


def test_open_app_fast_path(monkeypatch):
    import tools.simple_commands as sc

    monkeypatch.setattr(
        sc,
        "open_app",
        lambda name: {"ok": True, "message": f"Opening {name}."},
    )
    print_text, speech = try_handle_simple("open notepad", FakeTimerManager())
    assert print_text == "Opening notepad."
    assert speech == print_text


def test_open_unknown_phrase_not_forced_as_app():
    assert try_handle_simple("open the pod bay doors", FakeTimerManager()) is None


def test_ram_fast_path(monkeypatch):
    import tools.simple_commands as sc

    monkeypatch.setattr(
        sc,
        "get_system_status",
        lambda: {
            "ok": True,
            "message": "RAM is at 50 percent — about 8.0 of 16.0 gigabytes used. CPU is at 10 percent.",
        },
    )
    print_text, _ = try_handle_simple("how much ram is the system using", FakeTimerManager())
    assert "RAM is at 50 percent" in print_text


def test_ram_check_and_system_status_punct(monkeypatch):
    import tools.simple_commands as sc

    monkeypatch.setattr(
        sc,
        "get_system_status",
        lambda: {"ok": True, "message": "RAM is at 50 percent."},
    )
    assert try_handle_simple("Check for my RAM usage.", FakeTimerManager())[0].startswith("RAM")
    assert try_handle_simple("System status.", FakeTimerManager())[0].startswith("RAM")


def test_mute_volume_lock_fast_paths(monkeypatch):
    import tools.simple_commands as sc

    monkeypatch.setattr(sc, "set_mute", lambda muted: {"message": "Muted." if muted else "Unmuted."})
    monkeypatch.setattr(sc, "set_volume", lambda level: {"message": f"Volume set to {level} percent."})
    monkeypatch.setattr(sc, "lock_pc", lambda: {"message": "Locking the PC."})

    assert try_handle_simple("mute", FakeTimerManager())[0] == "Muted."
    assert try_handle_simple("volume to 40", FakeTimerManager())[0] == "Volume set to 40 percent."
    assert try_handle_simple("lock the pc", FakeTimerManager())[0] == "Locking the PC."
