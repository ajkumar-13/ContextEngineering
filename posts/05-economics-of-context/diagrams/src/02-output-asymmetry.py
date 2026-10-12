"""Post 05, section 3: the input-output asymmetry. Two calls drawn twice, in tokens and in dollars.

Run from anywhere:  python posts/05-economics-of-context/diagrams/src/02-output-asymmetry.py
Writes posts/05-economics-of-context/diagrams/02-output-asymmetry.svg.
The two calls are the section 3 example (illustrative token counts); the dollars are computed by
snippets/cost_model.py (call_cost at the Claude Sonnet 4.5 rates, Anthropic "Pricing", consulted 12 October 2026)
and asserted against the values it prints and the post quotes.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, num  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "cost_model.py"
M = runpy.run_path(str(SNIP), run_name="snippet")
RATE = M["RATES"]["Claude Sonnet 4.5"]
assert RATE == {"input": 3.00, "output": 15.00}
CALLS = [("Short prompt,", "long answer", 2000, 2500), ("Long prompt,", "short answer", 12000, 200)]
COST = [M["call_cost"](RATE, 0, i, o) for _, _, i, o in CALLS]
assert [f"{c['total']:.5f}" for c in COST] == ["0.04350", "0.03900"]
assert [f"{c['rest']:.5f}" for c in COST] == ["0.00600", "0.03600"]
assert [f"{c['output']:.5f}" for c in COST] == ["0.03750", "0.00300"]
RATIO = RATE["output"] / RATE["input"]
assert RATIO == 5


def usd(v):
    return f"${v:.5f}"


fig = Figure(
    "02-output-asymmetry", "A sixth of the input, and still the dearer call",
    "Two calls on Claude Sonnet 4.5, drawn in tokens on the left and in dollars on the right. The short "
    "prompt sends 2,000 input tokens and gets 2,500 output tokens; the long prompt sends 12,000 input tokens "
    "and gets 200. In dollars the short prompt costs $0.00600 for input plus $0.03750 for output, $0.04350, "
    "and the long prompt $0.03600 plus $0.00300, $0.03900, because an output token costs 5 times an input token.",
    subtitle="Claude Sonnet 4.5: $3 per million input tokens, $15 per million output tokens (Anthropic, 12 October 2026).",
    data_w=True)

TX0, TSCALE = 232, 288 / 12200          # token bars
DX0, DSCALE = 584, 256 / 0.045           # dollar bars
BAR_H = 48
ROW_Y = [168, 280]
STYLE = {"in": ("neutral-soft", "rule"), "out": ("ink-muted", None)}

fig.text(TX0, 144, "Tokens per call", "head")
fig.text(DX0, 144, "Dollars per call", "head")


def bar(x0, y, parts, scale, fmt):
    """parts: [(key, value)]; a value too long for its segment is called out below it."""
    x = x0
    for key, v in parts:
        w = v * scale
        fill, line = STYLE[key]
        b = Box(x, y, w, BAR_H)
        fig.fill(b, fill, fit=False)
        if line:
            fig.outline(b, line)
        s = fmt(v)
        if w >= 8 + 9 * len(s):
            with fig.data():
                fig.text(x + w / 2, y + 29, s, "value", anchor="middle",
                         color="surface" if key == "out" else None, snap=False)
        else:
            fig.callout(b, s, side="below", length=12)
        x += w
    return x


for (l1, l2, tin, tout), c, y in zip(CALLS, COST, ROW_Y):
    fig.text(40, y + 20, l1, "head")
    fig.text(40, y + 40, l2, "head")
    bar(TX0, y, [("in", tin), ("out", tout)], TSCALE, lambda v: num(v))
    end = bar(DX0, y, [("in", c["rest"]), ("out", c["output"])], DSCALE, usd)
    with fig.data():
        fig.text(end + 12, y + 29, usd(c["total"]), "value", bold=(c is COST[0]), snap=False)

for i, (key, label) in enumerate((("in", "input tokens"), ("out", "output tokens"))):
    lx = 40 + 200 * i
    fill, line = STYLE[key]
    sw = Box(lx, 380, 24, 16)
    fig.fill(sw, fill, fit=False)
    if line:
        fig.outline(sw, line)
    fig.text(lx + 36, 393, label, "label")
EQUIV = CALLS[0][3] * RATIO
assert EQUIV == 12500
fig.text(40, 444, f"At 5 times the price, the 2,500 output tokens cost as much as {num(int(EQUIV))} input tokens.",
         "label")
fig.caption("The bill follows the answer: trimming output saves five times what trimming input does, per token.")
fig.write()
