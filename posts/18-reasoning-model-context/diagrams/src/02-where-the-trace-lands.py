"""Post 18, figure 2 (section 5): what the next call's input costs, by where the thinking text was copied.

Run from the series root:  uv run python posts/18-reasoning-model-context/diagrams/src/02-where-the-trace-lands.py
Writes posts/18-reasoning-model-context/diagrams/02-where-the-trace-lands.svg.

Where every number comes from: snippets/trace_cache.py (BASE, TRACE, with_trace, price_prefix), imported and
asserted against the table that script prints and section 5 quotes. Token counts are illustrative, so every
segment has a dashed outline and the subtitle says so. Cache rule and multipliers: Anthropic, "Prompt caching",
consulted October 2026; prices: Claude Opus 4.6, Anthropic "Pricing", as of early 2026.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, num  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "trace_cache.py"
M = runpy.run_path(str(SNIP), run_name="snippet")
TRACE = M["TRACE"]
assert TRACE == 2000 and (M["CACHE_READ"], M["CACHE_WRITE"], M["RATE_IN"]) == (0.1, 1.25, 5.00)
PREV = M["with_trace"](None)
ROWS = [  # (layer the text is copied into, row heading, row note)
    (None, "Copied nowhere", "thinking text not reused"),
    ("06", "Into layer 06", "appended to the question"),
    ("03", "Into layer 03", "saved to memory, read back"),
    ("01", "Into layer 01", "spliced into the system prompt"),
]
PRICED = [M["price_prefix"](PREV, M["with_trace"](layer)) for layer, _, _ in ROWS]
# the table the snippet prints and the post quotes: (read, written, full price, input dollars)
assert [(r, w, f, f"{c:.5f}") for r, w, f, c in PRICED] == [
    (4600, 0, 5900, "0.03180"), (4600, 0, 7900, "0.04180"), (4600, 0, 7900, "0.04180"),
    (1600, 5000, 5900, "0.06155")]

fig = Figure(
    "02-where-the-trace-lands", "In the system prompt, the trace breaks the cached prefix",
    "Four horizontal bars price the input of the next call on Claude Opus 4.6 after a turn whose 2,000 tokens "
    "of thinking text are copied into one layer, drawn to one token scale with dashed outlines because the "
    "counts are illustrative. Copied nowhere: 4,600 tokens read from the cache and 5,900 at full price, "
    "$0.03180. Into layer 06, appended to the question: 4,600 read and 7,900 at full price, $0.04180. Into "
    "layer 03, saved to memory and read back: the same, $0.04180. Into layer 01, spliced into the system "
    "prompt: 1,600 read, 5,000 written to the cache again at 1.25 times the base price, and 5,900 at full "
    "price, $0.06155. A note states that the system prompt changes every turn, so the write repeats.",
    subtitle="Next call's input on Claude Opus 4.6, 2,000 tokens of thinking text copied; sizes illustrative.",
    data_w=True)

X0 = 264
SCALE = 560 / 12_500
BAR_H = 40
SEG = [  # (index in the priced tuple, fill, outline)
    (0, "stable-soft", "stable"),
    (1, "error-soft", "error"),
    (2, "neutral-soft", "ink-muted"),
]
for k, ((layer, head, note), (read, written, full, cost)) in enumerate(zip(ROWS, PRICED)):
    y = 128 + 72 * k
    fig.text(40, y + 16, head, "head")
    fig.text(40, y + 36, note, "note")
    x = X0
    with fig.data():
        for idx, fill, line in SEG:
            n = (read, written, full)[idx]
            if not n:
                continue
            w = n * SCALE
            b = Box(x, y, w, BAR_H)
            fig.fill(b, fill, fit=False)
            fig.outline(b, line, width=1, dash="proj")
            col = {0: "stable-ink", 1: "error-ink", 2: None}[idx]
            fig.text(x + w / 2, y + 25, num(n), "label", anchor="middle", color=col, snap=False)
            x += w
        fig.text(x + 12, y + 25, f"${cost:.5f}", "value", bold=(layer == "01"), snap=False)

fig.legend(40, 432, [
    dict(color="stable", label="read from the cache, 0.1×", mark="dashed-outline", dash="proj"),
    dict(color="error", label="written again, 1.25×", mark="dashed-outline", dash="proj"),
    dict(color="ink-muted", label="full input price", mark="dashed-outline", dash="proj"),
], direction="row")
fig.text(40, 468, "Layer 01 changes on every turn, so the write repeats on every call.", "label")
fig.caption("Only text copied in front of a cache breakpoint breaks the prefix; every copy costs tokens.")
fig.write()
