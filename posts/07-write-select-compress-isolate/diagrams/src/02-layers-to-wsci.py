"""Post 07, section 7: each of the six layers against the four operations, main and also.

Run from anywhere:  python posts/07-write-select-compress-isolate/diagrams/src/02-layers-to-wsci.py
Writes posts/07-write-select-compress-isolate/diagrams/02-layers-to-wsci.svg.
No numbers are drawn. Every cell is read from the layer table of section 7 of index.md (the Main operation and
Also columns), so the figure cannot drift from the text. The layer names and the lifetime hues are post 02's
(notation guide, Sections 1 and 2); the operations are neutral words in the WSCI order.
"""
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, text_width  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")

OPS = ["write", "select", "compress", "isolate"]
LAYERS = {1: "System prompt", 2: "Tools and MCP descriptions", 3: "Memory and state", 4: "Retrieved chunks",
          5: "Conversation history", 6: "User instruction"}
ROLE = {1: "stable", 2: "stable", 3: "turn", 4: "turn", 5: "history", 6: "user"}

# read the section 7 table: | Layer | Main operation | Also | How it shows up |
sec = BODY.split("## 7. ")[1].split("\n## ")[0]
rows = [l for l in sec.splitlines() if l.startswith("| 0")]
assert len(rows) == 6, rows
CELLS = {}
for line in rows:
    layer, main, also, _ = [c.strip() for c in line.strip("|").split("|")]
    k = int(layer[:2])
    assert layer == f"{k:02d} {LAYERS[k]}", layer
    cells = {}
    for word, col in (("main", main), ("also", also)):
        if col != "none":
            for op in col.split(", "):
                assert op in OPS, op
                cells[op] = word
    CELLS[k] = cells
assert CELLS[6] == {}
assert all(len(c) < 4 for c in CELLS.values())          # no layer needs all four
for phrase in ("First, no layer needs all four operations.",
               "layers 03 and 04 are each written before they are selected",
               "The trigger: placed last, never compressed."):
    assert phrase in BODY, phrase

KEY = {"main": "the operation that does most of the work", "also": "one that reaches what main cannot"}

desc = "A grid with one row per layer, from 01 System prompt to 06 User instruction, and one column per operation: "
desc += "write, select, compress, isolate. "
for k, cells in CELLS.items():
    parts = [f"{w} {op}" for op in OPS for w in [cells.get(op)] if w]
    desc += f"{k:02d} {LAYERS[k]}: {', '.join(parts) if parts else 'no operation, it is the trigger'}. "
desc += "Key: " + "; ".join(f"{k}, {v}" for k, v in KEY.items()) + "."

fig = Figure("02-layers-to-wsci", "Five layers have a main operation, and none needs all four", desc,
             subtitle="The six layers of post 02 against write, select, compress and isolate.",
             height=720, data_w=True)

LAYER_X, NUM_W = 40, 40
COL_X, COL_W = 336, 144
HEAD_Y, ROW_Y, ROW_H = 120, 152, 72
col_x = {op: COL_X + i * COL_W for i, op in enumerate(OPS)}

fig.text(LAYER_X, HEAD_Y + 12, "Layer", "head")
for op in OPS:
    fig.text(col_x[op] + COL_W / 2, HEAD_Y + 12, op.capitalize(), "head", anchor="middle")

for r, k in enumerate(LAYERS):
    top = ROW_Y + r * ROW_H
    fig.text(LAYER_X, top + 42, f"{k:02d}", "head", color=f"{ROLE[k]}-ink")
    fig.text(LAYER_X + NUM_W, top + 42, LAYERS[k], "head")
    if not CELLS[k]:
        fig.text(COL_X + 16, top + 42, "none: the trigger, placed last and never compressed", "note")
    for op, word in CELLS[k].items():
        cell = Box(col_x[op] + 4, top + 8, COL_W - 8, ROW_H - 16)
        fig.fill(cell, f"{ROLE[k]}-soft", radius=6, fit=False)
        fig.outline(cell, f"{ROLE[k]}-line", radius=6, dash=None if word == "main" else "lead")
        fig.text(cell.cx, top + 42, word, "label", anchor="middle", bold=(word == "main"))

ky = ROW_Y + 6 * ROW_H + 40
x = LAYER_X
for word, meaning in KEY.items():
    sw = Box(x, ky - 16, 48, 24)
    fig.fill(sw, "neutral-soft", radius=6, fit=False)
    fig.outline(sw, "rule", radius=6, dash=None if word == "main" else "lead")
    fig.text(sw.cx, ky + 1, word, "label", anchor="middle", bold=(word == "main"))
    x += 64
    fig.text(x, ky, meaning, "note")
    x += 8 * math.ceil((text_width(meaning, 14, weight=400) + 40) / 8)

fig.caption("Layers 03 and 04 need two operations in sequence: an item is written before it can be selected.")
fig.write()
