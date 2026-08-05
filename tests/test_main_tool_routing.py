from types import SimpleNamespace

import main as main_mod


def test_handle_turn_uses_simple_commands_when_available(monkeypatch):
    messages = [{"role": "system", "content": "sys"}]

    class FakeTimerManager:
        def set_timer(self, seconds: int, label: str = ""):
            return {"timer_id": "t1", "seconds": seconds, "label": label}

    # Force offline/simple gate to handle the utterance.
    monkeypatch.setattr(
        main_mod,
        "handle_offline_or_simple",
        lambda text, timer_manager: ("It's now.", "It's now."),
    )
    monkeypatch.setattr(main_mod, "chat_with_tools", lambda *args, **kwargs: "SHOULD NOT BE CALLED")
    monkeypatch.setattr(main_mod, "speak", lambda text: None)

    keep_going = main_mod.handle_turn(messages, "what time is it", timer_manager=FakeTimerManager())
    assert keep_going is True
    assert messages[-1]["role"] == "assistant"
    assert "It's now." in messages[-1]["content"]

