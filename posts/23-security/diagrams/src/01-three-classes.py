"""Post 23, section 2: the three classes of prompt injection, nested by how far each reaches.

Run from the series root:  uv run python posts/23-security/diagrams/src/01-three-classes.py
Writes posts/23-security/diagrams/01-three-classes.svg.
No numbers are drawn: the reach of each class is a containment, not a measured size, so it is drawn as nested
regions rather than bars. Who writes the text, the layers it enters and its reach are section 2's, asserted below;
each layer it enters is a chip in that layer's lifetime role colour, named by number and name.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, rich, span  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
for phrase in ("It arrives in layer 06, the user instruction.", "the user is attacking their own session, with their own permissions",
               "The text enters layer 04, retrieved chunks, or layer 05, conversation history, as a tool result, or layer 02, tools and MCP descriptions",
               "its reach is everything the agent can reach, including files, tools and other users' data",
               "Later sessions retrieve it into layer 03, memory and state", "reaches other users when the memory store is shared",
               "The class every demonstration shows has the smallest reach of the three."):
    assert phrase in BODY, phrase

LAYER = {2: ("Tools and MCP descriptions", "stable"), 3: ("Memory and state", "turn"), 4: ("Retrieved chunks", "turn"),
         5: ("Conversation history", "history"), 6: ("User instruction", "user")}
RINGS = [  # (box, heading, who, reach, layers entered, fill, outline, width)
    (Box(40, 112, 880, 364), "Memory poisoning", "A rule planted in the memory store, read back later",
     "later sessions, and other users of a shared store", [3], "neutral-soft", "border", 1),
    (Box(64, 208, 832, 244), "Indirect injection", "Text a third party planted in a page, an email, a tool result",
     "everything the agent can reach", [2, 4, 5], "surface", "rule", 1),
    (Box(88, 344, 784, 92), "Direct injection", "Text the user types",
     "the user's own session, with the user's own permissions", [6], "neutral-soft", "ink-muted", 1.5),
]
CX, CW, CH = 608, 248, 32

desc = ("Three nested rounded regions, each with the layers its text enters as coloured chips. The outermost is "
        "memory poisoning: a rule planted in the memory store and read back later into 03 Memory and state; it "
        "reaches later sessions and other users of a shared store. Inside it is indirect injection: text a third "
        "party planted in a page, an email or a tool result, entering 02 Tools and MCP descriptions, 04 Retrieved "
        "chunks or 05 Conversation history; it reaches everything the agent can reach. Innermost is direct "
        "injection: text the user types into 06 User instruction; it reaches the user's own session.")
fig = Figure("01-three-classes", "The class every demo shows has the smallest reach", desc,
             subtitle="Three classes of prompt injection: who writes the text, where it enters, and how far it reaches.",
             data_w=True)
for box, heading, who, reach, layers, fill, line, width in RINGS:
    fig.fill(box, fill, radius=8, fit=False)
    fig.outline(box, line, width=width, radius=8)
    fig.text(box.x + 16, box.y + 32, heading, "head")
    fig.text(box.x + 16, box.y + 56, who, "label")
    fig.text(box.x + 16, box.y + 80, rich(span("Reaches: ", bold=True), reach), "label")
    fig.text(CX - 16, box.y + 30, "enters", "note", anchor="end")
    for i, k in enumerate(layers):
        name, role = LAYER[k]
        chip = Box(CX, box.y + 8 + i * (CH + 8), CW, CH)
        fig.fill(chip, f"{role}-soft", radius=4, fit=False)
        fig.outline(chip, f"{role}-line", radius=4)
        fig.text(chip.x + 12, chip.y + 22, f"{k:02d} {name}", "label")

fig.caption("A user who attacks the session acts with only their own permissions; a third party's text needs no account.")
fig.write()
