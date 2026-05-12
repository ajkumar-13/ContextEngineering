"""Thin LLM wrappers, isolated for swappability."""
from __future__ import annotations

import os

from openai import OpenAI

_oai = OpenAI()


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    response_format: dict | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> str:
    model = model or os.environ.get("EMAILBOT_DRAFT_MODEL", "gpt-4o-mini")
    kwargs: dict = {"model": model, "messages": messages, "temperature": temperature}
    if response_format is not None:
        kwargs["response_format"] = response_format
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    resp = _oai.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""
