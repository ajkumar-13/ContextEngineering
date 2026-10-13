"""Post 23 hero: where the four defences sit around the six-layer window.

Run from the series root:  uv run python posts/23-security/diagrams/src/00-hero-defences.py
Writes posts/23-security/diagrams/00-hero-defences.svg.
No numbers are drawn. The entry points of external text (layers 02, 04, 05), the placement of D1 to D4 and the
trust tag are section 5's; the labels are asserted against the body. Layer bands take their lifetime role colour;
external text, which may carry an injection, is drawn in the error hue.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
for phrase in ("**D1. The model is not the permission system.**", "**D2. Constrain each tool's blast radius.**",
               "**D3. Filter at trust boundaries.**", "**D4. Never silently merge attacker text into trusted context.**",
               "A **trust tag** is a label", "`external` (anyone else: a web page, an email body, a retrieved chunk, a tool result)",
               "layer 04, retrieved chunks, or layer 05, conversation history, as a tool result, or layer 02, tools and MCP descriptions",
               "a rule proposed in a turn that read external text carries that text's tag and is refused",
               "The agent proposes; the application decides."):
    assert phrase in BODY, phrase

LAYERS = ["System prompt", "Tools and MCP descriptions", "Memory and state", "Retrieved chunks",
          "Conversation history", "User instruction"]
ROLE = {1: "stable", 2: "stable", 3: "turn", 4: "turn", 5: "history", 6: "user"}

desc = ("Left, a card of external text: web pages, emails, documents, tool results and unvetted MCP servers. Red "
        "arrows carry it across a dashed trust boundary, where D3 wraps it and tags it external, into three bands "
        "of the six-layer window: 02 Tools and MCP descriptions, 04 Retrieved chunks and 05 Conversation history. "
        "The window, 01 System prompt to 06 User instruction, feeds the model, which only proposes. Its proposed "
        "calls go to a gate in application code, D1 and D2: is the call in scope, is the recipient allowed; if not, "
        "it is blocked or held for a person. Only what passes reaches the action. Its proposed memory writes go to "
        "D4, which refuses a rule written from external text, so the rule never returns in 03 Memory and state.")
fig = Figure("00-hero-defences", "The model proposes; code decides what runs", desc,
             subtitle="Where the four defences sit: D3 where external text enters, D4 at memory, D1 and D2 before every action.",
             height=720, data_w=True)

# the window: six bands, sent top to bottom
SX, SW, Y0, BH, GAP = 264, 240, 168, 48, 12
tops = {k: Y0 + (k - 1) * (BH + GAP) for k in range(1, 7)}
fig.text(SX, Y0 - 16, "The model's window", "head")
for k, name in enumerate(LAYERS, start=1):
    band = Box(SX, tops[k], SW, BH)
    fig.fill(band, f"{ROLE[k]}-soft", radius=4, fit=False)
    fig.outline(band, f"{ROLE[k]}-line", radius=4)
    fig.text(SX + 12, tops[k] + 30, f"{k:02d} {name}", "label")

# external text, the trust boundary and D3
ext = Box(40, 200, 168, 264)
fig.fill(ext, "neutral-soft", radius=8, fit=False)
fig.outline(ext, "border", radius=8)
fig.text(ext.x + 16, ext.y + 32, "External text", "head")
for i, s in enumerate(["web pages", "emails", "documents", "tool results", "unvetted MCP", "servers"]):
    fig.text(ext.x + 16, ext.y + 68 + (32 * i if i < 5 else 32 * 4 + 24), s, "label")
BX = 232
fig.edge((BX, 136), (BX, 612), color="rule", dash="lead")
fig.text(40, 136, "Trust boundary, D3:", "label")
fig.text(40, 160, "wrap, tag external", "note")
for k in (2, 4, 5):
    y = tops[k] + BH // 2
    assert ext.y < y < ext.bottom
    fig.arrow((ext.right + 2, y), (SX - 2, y), color="error")
fig.legend(40, 504, [dict(color="error", label="may carry an injection", mark="line")])

# the model
model = Box(544, tops[3], 88, tops[4] + BH - tops[3])
fig.fill(model, "surface", radius=8, fit=False)
fig.outline(model, "ink-muted", width=1.5, radius=8)
fig.text(model.cx, model.cy + 5, "model", "head", anchor="middle")
fig.arrow((SX + SW + 2, model.cy), (model.x - 2, model.cy))
fig.text(model.cx, model.bottom + 28, "proposes", "note", anchor="middle")

# the gate in code: D1 and D2, then the action
gate = Box(680, tops[2], 240, 168)
fig.fill(gate, "neutral-soft", radius=8, fit=False)
fig.outline(gate, "border", radius=8)
fig.text(gate.x + 16, gate.y + 32, "Gate in code, D1 and D2", "head")
for i, s in enumerate(["in scope for this task?", "recipient on the allow-list?", "if not: blocked, or held",
                       "for a person to approve"]):
    fig.text(gate.x + 16, gate.y + 68 + 24 * i, s, "label" if i < 2 else "note")
fig.arrow((model.right + 2, model.cy), (gate.x - 2, model.cy), label="call")
act = Box(680, tops[5] + 40, 240, 72)
fig.fill(act, "surface", radius=8, fit=False)
fig.outline(act, "rule", radius=8)
fig.text(act.x + 16, act.y + 28, "Action", "head")
fig.text(act.x + 16, act.y + 52, "send, read, pay, delete", "label")
fig.arrow((gate.cx, gate.bottom + 2), (act.cx, act.y - 2), label="only what passes", side="right")

# memory: D4
mem = Box(472, 548, 288, 104)
fig.fill(mem, "surface", radius=8, fit=False)
fig.outline(mem, "rule", radius=8)
fig.fill(Box(mem.x + 8, mem.y + 8, mem.w - 16, 8), "turn", radius=4, fit=False)  # a store of layer 03 content
fig.text(mem.x + 16, mem.y + 44, "Memory write, D4", "head")
fig.text(mem.x + 16, mem.y + 68, "a rule from external text: refused,", "label")
fig.text(mem.x + 16, mem.y + 92, "never back in 03 as a rule", "label")
fig.arrow((model.cx, model.bottom + 44), (model.cx, mem.y - 2), label="write", side="right")

fig.caption("Text from any author reaches an action only through checks the model cannot rewrite.")
fig.write()
