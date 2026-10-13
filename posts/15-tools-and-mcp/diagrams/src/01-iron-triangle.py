"""Post 15, section 2: the iron triangle of a tool catalogue, with the price of each pair.

Run from anywhere:  uv run python posts/15-tools-and-mcp/diagrams/src/01-iron-triangle.py
Writes posts/15-tools-and-mcp/diagrams/01-iron-triangle.svg.
No numbers are drawn. The three goods (a large catalogue, rich descriptions, no selection step), the price of
each pair and the failure of wanting all three are section 2's sentences, asserted below; the failure names are
post 06's. The failure in the middle takes the error role; everything else is neutral.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("A design gets any two of a large catalogue, rich descriptions and no selection machinery",
               "*Large catalogue and rich descriptions, no selection*: layer 02 outgrows its budget and the tool-storm",
               "*Large catalogue, no selection, descriptions cut to fit*: the model chooses from one-line summaries, "
               "the confusion of post 06",
               "*Rich descriptions, no selection, a small catalogue*: the comfort zone",
               "Keeping a large catalogue and rich descriptions means paying for the third vertex: a selection "
               "pipeline, a retrieval step per turn, and a cache decision"):
    assert phrase in BODY, phrase

desc = ("A triangle of three goods: no selection step at the top, a large catalogue at the bottom left, rich "
        "descriptions at the bottom right. Each side is a pair a design can keep, with its price. No selection "
        "and a large catalogue: descriptions are cut to fit, and the model is confused. No selection and rich "
        "descriptions: the catalogue stays small, the comfort zone. A large catalogue and rich descriptions: pay "
        "for runtime selection, a pipeline, a retrieval step per turn and a cache decision. In the middle, in red, "
        "wanting all three: layer 02 overflows and tool-storm follows.")
fig = Figure("01-iron-triangle", "A tool catalogue keeps two of three goods", desc,
             subtitle="Catalogue size, description quality, runtime selection: each side is a pair and its price.",
             height=540, data_w=True)

VW, VH = 208, 48
top = Box(480 - VW // 2, 112, VW, VH)
left = Box(96, 400, VW, VH)
right = Box(656, 400, VW, VH)
fig.edge(top.anchor("bottom"), (left.cx, left.y), color="rule", width=1.5)
fig.edge(top.anchor("bottom"), (right.cx, right.y), color="rule", width=1.5)
fig.edge(left.anchor("right"), right.anchor("left"), color="rule", width=1.5)
for b, name in ((top, "No selection step"), (left, "Large catalogue"), (right, "Rich descriptions")):
    fig.fill(b, "surface", radius=8, fit=False)
    fig.outline(b, "ink-muted", width=1.5, radius=8)
    fig.text(b.cx, b.y + 30, name, "head", anchor="middle")

# the sides: each pair and its price
fig.text(304, 272, "Descriptions cut to fit", "head", anchor="end")
fig.text(304, 296, "one-line summaries: confusion", "note", anchor="end")
fig.text(656, 272, "Catalogue kept small", "head")
fig.text(656, 296, "the comfort zone, until it is not", "note")
fig.text(480, 480, "Keep both: pay for runtime selection", "head", anchor="middle")
fig.text(480, 504, "a pipeline, a retrieval step per turn, a cache decision", "note", anchor="middle")

# the middle: wanting all three
mid = Box(360, 312, 240, 64)
fig.fill(mid, "error-soft", radius=8, fit=False)
fig.outline(mid, "error-line", radius=8)
fig.text(mid.cx, mid.y + 26, "All three at once", "head", anchor="middle")
fig.text(mid.cx, mid.y + 50, "layer 02 overflows: tool-storm", "note", anchor="middle")

fig.write()
