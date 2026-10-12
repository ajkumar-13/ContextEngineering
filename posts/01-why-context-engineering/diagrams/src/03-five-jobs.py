"""Post 01, section 4: the five jobs of a context engineer, each drawn where it acts on the window.

Run from anywhere:  python posts/01-why-context-engineering/diagrams/src/03-five-jobs.py
Writes posts/01-why-context-engineering/diagrams/03-five-jobs.svg.
No numbers are drawn. The five job names are the bold lead-ins of section 4 of index.md and the layer names are
plan Section 6's, both asserted below; which source fills which layer (tool schemas 02, memories 03, documents 04)
is section 1's account.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
JOBS = ["Decide what goes in.", "Decide what stays out.", "Decide where each piece sits.",
        "Decide when to refresh, compress, or write out.", "Decide how to measure whether it worked."]
for k, job in enumerate(JOBS, 1):
    assert f"**{k}. {job}**" in BODY, job

LAYERS = [("01", "System prompt", "stable"), ("02", "Tools and MCP descriptions", "stable"),
          ("03", "Memory and state", "turn"), ("04", "Retrieved chunks", "turn"),
          ("05", "Conversation history", "history"), ("06", "User instruction", "user")]
SOURCES = [("tool schemas", 1), ("memories", 2), ("documents", 3)]     # source, index of the layer it fills

fig = Figure(
    "03-five-jobs", "Every job of the work acts on the same window",
    "A stack of the six layers in the centre, 01 System prompt at the top to 06 User instruction at the bottom, "
    "sent as a whole, a brace on its right edge, into a model box that produces an answer. Job 1, what goes in: arrows from tool schemas, "
    "memories and documents on the left into layers 02, 03 and 04. Job 2, what stays out: a red dashed card for "
    "an unused tool and a stale chunk, with no arrow into the stack. Job 3, where each piece sits: the order of "
    "the stack, stable prefix first and the user instruction last. Job 4, when to refresh: a leader from layer 05, "
    "conversation history, to compress or write out. Job 5, how to measure: traces, evaluations and cost "
    "dashboards, joined by a leader to the answer.",
    subtitle="Two jobs choose what the window holds, one orders it, one tends its growing tail, one checks the result.",
    data_w=True)

SX, SW, BH, GAP, SY = 376, 240, 32, 8, 184
rows = [Box(SX, SY + k * (BH + GAP), SW, BH) for k in range(6)]
fig.text(SX, 136, "3 Where each piece sits", "head")
fig.text(SX, 160, "stable prefix first, instruction last", "note")
for (n, name, role), b in zip(LAYERS, rows):
    fig.card(b.x, b.y, b.w, b.h, color=role)
    fig.text(b.x + 12, b.cy + 5, f"{n} {name}", "label")

# job 1: sources into the layers they fill
SRC_X, SRC_W = 40, 168
fig.text(SRC_X, rows[1].y - 16, "1 What goes in", "head")
for name, k in SOURCES:
    b = Box(SRC_X, rows[k].y, SRC_W, BH)
    fig.card(b.x, b.y, b.w, b.h)
    fig.text(b.x + 12, b.cy + 5, name, "label")
    fig.arrow((b.right + 8, b.cy), (SX - 8, rows[k].cy))

# job 2: candidates that never enter
out = Box(SRC_X, rows[5].y - 8, SRC_W, 48)
fig.text(SRC_X, out.y - 16, "2 What stays out", "head")
fig.outline(out, "error", width=1.5, dash="proj", radius=8)
fig.text(out.x + 12, out.y + 20, "unused tool", "label", color="error")
fig.text(out.x + 12, out.y + 40, "stale chunk", "label", color="error")

# the model and its answer
stack = Box(SX, rows[0].y, SW, rows[-1].bottom - rows[0].y)
fig.brace(stack.y, stack.bottom, SX + SW + 8, side="right", vertical=True)     # the whole window is sent
model = Box(672, stack.cy - 24, 72, 48)
fig.card(model.x, model.y, model.w, model.h)
fig.text(model.cx, model.cy + 5, "model", "label", anchor="middle")
fig.arrow((SX + SW + 24, model.cy), (model.x - 8, model.cy))
ans = Box(792, model.y, 88, model.h)
fig.card(ans.x, ans.y, ans.w, ans.h)
fig.text(ans.cx, ans.cy + 5, "answer", "label", anchor="middle")
fig.arrow((model.right + 8, model.cy), (ans.x - 8, ans.cy))

# job 5: checks on the answer
fig.text(ans.x - 16, 136, "5 How to measure", "head")
fig.text(ans.x - 16, 160, "traces, evaluations,", "note")
fig.text(ans.x - 16, 180, "cost dashboards", "note")
fig.edge((ans.cx, 196), (ans.cx, ans.y - 8), color="rule", width=1, dash="lead")

# job 4: the growing tail
h = rows[4]
fig.edge((h.right + 12, h.cy), (model.x, h.cy), color="rule", width=1, dash="lead")
fig.text(model.x + 8, h.cy + 5, "4 When to refresh", "head")
fig.text(model.x + 8, h.cy + 29, "compress or write out", "note")

fig.caption("Teams often start with job 1; job 2, keeping things out, is the harder and more important one.")
fig.write()
