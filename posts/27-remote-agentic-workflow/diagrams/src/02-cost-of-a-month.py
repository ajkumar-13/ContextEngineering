"""Post 27, section 6: one month of remote agent work, the server bills against the model bill.

Run from the series root:  uv run python posts/27-remote-agentic-workflow/diagrams/src/02-cost-of-a-month.py
Writes posts/27-remote-agentic-workflow/diagrams/02-cost-of-a-month.svg.

Where every number comes from: snippets/remote_costs.py, imported, its values asserted against what it prints
and what section 6 quotes. Server bars are cited hourly or monthly rates times hours (AWS "Amazon EC2 On-Demand
Pricing", US East (N. Virginia), Linux; Hetzner "Price adjustment", US locations from 15 June 2026; both consulted
October 2026): solid outlines. The model bar rests on illustrative task sizes on cited Claude Opus 4.6 prices
(as of early 2026): dashed outline, and the legend says so.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
M = runpy.run_path(str(POST / "snippets" / "remote_costs.py"), run_name="snippet")
BODY = (POST / "index.md").read_text(encoding="utf-8")

H = M["MONTH_H"]
xl, big = M["EC2"]["c6i.xlarge"][2], M["EC2"]["c6i.4xlarge"][2]
assert (xl, big, M["HETZNER_CPX31"], M["WORK_H"], round(H)) == (0.17, 0.68, 73.49, 176, 730)
r, w, o = M["task_cost"](cache=True)
model = M["TASKS"] * (r + w + o)
ROWS = [  # label, dollars a month, cited (solid) or illustrative (dashed)
    ("c6i.4xlarge, all month", big * H, True),
    ("Model, 88 tasks", model, False),
    ("c6i.xlarge, all month", xl * H, True),
    ("Hetzner CPX31", M["HETZNER_CPX31"], True),
    ("c6i.xlarge, working hours", xl * M["WORK_H"], True),
]
assert [f"{v:.2f}" for _, v, _ in ROWS] == ["496.40", "443.52", "124.10", "73.49", "29.92"]
assert M["TASKS"] == 88
for phrase in ("496.40", "443.52", "124.10", "73.49", "29.92", "The figure below sets the month side by side."):
    assert phrase in BODY, phrase

desc = ("Five horizontal bars of dollars per month on one axis from 0 to 500. Solid, from cited rates: a "
        "c6i.4xlarge left running all month, 496.40; a c6i.xlarge all month, 124.10; a Hetzner CPX31, 73.49; a "
        "c6i.xlarge stopped outside 176 working hours, 29.92. Dashed, from illustrative task sizes: the model "
        "bill for 88 thirty-minute tasks on Claude Opus 4.6 with caching, 443.52.")
fig = Figure("02-cost-of-a-month", "The model bill outweighs a right-sized server", desc,
             subtitle="Dollars a month: EC2 US East and Hetzner US rates, October 2026; Claude Opus 4.6 as of "
                      "early 2026.",
             data_w=True)

X0, X1, HI = 256, 840, 500
SCALE = (X1 - X0) / HI
Y0, STEP, BAR_H = 160, 52, 32
fig.legend(40, 128, [dict(color="ink", label="cited rate times hours", mark="outline"),
                     dict(color="ink", label="illustrative task sizes", mark="dashed-outline", dash="proj")],
           direction="row")

AXIS_Y = Y0 + len(ROWS) * STEP - 8
for t in range(0, HI + 1, 100):
    x = X0 + t * SCALE
    if t:
        fig.edge((x, Y0 - 8), (x, AXIS_Y), color="grid", width=0.75)
    fig.text(x, AXIS_Y + 20, f"{t}", "tick", anchor="middle")
fig.edge((X0, Y0 - 8), (X0, AXIS_Y), color="rule")
fig.edge((X0, AXIS_Y), (X1, AXIS_Y), color="rule")
fig.text((X0 + X1) // 2, AXIS_Y + 44, "dollars a month", "note", anchor="middle")

for k, (label, v, cited) in enumerate(ROWS):
    y = Y0 + k * STEP
    fig.text(40, y + 21, label, "label")
    with fig.data():
        bar = Box(X0, y, v * SCALE, BAR_H)
        fig.fill(bar, "neutral-soft", fit=False)
        fig.outline(bar, "ink", width=1.5, dash=None if cited else "proj")
        fig.text(bar.right + 12, y + 21, f"{v:.2f}", "value", snap=False)

fig.caption("Only a large instance left running rivals the model; the right-sized box is a fraction of it.")
fig.write()
