"""Post 18, figure 3 (section 6): one tool-use turn with interleaved thinking, and its three requests.

Run from the series root:  uv run python posts/18-reasoning-model-context/diagrams/src/03-interleaved-tool-turn.py
Writes posts/18-reasoning-model-context/diagrams/03-interleaved-tool-turn.svg.

Where every number comes from: snippets/trace_cache.py (BASE, STEPS, tool_turn), imported and asserted against
the table that script prints and section 6 quotes. Token counts are illustrative, so the bars and the thinking
blocks have dashed outlines and the subtitle says so. Turn structure and caching of thinking blocks: Anthropic,
"Thinking" and "Prompt caching", consulted October 2026.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, num  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "trace_cache.py"
M = runpy.run_path(str(SNIP), run_name="snippet")
STEPS = M["STEPS"]
assert STEPS == [(1200, 100, 800), (900, 100, 600), (700, 400, 0)]
ROWS = M["tool_turn"]()
assert ROWS == [(10500, 4600, 5900), (12600, 10500, 2100), (14200, 12600, 1600)]
THINK = sum(t for t, _, _ in STEPS)
OUT = sum(t + c for t, c, _ in STEPS)
assert (THINK, OUT, f"{THINK / OUT:.1%}") == (2800, 3400, "82.4%")

# The turn's blocks in the order they occur: (kind, label, tokens)
BLOCKS = []
for k, (think, call, result) in enumerate(STEPS):
    BLOCKS.append(("thinking", "thinking", think))
    if result:
        BLOCKS += [("call", "tool call", call), ("result", "tool result", result)]
    else:
        BLOCKS.append(("answer", "answer", call))
assert [b[2] for b in BLOCKS] == [1200, 100, 800, 900, 100, 600, 700, 400]

fig = Figure(
    "03-interleaved-tool-turn", "Each step of a tool loop reads the last request",
    "Top: one tool-use turn on Claude Opus 4.6 as a row of blocks in the order they occur, with illustrative "
    "token counts: thinking 1,200, tool call 100, tool result 800, thinking 900, tool call 100, tool result "
    "600, thinking 700, answer 400. Each thinking block opens step 1, 2 or 3 of the turn. Bottom: "
    "the three requests drawn to one token scale with dashed outlines. Request 1 sends 10,500 input tokens, "
    "4,600 read from the cache and 5,900 new; request 2 sends 12,600, 10,500 read and 2,100 new; request 3 "
    "sends 14,200, 12,600 read and 1,600 new. A note states that the turn's output is 3,400 tokens, 2,800 of "
    "them thinking in three segments.",
    subtitle="One tool-use turn on Claude Opus 4.6, blocks passed back unchanged; token counts illustrative.",
    data_w=True)

STYLE = {  # kind -> (fill, outline, dash)
    "thinking": ("neutral-soft", "ink", "proj"),
    "call": ("history-soft", "history-line", None),
    "result": ("history-soft", "history-line", None),
    "answer": ("ink-muted", "ink-muted", None),
}
L, R, GAP = 40, 920, 8
CW = (R - L - GAP * (len(BLOCKS) - 1)) / len(BLOCKS)
Y, H = 132, 56
req = 0
with fig.data():
    for i, (kind, label, tokens) in enumerate(BLOCKS):
        x = L + i * (CW + GAP)
        b = Box(x, Y, CW, H)
        fill, line, dash = STYLE[kind]
        fig.fill(b, fill, fit=False)
        fig.outline(b, line, width=1.5 if kind == "thinking" else 1, dash=dash)
        col = "surface" if kind == "answer" else None
        fig.text(b.cx, Y + 24, label, "label", anchor="middle", color=col, snap=False)
        fig.text(b.cx, Y + 44, num(tokens), "label", anchor="middle", color=col, snap=False)
        if kind == "thinking":
            req += 1
            fig.text(x, Y - 12, f"step {req}", "note", snap=False)

# The three requests, to one token scale.
fig.text(40, 236, "Input of each request, tokens", "head")
X0 = 200
SCALE = (R - 120 - X0) / ROWS[-1][0]
for k, (request, read, new) in enumerate(ROWS):
    y = 256 + 60 * k
    fig.text(40, y + 26, f"request {k + 1}", "label")
    with fig.data():
        rb = Box(X0, y, read * SCALE, 40)
        fig.fill(rb, "stable-soft", fit=False)
        fig.outline(rb, "stable", width=1, dash="proj")
        fig.text(rb.cx, y + 26, num(read), "label", anchor="middle", color="stable-ink", snap=False)
        nb = Box(X0 + read * SCALE, y, new * SCALE, 40)
        fig.fill(nb, "neutral-soft", fit=False)
        fig.outline(nb, "ink-muted", width=1, dash="proj")
        fig.text(nb.cx, y + 26, num(new), "label", anchor="middle", snap=False)
        fig.text(nb.right + 12, y + 26, num(request), "value", snap=False)

fig.legend(40, 452, [
    dict(color="stable", label="read from the cache", mark="dashed-outline", dash="proj"),
    dict(color="ink-muted", label="new in this request", mark="dashed-outline", dash="proj"),
    dict(color="history-soft", label="tool call or result"),
], direction="row")
fig.caption(f"The turn's output is {num(OUT)} tokens, {num(THINK)} of them thinking in three segments.")
fig.write()
