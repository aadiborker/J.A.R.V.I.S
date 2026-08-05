from __future__ import annotations

import json
from typing import Any, Callable

from config import GROQ_MODEL
from llm.client import get_client


def chat_with_tools(
    messages: list[dict[str, str]],
    tools: list[dict[str, Any]],
    tool_registry: dict[str, Callable[..., Any]],
    *,
    client: Any | None = None,
) -> str:
    groq_client = client if client is not None else get_client()

    while True:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=tools,
        )

        msg = response.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)

        if tool_calls:
            tool_calls_payload = []
            for tc in tool_calls:
                tool_calls_payload.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                )

            # Assistant message that contains tool calls.
            messages.append(
                {"role": "assistant", "content": "", "tool_calls": tool_calls_payload}  # type: ignore[list-item]
            )

            # Execute tools and feed results back.
            for tc in tool_calls:
                name = tc.function.name
                args_raw = tc.function.arguments or "{}"
                try:
                    args = json.loads(args_raw)
                except json.JSONDecodeError:
                    args = {}

                fn = tool_registry.get(name)
                if fn is None:
                    result = {"error": f"Unknown tool: {name}"}
                else:
                    result = fn(**args)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result),
                    }
                )

            continue

        content = getattr(msg, "content", None) or ""
        return str(content).strip()

