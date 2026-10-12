"""Post 04, hero (sections 2 and 5): one call of the support agent against the context window.

Run from the series root:  uv run python posts/04-tokens-windows-budgets/diagrams/src/01-window-and-budget.py
Writes posts/04-tokens-windows-budgets/diagrams/01-window-and-budget.svg.

Where every number comes from:
- The token count of each layer and of the output: snippets/envelope.py (LAYERS, OUT_TOKENS), imported and
  asserted against the values section 5 states. They are illustrative, so the segments are drawn with dashed
  outlines and the subtitle says so.
- The window, 200,000 tokens for Claude Sonnet 4.5: Anthropic, "Context windows", consulted October 2026, as
  section 2 cites it (listed in the table below and asserted).
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, num  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "envelope.py"
ENV = runpy.run_path(str(SNIP), run_name="snippet")
LAYERS, OUT = ENV["LAYERS"], ENV["OUT_TOKENS"]
assert list(LAYERS.values()) == [3000, 1600, 1200, 2500, 2000, 200] and OUT == 400

CITED = {"window, Claude Sonnet 4.5": (200_000, 'Anthropic, "Context windows", consulted October 2026')}
WINDOW = CITED["window, Claude Sonnet 4.5"][0]
assert WINDOW == 200_000

TOTAL_IN = sum(LAYERS.values())
CALL = TOTAL_IN + OUT
assert TOTAL_IN == 10_500 and CALL == 10_900 and WINDOW - CALL == 189_100

ROLE = ["stable", "stable", "turn", "turn", "history", "user"]
NAMES = [["System prompt"], ["Tools and MCP", "descriptions"], ["Memory and", "state"], ["Retrieved chunks"],
         ["Conversation", "history"]]

fig = Figure(
    "01-window-and-budget", f"One call spends {num(CALL)} of a {num(WINDOW)}-token window",
    "A long bar for the context window of Claude Sonnet 4.5, 200,000 tokens, with a thin slice at its left end "
    "for one call of the support agent, 10,900 tokens, and 189,100 tokens left unused. Dashed connectors enlarge "
    "the slice into a strip of the six layers and the output, each drawn to scale with a dashed outline: "
    "01 System prompt 3,000, 02 Tools and MCP descriptions 1,600, 03 Memory and state 1,200, 04 Retrieved "
    "chunks 2,500, 05 Conversation history 2,000, 06 User instruction 200, and the output 400. Brackets mark layers 01 and 02 as the stable prefix of 4,600 tokens and the six layers as the input of 10,500 tokens.",
    subtitle="Window of Claude Sonnet 4.5 (Anthropic, consulted October 2026); token counts illustrative.",
    data_w=True)

L, R = 40, 920
# The window bar.
fig.text(L, 128, f"Context window: {num(WINDOW)} tokens", "head")
bar = Box(L, 144, R - L, 40)
fig.fill(bar, "neutral-soft", fit=False)
fig.outline(bar, "ink-muted", width=1)
slice_w = (R - L) * CALL / WINDOW
with fig.data():
    sl = Box(L, 144, slice_w, 40)
    fig.fill(sl, "ink-muted", fit=False)
fig.text(L + 64, 168, f"one call, {num(CALL)} tokens", "label")
fig.text(R - 16, 168, f"{num(WINDOW - CALL)} tokens unused", "note", anchor="end")

# The call, enlarged: every layer and the output to one scale.
Y, H = 256, 56
scale = (R - L) / CALL
xs = [L]
for n in list(LAYERS.values()) + [OUT]:
    xs.append(xs[-1] + n * scale)
assert abs(xs[-1] - R) < 1e-9
fig.zoom(sl, Box(L, Y, R - L, H))
with fig.data():
    for k, n in enumerate(list(LAYERS.values()) + [OUT]):
        b = Box(xs[k], Y, xs[k + 1] - xs[k], H)
        role = ROLE[k] if k < 6 else "ink-muted"
        fig.fill(b, f"{role}-soft" if k < 6 else "neutral-soft", fit=False)
        fig.outline(b, f"{role}-line" if k < 6 else "ink-muted", width=1, dash="proj")
        if k < 5:
            fig.text(b.x + 8, Y + 24, f"{k + 1:02d}", "head", snap=False)
            fig.text(b.x + 8, Y + 44, num(n), "label", snap=False)
            for i, line in enumerate(NAMES[k]):
                fig.text(b.cx, Y + 80 + 18 * i, line, "label", anchor="middle", snap=False)
    # 06 and the output are too narrow to hold a label: leaders down to labels below the names.
    x6 = (xs[5] + xs[6]) / 2
    xo = (xs[6] + xs[7]) / 2
    fig.leader((x6, Y + H), (x6, 388))
    fig.leader((xo, Y + H), (xo, 412))
fig.text(884, 404, f"06 User instruction, {num(LAYERS['06 User instruction'])}", "label", anchor="end")
fig.text(R, 428, f"output, {num(OUT)}", "label", anchor="end")
PREFIX = LAYERS["01 System prompt"] + LAYERS["02 Tools and MCP descriptions"]
assert PREFIX == ENV["PREFIX"] == 4600
fig.brace(L, xs[2], 380, f"stable prefix, {num(PREFIX)} tokens", kind="bracket", side="below", color="stable")
fig.brace(L, xs[6], 452, f"input, {num(TOTAL_IN)} tokens", kind="bracket", side="below")

fig.caption("Only the stable prefix repeats on every call, so only it can be read from a cache.")
fig.write()
