"""Post 22, figure 3 (section 5): the four bug shapes as a trace shows them, what the prompt shows, and the fix.

Run from the series root:  uv run python posts/22-observability/diagrams/src/03-bug-shapes.py
Writes posts/22-observability/diagrams/03-bug-shapes.svg.

Where every word comes from: section 5 of index.md. The script reads the body and asserts that each shape's
name, layer and fix appear in it; the layer names are notation_guide.md's, in the role colour of their
lifetime class (ctx_fig_design.md Section 0). The fixes follow post 06's table (tool-storm: select, isolate)
and posts 09 and 12. The only number, fifteen calls, is the body's illustrative example.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, rich, span  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")

# shape, trace shows, (layer, role, prompt shows), (operation or gate, fix)
ROWS = [
    ("Context bloat", "input tokens climb", ("05 Conversation history", "history", "old tool results kept"),
     ("compress", "clear tool results")),
    ("Buried evidence", "right chunk, wrong answer", ("04 Retrieved chunks", "turn", "best chunk in the middle"),
     ("select", "bookend packing")),
    ("Tool-storm", "15 calls to one tool", ("02 Tools and MCP descriptions", "stable", "overlap, no stop rule"),
     ("select, isolate", "trim the catalogue, add a budget")),
    ("Silent regression", "cost and quality fall", ("01 System prompt", "stable", "lost a relied-on line"),
     ("replay gate", "restore the line, add a fixture")),
]
for phrase in ["**Shape 1: context bloat.**", "**Shape 2: buried evidence.**", "**Shape 3: tool-storm.**",
               "**Shape 4: silent regression.**", "layer 05, conversation history", "layer 04, retrieved chunks",
               "layer 02, tools and MCP (Model Context Protocol) descriptions", "layer 01, the system prompt", "tool-result clearing",
               "bookend packing", "first fixes are select and isolate", "fifteen calls in one turn",
               "restore the line and add a fixture", "add a budget rule"]:
    assert phrase in BODY, phrase

fig = Figure(
    "03-bug-shapes", "Four bug shapes, and where each fix lives",
    "A four-row table with columns shape, in the trace, in the prompt, and fix. Context bloat: input tokens "
    "climb; layer 05 conversation history keeps old tool results; compress by clearing tool results. Buried "
    "evidence: the right chunk retrieved but a wrong answer; layer 04 retrieved chunks has the best chunk in the "
    "middle; select by bookend packing. Tool-storm: 15 calls to one tool; layer 02 tools and MCP descriptions "
    "overlap with no stop rule; select and isolate by trimming the catalogue and adding a budget rule. Silent "
    "regression: cost and quality fall; layer 01 system prompt lost a line it relied on; restore it and add a "
    "replay fixture.",
    subtitle="Read each row left to right: what the trace shows, what the prompt shows, where the fix lives.",
    data_w=True)

COLS = [40, 216, 432, 688]
HEADS = ["Shape", "In the trace", "In the prompt", "Fix"]
for x, h in zip(COLS, HEADS):
    fig.text(x, 128, h, "head")
fig.edge((40, 144), (920, 144), color="ink-muted", width=1)
TOP, ROW_H = 144, 76
for k, (shape, trace, (layer, role, prompt), fix) in enumerate(ROWS):
    y = TOP + k * ROW_H
    fig.text(COLS[0], y + 32, shape, "label", bold=True)
    fig.text(COLS[1], y + 32, trace, "label")
    fig.text(COLS[2], y + 32, rich(span(layer, color=role)), "label")
    fig.text(COLS[2], y + 56, prompt, "note")
    fig.text(COLS[3], y + 32, fix[0], "label")
    fig.text(COLS[3], y + 56, fix[1], "note")
    fig.edge((40, y + ROW_H), (920, y + ROW_H), color="border", width=1)
fig.caption("None of the four is fixed in the model.")
fig.write()
