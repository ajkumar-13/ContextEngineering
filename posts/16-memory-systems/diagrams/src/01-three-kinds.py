"""Post 16 hero: the three kinds of memory, each with its own write trigger, retrieval path and decay, all feeding layer 03.

Run from anywhere:  python posts/16-memory-systems/diagrams/src/01-three-kinds.py
Writes posts/16-memory-systems/diagrams/01-three-kinds.svg.
No numbers are drawn. What each kind holds, when it is written, how it is retrieved and whether it decays are
sections 4 to 7 of index.md (asserted below); the order 1 to 3 is the orchestrator's (section 7); the layer names are
notation_guide.md's. The store cards carry the turn role as a thin band (ctx_fig_design.md, section 3), because a
memory store holds the content of layer 03, memory and state.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("**What it stores.** Events", "At the end of an interaction", "*Reference recall*",
               "**What it stores.** Facts and preferences", "On explicit assertion", "On an observed pattern",
               "**How it is retrieved.** In the background", "How-tos and rules learned about one user",
               "on an explicit instruction", "By **trigger matching**", "**Decay.** None.",
               "1. Do any **procedural** rules trigger", "2. Which **semantic** facts",
               "3. Does the turn **refer** to a past episode"):
    assert phrase.lower() in BODY.lower(), phrase

# (number and kind, holds, written, retrieved by, decays), in the orchestrator's order
KINDS = [("1 Procedural", "learned rules", "on instruction", "trigger match", "no"),
         ("2 Semantic", "facts, preferences", "on assertion", "background top-k", "yes"),
         ("3 Episodic", "events", "end of interaction", "reference recall", "yes")]
LAYERS = ["01 System prompt", "02 Tools and MCP", "03 Memory and state", "04 Retrieved chunks",
          "05 Conversation history", "06 User instruction"]
ROLE = ["stable", "stable", "turn", "turn", "history", "user"]

desc = "Three memory store cards, in the order the orchestrator reads them. "
for name, holds, written, path, decays in KINDS:
    desc += f"{name}: holds {holds}, written {written}, retrieved by {path}, decays: {decays}. "
desc += ("An arrow from each card runs into band 03 Memory and state of the six-layer window on the right, "
         "drawn from 01 System prompt at the top to 06 User instruction at the bottom; band 03 is outlined.")

fig = Figure("01-three-kinds", "Three kinds of memory, one layer", desc,
             subtitle="Each kind has its own write trigger, retrieval path and decay; all three enter layer 03.",
             data_w=True)

# the three store cards
CX, CR = 40, 640
COLS = [("holds", 176), ("written", 320), ("retrieved by", 448), ("decays", 600)]
for label, x in COLS:
    fig.text(x, 128, label, "note")
CH, CG, CY = 88, 16, 144
centres = []
for i, (name, holds, written, path, decays) in enumerate(KINDS):
    top = CY + i * (CH + CG)
    b = Box(CX, top, CR - CX, CH)
    fig.fill(b, "surface", radius=8, fit=False)
    fig.outline(b, "border", radius=8)
    fig.fill(Box(CX + 8, top + 8, CR - CX - 16, 8), "turn", radius=4, fit=False)
    base = top + 56
    fig.text(CX + 16, base, name, "head")
    for (_, x), value in zip(COLS, (holds, written, path, decays)):
        fig.text(x, base, value, "label")
    centres.append(top + CH // 2 + 4)

# the window as a stack, 03 outlined
SX, SW, SH, SG, SY = 712, 208, 48, 8, 136
fig.text(SX, 128, "The window, sent 01 to 06", "note")
bands = []
for k, (label, role) in enumerate(zip(LAYERS, ROLE)):
    y = SY + k * (SH + SG)
    b = Box(SX, y, SW, SH)
    fig.fill(b, f"{role}-soft", radius=6, fit=False)
    fig.outline(b, "turn" if k == 2 else f"{role}-line", radius=6, width=2.5 if k == 2 else 1)
    fig.text(SX + 12, y + 30, label, "label")
    bands.append(b)

m = bands[2]
for i, cy in enumerate(centres):
    fig.arrow((CR + 4, cy), (m.x - 4, m.y + 12 + 12 * i))

fig.caption("Rules are obeyed and never decay; facts and events are weighed and fade without reads.")
fig.write()
