"""tool-schemas: cost and correctness for tool definitions.

Companion code for Post 15 (Tools and MCP) and Post 21 (Structured output and
guardrails). Two small, offline utilities:

    budget   : estimate the token / dollar cost of a tool catalogue, and what
                trimming it saves (tools compete for the same window as data).
    validate : a dependency-free JSON-Schema-subset validator for structured
                output, returning a list of errors for a validate-and-retry loop.
"""
from __future__ import annotations

from .budget import (
    catalog_cost_usd,
    catalog_tokens,
    estimate_tokens,
    schema_tokens,
    trim,
)
from .validate import is_valid, validate

__all__ = [
    "catalog_cost_usd",
    "catalog_tokens",
    "estimate_tokens",
    "is_valid",
    "schema_tokens",
    "trim",
    "validate",
]

__version__ = "0.1.0"
