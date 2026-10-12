"""Post 08 hero: the four write destinations, who writes each, how long it lasts, and the layer it returns through.

Run from anywhere:  python posts/08-write-strategies/diagrams/src/01-four-destinations.py
Writes posts/08-write-strategies/diagrams/01-four-destinations.svg.
No numbers are drawn. The destinations, writers and lifetimes are sections 1 to 6 of index.md (asserted below);
the layer each destination returns through is section 1's sentence, in the layer names of notation_guide.md.
The colour band on each card is the role of the layer it feeds (ctx_fig_design.md, section 3).
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("repository files through layer 01, the system prompt; memory stores and scratchpads through layer 03, "
               "memory and state; an embedding index through layer 04, retrieved chunks",
               "| Months, decays |", "| Weeks to months |", "| Until the policy changes |", "| This task |",
               "| Until the manual changes |", "checked into the repository: reviewed",
               "an *offline* write path that prepares the corpus",
               "a single agent or sub-agent uses to keep its working state across iterations",
               "Write takes information out of the window; a later select brings it back"):
    assert phrase in BODY, phrase

LAYERS = {1: ("01 System", "prompt"), 2: ("02 Tools and", "MCP descriptions"), 3: ("03 Memory", "and state"),
          4: ("04 Retrieved", "chunks"), 5: ("05 Conversation", "history"), 6: ("06 User", "instruction")}
ROLE = {1: "stable", 2: "stable", 3: "turn", 4: "turn", 5: "history", 6: "user"}
# (destination, written by, lasts, layer it returns through)
DEST = [("Repository files", "people, by review", "until a reviewed change", 1),
        ("Memory store", "agent or background job", "weeks to months, decays", 3),
        ("Scratchpad", "the agent, each iteration", "one task", 3),
        ("Embedding index", "an offline pipeline", "until the source changes", 4)]

desc = ("At the top, the agent at work on this call, with an arrow labelled write into each of four destinations. ")
for name, who, lasts, k in DEST:
    desc += f"{name}: written by {who}, lasts {lasts}, returns through layer {' '.join(LAYERS[k])}. "
desc += ("At the bottom, a later call's window as a strip of the six layers, 01 to 06; arrows labelled select run from "
         "each destination down to its layer. Layers 02, 05 and 06 receive nothing from a store.")

fig = Figure("01-four-destinations", "Write takes it out of the window; select brings it back", desc,
             subtitle="Four destinations: who writes each, how long it lasts, and the layer it returns through.",
             height=720, data_w=True)

# the agent at work on this call
src = Box(40, 112, 880, 48)
fig.fill(src, "neutral-soft", radius=8, fit=False)
fig.outline(src, "border", radius=8)
fig.text(src.cx, 142, "The agent at work on this call", "head", anchor="middle")

CW, CG, CY, CH = 208, 16, 232, 176
cards = []
for i, (name, who, lasts, k) in enumerate(DEST):
    x = 40 + i * (CW + CG)
    b = Box(x, CY, CW, CH)
    fig.fill(b, "surface", radius=8, fit=False)
    fig.outline(b, "border", radius=8)
    fig.fill(Box(x + 8, CY + 8, CW - 16, 8), ROLE[k], radius=4, fit=False)   # the role of the layer it feeds
    fig.text(x + 16, CY + 48, name, "head")
    fig.text(x + 16, CY + 84, "written by", "note")
    fig.text(x + 16, CY + 104, who, "label")
    fig.text(x + 16, CY + 136, "lasts", "note")
    fig.text(x + 16, CY + 156, lasts, "label")
    cards.append(b)
    fig.arrow((b.cx, src.bottom + 4), (b.cx, CY - 4))
fig.text(cards[0].cx + 12, 200, "write", "note")

# a later call's window
SW, SG, SY, SH = 140, 8, 552, 64
cells = {}
for k, (l1, l2) in LAYERS.items():
    x = 40 + (k - 1) * (SW + SG)
    c = Box(x, SY, SW, SH)
    fig.fill(c, f"{ROLE[k]}-soft", radius=6, fit=False)
    fig.outline(c, f"{ROLE[k]}-line", radius=6)
    fig.text(x + 12, SY + 28, l1, "label")
    fig.text(x + 12, SY + 50, l2, "label")
    cells[k] = c
fig.text(40, SY + SH + 28, "A later call's window, sent from 01 to 06", "note")

# select: each destination back into its layer
bot = CY + CH
fig.arrow((cells[1].cx, bot + 4), (cells[1].cx, SY - 4))
fig.text(cells[1].cx + 12, bot + 76, "select", "note")
fig.arrow((cells[3].cx, bot + 4), (cells[3].cx, SY - 4))
fig.arrow((cards[2].x + 48, bot + 4), (cells[3].right - 32, SY - 4),
          via=[(cards[2].x + 48, 464), (cells[3].right - 32, 464)])
fig.arrow((cards[3].x + 48, bot + 4), (cells[4].cx, SY - 4),
          via=[(cards[3].x + 48, 504), (cells[4].cx, 504)])

fig.caption("Written information costs no tokens on later calls until a select brings it back.")
fig.write()
