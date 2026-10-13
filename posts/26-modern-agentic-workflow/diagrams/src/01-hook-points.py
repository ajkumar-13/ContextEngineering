"""Post 26, section 6: where Claude Code's hook events fire on the agent loop, and which of them can block.

Run from the series root:  uv run python posts/26-modern-agentic-workflow/diagrams/src/01-hook-points.py
Writes posts/26-modern-agentic-workflow/diagrams/01-hook-points.svg.
No numbers are drawn except exit codes 0 and 2. Event names and what exit code 2 does at each are from
Anthropic, "Hooks reference" (Claude Code documentation, consulted October 2026), as section 6 of index.md
states them; the phrases are asserted against the body. Every box is neutral: no layer is drawn. The three events
that can block carry the emphasis outline.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("\"Exit with code 2 to block the action\"", "which before a tool call blocks it and tells the model why",
               "after a tool call (the tool has already run) is shown to the model", "\"a non-blocking error\"",
               "**`SessionStart`.** Claude Code adds such a hook's plain-text output \"to Claude's context\"",
               "`SessionEnd` cannot block, while `PreCompact` exiting 2 blocks compaction",
               "PreToolUse, UserPromptSubmit and PreCompact can block"):
    assert phrase in BODY, phrase

fig = Figure(
    "01-hook-points", "Only a hook in front of an action can stop it",
    "The agent loop left to right: session start, user prompt, then a loop of a model call and the tool it runs, "
    "with the tool call going right and the result coming back, then session end. Hook events attached by dashed "
    "leaders. Above, emphasised: UserPromptSubmit, which can block the prompt, and PreToolUse, on the tool call, "
    "which can block the call. Below: SessionStart, whose output enters the context; PreCompact, on the model call, "
    "emphasised, which can block compaction; PostToolUse, on the result, which reports to the model after the tool has run; SessionEnd, "
    "which cannot block. A note says exit code 2 blocks where the event can block and any other non-zero code does not.",
    subtitle="Claude Code's hook events on the agent loop, and what an exit code of 2 does at each.",
    height=540, data_w=True)


def step(x, w, label):
    b = Box(x, 232, w, 56)
    fig.fill(b, "neutral-soft", radius=8, fit=False)
    fig.outline(b, "border", radius=8)
    fig.text(b.cx, b.y + 33, label, "label", anchor="middle")
    return b


start = step(40, 128, "session start")
prompt = step(200, 128, "user prompt")
loop = Box(360, 200, 400, 120)
fig.outline(loop, "ink-muted", radius=8, dash="lead")
fig.text(loop.x + 16, loop.y + 22, "the loop", "note")
model = step(384, 136, "model call")
tool = step(600, 136, "tool runs")
end = step(792, 128, "session end")

fig.arrow((start.right + 2, 260), (prompt.x - 2, 260))
fig.arrow((prompt.right + 2, 260), (loop.x - 2, 260))
fig.arrow((model.right + 2, 248), (tool.x - 2, 248))
fig.arrow((tool.x - 2, 272), (model.right + 2, 272))
fig.arrow((loop.right + 2, 260), (end.x - 2, 260))


def tag(x, y, event, note, blocks=False):
    b = Box(x, y, 200, 64)
    fig.fill(b, "surface", radius=8, fit=False)
    fig.outline(b, "ink-muted" if blocks else "border", radius=8, width=2.5 if blocks else 1)
    fig.text(x + 16, y + 26, event, "code")
    fig.text(x + 16, y + 50, note, "note")
    return b


# events that can block, above the loop
tag(164, 104, "UserPromptSubmit", "can block the prompt", blocks=True)
fig.leader((264, 168), (264, prompt.y - 2))
tag(460, 104, "PreToolUse", "can block the call", blocks=True)
fig.leader((536, 168), (536, 244))

# events that cannot block, below the loop
tag(40, 368, "SessionStart", "output enters context")
fig.leader((104, 368), (104, start.bottom + 2))
tag(256, 368, "PreCompact", "can block compaction", blocks=True)
fig.leader((416, 368), (416, model.bottom + 2))
tag(472, 368, "PostToolUse", "reports; tool has run")
fig.leader((584, 368), (584, 276))
tag(720, 368, "SessionEnd", "cannot block")
fig.leader((856, 368), (856, end.bottom + 2))

fig.text(40, 464, "Exit code 2 blocks where the event can block; any other non-zero code is a non-blocking error.", "note")
fig.caption("A policy hook sits in front of the action and exits 2.")
fig.write()
