"""Post 05, section 4: when the cache-write premium pays for itself.

Run from anywhere:  python posts/05-economics-of-context/diagrams/src/03-write-premium-break-even.py
Writes posts/05-economics-of-context/diagrams/03-write-premium-break-even.svg.
Every plotted value is computed by snippets/cost_model.py (prefix_cost_over_calls: the 4,600-token prefix of
layers 01 and 02 at the Claude Sonnet 4.5 input price, with the write and read multipliers of Anthropic's
"Prompt caching" page, consulted 12 October 2026) and asserted against the table the script prints.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "cost_model.py"
M = runpy.run_path(str(SNIP), run_name="snippet")
RATE, PREFIX = M["RATES"]["Claude Sonnet 4.5"], M["PREFIX"]
assert PREFIX == 4600  # the prefix size the subtitle and alt text state
run = lambda write, lapsed=False: M["prefix_cost_over_calls"](RATE, PREFIX, 5, write, lapsed)  # noqa: E731
NONE, W5, W1, LAPSED = run(None), run(M["CACHE_WRITE_5M"]), run(M["CACHE_WRITE_1H"]), run(M["CACHE_WRITE_5M"], True)
# the table the snippet prints
assert [f"{v:.5f}" for v in NONE] == ["0.01380", "0.02760", "0.04140", "0.05520", "0.06900"]
assert [f"{v:.5f}" for v in W5] == ["0.01725", "0.01863", "0.02001", "0.02139", "0.02277"]
assert [f"{v:.5f}" for v in W1] == ["0.02760", "0.02898", "0.03036", "0.03174", "0.03312"]
assert [f"{v:.5f}" for v in LAPSED] == ["0.01725", "0.03450", "0.05175", "0.06900", "0.08625"]
# the break-even points the post states: the five-minute cache wins from call 2, the one-hour cache from call 3
assert W5[0] > NONE[0] and W5[1] < NONE[1]
assert W1[1] > NONE[1] and W1[2] < NONE[2]
XS = [1, 2, 3, 4, 5]

fig = Figure(
    "03-write-premium-break-even", "One cache read repays the five-minute write premium",
    "A line chart of the cumulative cost of the 4,600-token prefix over five calls on Claude Sonnet 4.5. "
    "Without caching it rises by $0.01380 a call, to $0.06900. A five-minute cache costs $0.01725 on call 1, "
    "more than no caching, and is already cheaper on call 2 at $0.01863, ending at $0.02277. A one-hour cache "
    "costs $0.02760 on call 1, is still dearer on call 2 and cheaper from call 3, ending at $0.03312. A cache "
    "that expires between calls is written again every time and ends at $0.08625, the most expensive line.",
    subtitle="Cumulative cost of the 4,600-token prefix on Claude Sonnet 4.5; Anthropic prices, 12 October 2026.",
    data_w=True)

body = Box(40, 104, 880, 360)
ax = fig.line_chart(
    body,
    [dict(xs=XS, ys=NONE, color="ink", label="no caching", shape="circle"),
     dict(xs=XS, ys=W5, color="stable", label="5-minute cache", shape="square"),
     dict(xs=XS, ys=W1, color="stable", label="1-hour cache", shape="triangle"),
     dict(xs=XS, ys=LAPSED, color="error", label="expires between calls", shape="diamond", dash="ref")],
    x=(1, 5, XS), y=(0, 0.09, [0, 0.02, 0.04, 0.06, 0.08]),
    x_label="calls that send the same prefix", y_label="dollars, cumulative",
    fmt_y=lambda v: f"${v:.2f}", label_w=184)
fig.caption("The one-hour write needs two reads to pay off; a cache that expires between calls never does.")
fig.write()
