"""Post 29, section 5: the permission boundary on issue_refund, and what the tool returns for three calls.

Run from the series root (the companion needs the MCP SDK, which the series environment does not install):
    uv run --no-project --with "mcp==2.3.0" --with pydantic python posts/29-build-mcp-server/diagrams/src/02-permission-boundary.py
Writes posts/29-build-mcp-server/diagrams/02-permission-boundary.svg.
Every result in the table is computed by calling the companion's issue_refund (code/29-mcp-server-full/server.py)
and asserted against the body; the order total (12,000) is read from its data/orders.json and the threshold
(1,000) from REFUND_THRESHOLD. The four steps are section 5's: the host's approval is the specification's "human in
the loop" and the hosts' documentation as the body quotes them. The boundary in code is the emphasised card.
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
COMP = POST.parents[1] / "code" / "29-mcp-server-full"
BODY = (POST / "index.md").read_text(encoding="utf-8")
sys.path.insert(0, str(COMP))
import server  # noqa: E402

ORDERS = {o["id"]: o for o in json.loads((COMP / "data" / "orders.json").read_text(encoding="utf-8"))}
TOTAL = ORDERS["ORD-9004"]["total"]
assert TOTAL == 12000 and ORDERS["ORD-9001"]["total"] == 1499 and server.REFUND_THRESHOLD == 1000

CALLS = [("ORD-9001", 50), ("ORD-9004", 1500), ("ORD-9001", 1500)]
rows = []
for order_id, amount in CALLS:
    r = server.issue_refund(order_id=order_id, amount=amount, reason="customer cancelled")
    if r.ok:
        result, stop = f"ok, refund {r.refund_id}", "passes both checks"
    elif r.requires_confirmation:
        result, stop = "requires_confirmation: true", "the threshold"
    else:
        result, stop = r.reason, "the order total"
    rows.append((order_id, f"{amount:,}", result, stop))
assert rows == [("ORD-9001", "50", "ok, refund RF-9001-50", "passes both checks"),
                ("ORD-9004", "1,500", "requires_confirmation: true", "the threshold"),
                ("ORD-9001", "1,500", "amount_exceeds_order_total", "the order total")], rows
for phrase in ("ORD-9001 for 50 gives refund RF-9001-50",
               "ORD-9004 for 1,500 gives requires_confirmation true at the threshold",
               "ORD-9001 for 1,500 gives amount_exceeds_order_total at the order total",
               "1,500 is under the order's total of 12,000 but over the threshold",
               '"SHOULD always be a human in the loop with the ability to deny tool invocations"',
               "The agent calls `escalate_to_human`, and the manager queue"):
    assert phrase in BODY, phrase

desc = ("Four step cards joined by arrows. 1, the model proposes issue_refund for ORD-9004 with an amount of 1,500 "
        "dollars. 2, the host asks the user to approve or deny the call. 3, emphasised, the server checks in code "
        "whether the amount exceeds the order total of 12,000 (no) and the threshold of 1,000 (yes). 4, a person in "
        "the manager queue decides, after escalate_to_human. Below, a table of three calls computed with the "
        "companion and the check that stopped each: ORD-9001 for 50 returns ok with refund RF-9001-50, passing both "
        "checks; ORD-9004 for 1,500 returns requires_confirmation true, stopped at the threshold; ORD-9001 for "
        "1,500, whose total is 1,499, returns amount_exceeds_order_total, stopped at the order total.")
fig = Figure("02-permission-boundary", "The model proposes; code decides", desc,
             subtitle="The refund path of the companion acme-support; the table is what issue_refund returns.",
             data_w=True)

cols = [Box(40 + 228 * i, 120, 196, 160) for i in range(4)]  # four equal cards, 32 apart, filling 880
STEPS = [("1  Model proposes", [("code", "issue_refund("), ("code", '"ORD-9004", 1500)')]),
         ("2  Host asks", [("label", "the user approves"), ("label", "or denies the call")]),
         ("3  Server checks", [("code", "1500 > total?"), ("label", f"no, total {int(TOTAL):,}"),
                               ("code", "1500 > 1000?"), ("label", "yes: confirm")]),
         ("4  A person decides", [("code", "escalate_to_human"), ("label", "the manager queue"),
                                  ("label", "approves or refuses")])]
for i, (col, (heading, lines)) in enumerate(zip(cols, STEPS)):
    fig.fill(col, "surface" if i == 2 else "neutral-soft", radius=8, fit=False)
    if i == 2:
        fig.outline(col, "ink", width=2.5, radius=8)
    else:
        fig.outline(col, "border", radius=8)
    fig.text(col.x + 16, col.y + 28, heading, "head")
    for j, (style, s) in enumerate(lines):
        fig.text(col.x + 16, col.y + 60 + 24 * j, s, style)
fig.chain(cols)

fig.text(40, 328, "What issue_refund returns", "head")
table = [["order", "amount, dollars", "result", "stopped at"]] + [list(r) for r in rows]
fig.table(40, 344, table, [144, 160, 320, 256], col_align=["start", "end", "start", "start"])

fig.caption("Only the third card holds when the others fail: it runs on every call, whatever was proposed.")
fig.write()
