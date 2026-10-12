"""Post 12, section 10: what each of the six techniques removes from the history, with the toy replay set's numbers.

Run from anywhere:  python posts/12-compress-strategies/diagrams/src/03-six-techniques.py
Writes posts/12-compress-strategies/diagrams/03-six-techniques.svg.
The strips are schematic (no sizes are claimed): ten entries of layer 05, oldest left, and what each technique keeps,
replaces or removes, following sections 2 to 7. The two right columns are printed by snippets/retention.py
(measure(): token reduction and IRR pooled over its three conversations) and asserted against the post's table;
semantic chunking and token-level compression need a model and are not run there.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, num  # noqa: E402

POST = Path(__file__).resolve().parents[2]
R = runpy.run_path(str(POST / "snippets" / "retention.py"), run_name="snippet")
MEASURED = {}
for name, technique in R["TECHNIQUES"]:
    before, after, kept, total = R["measure"](technique)
    MEASURED[name] = (f"{1 - after / before:.1%}", f"{kept / total:.0%}")
BEFORE, _, _, N_FACTS = R["measure"](R["TECHNIQUES"][0][1])
assert (BEFORE, N_FACTS) == (19931, 22)
assert MEASURED == {"windowing": ("56.6%", "55%"), "windowing, pinned": ("56.0%", "91%"),
                    "tool-result clearing": ("87.0%", "100%"), "priority pruning": ("88.7%", "73%"),
                    "summarisation": ("87.7%", "95%")}
assert R["WINDOW_TURNS"] == 6 and "windowing to the last six entries" in (POST / "index.md").read_text(encoding="utf-8")
BODY = (POST / "index.md").read_text(encoding="utf-8")
for name, (red, irr) in MEASURED.items():
    assert f"{name:<22} {BEFORE:>7}" in BODY and f"{red:>9}" in BODY and f"{irr:>5}" in BODY, name

# the schematic history: kinds of the ten entries, oldest first; the last three are the recent turns
KINDS = ["first", "msg", "tool", "decision", "msg", "tool", "msg", "tool", "msg", "msg"]
RECENT = {7, 8, 9}
TAG = {"first": "1st", "decision": "dec", "tool": "tool"}
WIDTH = {"msg": 32, "first": 32, "decision": 32, "tool": 72}
X0, GAP, CELL_H = 248, 4, 32
XS = []
x = X0
for k in KINDS:
    XS.append(x)
    x += WIDTH[k] + GAP
STRIP_END = x - GAP

# per technique: what happens to each entry: keep, drop, stub (a cleared tool keeps a note), shrink (token-level),
# or a list of replacement boxes [(label, first index, last index)] over a span that is otherwise removed
ROWS = [
    ("original", {i: "keep" for i in range(10)}, None),
    ("windowing", {i: ("keep" if i >= 4 else "drop") for i in range(10)}, None),
    ("windowing, pinned", {i: ("keep" if i >= 4 or KINDS[i] in ("first", "decision") else "drop") for i in range(10)},
     None),
    ("tool-result clearing", {i: ("stub" if KINDS[i] == "tool" and i not in RECENT else "keep") for i in range(10)},
     None),
    ("priority pruning", {i: ("keep" if i in RECENT or KINDS[i] == "first" else "drop") for i in range(10)}, None),
    ("summarisation", {i: ("keep" if i in RECENT else "span") for i in range(10)}, [("summary", 72)]),
    ("semantic chunking", {i: ("keep" if i in RECENT else "span") for i in range(10)},
     [("topic 1", 64), ("topic 2", 64)]),
    ("token-level", {i: "shrink" for i in range(10)}, None),
]
NOT_RUN = {"semantic chunking", "token-level"}

desc = ("Eight strips of the same schematic ten-entry history of layer 05, oldest left, with the first turn, a "
        "decision and three tool results marked and the last three entries recent. Windowing keeps the last six; "
        "pinned windowing also keeps the first turn and the decision; tool-result clearing replaces the old tool "
        "results with short notes; priority pruning keeps only the first turn and the recent entries; summarisation "
        "replaces the older span with one summary and semantic chunking with two topic summaries; token-level "
        "compression shortens every entry. On the toy replay set of 19,931 tokens and 22 facts, reduction and IRR "
        "are 56.6 and 55, 56.0 and 91, 87.0 and 100, 88.7 and 73, and 87.7 and 95 percent; the last two are not run.")

fig = Figure("03-six-techniques", "Each technique removes a different part of the history", desc,
             subtitle="Strips are schematic. Numbers: the toy replay set of retention.py, with a rule-based summary.",
             height=720, data_w=True)

RX, IX = 832, 912                    # right edges of the reduction and IRR columns
TOP, PITCH = 160, 60
fig.text(X0, 128, "layer 05, oldest entry left", "tick")
fig.text(RX, 128, "reduction", "tick", anchor="end")
fig.text(IX, 128, "IRR", "tick", anchor="end")


def cell(i, y, mode):
    b = Box(XS[i], y, WIDTH[KINDS[i]], CELL_H)
    if mode == "keep":
        fig.fill(b, "history-soft", fit=False)
        fig.outline(b, "history-line")
        if KINDS[i] in TAG:
            fig.text(b.cx, y + 21, TAG[KINDS[i]], "tick", anchor="middle", color="ink")
    elif mode == "drop":
        fig.outline(b, "error", dash="lead")
    elif mode == "stub":
        stub = Box(b.x, y, 16, CELL_H)
        fig.fill(stub, "history-soft", fit=False)
        fig.outline(stub, "history-line")
        fig.outline(Box(b.x + 20, y, b.w - 20, CELL_H), "error", dash="lead")
    elif mode == "shrink":
        keep_w = 4 * round(b.w * 0.6 / 4)
        kept = Box(b.x, y, keep_w, CELL_H)   # the tokens the compressor keeps, unchanged
        fig.fill(kept, "history-soft", fit=False)
        fig.outline(kept, "history-line")
        fig.outline(Box(b.x + keep_w + 4, y, b.w - keep_w - 4, CELL_H), "error", dash="lead")


for r, (name, modes, boxes) in enumerate(ROWS):
    y = TOP + r * PITCH
    fig.text(40, y + 21, name, "head" if r == 0 else "label")
    for i in range(10):
        if modes[i] != "span":
            cell(i, y, modes[i])
    if boxes:
        span = [i for i in range(10) if modes[i] == "span"]
        x, end = XS[span[0]], XS[span[-1]] + WIDTH[KINDS[span[-1]]]
        for label, w in boxes:
            b = Box(x, y, w, CELL_H)
            fig.fill(b, "history", fit=False)
            fig.text(b.cx, y + 21, label, "tick", anchor="middle", color="surface")
            x += w + GAP
        fig.outline(Box(x, y, end - x, CELL_H), "error", dash="lead")
    if r == 0:
        fig.text(IX, y + 21, f"{num(BEFORE)} tokens, {N_FACTS} facts", "label", anchor="end")
    elif name in NOT_RUN:
        fig.text(IX, y + 21, "needs a model; not run", "note", anchor="end")
    else:
        red, irr = MEASURED[name]
        fig.text(RX, y + 21, red, "value", anchor="end")
        fig.text(IX, y + 21, irr, "value", anchor="end")

fig.legend(40, 648, [dict(color="history", label="kept verbatim", mark="outline"),
                     dict(color="history", label="written by a model", mark="swatch"),
                     dict(color="error", label="removed", mark="dashed-outline")], direction="row")
fig.caption("Windowing and pinned windowing remove about the same share and keep 12 and 20 of the 22 facts.")
fig.write()
