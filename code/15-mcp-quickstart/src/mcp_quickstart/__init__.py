"""mcp-quickstart: a 49-line MCP server around pure, testable tool logic.

Companion code for Post 15 (Tools and MCP) and Post 29 (Build an MCP server).
The refund rules live in ``refunds`` (pure, unit-tested offline); ``server``
is the thin MCP wrapper that exposes them as a tool, a resource, and a prompt.
"""
from __future__ import annotations

from .refunds import (
    Decision,
    Order,
    REFUND_POLICY,
    check_refund_eligibility,
)

__all__ = ["Decision", "Order", "REFUND_POLICY", "check_refund_eligibility"]
__version__ = "0.1.0"
