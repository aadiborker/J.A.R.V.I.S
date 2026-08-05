from tools import offline_gate as og


class FakeTimer:
    def set_timer(self, seconds, label="", *, announce=True):
        return {}


def test_offline_gate_allows_time(monkeypatch):
    monkeypatch.setattr(og, "is_online", lambda: False)
    monkeypatch.setattr(
        og,
        "try_handle_simple",
        lambda text, tm: (
            "It's 1:00 PM on 05-08-2026.",
            "It's 1:00 PM on the fifth of August twenty twenty six.",
        ),
    )
    out = og.handle_offline_or_simple("what time is it", FakeTimer())
    assert out is not None
    assert "05-08-2026" in out[0]


def test_offline_gate_blocks_general_chat(monkeypatch):
    monkeypatch.setattr(og, "is_online", lambda: False)
    monkeypatch.setattr(og, "try_handle_simple", lambda text, tm: None)
    out = og.handle_offline_or_simple("tell me a joke", FakeTimer())
    assert out == (og.OFFLINE_CHAT_REPLY, og.OFFLINE_CHAT_REPLY)


def test_online_gate_passes_through(monkeypatch):
    monkeypatch.setattr(og, "is_online", lambda: True)
    monkeypatch.setattr(og, "try_handle_simple", lambda text, tm: None)
    assert og.handle_offline_or_simple("hello", FakeTimer()) is None
