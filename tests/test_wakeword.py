import numpy as np

from wakeword import listen as listen_mod


def test_score_for_wakeword_prefers_named_key(monkeypatch):
    monkeypatch.setattr(listen_mod, "WAKEWORD_MODEL", "hey jarvis")
    score = listen_mod._score_for_wakeword({"hey jarvis": 0.91, "alexa": 0.1})
    assert score == 0.91


def test_wait_for_wake_word_triggers_on_threshold():
    class FakeModel:
        def __init__(self):
            self.n = 0

        def predict(self, frame):
            self.n += 1
            if self.n < 3:
                return {"hey jarvis": 0.1}
            return {"hey jarvis": 0.77}

    detected = []

    def fake_read():
        return np.zeros(1280, dtype=np.int16)

    score = listen_mod.wait_for_wake_word(
        model=FakeModel(),
        threshold=0.5,
        read_chunk=fake_read,
        on_detect=lambda: detected.append(True),
    )
    assert score == 0.77
    assert detected == [True]
