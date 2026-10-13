"""Post 24 hero: personal data crosses one detect-and-redact gate into layers 03 to 06, and the assembled prompt
goes to the model and, as a copy, to the trace store.

Run from anywhere:  python posts/24-privacy-and-governance/diagrams/src/01-one-gate-two-copies.py
Writes posts/24-privacy-and-governance/diagrams/01-one-gate-two-copies.svg.
The layer names are post 02's (snippets/context_inspector.py, LAYERS); the channel-to-layer map is section 2 of
this post, asserted against the body. The figure shows no sizes and no numbers.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
LAYERS = runpy.run_path(str(POST.parent / "02-six-layers-of-context" / "snippets" / "context_inspector.py"),
                        run_name="snippet")["LAYERS"]
assert list(LAYERS.values()) == ["System prompt", "Tools and MCP descriptions", "Memory and state",
                                 "Retrieved chunks", "Conversation history", "User instruction"]
ROLE = {1: "stable", 2: "stable", 3: "turn", 4: "turn", 5: "history", 6: "user"}
# section 2: which channel lands in which layer
CHANNELS = {3: "Memory rows", 4: "Retrieved chunks", 5: "Tool results", 6: "User message"}
for k, phrase in {3: "**Layer 03, memory and state.**", 4: "**Layer 04, retrieved chunks.**",
                  5: "**Layer 05, conversation history**, holds every earlier message of the session and every tool result",
                  6: "**Layer 06, the user instruction.**"}.items():
    assert phrase in BODY, phrase
assert "two layers are written by the team and four are not" in BODY
assert "four channels cross one gate at the trust boundary and land in their layers" in BODY
assert "the assembled prompt goes to the model and, as a copy, to the trace store" in BODY

desc = ("Six bands, the window as post 02 draws it: 01 System prompt and 02 Tools and MCP descriptions in blue, "
        "03 Memory and state and 04 Retrieved chunks in orange, 05 Conversation history in green, 06 User "
        "instruction in purple. Beside 01 and 02 a note says the team writes them and they hold no personal data. "
        "Four channels on the left, memory rows, retrieved chunks, tool results and the user message, pass through "
        "one detect-and-redact box at the trust boundary and enter layers 03, 04, 05 and 06. A bracket gathers the "
        "six layers and two arrows leave it: one to the model, one to the trace store, which holds a copy of all "
        "six layers of every prompt.")

fig = Figure("01-one-gate-two-copies", "Personal data crosses one gate, then lives in two copies", desc,
             subtitle="Post 02's six layers: the team writes 01 and 02; users, tools, retrieval and memory fill 03 to 06.",
             data_w=True)

Y0, BH, GAP = 112, 48, 8
tops = {k: Y0 + (k - 1) * (BH + GAP) for k in LAYERS}
SX0, SX1 = 392, 664                 # the stack
CX0, CX1 = 40, 232                  # the channels
GX0, GX1 = 264, 360                 # the gate

for k, name in LAYERS.items():
    band = Box(SX0, tops[k], SX1 - SX0, BH)
    fig.fill(band, f"{ROLE[k]}-soft", radius=8, fit=False)
    fig.outline(band, f"{ROLE[k]}-line", radius=8)
    fig.text(SX0 + 16, tops[k] + 30, f"{k:02d} {name}", "head")

# 01 and 02: written by the team
team = Box(CX0, tops[1], GX1 - CX0, tops[2] + BH - tops[1])
fig.fill(team, "neutral-soft", radius=8, fit=False)
fig.outline(team, "border", radius=8)
fig.text(CX0 + 16, tops[1] + 44, "Written and reviewed by the team", "label")
fig.text(CX0 + 16, tops[1] + 72, "no personal data belongs here", "note")

# the gate at the trust boundary
gate = Box(GX0, tops[3], GX1 - GX0, tops[6] + BH - tops[3])
fig.fill(gate, "surface", radius=8, fit=False)
fig.outline(gate, "ink", radius=8, width=2.5)
fig.text(gate.cx, gate.cy - 6, "Detect", "head", anchor="middle")
fig.text(gate.cx, gate.cy + 16, "and redact", "head", anchor="middle")
fig.text(gate.cx, gate.bottom + 28, "trust boundary", "note", anchor="middle")

for k, name in CHANNELS.items():
    card = Box(CX0, tops[k], CX1 - CX0, BH)
    fig.fill(card, "surface", radius=8, fit=False)
    fig.outline(card, "border", radius=8)
    fig.text(CX0 + 16, tops[k] + 30, name, "label")
    y = tops[k] + BH // 2
    fig.arrow((CX1 + 2, y), (GX0, y))
    fig.arrow((GX1 + 2, y), (SX0, y))

# the two copies
fig.brace(tops[1] + 4, tops[6] + BH - 4, SX1 + 12, side="right", kind="bracket", vertical=True)
mid = (tops[1] + tops[6] + BH) // 2
model = Box(736, 112, 184, 88)
fig.fill(model, "neutral-soft", radius=8, fit=False)
fig.outline(model, "border", radius=8)
fig.text(model.cx, model.cy + 6, "Model", "head", anchor="middle")
store = Box(736, 296, 184, 144)
fig.fill(store, "neutral-soft", radius=8, fit=False)
fig.outline(store, "border", radius=8)
fig.text(store.x + 16, store.y + 32, "Trace store", "head")
fig.text(store.x + 16, store.y + 56, "a copy of every prompt", "note")
SEG = 24
for i, k in enumerate(LAYERS):
    seg = Box(store.x + 16 + i * SEG, store.y + 80, SEG, 32)
    fig.fill(seg, f"{ROLE[k]}-soft", fit=False)
    fig.outline(seg, f"{ROLE[k]}-line")
fig.text(store.x + 16, store.y + 132, "01 to 06", "note")
fig.arrow((SX1 + 36, mid), model.anchor("left", 0.5))
fig.arrow((SX1 + 36, mid), store.anchor("left", 0.5))

fig.caption("The trace store keeps all six layers of every call, long after the model has answered.")
fig.write()
