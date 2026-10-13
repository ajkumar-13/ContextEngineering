"""Post 26 hero: the repository's files and the layer of the window each one feeds.

Run from the series root:  uv run python posts/26-modern-agentic-workflow/diagrams/src/00-hero-modern-agentic-workflow.py
Writes posts/26-modern-agentic-workflow/diagrams/00-hero-modern-agentic-workflow.svg.
No numbers are drawn. The file names are Claude Code's, as sections 3 to 6 of index.md cite them (`.mcp.json`
from "Connect Claude Code to tools via MCP", consulted October 2026); every phrase drawn is asserted against the
body. Layer names and roles are notation_guide.md's and ctx_fig_design.md section 0's; the sub-agent window and
the hook are neutral (an operation or a piece of code is never a layer).
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("selected into layer 01, the system prompt, every session",
               "skill descriptions are loaded into context so Claude knows what's available, but full skill content only loads when invoked",
               "loaded on demand via tool search", "returns only the summary",
               "The model sees only what the hook chooses to say", "Automatic compaction of layer 05",
               "`.claude/skills/<skill-name>/SKILL.md`", "`.claude/agents/`", "`.claude/settings.json`",
               "Sub-agents run in windows of their own; hooks run as code outside the window"):
    assert phrase in BODY, phrase

LAYERS = ["01 System prompt", "02 Tools and MCP descriptions", "03 Memory and state",
          "04 Retrieved chunks", "05 Conversation history", "06 User instruction"]
ROLE = ["stable", "stable", "turn", "turn", "history", "user"]

fig = Figure(
    "00-hero-modern-agentic-workflow", "The repository configures the window",
    "Left, five files of a repository in Claude Code's names. Right, the six-layer window, 01 System prompt at the "
    "top to 06 User instruction at the bottom. AGENTS.md or CLAUDE.md is selected into layer 01 every session. The "
    "skills' SKILL.md files reach layer 01 as descriptions, with each body loaded on demand. The MCP servers in "
    ".mcp.json reach layer 02 through tool search. Sub-agent definitions start a separate sub-agent window, which "
    "returns only a summary to layer 05. Hook settings run hooks as code outside the window; only their messages "
    "reach layer 05. Layer 05 is marked compress, for compaction.",
    subtitle="Each file reaches the window by one operation, or acts from outside it. Claude Code's file names.",
    height=540, data_w=True)

# the six-layer window, right
SX, SW, SY, BH, STEP = 600, 320, 112, 48, 56
bands = []
for k, (label, role) in enumerate(zip(LAYERS, ROLE)):
    b = Box(SX, SY + k * STEP, SW, BH)
    fig.fill(b, f"{role}-soft", radius=8, fit=False)
    fig.outline(b, f"{role}-line", radius=8)
    fig.text(SX + 16, b.y + 29, label, "label")
    bands.append(b)
fig.text(SX + SW - 16, bands[4].y + 29, "compress", "note", anchor="end")
assert "compress" in BODY

# the repository's files, left, each with the operation that brings it into the window
CX, CW = 40, 296


def file_card(y, name, how):
    b = Box(CX, y, CW, 64)
    fig.fill(b, "neutral-soft", radius=8, fit=False)
    fig.outline(b, "border", radius=8)
    fig.text(CX + 16, y + 26, name, "code")
    fig.text(CX + 16, y + 50, how, "note")
    return b


rules = file_card(112, "AGENTS.md or CLAUDE.md", "select: every session")
skills = file_card(184, ".claude/skills/*/SKILL.md", "select: description, then body")
mcp = file_card(256, ".mcp.json", "select: tool search")
agents = file_card(328, ".claude/agents/*.md", "isolate: summary back")
hooks = file_card(400, ".claude/settings.json", "hooks: messages back")


def mid_box(y, head, line, dash=None):
    b = Box(376, y, 184, 64)
    fig.fill(b, "surface", radius=8, fit=False)
    fig.outline(b, "ink-muted", radius=8, dash=dash)
    fig.text(b.x + 16, y + 26, head, "label")
    fig.text(b.x + 16, y + 50, line, "note")
    return b


sub = mid_box(328, "sub-agent window", "its own loop")
code = mid_box(400, "hook", "code, not context", dash="lead")

fig.arrow((rules.right + 2, 140), (SX - 2, 140))
fig.arrow((skills.right + 2, 212), (SX - 2, 152))
fig.arrow((mcp.right + 2, 284), (SX - 2, 200))
fig.arrow((agents.right + 2, 360), (sub.x - 2, 360))
fig.arrow((sub.right + 2, 360), (SX - 2, 360))
fig.arrow((hooks.right + 2, 432), (code.x - 2, 432))
fig.arrow((code.right + 2, 424), (SX - 2, 376))

fig.caption("Sub-agents and hooks work outside the window; only a summary or a message comes back in.")
fig.write()
