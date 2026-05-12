"""Thin LLM wrappers, kept here so swapping providers is one file."""
from __future__ import annotations

import os
from openai import OpenAI

_oai = OpenAI()


def small_llm(prompt: str, *, model: str | None = None) -> str:
    """Cheap, deterministic completion. Used for chunk-header generation."""
    model = model or os.environ.get("RAG_HEADER_MODEL", "gpt-4o-mini")
    resp = _oai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=80,
    )
    return resp.choices[0].message.content or ""


def chat_llm(messages: list[dict], *, model: str | None = None) -> dict:
    """Main generation call. Returns answer + token usage."""
    model = model or os.environ.get("RAG_GENERATION_MODEL", "gpt-4o-mini")
    resp = _oai.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.0,
    )
    return {
        "text": resp.choices[0].message.content or "",
        "usage": resp.usage.model_dump() if resp.usage else {},
    }
