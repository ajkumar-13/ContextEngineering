"""Post 06 hero: the five failure modes, the layers each one starts in, and the first fix of each.

Run from anywhere:  python posts/06-context-failure-modes/diagrams/src/01-failure-modes-grid.py
Writes posts/06-context-failure-modes/diagrams/01-failure-modes-grid.svg.
No numbers are drawn. The layer of every cell and every first fix are sections 2 to 6 of index.md; the phrases
that state them are asserted below, so the figure cannot drift from the text. The layer names and the lifetime
hues are post 02's (notation guide, Section 1); the mode names are the fixed vocabulary (notation guide, Section 4).
"""
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, text_width  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")

LAYERS = {1: ("System", "prompt"), 2: ("Tools and", "MCP", "descriptions"), 3: ("Memory and", "state"),
          4: ("Retrieved", "chunks"), 5: ("Conversation", "history"), 6: ("User", "instruction")}
ROLE = {1: "stable", 2: "stable", 3: "turn", 4: "turn", 5: "history", 6: "user"}

# mode: ({layer: word}, first fix in two lines, the sentences of index.md that state both)
MODES = [
    ("Distraction", {4: "starts", 1: "also", 5: "also"}, ("lower top-k,", "add a reranker"),
     ["Distraction starts in layer 04, retrieved chunks, or in layer 01, the system prompt.",
      "Layer 05, conversation history, can distract too",
      "Lower top-k, the number of chunks packed into the window. Add a reranker"]),
    ("Confusion", {1: "starts", 2: "starts"}, ("explicit, motivated,", "exemplified rules"),
     ["Confusion is the failure mode of layer 01, the system prompt, and layer 02, tools and MCP descriptions",
      "Make the rules explicit, motivated and exemplified."]),
    ("Conflict", {1: "a side", 3: "a side", 4: "a side", 5: "a side"}, ("provenance stamp,", "precedence rule"),
     ["A semantic memory in layer 03 says", "a chunk retrieved into layer 04",
      "Layer 01, the system prompt, forbids an action; an episodic memory note in layer 03",
      "The model's own earlier turns in layer 05 can be one side of the disagreement.",
      "(a provenance and recency stamp). Add an explicit precedence rule"]),
    ("Lost-in-the-middle", {4: "starts", 5: "starts", 6: "also"}, ("bookend packing;", "summarise old history"),
     ["when layer 04, retrieved chunks, or layer 05, conversation history, grows long",
      "Layer 06, the user instruction, is involved too",
      "**First fix.** Bookend packing.", "summarise older turns into a short brief"]),
    ("Tool-storm", {2: "starts", 1: "also"}, ("trim the catalogue,", "cap the loop"),
     ["Tool-storm is the failure mode of layer 02, tools and MCP descriptions, with layer 01, the system prompt, "
      "sharing the blame", "Trim the catalogue to the tools this conversation needs",
      "Add a budget rule to the system prompt"]),
]
for _, _, _, phrases in MODES:
    for p in phrases:
        assert p in BODY, p
assert "Conflict is the cross-layer failure mode: two parts of the window disagree" in BODY

KEY = {"starts": "the layer the mode begins in", "also": "a layer that shares it",
       "a side": "one of two parts that disagree"}

desc = ("A grid with one row per failure mode, one column per layer from 01 System prompt to 06 User instruction, "
        "and a last column for the first fix. ")
for mode, cells, fix, _ in MODES:
    parts = [f"{w} in {k:02d}" for k, w in sorted(cells.items())]
    desc += f"{mode}: {', '.join(parts)}; first fix: {' '.join(fix)}. "
desc += "Key: " + "; ".join(f"{k}, {v}" for k, v in KEY.items()) + "."

fig = Figure("01-failure-modes-grid", "Each failure mode starts in a few layers", desc,
             subtitle="The five modes of this post, the layers each one starts in, and the first fix to try.",
             height=720, data_w=True)

MODE_X, MODE_W = 40, 168
COL_X, COL_W = MODE_X + MODE_W, 88          # six layer columns
FIX_X = COL_X + 6 * COL_W + 16              # the first-fix column
HEAD_Y, ROW_Y, ROW_H = 112, 216, 80         # header top, first row top, row height
col_x = {k: COL_X + (k - 1) * COL_W for k in LAYERS}

# header: the layer number in its lifetime hue, the name under it; "Mode" and "First fix" on the number line
fig.text(MODE_X, HEAD_Y + 24, "Mode", "head")
fig.text(FIX_X, HEAD_Y + 24, "First fix", "head")
for k, lines in LAYERS.items():
    cx = col_x[k] + COL_W / 2
    fig.text(cx, HEAD_Y + 24, f"{k:02d}", "head", anchor="middle", color=f"{ROLE[k]}-ink")
    for i, line in enumerate(lines):
        fig.text(cx, HEAD_Y + 48 + 20 * i, line, "tick", anchor="middle", color="ink")

for r, (mode, cells, fix, _) in enumerate(MODES):
    top = ROW_Y + r * ROW_H
    fig.text(MODE_X, top + 44, mode, "head")
    for k in LAYERS:
        cell = Box(col_x[k] + 4, top + 8, COL_W - 8, ROW_H - 16)
        if k in cells:
            fig.fill(cell, f"{ROLE[k]}-soft", radius=6, fit=False)
            fig.outline(cell, f"{ROLE[k]}-line", radius=6)
            fig.text(cell.cx, top + 44, cells[k], "label", anchor="middle")
    fig.text(FIX_X, top + 32, fix[0], "label")
    fig.text(FIX_X, top + 56, fix[1], "label")

# the key, one line per word
ky = ROW_Y + len(MODES) * ROW_H + 32
x = MODE_X
for word, meaning in KEY.items():
    fig.text(x, ky, word, "label", bold=True)
    x += 8 * math.ceil((text_width(word, 14, weight=600) + 8) / 8)
    fig.text(x, ky, meaning, "note")
    x += 8 * math.ceil((text_width(meaning, 14, weight=400) + 32) / 8)

fig.caption("Conflict is the one mode that needs two parts of the window to disagree.")
fig.write()
