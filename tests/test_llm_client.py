from types import SimpleNamespace

import pytest

from llm.client import chat, ensure_api_key


def test_ensure_api_key_missing(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        ensure_api_key()


def test_ensure_api_key_blank(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "   ")
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        ensure_api_key()


def test_ensure_api_key_ok(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    assert ensure_api_key() == "gsk_test"


def test_chat_returns_assistant_text(monkeypatch):
    class FakeCompletions:
        def create(self, **kwargs):
            assert kwargs["model"] == "llama-3.1-8b-instant"
            assert kwargs["messages"][0]["role"] == "system"
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="  hello there  "))]
            )

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]
    assert chat(messages, client=FakeClient()) == "hello there"
