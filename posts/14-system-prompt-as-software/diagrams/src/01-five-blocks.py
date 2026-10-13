"""Post 14 hero: layer 01, the system prompt, opened out into its five named blocks.

Run from anywhere:  python posts/14-system-prompt-as-software/diagrams/src/01-five-blocks.py
Writes posts/14-system-prompt-as-software/diagrams/01-five-blocks.svg.
No numbers are drawn. The block names and the example lines come from snippets/prompt_ci.py (BLOCKS and
PARTS_V1, imported and asserted); the one-clause jobs are section 2's, shortened (phrases asserted against
index.md); the layer names are notation_guide.md's. Layers 01 and 02 are stable (blue); 03 and 04 turn
(orange); 05 history (green); 06 user (purple), as ctx_fig_design.md section 0.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
SNIP = runpy.run_path(str(POST / "snippets" / "prompt_ci.py"), run_name="snippet")
BLOCKS, PARTS = SNIP["BLOCKS"], SNIP["PARTS_V1"]
assert BLOCKS == ("Identity", "Rules", "Format", "Knowledge", "Tool-use guidance")

# (block, job as drawn, the body phrase it shortens, one line of the snippet's prompt)
ROWS = [
    ("Identity", "who the agent is, its scope", "who the agent is, whom it serves, where its scope ends",
     "You are the support agent for Acme."),
    ("Rules", "constraints, each with an issue id", "Each carries the issue id of the incident",
     "- [#455] Reply in formal British English."),
    ("Format", "the shape of every reply", "The shape of every reply",
     "Answer in plain prose of at most 150 words."),
    ("Knowledge", "small facts needed on almost every call", "Small, stable facts needed on almost every call",
     "Office hours are 9:00 to 18:00 IST, Monday to Saturday"),
    ("Tool-use guidance", "when to reach for which tool", "When to reach for which tool",
     "- lookup_order: questions about where an order is."),
]
for name, _, phrase, example in ROWS:
    assert name in BLOCKS and phrase in BODY and example in PARTS[name][1], (name, phrase, example)
assert "The schemas themselves are layer 02, tools and MCP descriptions" in BODY

LAYERS = ["01 System prompt", "02 Tools and MCP descriptions", "03 Memory and state",
          "04 Retrieved chunks", "05 Conversation history", "06 User instruction"]
ROLE = ["stable", "stable", "turn", "turn", "history", "user"]

desc = ("Left: the six-layer stack, 01 System prompt at the top to 06 User instruction at the bottom, with layer 01 "
        "outlined. Dashed lines open layer 01 out to the right into five blocks, in order. ")
desc += " ".join(f"{name}: {job}; example line: {ex}" for name, job, _, ex in ROWS)
desc += " The caption says tool-use guidance says when to call a tool, and the schemas it points at are layer 02."

fig = Figure("01-five-blocks", "Layer 01 is five named blocks", desc,
             subtitle="The system prompt of the post's snippet, block by block, inside the six-layer window.",
             data_w=True)

# the six-layer stack
SX, SW, SY, BH, BG = 40, 248, 112, 52, 8
bands = []
for k, (label, role) in enumerate(zip(LAYERS, ROLE)):
    b = Box(SX, SY + k * (BH + BG), SW, BH)
    fig.fill(b, f"{role}-soft", radius=8, fit=False)
    if k == 0:
        fig.outline(b, role, radius=8, width=2.5)
        fig.text(SX + 16, b.y + 32, label, "head")
    else:
        fig.outline(b, f"{role}-line", radius=8)
        fig.text(SX + 16, b.y + 32, label, "label")
    bands.append(b)

# the five blocks of layer 01
CX, CW, CH, CG = 352, 568, 64, 8
cards = []
for i, (name, job, _, example) in enumerate(ROWS):
    c = Box(CX, SY + i * (CH + CG), CW, CH)
    fig.fill(c, "stable-soft", radius=8, fit=False)
    fig.outline(c, "stable-line", radius=8)
    fig.text(CX + 16, c.y + 26, name, "head")
    fig.text(CX + 200, c.y + 26, job, "note")
    fig.text(CX + 16, c.y + 50, example, "code")
    cards.append(c)

column = Box(CX, SY, CW, cards[-1].bottom - SY)
fig.zoom(bands[0], column)

fig.caption("Tool-use guidance says when to call a tool; the schemas it points at are layer 02.")
fig.write()
