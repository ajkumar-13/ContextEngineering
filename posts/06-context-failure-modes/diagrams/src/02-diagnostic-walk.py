"""Post 06, section 7: the five diagnostic questions, asked in order, and the mode each yes names.

Run from anywhere:  python posts/06-context-failure-modes/diagrams/src/02-diagnostic-walk.py
Writes posts/06-context-failure-modes/diagrams/02-diagnostic-walk.svg.
No numbers are drawn. The questions, the modes, the place to look first and the fall-through are section 7 of
index.md; each question is a shortened form of the numbered list there, whose bold lines are asserted below.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")

# (question as drawn, the bold question of section 7, mode, where to look first)
STEPS = [
    ("Is the answer fluent but off topic?", "**Is the answer fluent but off topic?** Distraction.",
     "Distraction", "the retrieved set, then the system prompt"),
    ("Does it break a clearly stated rule or misuse a tool?",
     "**Does the answer break a rule, or misuse a tool, that the window states clearly?** Confusion.",
     "Confusion", "the system prompt and tool descriptions"),
    ("Do two parts of the window disagree?",
     "**Do two parts of the window disagree, or does the answer contradict itself or an earlier turn?** Conflict.",
     "Conflict", "memory and retrieval, for a precedence rule"),
    ("Does quality drop only on long inputs?",
     "**Does quality drop only when the input is long, although the relevant content is in it?** "
     "Lost-in-the-middle.", "Lost-in-the-middle", "the packing order, then the length"),
    ("Do tool calls pile up without progress?",
     "**Is the trace full of tool calls that make no progress?** Tool-storm.",
     "Tool-storm", "the catalogue and the loop cap"),
]
for _, bold, _, _ in STEPS:
    assert bold in BODY, bold
for phrase in ("Look at the retrieved set first and the system prompt second.",
               "Audit the system prompt and the tool descriptions for ambiguity.",
               "Look in memory and retrieval for two sources that disagree with no precedence rule.",
               "Pack with bookends; otherwise compress.", "Trim the catalogue, or cap the loop.",
               "A report that earns none is, by this series' rule, not a context problem but a model problem",
               "first rule out the faults that the logs show directly"):
    assert phrase in BODY, phrase

desc = "A walk of five numbered questions down a spine, asked in order after systems faults are ruled out. "
for i, (q, _, mode, look) in enumerate(STEPS, 1):
    desc += f"Question {i}, {q} Yes leads right to {mode}: look at {look}. "
desc += ("Every question is asked in turn, whatever the answer before; a report with no yes reaches a dashed box: none of the five, "
         "a model problem, not a context problem.")

fig = Figure("02-diagnostic-walk", "Five questions, asked in order, name the mode", desc,
             subtitle="Systems faults in the logs are ruled out first; each yes names a mode and the place to look first.",
             height=720, data_w=True)

Q_X, Q_W, BOX_H, GAP = 40, 432, 72, 24      # question boxes on the spine
M_X, M_W = 568, 352                          # mode boxes on the right
tops = [104 + i * (BOX_H + GAP) for i in range(len(STEPS) + 1)]

for i, (q, _, mode, look) in enumerate(STEPS):
    qb = Box(Q_X, tops[i], Q_W, BOX_H)
    fig.fill(qb, "neutral-soft", radius=8, fit=False)
    fig.outline(qb, "border", radius=8)
    fig.text(Q_X + 16, tops[i] + 42, str(i + 1), "head", color="ink-muted")
    fig.text(Q_X + 48, tops[i] + 42, q, "label")
    mb = Box(M_X, tops[i], M_W, BOX_H)
    fig.outline(mb, "rule", radius=8)
    fig.text(M_X + 16, tops[i] + 32, mode, "head")
    fig.text(M_X + 16, tops[i] + 56, f"look at {look}", "note")
    fig.arrow((qb.right + 8, qb.cy), (mb.x - 8, mb.cy), label="yes")
    fig.arrow((Q_X + 64, qb.bottom + 2), (Q_X + 64, tops[i + 1] - 2))
    fig.text(Q_X + 76, qb.bottom + 16, "then" if i < len(STEPS) - 1 else "no yes at all", "note")

end = Box(Q_X, tops[-1], Q_W, BOX_H)
fig.outline(end, "ink-muted", radius=8, dash="lead")
fig.text(Q_X + 16, tops[-1] + 32, "None of the five: a model problem", "head")
fig.text(Q_X + 16, tops[-1] + 56, "not a context problem (post 01, section 5)", "note")

fig.caption("A report can earn two yeses; then both modes are present and both first fixes apply.")
fig.write()
