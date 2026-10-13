"""Post 15: the refund rule of the MCP quickstart, enforced in code whatever the model asks.

Run from the series root:  uv run python posts/15-tools-and-mcp/snippets/refund_gate.py
It imports mcp_quickstart.refunds from code/15-mcp-quickstart/src, the pure module behind the
companion's check_refund tool. It needs neither the mcp SDK nor a network: the server is not started.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code" / "15-mcp-quickstart" / "src"))
from mcp_quickstart.refunds import Order, check_refund_eligibility  # noqa: E402

REQUESTS = [  # (order, amount the model asks to refund)
    (Order("A-4821", total_usd=120.0, days_since_purchase=6), 120.0),
    (Order("B-1177", total_usd=2400.0, days_since_purchase=3), 1500.0),
    (Order("C-0932", total_usd=80.0, days_since_purchase=41), 80.0),
    (Order("D-5510", total_usd=60.0, days_since_purchase=2), 95.0),
]

if __name__ == "__main__":
    for order, amount in REQUESTS:
        d = check_refund_eligibility(order, amount)
        flags = f"eligible={d.eligible}, manager={d.requires_manager_approval}"
        print(f"{order.order_id}  {amount:8.2f}  {flags:30s} {d.reason}")
