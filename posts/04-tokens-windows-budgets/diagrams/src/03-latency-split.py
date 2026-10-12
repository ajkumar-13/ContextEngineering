"""Post 04, section 3: for the support agent's call, decode takes longer than prefill at every class.

Run from the series root:  uv run python posts/04-tokens-windows-budgets/diagrams/src/03-latency-split.py
Writes posts/04-tokens-windows-budgets/diagrams/03-latency-split.svg.

Where every number comes from: snippets/envelope.py (imported): the call's 10,500 input and 400 output tokens
(LAYERS, OUT_TOKENS) and the illustrative per-token rates (LATENCY_MS); the times are computed with its
wall_time() and asserted against the values section 3 quotes from the snippet's output. The rates are
illustrative, so every bar has a dashed outline and the subtitle says so.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "envelope.py"
ENV = runpy.run_path(str(SNIP), run_name="snippet")
N_IN, N_OUT = sum(ENV["LAYERS"].values()), ENV["OUT_TOKENS"]
assert (N_IN, N_OUT) == (10_500, 400)
RATES = ENV["LATENCY_MS"]
ROWS = []
for cls, (p, d) in RATES.items():
    pre, dec = N_IN * p / 1000, N_OUT * d / 1000
    assert abs(pre + dec - ENV["wall_time"](N_IN, N_OUT, p, d)) < 1e-12
    ROWS.append((cls, p, d, pre, dec))
assert [(f"{r[3]:.2f}", f"{r[4]:.2f}", f"{r[3] + r[4]:.2f}") for r in ROWS] == [
    ("1.05", "3.20", "4.25"), ("2.10", "6.40", "8.50"), ("4.20", "12.80", "17.00")]

assert round(N_IN / N_OUT) == 26                                   # the caption's "26 times longer"
assert all(round(r[4] / r[3]) == 3 for r in ROWS)                  # and "three times as long"

fig = Figure(
    "03-latency-split", "Decode outlasts prefill at every model class",
    "Three horizontal bars on a seconds axis from 0 to 20, one per model class, for one call of 10,500 input "
    "and 400 output tokens at illustrative per-token rates, each split into prefill and decode: cheap, 0.1 and "
    "8 ms per token, 1.05 plus 3.20 seconds, 4.25 in all; mid, 0.2 and 16 ms, 2.10 plus 6.40, 8.50; frontier, "
    "0.4 and 32 ms, 4.20 plus 12.80, 17.00. Every bar has a dashed outline because the rates are illustrative.",
    subtitle="One call of 10,500 input and 400 output tokens; per-token rates illustrative, not measured.",
    data_w=True)

LBL, X0, X1, HI = 40, 216, 736, 20.0
sx = lambda v: X0 + (X1 - X0) * v / HI  # noqa: E731
fig.legend(LBL, 128, [dict(color="ink-muted", label="prefill: reads the 10,500-token prompt",
                           mark="dashed-outline", dash="proj"),
                      dict(color="border", label="decode: writes the 400-token answer", mark="swatch")],
           direction="row", gap=40)
TOP, STEP, BH = 168, 88, 40
AX = TOP + STEP * len(ROWS) - 24
with fig.data():
    for t in (0, 5, 10, 15, 20):
        fig.edge((sx(t), TOP - 8), (sx(t), AX), color="grid", width=0.75)
        fig.text(sx(t), AX + 20, f"{t}", "tick", anchor="middle", snap=False)
    for i, (cls, p, d, pre, dec) in enumerate(ROWS):
        y = TOP + STEP * i
        b_pre = Box(sx(0), y, sx(pre) - sx(0), BH)
        b_dec = Box(sx(pre), y, sx(pre + dec) - sx(pre), BH)
        fig.fill(b_dec, "border", fit=False)
        fig.outline(b_pre, "ink-muted", width=1, dash="proj")
        fig.outline(b_dec, "ink-muted", width=1, dash="proj")
        fig.text(LBL, y + 18, f"{cls}, ms per token", "label", snap=False)
        fig.text(LBL, y + 36, f"prefill {p:g}, decode {d:g}", "note", snap=False)
        fig.text(sx(pre + dec) + 12, y + 26, f"{pre:.2f} + {dec:.2f} = {pre + dec:.2f} s", "value", snap=False)
    fig.edge((X0, TOP - 8), (X0, AX), color="ink-muted", width=1)
fig.text((X0 + X1) / 2, AX + 44, "seconds", "note", anchor="middle")

fig.caption("The prompt is 26 times longer than the answer, yet the answer takes three times as long.")
fig.write()
