"""Post 01, section 1 (the hero): the surface of the work grows from one message to a window of six layers.

Run from anywhere:  python posts/01-why-context-engineering/diagrams/src/01-from-message-to-window.py
Writes posts/01-why-context-engineering/diagrams/01-from-message-to-window.svg.
No numbers are drawn and band heights are equal (the post states no layer sizes). The layer names and their order
are plan Section 6's; the lifetime classes and role colours are the series design page's; which change added which
layer (tools 02, memory 03, retrieval 04; 01 and 05 already existed) is section 1 of index.md, asserted below.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2] / "index.md"
BODY = POST.read_text(encoding="utf-8")

# number, name, role, what section 1 says brought the layer into the call
LAYERS = [
    ("01", "System prompt", "stable", "there, rarely engineered"),
    ("02", "Tools and MCP descriptions", "stable", "added by tools"),
    ("03", "Memory and state", "turn", "added by memory"),
    ("04", "Retrieved chunks", "turn", "added by retrieval"),
    ("05", "Conversation history", "history", "there, rarely engineered"),
    ("06", "User instruction", "user", None),
]
for phrase in ("layer 01, the system prompt", "layer 02, tools and MCP descriptions", "layer 03, memory and state",
               "layer 04, retrieved chunks", "layer 05, conversation history", "layer 06, the user instruction",
               "**First, models gained tools.**", "**Second, models gained access to outside data.**",
               "**Third, models gained memory.**",
               "Add the system prompt and the conversation history that already existed"):
    assert phrase in BODY, phrase
# lifetime classes (design page Section 0): rows they span and the label
LIFETIMES = [(0, 1, "stable", "stable prefix"), (2, 3, "turn", "per-turn injection"),
             (4, 4, "history", "growing tail"), (5, 5, "user", "trigger")]

fig = Figure(
    "01-from-message-to-window", "The work moved from one message to a window of six layers",
    "Two panels of equal height. Left, prompt engineering in 2022: one tall purple box, 06 User instruction, the one "
    "message the engineer rewords, fills the whole surface. "
    "Right, context engineering in 2025: a stack of six equal bands sent top to bottom, 01 System prompt and 02 "
    "Tools and MCP descriptions in blue, bracketed as the stable prefix; 03 Memory and state and 04 Retrieved "
    "chunks in orange, the per-turn injection; 05 Conversation history in green, the growing tail; 06 User "
    "instruction in purple, the trigger. Labels left of the bands say 02 was added by tools, 03 by memory and 04 "
    "by retrieval, and that 01 and 05 were already there. No token sizes are drawn.",
    subtitle="Layer 06 is still the user's sentence; the five layers above it are assembled by an engineer.",
    data_w=True)

left, right = fig.row((1, 2))
lb = fig.panel(left, "Prompt engineering, 2022")
rb = fig.panel(right, "Context engineering, 2025")

BH, GAP = 40, 8
Y0 = rb.y + 32                                   # first band; "sent first" sits above it
SX, SW = 472, 272                                # the stack
rows = [Box(SX, Y0 + k * (BH + GAP), SW, BH) for k in range(6)]

fig.text(SX, rows[0].y - 12, "sent first", "note")
for (n, name, role, why), b in zip(LAYERS, rows):
    fig.card(b.x, b.y, b.w, b.h, color=role)
    fig.text(b.x + 16, b.cy + 5, f"{n} {name}", "label")
    if why:
        fig.text(SX - 16, b.cy + 5, why, "note", anchor="end")
fig.text(SX, rows[-1].bottom + 24, "sent last", "note")

for i0, i1, role, label in LIFETIMES:
    fig.brace(rows[i0].y, rows[i1].bottom, SX + SW + 8, label, side="right", vertical=True, color=role)

# left: in 2022 the one message was the whole surface of the work, drawn as tall as the whole stack
whole = Box(lb.x, rows[0].y, 224, rows[-1].bottom - rows[0].y)
fig.card(whole.x, whole.y, whole.w, whole.h, color="user")
fig.text(whole.x + 16, whole.cy - 7, "06 User instruction", "label")
fig.text(whole.x + 16, whole.cy + 17, "the one message the", "note")
fig.text(whole.x + 16, whole.cy + 37, "engineer rewords", "note")

fig.caption("Tools, memory and retrieval each added a layer that the user never typed.")
fig.write()
