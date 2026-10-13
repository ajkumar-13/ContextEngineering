"""Post 26, section 5: the four-step handshake between a parent agent and a sub-agent.

Run from the series root:  uv run python posts/26-modern-agentic-workflow/diagrams/src/02-orchestrator-handshake.py
Writes posts/26-modern-agentic-workflow/diagrams/02-orchestrator-handshake.svg.
No numbers are drawn except the step numbers. The four steps, the turn cap and the sample review are section 5
of index.md (after Claude Code's "Create custom subagents" and post 13); the phrases are asserted against the
body. Every box is neutral: an agent is never a layer.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("The parent (1) frames a scoped task and names the result it expects",
               "(2) spawns the sub-agent with a fresh window, only the tools the task needs and a turn cap",
               "the sub-agent (3) runs its own loop of reads, tool calls and retries in isolation",
               "the parent (4) folds only the returned summary into its window",
               "It never sees the child's intermediate calls", "**Review transcripts on a sample.**",
               "A summary can hide a skipped test"):
    assert phrase in BODY, phrase

fig = Figure(
    "02-orchestrator-handshake", "The parent sees the brief and the summary, nothing else",
    "Two lanes, the parent's window above and the sub-agent's window below, across four steps. Step 1, parent: "
    "frame the task and the shape of the result. Step 2, parent: spawn with a fresh window, scoped tools and a turn "
    "cap. Step 3, sub-agent: its own loop in isolation, drawn as read, search, run tests, read log and edit, none of "
    "which reaches the parent. Step 4, "
    "parent: fold in the summary only. Arrows: the brief from step 2 down to step 3, the summary from step 3 up to step 4. The "
    "caption says to review sub-agent transcripts on a sample, because a summary can hide a skipped test.",
    subtitle="Delegation in four steps. The child's intermediate calls never reach the parent's window.",
    height=540, data_w=True)

LX = 40
lanes = {"parent": Box(LX, 104, 880, 148), "child": Box(LX, 300, 880, 164)}
for key, label in (("parent", "parent's window"), ("child", "sub-agent's window")):
    lane = lanes[key]
    fig.fill(lane, "neutral-soft", radius=8, fit=False)
    fig.outline(lane, "border", radius=8)
    fig.text(LX + 16, lane.y + 28, label, "head")


def step(x, w, lane, head, lines, h=88):
    b = Box(x, lanes[lane].y + 44, w, h)
    fig.fill(b, "surface", radius=8, fit=False)
    fig.outline(b, "ink-muted", radius=8)
    fig.text(x + 16, b.y + 26, head, "head")
    for k, line in enumerate(lines):
        fig.text(x + 16, b.y + 50 + 22 * k, line, "note")
    return b


s1 = step(56, 176, "parent", "1 Frame", ["the task and the", "result's shape"])
s2 = step(256, 176, "parent", "2 Spawn", ["fresh window,", "scoped tools, cap"])
s4 = step(720, 184, "parent", "4 Fold in", ["the summary", "only"])
s3 = step(456, 448, "child", "3 Own loop, in isolation", [], h=108)
# the child's intermediate calls, which stay in its window
CHIPS = ["read", "search", "run tests", "read log", "edit"]
for k, chip in enumerate(CHIPS):
    c = Box(s3.x + 16 + k * 84, s3.y + 40, 76, 32)
    fig.fill(c, "neutral-soft", radius=4, fit=False)
    fig.outline(c, "border", radius=4)
    fig.text(c.cx, c.y + 21, chip, "label", anchor="middle")

fig.arrow((s1.right + 2, s1.cy), (s2.x - 2, s2.cy))
fig.arrow((s2.cx, s2.bottom + 2), (s3.x - 2, s3.y + 56), via=[(s2.cx, s3.y + 56)])
fig.arrow((s4.cx, s3.y - 2), (s4.cx, s4.bottom + 2))
fig.text(s2.cx + 8, 284, "the brief", "note")
fig.text(s3.x + 16, s3.y + 96, "None of these calls reaches the parent.", "note")
fig.text(s4.cx - 8, 284, "the summary", "note", anchor="end")

fig.caption("Review transcripts on a sample: a summary can hide a skipped test.")
fig.write()
