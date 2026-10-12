"""Post 05, hero (sections 1 and 6): the same agent turn priced three ways on Claude Sonnet 4.5.

Run from anywhere:  python posts/05-economics-of-context/diagrams/src/01-cache-miss-and-hit.py
Writes posts/05-economics-of-context/diagrams/01-cache-miss-and-hit.svg.
Every number is computed by snippets/cost_model.py (call_cost, RATES, the multipliers and the illustrative
token counts of post 04's agent) and asserted against the values that script prints and the post quotes.
Prices: Anthropic "Pricing" and "Prompt caching", consulted 12 October 2026.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, rich, span  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "cost_model.py"
M = runpy.run_path(str(SNIP), run_name="snippet")
RATE = M["RATES"]["Claude Sonnet 4.5"]
PREFIX, REST, OUT = M["PREFIX"], M["REST"], M["OUTPUT_TOKENS"]
assert (PREFIX, REST, OUT) == (4600, 5900, 400)
COST = {mode: M["call_cost"](RATE, PREFIX, REST, OUT, mode) for mode in ("none", "write", "read")}
# the values the snippet prints and the post quotes
assert f"{COST['none']['total']:.5f}" == "0.03750"
assert f"{COST['write']['total']:.5f}" == "0.04095"
assert f"{COST['read']['total']:.5f}" == "0.02508"
assert f"{COST['read']['prefix']:.5f}" == "0.00138" and f"{COST['write']['prefix']:.5f}" == "0.01725"
assert (M["CACHE_WRITE_5M"], M["CACHE_READ"]) == (1.25, 0.1)  # the multipliers the row labels state


def usd(v):
    return f"${v:.5f}"


fig = Figure(
    "01-cache-miss-and-hit", "A cache read takes a third off the same call",
    "Three horizontal bars price one agent turn on Claude Sonnet 4.5: 10,500 input tokens, of which 4,600 are "
    "layers 01 and 02, and 400 output tokens. With no caching the call costs $0.01380 for the prefix, $0.01770 "
    "for layers 03 to 06 and $0.00600 for output, $0.03750 in all. The first call that writes the prefix to the "
    "cache pays $0.01725 for it, $0.04095 in all. A later call that reads the prefix from the cache pays $0.00138 "
    "for it, $0.02508 in all. Layers 03 to 06 and the output cost the same in every bar. A note states that "
    "every later call saves 33.1% of the uncached price.",
    subtitle="One agent turn on Claude Sonnet 4.5. Anthropic prices, consulted 12 October 2026.",
    data_w=True)

X0 = 248                      # bar origin
SCALE = 600 / 0.045           # pixels per dollar
BAR_H = 48
ROWS = [  # (y, label lines, mode)
    (152, ["No caching", "full input price"], "none"),
    (248, ["First call", "writes the prefix, 1.25×"], "write"),
    (344, ["Later calls", "read the prefix, 0.1×"], "read"),
]
SEG_STYLE = {"prefix": ("stable-soft", "stable"), "rest": ("neutral-soft", "rule"), "output": ("ink-muted", None)}

# column headings over the first bar, at each segment's centre
x = X0
for key, head in (("prefix", "layers 01 and 02"), ("rest", "layers 03 to 06"), ("output", "output")):
    w = COST["none"][key] * SCALE
    with fig.data():
        fig.text(x + w / 2, 136, head, "note", anchor="middle", snap=False)
    x += w

for y, lines, mode in ROWS:
    c = COST[mode]
    fig.text(40, y + 20, lines[0], "head")
    fig.text(40, y + 40, lines[1], "note")
    x = X0
    for key in ("prefix", "rest", "output"):
        w = c[key] * SCALE
        fill, line = SEG_STYLE[key]
        b = Box(x, y, w, BAR_H)
        fig.fill(b, fill, fit=False)
        if line:
            fig.outline(b, line)
        if key == "prefix" and mode == "read":
            fig.callout(b, usd(c[key]), side="below", length=12, color="stable-ink")
        else:
            col = "surface" if key == "output" else ("stable-ink" if key == "prefix" else None)
            with fig.data():
                fig.text(x + w / 2, y + 29, usd(c[key]), "value", anchor="middle", color=col, snap=False)
        x += w
    with fig.data():
        fig.text(x + 12, y + 29, usd(c["total"]), "value", bold=(mode == "read"), snap=False)

SAVING = 1 - COST["read"]["total"] / COST["none"]["total"]
assert f"{SAVING:.1%}" == "33.1%"
fig.text(40, 456, f"Every later call saves {SAVING:.1%} of the uncached price.", "label")
fig.caption("The prefix price changes with the cache; layers 03 to 06 and the output cost the same every time.")
fig.write()
