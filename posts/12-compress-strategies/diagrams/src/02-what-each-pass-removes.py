"""Post 12, section 9: what the soft pass and the summary each remove from the input.

Run from anywhere:  python posts/12-compress-strategies/diagrams/src/02-what-each-pass-removes.py
Writes posts/12-compress-strategies/diagrams/02-what-each-pass-removes.svg.
Every bar is computed by snippets/compaction_policy.py: run("two-trigger", trace) records, for each turn with an
event, the input split into layers 01-02, layers 03-04, the messages, notes and summary of layer 05, and the
tool results of layer 05 still kept verbatim, before and after the pass. Sizes are the snippet's illustrative
constants; the percentages the post states are asserted.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, num  # noqa: E402

POST = Path(__file__).resolve().parents[2]
M = runpy.run_path(str(POST / "snippets" / "compaction_policy.py"), run_name="snippet")
BUDGET = M["BUDGET"]
trace = []
M["run"]("two-trigger", trace)
EVENTS = {t: (before, after) for t, before, after in trace}
S25, S98 = EVENTS[25], EVENTS[98]
assert S25 == ((4600, 3700, 35000, 104000), (4600, 3700, 35600, 62400))
assert S98 == ((4600, 3700, 142840, 20000), (4600, 3700, 7200, 16500))
pct = lambda split: 100 * sum(split) / BUDGET  # noqa: E731
assert [f"{pct(s):.1f}" for s in (*S25, *S98)] == ["81.8", "59.1", "95.1", "17.8"]
BODY = (POST / "index.md").read_text(encoding="utf-8")
for phrase in ("At turn 25 the soft pass cuts the input from 81.8 to 59.1 percent",
               "At turn 98 the summary cuts it from 95.1 to 17.8 percent"):
    assert phrase in BODY, phrase

ROWS = [("before", S25[0]), ("after", S25[1]), ("before", S98[0]), ("after", S98[1])]
GROUPS = [("Turn 25: the soft pass clears old tool results", 0), ("Turn 98: the summary", 2)]
SEG = [("stable", "solid"), ("turn", "solid"), ("history", "solid"), ("history", "soft")]

desc = ("Four stacked bars of the input, in percent of the 180,000-token budget, with dotted lines at 60, 80 and 95 "
        "percent. Each bar is split into layers 01 and 02 (4,600 tokens), layers 03 and 04 (3,700), the messages, "
        "notes and summary of layer 05, and the tool results of layer 05 kept verbatim. At turn 25 the soft pass "
        "takes the input from 81.8 percent (35,000 and 104,000 tokens in layer 05) to 59.1 percent (35,600 and "
        "62,400), replacing old tool results with notes. At turn 98 the summary takes it from 95.1 percent (142,840 "
        "and 20,000) to 17.8 percent (7,200 and 16,500).")

fig = Figure("02-what-each-pass-removes", "The soft pass removes tool bodies; the summary, the rest", desc,
             subtitle="The two-trigger run of the section 9 simulation; illustrative sizes, percent of a "
                      "180,000-token input budget.", data_w=True)

LX, X0, W = 40, 136, 680                 # label column, bar start, bar width for 100 percent
sx = lambda p: X0 + W * p / 100          # noqa: E731
BAR_H = 40
ROW_Y = [172, 228, 324, 380]             # bar tops
TOP, BOTTOM = 124, 432                   # tick baseline, bottom of the reference lines
VX = 872                                 # the column of shares

for heading, first in GROUPS:
    fig.text(LX, ROW_Y[first] - 16, heading, "head")

with fig.data():
    for p in (60, 80, 95):
        fig.edge((sx(p), TOP + 8), (sx(p), BOTTOM), color="ink-muted", dash="ref")
    for (label, split), y in zip(ROWS, ROW_Y):
        acc = 0.0
        for v, (color, form) in zip(split, SEG):
            b = Box(sx(100 * acc / BUDGET), y, W * v / BUDGET, BAR_H)
            if form == "solid":
                fig.fill(b, color, fit=False)
            else:
                fig.fill(b, color + "-soft", fit=False)
                fig.outline(b, color + "-line")
            # the two layer 05 segments carry their token counts when the number fits inside
            if color == "history" and b.w >= 64:
                fig.text(b.cx, y + 25, num(v), "value", anchor="middle",
                         color="surface" if form == "solid" else "ink")
            acc += v
        fig.text(VX + 48, y + 25, f"{pct(split):.1f}%", "value", anchor="end")

for p in (60, 80, 95):
    fig.text(sx(p), TOP, f"{p}%", "tick", anchor="middle")
for (label, _), y in zip(ROWS, ROW_Y):
    fig.text(LX, y + 25, label, "label")
fig.text(VX + 48, TOP, "of budget", "tick", anchor="end")

fig.legend(40, 464, [dict(color="stable", label="01 to 02 stable prefix", mark="swatch"),
                     dict(color="turn", label="03 to 04 per-turn", mark="swatch"),
                     dict(color="history", label="05 messages, notes, summary", mark="swatch"),
                     dict(color="history", label="05 tool results, verbatim", mark="outline")],
           direction="row")
fig.caption("Inside the bars: tokens of the two layer 05 parts. Right: the whole input as a share of the budget.")
fig.write()
