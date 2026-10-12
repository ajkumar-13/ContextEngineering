"""Post 07 hero: the four operations on the two axes, with one canonical technique and the move each one makes.

Run from anywhere:  python posts/07-write-select-compress-isolate/diagrams/src/01-wsci-quadrants.py
Writes posts/07-write-select-compress-isolate/diagrams/01-wsci-quadrants.svg.
No numbers are drawn. The axes, the cell of each operation and its canonical technique are section 1 of
index.md (and the WSCI table of the notation guide, Section 3); the phrases that state them are asserted below.
The operations are neutral (ctx_fig_design.md, Section 0): no layer hue appears, because no layer is drawn.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in (
    "| **One window** | **Select:** pull the right items in for this call | **Compress:** shrink what is already inside |",
    "| **Several windows** | **Isolate:** give a sub-task a fresh window of its own | "
    "**Write:** move information to a store that later windows can read |",
    "| | **Into a window** | **Out of the window** |",
    "(retrieve, rerank, pack)", "a rolling summary", "Each sub-task runs in its own window",
    "a memory store", "**Scratchpads and plan files:**",
    "Write parks information in a store (a file, a database, an index) that a later call or session can read.",
    "only the result comes back into the parent's window",
):
    assert phrase in BODY, phrase

COLS = ["Into a window", "Out of the window"]
ROWS = [("One", "window"), ("Several", "windows")]
# (row, col): operation, canonical technique, glyph kind
CELLS = {
    (0, 0): ("Select", "retrieve, rerank, pack", "select"),
    (0, 1): ("Compress", "rolling summary", "compress"),
    (1, 0): ("Isolate", "sub-agents, one window each", "isolate"),
    (1, 1): ("Write", "memory store, scratchpad", "write"),
}

desc = ("A two-by-two grid of the four operations on a context window. The columns are the direction: into a "
        "window, out of the window. The rows are the scope: one window, several windows. ")
for (r, c), (op, tech, _) in sorted(CELLS.items()):
    desc += f"{op} sits at {COLS[c].lower()} and {' '.join(ROWS[r]).lower()}; canonical technique: {tech}. "
desc += ("Each cell carries a small picture of its move, the item that moves drawn darker: select carries one item from a store into the window; "
         "compress shrinks four blocks in a window to one; isolate hands work from a parent window to two "
         "sub-agent windows; write carries an item from the window to a store that a later call reads.")

fig = Figure("01-wsci-quadrants", "Four operations, one cell each", desc,
             subtitle="Direction: into a window or out of one. Scope: inside one window, or across several.",
             data_w=True)

LBL_X = 40
CELL_X = [176, 556]
CELL_W = 364
CELL_Y = [136, 312]
CELL_H = 164
for c, name in enumerate(COLS):
    fig.text(CELL_X[c] + CELL_W / 2, 124, name, "head", anchor="middle")
for r, (a, b) in enumerate(ROWS):
    fig.text(LBL_X, CELL_Y[r] + 76, a, "head")
    fig.text(LBL_X, CELL_Y[r] + 100, b, "head")


def window(x, y, w=72, h=64, blocks=0, label=None, mark=None):
    box = Box(x, y, w, h)
    fig.fill(box, "surface", radius=6, fit=False)
    fig.outline(box, "ink-muted", width=1.5, radius=6)
    for i in range(blocks):
        fig.fill(Box(x + 12, y + 12 + 12 * i, w - 24, 8), "ink-muted" if i == mark else "rule", fit=False)
    if label:
        fig.text(box.cx, y + h + 20, label, "tick", anchor="middle")
    return box


def store(x, y, blocks, label="store", mark=None):
    box = Box(x, y, 72, 64)
    fig.fill(box, "neutral-soft", radius=8, fit=False)
    fig.outline(box, "rule", radius=8)
    for i in range(blocks):
        fig.fill(Box(x + 12, y + 12 + 12 * i, 48, 8), "ink-muted" if i == mark else "rule", fit=False)
    fig.text(box.cx, y + 84, label, "tick", anchor="middle")
    return box


for (r, c), (op, tech, kind) in CELLS.items():
    x0, y0 = CELL_X[c], CELL_Y[r]
    cell = Box(x0, y0, CELL_W, CELL_H)
    fig.fill(cell, "neutral-soft", radius=8, fit=False)
    fig.outline(cell, "border", radius=8)
    fig.text(x0 + 16, y0 + 28, op, "head")
    fig.text(x0 + 16, y0 + 52, tech, "note")
    gy = y0 + 68
    if kind == "select":
        s = store(x0 + 64, gy, 4, mark=2)
        w = window(x0 + 228, gy, blocks=1, label="window", mark=0)
        fig.arrow((s.right + 8, s.cy), (w.x - 8, w.cy))
    elif kind == "compress":
        a = window(x0 + 64, gy, blocks=4, label="before")
        b = window(x0 + 228, gy, blocks=1, label="after")
        fig.arrow((a.right + 8, a.cy), (b.x - 8, b.cy))
    elif kind == "isolate":
        p = window(x0 + 48, gy, blocks=2, label="parent")
        for i in range(2):
            ch = window(x0 + 196, gy + 36 * i, h=28, blocks=1)
            fig.arrow((p.right + 8, p.y + 20 + 24 * i), (ch.x - 8, ch.cy))
        fig.text(x0 + 280, gy + 36, "sub-agents", "tick")
    else:
        w = window(x0 + 32, gy, blocks=3, label="window", mark=2)
        s = store(x0 + 160, gy, 1, mark=0)
        later = window(x0 + 280, gy, w=64, blocks=1, label="later call", mark=0)
        fig.arrow((w.right + 8, w.cy), (s.x - 8, s.cy))
        fig.arrow((s.right + 8, s.cy), (later.x - 8, later.cy), dash="proj")

fig.caption("The technique in each cell is the canonical one; posts 08, 09, 12 and 13 cover the rest.")
fig.write()
