from types import SimpleNamespace

from llm.tool_loop import chat_with_tools


def test_chat_with_tools_executes_tool_calls_and_returns_final_content():
    # 1st Groq response asks for get_time tool
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="get_time", arguments="{}"),
    )
    msg1 = SimpleNamespace(content=None, tool_calls=[tool_call])
    choice1 = SimpleNamespace(message=msg1)
    resp1 = SimpleNamespace(choices=[choice1])

    # 2nd Groq response returns final text
    msg2 = SimpleNamespace(content="Jarvis: It's 3:05 PM.", tool_calls=None)
    choice2 = SimpleNamespace(message=msg2)
    resp2 = SimpleNamespace(choices=[choice2])

    class FakeChatCompletions:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            return resp1 if self.calls == 1 else resp2

    class FakeClient:
        chat = SimpleNamespace(completions=FakeChatCompletions())

    def get_time_tool():
        return {"time": "3:05 PM"}

    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "what time is it"},
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "Get current time",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]
    tool_registry = {"get_time": get_time_tool}

    reply = chat_with_tools(messages, tools, tool_registry, client=FakeClient())
    assert "3:05" in reply


def test_chat_with_tools_handles_null_arguments():
    tool_call = SimpleNamespace(
        id="call_null",
        function=SimpleNamespace(name="get_time", arguments="null"),
    )
    msg1 = SimpleNamespace(content=None, tool_calls=[tool_call])
    resp1 = SimpleNamespace(choices=[SimpleNamespace(message=msg1)])
    msg2 = SimpleNamespace(content="It is noon.", tool_calls=None)
    resp2 = SimpleNamespace(choices=[SimpleNamespace(message=msg2)])

    class FakeChatCompletions:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            return resp1 if self.calls == 1 else resp2

    class FakeClient:
        chat = SimpleNamespace(completions=FakeChatCompletions())

    reply = chat_with_tools(
        [{"role": "user", "content": "time"}],
        [{"type": "function", "function": {"name": "get_time"}}],
        {"get_time": lambda **_: {"time": "12:00"}},
        client=FakeClient(),
    )
    assert "noon" in reply.lower()

