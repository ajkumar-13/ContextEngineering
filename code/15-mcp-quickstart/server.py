"""A minimal MCP server: one tool, one resource, one prompt.

Run it:  python server.py     (speaks MCP over stdio)

It wraps the pure logic in ``mcp_quickstart.refunds`` so the interesting rules stay
unit-testable without the MCP runtime. Requires the official SDK: ``pip install mcp``.
Pin the version you test against, the SDK's API still moves.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from mcp_quickstart.refunds import REFUND_POLICY, check_refund_eligibility, lookup_order

mcp = MCPServer("refunds-demo")


@mcp.tool()
def check_refund(order_id: str, amount_usd: float) -> dict:
    """Check whether a refund may proceed for an order. Returns a structured decision."""
    order = lookup_order(order_id)  # the order's facts come from the store, never from the model
    if order is None:
        return {"eligible": False, "requires_manager_approval": False, "reason": f"Unknown order {order_id}."}
    d = check_refund_eligibility(order, amount_usd)
    return {
        "eligible": d.eligible,
        "requires_manager_approval": d.requires_manager_approval,
        "reason": d.reason,
    }


@mcp.resource("refunds://policy")
def policy() -> str:
    """The refund policy document (a read-only resource the host can fetch)."""
    return REFUND_POLICY


@mcp.prompt()
def draft_refund_reply(order_id: str, decision: str) -> str:
    """A prompt template for drafting a customer reply about a refund decision."""
    return (
        f"Write a short, warm reply to the customer about order {order_id}. "
        f"The refund decision was: {decision}. Explain it plainly and, if it was "
        "declined, say what they can do next."
    )


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
