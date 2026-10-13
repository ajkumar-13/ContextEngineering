"""Tools-as-token-budget calculator.

Every tool you expose is spent from the same context window as the user's data
(Post 15). Its JSON schema, name, description, and every parameter description -
is rendered into the prompt on every call. This module estimates that cost so you
can see what a fat catalogue actually buys, and what trimming it saves.

Token counts are ESTIMATED with a simple characters-per-token heuristic so the module runs
offline with no tokenizer dependency. For real numbers, count with the provider's
tokenizer (Post 04); the *relative* comparison this module makes, is catalogue A
cheaper than catalogue B, is what matters for the design decision, and that holds.
"""
from __future__ import annotations

import json

# Rough characters per token for English JSON. Documented heuristic, not a real tokenizer.
_CHARS_PER_TOKEN = 4.0


def estimate_tokens(text: str) -> int:
    """Estimate token count from character length. Deterministic; offline."""
    return max(1, round(len(text) / _CHARS_PER_TOKEN))


def schema_tokens(tool_schema: dict) -> int:
    """Estimate the tokens one tool definition occupies when serialised into the prompt."""
    return estimate_tokens(json.dumps(tool_schema, separators=(",", ":")))


def catalog_tokens(tools: list[dict]) -> int:
    """Total estimated tokens for a whole tool catalogue."""
    return sum(schema_tokens(t) for t in tools)


def catalog_cost_usd(tools: list[dict], input_price_per_mtok: float = 3.0) -> float:
    """Estimated USD cost of shipping this catalogue ONCE, at a given input price.

    ``input_price_per_mtok`` defaults to a Sonnet-tier ~$3 / 1M input tokens
    (current as of early 2026; see Post 05). This is per call, multiply by turns
    and users to get the real bill.
    """
    return catalog_tokens(tools) * input_price_per_mtok / 1_000_000


def trim(tools: list[dict], keep: int) -> list[dict]:
    """Keep only the first ``keep`` tools, the crude version of runtime tool selection.

    Real systems rank tools by relevance to the turn (Post 15's 'iron triangle');
    this just shows that a smaller catalogue costs fewer tokens.
    """
    if keep < 0:
        raise ValueError("keep must be non-negative")
    return tools[:keep]
