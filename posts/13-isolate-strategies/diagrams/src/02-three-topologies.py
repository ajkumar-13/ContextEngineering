"""Post 13, section 4: the three topologies, and which of them leaves the next step to the model.

Run from anywhere:  uv run python posts/13-isolate-strategies/diagrams/src/02-three-topologies.py
Writes posts/13-isolate-strategies/diagrams/02-three-topologies.svg.
No numbers are drawn. The three wirings, their risks and the workflow-versus-agent line are section 4 of index.md
(after Anthropic, "Building Effective AI Agents", December 2024); the phrases drawn are asserted against the body.
Every box is neutral: an operation or an agent is never a layer, so no role colour applies.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("**Sequential pipeline.**", "parse, then analyse, then format", "The risk is latency",
               "**Fan-out and fan-in (map-reduce).**", "the merge step is where the bugs collect",
               "**Supervisor and workers.**", "does every worker's job itself",
               "The first two are workflows in Anthropic's sense", "The supervisor is where the model starts choosing the next step"):
    assert phrase in BODY, phrase

fig = Figure(
    "02-three-topologies", "Only the supervisor lets the model pick the next step",
    "Three panels of neutral boxes. Sequential pipeline: A parse, B analyse and C format in a chain, each output the "
    "next input; risk, the latency adds up. Fan-out and fan-in: a parent sends the same kind of task to workers 1, 2 "
    "and N in parallel, and a merge step combines their results; risk, the merge step. Supervisor and workers: a "
    "supervisor exchanges calls and results with three workers in a loop; risk, it does the work itself. The first "
    "two are marked as workflows, control flow in code; the supervisor as the next step chosen by the model.",
    subtitle="Three ways to wire sub-agents. The engineer writes the control flow of the first two.",
    height=540, data_w=True)

panels = fig.row(3)


def blk(cx, y, w, label, h=40, dash=None):
    b = Box(cx - w / 2, y, w, h)
    fig.fill(b, "neutral-soft", radius=8, fit=False)
    fig.outline(b, "border" if dash is None else "ink-muted", radius=8, dash=dash)
    fig.text(b.cx, b.y + 25, label, "label", anchor="middle")
    return b


def footer(p, risk, kind, model_side=False):
    fig.text(p.x, 412, risk, "note")
    tag = Box(p.x, 432, p.w, 40)
    fig.outline(tag, "ink-muted" if model_side else "border", radius=8, dash="lead" if model_side else None)
    fig.text(tag.x + 16, tag.y + 25, kind, "label")


# 1. Sequential
p = fig.panel(panels[0], "Sequential pipeline")
cx = p.cx
seq = [blk(cx, 152, 272, "A: parse"), blk(cx, 232, 272, "B: analyse"), blk(cx, 312, 272, "C: format")]
fig.chain(seq)
footer(panels[0], "Risk: the latency adds up", "workflow: flow in code")

# 2. Fan-out and fan-in
p = fig.panel(panels[1], "Fan-out and fan-in")
cx = p.cx
par = blk(cx, 152, 272, "parent")
ws = [blk(cx + dx, 232, 80, lab) for dx, lab in ((-96, "worker 1"), (0, "worker 2"), (96, "worker N"))]
mer = blk(cx, 312, 272, "merge")
for w in ws:
    fig.arrow((w.cx, par.bottom + 2), (w.cx, w.y - 2))
    fig.arrow((w.cx, w.bottom + 2), (w.cx, mer.y - 2))
footer(panels[1], "Risk: the merge step", "workflow: flow in code")

# 3. Supervisor
p = fig.panel(panels[2], "Supervisor and workers")
cx = p.cx
sup = blk(cx, 152, 272, "supervisor model")
ws = [blk(cx + dx, 296, 80, lab) for dx, lab in ((-96, "worker 1"), (0, "worker 2"), (96, "worker 3"))]
for w in ws:
    fig.arrow((w.cx - 12, sup.bottom + 2), (w.cx - 12, w.y - 2))
    fig.arrow((w.cx + 12, w.y - 2), (w.cx + 12, sup.bottom + 2))
fig.text(panels[2].x, 368, "calls and results, call by call", "note")
footer(panels[2], "Risk: it does the work itself", "the model picks the next step", model_side=True)

fig.caption("Start with a sequential or fan-out design; use a supervisor when the split cannot be planned.")
fig.write()
