"""System prompt (loaded from prompts/system.md) and bookend packing."""
from __future__ import annotations

from pathlib import Path

SYSTEM = (Path(__file__).resolve().parents[2] / "prompts" / "system.md").read_text(encoding="utf-8")


def pack(query: str, hits: list[dict]) -> list[dict]:
    """Bookend layout: best chunk first, second-best last, rest in middle."""
    if not hits:
        ordered: list[dict] = []
    elif len(hits) == 1:
        ordered = hits
    else:
        ordered = [hits[0]] + hits[2:] + [hits[1]]
    sources_block = "\n\n".join(
        f"[{h['meta']['title']}] {h['text']}" for h in ordered
    )
    user = f"Sources:\n\n{sources_block}\n\nQuestion: {query}"
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
    ]
