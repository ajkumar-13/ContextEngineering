import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import (  # noqa: E402
    REFUND_THRESHOLD,
    escalate_to_human,
    issue_refund,
    search_orders,
)


def test_search_by_email():
    r = search_orders(email="alex@example.com")
    assert r.count >= 1
    assert all(m["email"].lower() == "alex@example.com" for m in r.matches)


def test_search_requires_some_input():
    try:
        search_orders()
    except ValueError:
        return
    assert False, "expected ValueError"


def test_refund_under_threshold():
    r = issue_refund(order_id="ORD-9001", amount=50, reason="duplicate charge")
    assert r.ok is True and r.refund_id is not None


def test_refund_over_threshold_requires_confirmation():
    r = issue_refund(
        order_id="ORD-9004",
        amount=REFUND_THRESHOLD + 1,
        reason="customer cancelled",
    )
    assert r.requires_confirmation and not r.ok


def test_refund_unknown_order():
    r = issue_refund(order_id="ORD-DOES-NOT-EXIST", amount=10, reason="test")
    assert not r.ok and r.reason == "order_not_found"


def test_escalate_validates_queue():
    try:
        escalate_to_human(summary="enough characters here", queue="bogus")
    except Exception:
        return
    assert False, "expected validation error"
