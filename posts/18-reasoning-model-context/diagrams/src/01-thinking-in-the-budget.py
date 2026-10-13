"""Post 18, hero (sections 1 and 4): one hard turn budgeted with a thinking line at three effort levels.

Run from the series root:  uv run python posts/18-reasoning-model-context/diagrams/src/01-thinking-in-the-budget.py
Writes posts/18-reasoning-model-context/diagrams/01-thinking-in-the-budget.svg.

Where every number comes from: snippets/thinking_budget.py (LAYERS, ANSWER, THINKING, RATE, turn_cost),
imported and asserted against the values that script prints and section 4 quotes. The token counts are
illustrative, so every segment has a dashed outline and the subtitle says so. Prices: Claude Opus 4.6,
Anthropic "Pricing", as of early 2026 (consulted October 2026, as post 05 quotes them).
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, num  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "thinking_budget.py"
M = runpy.run_path(str(SNIP), run_name="snippet")
LAYERS, ANSWER, THINKING, RATE = M["LAYERS"], M["ANSWER"], M["THINKING"], M["RATE"]
assert [t for _, t in LAYERS] == [3000, 1600, 1200, 2500, 2000, 200]
assert ANSWER == 1500 and THINKING == {"low": 1000, "medium": 4000, "high": 16000}
assert RATE == {"input": 5.00, "output": 25.00}
INPUT = sum(t for _, t in LAYERS)
assert INPUT == 10_500
COST = {k: M["turn_cost"](v, ANSWER) for k, v in THINKING.items()}
# the values the snippet prints and the post quotes
assert [f"{COST[k]['total']:.5f}" for k in THINKING] == ["0.09430", "0.16930", "0.46930"]
SHARE = {k: v / (v + ANSWER) for k, v in THINKING.items()}
assert [f"{SHARE[k]:.1%}" for k in THINKING] == ["40.0%", "72.7%", "91.4%"]
RATIO = COST["high"]["total"] / COST["low"]["total"]
assert f"{RATIO:.2f}" == "4.98"
assert RATE["output"] / RATE["input"] == 5

ROLE = ["stable", "stable", "turn", "turn", "history", "user"]

fig = Figure(
    "01-thinking-in-the-budget", "At high effort, thinking outweighs the whole prompt",
    "Three horizontal bars budget one hard agent turn on Claude Opus 4.6 at low, medium and high effort, drawn "
    "to one token scale with dashed outlines because every count is illustrative. Each bar starts with the "
    "same 10,500 input tokens, split by layer: 01 System prompt 3,000, 02 Tools and MCP descriptions 1,600, "
    "03 Memory and state 1,200, 04 Retrieved chunks 2,500, 05 Conversation history 2,000 and 06 User "
    "instruction 200. Then come the thinking tokens, 1,000 at low, 4,000 at medium and 16,000 at high effort, "
    "and a 1,500-token answer. The turn costs $0.09430, $0.16930 and $0.46930, and thinking is 40.0%, 72.7% "
    "and 91.4% of the output. A note states that high effort costs 4.98 times low effort.",
    subtitle="One hard turn on Claude Opus 4.6; dashed outlines mark illustrative counts; prices as of early 2026.",
    data_w=True)

X0 = 200                       # bar origin
SCALE = 528 / (INPUT + THINKING["high"] + ANSWER)
BAR_H = 48
ROWS = [("low", 136, "Low effort"), ("medium", 216, "Medium effort"), ("high", 296, "High effort")]

# heading over the input segments of the first bar
with fig.data():
    fig.text(X0 + INPUT * SCALE / 2, 128, f"input, {num(INPUT)} tokens", "note", anchor="middle", snap=False)

for level, y, name in ROWS:
    fig.text(40, y + 20, name, "head")
    fig.text(40, y + 40, f"thinking {num(THINKING[level])}", "note")
    x = X0
    with fig.data():
        for (lname, tokens), role in zip(LAYERS, ROLE):
            w = tokens * SCALE
            b = Box(x, y, w, BAR_H)
            fig.fill(b, f"{role}-soft", fit=False)
            fig.outline(b, f"{role}-line", width=1, dash="proj")
            x += w
        tw = THINKING[level] * SCALE
        tb = Box(x, y, tw, BAR_H)
        fig.fill(tb, "neutral-soft", fit=False)
        fig.outline(tb, "ink", width=1.5, dash="proj")
        if tw > 160:
            fig.text(x + tw / 2, y + 29, f"{num(THINKING[level])} thinking tokens", "label", anchor="middle",
                     snap=False)
        elif tw > 56:
            fig.text(x + tw / 2, y + 29, num(THINKING[level]), "label", anchor="middle", snap=False)
        x += tw
        ab = Box(x, y, ANSWER * SCALE, BAR_H)
        fig.fill(ab, "ink-muted", fit=False)
        fig.outline(ab, "ink", width=1.5, dash="proj")
        x += ANSWER * SCALE
        fig.text(x + 12, y + 20, f"${COST[level]['total']:.5f}", "value", bold=(level == "high"), snap=False)
        fig.text(x + 12, y + 40, f"thinking {SHARE[level]:.1%} of output", "note", snap=False)

fig.legend(40, 392, [
    dict(color="stable-soft", label="01 and 02, stable prefix"),
    dict(color="turn-soft", label="03 and 04"),
    dict(color="history-soft", label="05 history"),
    dict(color="user-soft", label="06 user instruction"),
], direction="row")
fig.legend(40, 424, [
    dict(color="ink", label="thinking, billed as output", mark="dashed-outline", dash="proj"),
    dict(color="ink-muted", label=f"answer, {num(ANSWER)} tokens, billed as output"),
], direction="row")
fig.text(40, 464, f"High effort costs {RATIO:.2f} times low effort; the input costs the same in every row.", "label")
fig.caption("Thinking is billed at the output rate, five times the input rate on this model.")
fig.write()
