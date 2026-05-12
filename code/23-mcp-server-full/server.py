"""acme-support — a small MCP server companion to Post 23.

Three tools, one resource, one prompt. Permission boundary on issue_refund
is enforced in code, not in the tool description.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

DATA = Path(__file__).parent / "data"
ORDERS: list[dict] = json.loads((DATA / "orders.json").read_text(encoding="utf-8"))
REFUND_THRESHOLD = 1000  # dollars; over this, require human confirmation

mcp = FastMCP("acme-support")


# -- tool 1: search_orders (read) --------------------------------------------

class SearchOrdersResult(BaseModel):
    matches: list[dict]
    count: int


@mcp.tool(
    description=(
        "Search orders by customer email or by order id. "
        "Use this when the user provides either piece of information. "
        "Do NOT use for refunds; use `issue_refund` for refunds."
    ),
)
def search_orders(
    email: Annotated[str | None, Field(description="Customer email")] = None,
    order_id: Annotated[str | None, Field(description="Order id (e.g. ORD-1234)")] = None,
) -> SearchOrdersResult:
    if not email and not order_id:
        raise ValueError("Provide email or order_id (or both).")
    matches = [
        o for o in ORDERS
        if (not email or o["email"].lower() == email.lower())
        and (not order_id or o["id"] == order_id)
    ]
    return SearchOrdersResult(matches=matches, count=len(matches))


# -- tool 2: issue_refund (write, with permission boundary) ------------------

class IssueRefundResult(BaseModel):
    ok: bool
    refund_id: str | None = None
    requires_confirmation: bool = False
    reason: str | None = None


@mcp.tool(
    description=(
        f"Issue a refund for an order. Confirm the amount and order id with "
        f"the user before calling. Refunds over ${REFUND_THRESHOLD} require "
        f"human confirmation; the tool will return requires_confirmation=true "
        f"and not actually refund."
    ),
)
def issue_refund(
    order_id: Annotated[str, Field(description="Order id")],
    amount: Annotated[float, Field(gt=0, description="Refund amount in USD")],
    reason: Annotated[str, Field(min_length=4, description="Short reason")],
) -> IssueRefundResult:
    order = next((o for o in ORDERS if o["id"] == order_id), None)
    if order is None:
        return IssueRefundResult(ok=False, reason="order_not_found")
    if amount > order["total"]:
        return IssueRefundResult(ok=False, reason="amount_exceeds_order_total")
    if amount > REFUND_THRESHOLD:
        return IssueRefundResult(
            ok=False,
            requires_confirmation=True,
            reason=(
                f"Refund of ${amount:.2f} exceeds the ${REFUND_THRESHOLD} "
                "auto-approve threshold. Route to manager queue."
            ),
        )
    refund_id = f"RF-{order_id[-4:]}-{int(amount)}"
    return IssueRefundResult(ok=True, refund_id=refund_id)


# -- tool 3: escalate_to_human ----------------------------------------------

class EscalateResult(BaseModel):
    ticket_id: str
    queue: str


@mcp.tool(
    description=(
        "Create a human-handoff ticket. Use when the user asks for a human, "
        "when the issue is outside Acme product scope, or when issue_refund "
        "returns requires_confirmation=true."
    ),
)
def escalate_to_human(
    summary: Annotated[str, Field(min_length=10)],
    queue: Annotated[str, Field(pattern="^(general|billing|engineering)$")] = "general",
) -> EscalateResult:
    ticket_id = f"TKT-{abs(hash(summary)) % 10_000:04d}"
    return EscalateResult(ticket_id=ticket_id, queue=queue)


# -- resource: refunds_policy -----------------------------------------------

@mcp.resource("file://refunds_policy.md")
def refunds_policy() -> str:
    return (DATA / "refunds_policy.md").read_text(encoding="utf-8")


# -- prompt: triage_intake --------------------------------------------------

@mcp.prompt("triage_intake")
def triage_intake(customer_msg: str) -> str:
    template = (Path(__file__).parent / "prompts" / "triage_intake.md").read_text(encoding="utf-8")
    return template.format(customer_msg=customer_msg)


if __name__ == "__main__":
    mcp.run()
