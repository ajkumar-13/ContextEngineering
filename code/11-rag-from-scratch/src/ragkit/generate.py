"""Grounded generation with citations (online adapter, guarded).

This is the only part of ragkit that calls a provider. The SDK is imported lazily
*inside* the function, and the function raises a clear error if the key is missing,
so importing ``ragkit`` never requires the SDK or a key. The offline core
(chunk / bm25 / fuse / pack) does all the interesting retrieval work; this just
stuffs the packed context into a prompt and asks the model to answer from it.
"""
from __future__ import annotations

import os

_SYSTEM = (
    "You answer strictly from the provided context. Cite the source of each claim "
    "as [source]. If the context does not contain the answer, say so."
)


def build_prompt(question: str, packed_chunks: list[tuple[str, str]]) -> str:
    """Assemble the user message from (source, text) chunks. Pure/offline."""
    blocks = [f"[{src}]\n{text}" for src, text in packed_chunks]
    context = "\n\n".join(blocks)
    return f"Context:\n{context}\n\nQuestion: {question}"


def answer(question: str, packed_chunks: list[tuple[str, str]], model: str = "claude-sonnet-4-5") -> str:
    """Call Anthropic to answer the question from the packed chunks.

    Requires ANTHROPIC_API_KEY and the ``anthropic`` package. Raises RuntimeError
    with a clear message if either is missing.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set: this is the online path; see README.")
    try:
        import anthropic  # lazy import: offline core never needs this
    except ImportError as e:  # pragma: no cover - exercised only when SDK absent
        raise RuntimeError("Install the optional 'online' extra: pip install '.[online]'") from e

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": build_prompt(question, packed_chunks)}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")
