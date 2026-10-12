"""Post 05, section 5: where the time of one agent turn goes, with and without a cache hit.

Run from anywhere:  python posts/05-economics-of-context/diagrams/src/04-turn-latency.py
Writes posts/05-economics-of-context/diagrams/04-turn-latency.svg.
This is a mechanism drawing, not a timing chart: no latency is measured or cited, so no seconds are drawn.
The prefill boxes are drawn to scale in tokens computed (10,500 against 5,900, from snippets/cost_model.py:
PREFIX + REST and REST); the decode box is the same 400 output tokens in both rows. The rule drawn is the one
section 5 states (Pope et al., 2022; Anthropic, "Prompt caching"): prefill computes the uncached input before
the first token, decode runs one forward pass per output token, and a cache hit skips the cached prefix.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, rich, var, sub, num, CDOT  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "cost_model.py"
M = runpy.run_path(str(SNIP), run_name="snippet")
PREFIX, REST, OUT = M["PREFIX"], M["REST"], M["OUTPUT_TOKENS"]
assert (PREFIX + REST, REST, OUT) == (10500, 5900, 400)

fig = Figure(
    "04-turn-latency", "A cache hit shortens the wait for the first token",
    "Two rows show one agent turn. On a cache miss, prefill computes all 10,500 input tokens in one parallel "
    "pass before the first token appears, then decode runs 400 forward passes in sequence, one per output "
    "token. On a cache hit, the 4,600 prefix tokens are read from the cache and prefill computes only 5,900, "
    "so the first token comes sooner; decode is the same 400 passes. Below, total time is prefill time plus "
    "the number of output tokens times the time per decode step.",
    subtitle="Prefill boxes are drawn to scale in tokens computed, not in seconds; no timings are claimed.",
    data_w=True)

X0, SCALE, BAR_H, DEC_W = 248, 400 / 10500, 56, 224
ROWS = [(152, "Cache miss", "nothing cached", PREFIX + REST, False),
        (296, "Cache hit", "layers 01 and 02 cached", REST, True)]

for y, head, note, computed, hit in ROWS:
    fig.text(40, y + 24, head, "head")
    fig.text(40, y + 44, note, "note")
    w = computed * SCALE
    pre = Box(X0, y, w, BAR_H)
    fig.fill(pre, "neutral-soft", fit=False)
    fig.outline(pre, "rule")
    with fig.data():
        fig.text(X0 + 16, y + 34, f"prefill: {num(computed)} tokens", "label", snap=False)
        dx = X0 + w + 8
        dec = Box(dx, y, DEC_W, BAR_H)
        fig.fill(dec, "ink-muted", fit=False)
        for k in range(1, 14):                      # sequential steps: one pass after another
            fig.edge((dx + 16 * k, y + 4), (dx + 16 * k, y + 12), color="surface")
            fig.edge((dx + 16 * k, y + BAR_H - 12), (dx + 16 * k, y + BAR_H - 4), color="surface")
        fig.text(dx + DEC_W / 2, y + 34, f"decode: {OUT} passes", "value", anchor="middle", color="surface",
                 snap=False)
        fig.text(dx, y - 28, "first token", "note", anchor="middle", snap=False)
    fig.arrow((dx, y - 20), (dx, y), color="ink-muted", width=1)
    if hit:
        with fig.data():
            fig.text(X0, y + BAR_H + 28, f"+ {num(PREFIX)} prefix tokens read from the cache, not recomputed",
                     "label", color="stable-ink", snap=False)

fig.text(40, 448, rich(sub(var("T"), "total"), " = ", sub(var("T"), "prefill"), " + ", sub(var("N"), "out"),
                       f" {CDOT} ", sub(var("T"), "decode")), "math")
fig.caption("Streaming shows decode as it happens; nothing shows the user anything before prefill ends.")
fig.write()
