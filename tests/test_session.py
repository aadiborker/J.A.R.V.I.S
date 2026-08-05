from config import SESSION_END_PHRASES


def _is_session_end(text: str) -> bool:
    lowered = text.lower().strip()
    return any(phrase in lowered for phrase in SESSION_END_PHRASES)


def test_is_session_end_phrases():
    assert _is_session_end("Okay goodbye Jarvis")
    assert _is_session_end("please stop listening")
    assert _is_session_end("that's all for now")
    assert not _is_session_end("what's the weather")
