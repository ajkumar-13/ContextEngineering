"""Pure refund-eligibility logic, the business rules, with no MCP runtime.

Keeping the logic out of the server file is the point: the rules below are a plain
function you can unit-test offline, while ``server.py`` is a thin MCP wrapper around
them. This is the pattern Post 15 recommends, the protocol is a transport, not the
place your logic should live.
"""
from __future__ import annotations

from dataclasses import dataclass

RETURN_WINDOW_DAYS = 30
MANAGER_APPROVAL_OVER_USD = 1000.0


@dataclass(frozen=True)
class Order:
    order_id: str
    total_usd: float
    days_since_purchase: int
    already_refunded: bool = False


@dataclass(frozen=True)
class Decision:
    eligible: bool
    requires_manager_approval: bool
    reason: str


def check_refund_eligibility(order: Order, amount_usd: float) -> Decision:
    """Decide whether a refund of ``amount_usd`` against ``order`` may proceed.

    Rules (illustrative, a real policy lives in code, not the model, per Post 23):
      - an already-refunded order cannot be refunded again;
      - refunds must be requested within the return window;
      - you cannot refund more than the order total;
      - refunds over the approval threshold need a manager's sign-off.
    """
    if amount_usd <= 0:
        return Decision(False, False, "Refund amount must be positive.")
    if order.already_refunded:
        return Decision(False, False, "Order has already been refunded.")
    if order.days_since_purchase > RETURN_WINDOW_DAYS:
        return Decision(
            False, False,
            f"Outside the {RETURN_WINDOW_DAYS}-day return window "
            f"({order.days_since_purchase} days since purchase).",
        )
    if amount_usd > order.total_usd:
        return Decision(
            False, False,
            f"Requested ${amount_usd:.2f} exceeds order total ${order.total_usd:.2f}.",
        )
    if amount_usd > MANAGER_APPROVAL_OVER_USD:
        return Decision(
            True, True,
            f"Eligible, but ${amount_usd:.2f} is over ${MANAGER_APPROVAL_OVER_USD:.0f} "
            "and needs manager approval.",
        )
    return Decision(True, False, "Eligible for automatic refund.")


REFUND_POLICY = f"""\
Refund policy (demo)
- Window: refunds must be requested within {RETURN_WINDOW_DAYS} days of purchase.
- Amount: may not exceed the order total; an order may be refunded once.
- Approval: refunds over ${MANAGER_APPROVAL_OVER_USD:.0f} require manager sign-off.
"""


# Stands in for the shop's order store: the facts a refund rule checks are looked up, never taken from the model.
DEMO_ORDERS = {
    o.order_id: o
    for o in (
        Order("A-4821", total_usd=120.0, days_since_purchase=6),
        Order("B-1177", total_usd=2400.0, days_since_purchase=3),
        Order("C-0932", total_usd=80.0, days_since_purchase=41),
        Order("D-5510", total_usd=60.0, days_since_purchase=2),
    )
}


def lookup_order(order_id: str) -> Order | None:
    """Return the stored order, or None if the id is unknown."""
    return DEMO_ORDERS.get(order_id)
