from __future__ import annotations

import os
from typing import Any

from groq import Groq

from config import GROQ_MODEL


def ensure_api_key() -> str:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Copy .env.example to .env and set your Groq API key."
        )
    return key


def get_client() -> Groq:
    return Groq(api_key=ensure_api_key())


def chat(messages: list[dict[str, str]], *, client: Any | None = None) -> str:
    groq_client = client if client is not None else get_client()
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
    )
    content = response.choices[0].message.content
    if content is None:
        return ""
    return str(content).strip()
