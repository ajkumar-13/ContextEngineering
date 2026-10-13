"""Post 19, hero (sections 1 and 2): one retrieved A4 page, cut into 28-pixel patches, joins the six layers.

Run from the series root:  uv run python posts/19-multimodal-context/diagrams/src/01-page-in-the-window.py
Writes posts/19-multimodal-context/diagrams/01-page-in-the-window.svg.

Where every number comes from:
- The page: snippets/image_tokens.py (a4, resized, visual_tokens), imported and asserted: an A4 page at 130 dpi,
  1075 x 1520 pixels, is resized on the standard tier to 924 x 1307, 33 x 47 patches, 1,551 tokens
  (Anthropic, "Vision" and "Coordinates and bounding boxes", consulted October 2026).
- The text layers: post 04's illustrative support agent (posts/04-tokens-windows-budgets/snippets/envelope.py,
  LAYERS), imported and asserted; drawn dashed because they are illustrative.
"""
import math
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, num, TIMES  # noqa: E402

POST = Path(__file__).resolve().parents[2]
S = runpy.run_path(str(POST / "snippets" / "image_tokens.py"), run_name="snippet")
ENV = runpy.run_path(str(POST.parent / "04-tokens-windows-budgets" / "snippets" / "envelope.py"), run_name="snippet")

W0, H0 = S["a4"](130)
W1, H1 = S["resized"](W0, H0)
COLS, ROWS = math.ceil(W1 / 28), math.ceil(H1 / 28)
PAGE = S["visual_tokens"](W1, H1)
assert (W0, H0, W1, H1, COLS, ROWS, PAGE) == (1075, 1520, 924, 1307, 33, 47, 1551)

LAYERS = ENV["LAYERS"]
SIZES = list(LAYERS.values())
assert SIZES == [3000, 1600, 1200, 2500, 2000, 200]
TEXT_IN = sum(SIZES)
assert (TEXT_IN, TEXT_IN + PAGE) == (10_500, 12_051)

ROLE = ["stable", "stable", "turn", "turn", "history", "user"]

fig = Figure(
    "01-page-in-the-window", f"A page image is {num(PAGE)} tokens in the same window",
    "On the left, the six layers of post 04's support agent as bars drawn to one scale with dashed outlines, "
    "because the sizes are illustrative: 01 System prompt 3,000 tokens, 02 Tools and MCP descriptions 1,600, "
    "03 Memory and state 1,200, 04 Retrieved chunks 2,500 of text, 05 Conversation history 2,000, 06 User "
    "instruction 200. On the right, an A4 page scanned at 130 dpi, 1,075 by 1,520 pixels, resized to 924 by "
    "1,307 and cut into a grid of 33 by 47 patches of 28 by 28 pixels, one token each, 1,551 tokens. An arrow "
    "carries the page into layer 04, where a solid segment of 1,551 tokens follows the 2,500 tokens of text. "
    "The input of the call grows from 10,500 to 12,051 tokens.",
    subtitle="Post 04's agent, text sizes illustrative; image tokens by Anthropic's Vision rule, standard tier.",
    data_w=True)

# The six layers as bars to one scale.
X0, SCALE = 272, 0.068          # bar origin, pixels per token
Y0, PITCH, BH = 120, 52, 32
rows = {}
for k, ((name, n), role) in enumerate(zip(LAYERS.items(), ROLE)):
    y = Y0 + k * PITCH
    fig.text(40, y + 20, name, "label")
    with fig.data():
        bar = Box(X0, y, n * SCALE, BH)
        fig.fill(bar, f"{role}-soft", fit=False)
        fig.outline(bar, f"{role}-line", width=1, dash="proj")
        if k == 3:
            fig.text(bar.cx, y + 20, num(n), "label", anchor="middle", snap=False)
        else:
            fig.text(bar.x + bar.w + 8, y + 20, num(n), "label", snap=False)
    rows[k] = (y, bar)

# The page image inside layer 04: a solid segment with the patch texture.
y4, text4 = rows[3]
with fig.data():
    seg = Box(text4.x + text4.w, y4, PAGE * SCALE, BH)
    fig.fill(seg, "turn-soft", fit=False)
    step = seg.w / 16
    for i in range(1, 16):
        fig.edge((seg.x + i * step, y4), (seg.x + i * step, y4 + BH), color="turn-line", width=0.75)
    fig.outline(seg, "turn", width=1.5)
    fig.text(seg.cx, y4 + 20, num(PAGE), "value", anchor="middle", snap=False)
SEG_END = seg.x + seg.w

# The page, cut into patches (33 x 47 cells; the last row is the padding to a multiple of 28).
PX, PY, PW, PH = 704, 120, 216, 304
PATCH_ROW = 16
g = fig.grid(PX, PY, ROWS, COLS, width=PW, height=PH, fill=lambda i, j: "turn-soft" if (i, j) == (PATCH_ROW, 0) else None)
g.outline(PATCH_ROW, 0, 1, 1, "turn", 1.5)
with fig.data():   # a hint of page content: a heading, lines of text and a small table
    fig.fill(Box(PX + 20, PY + 20, 120, 8), "ink-muted", fit=False)
    for i, w in enumerate((176, 176, 176, 150, 176, 176, 120)):
        fig.fill(Box(PX + 20, PY + 44 + 14 * i, w, 4), "rule", fit=False)
    fig.outline(Box(PX + 20, PY + 160, 176, 64), "ink-muted", width=1)
    for yy in (PY + 176, PY + 192, PY + 208):
        fig.edge((PX + 20, yy), (PX + 196, yy), color="ink-muted", width=0.75)
    fig.edge((PX + 80, PY + 160), (PX + 80, PY + 224), color="ink-muted", width=0.75)
    for i, w in enumerate((176, 176, 140)):
        fig.fill(Box(PX + 20, PY + 244 + 14 * i, w, 4), "rule", fit=False)
fig.outline(Box(PX, PY, PW, PH), "turn", width=1.5)
fig.text(PX + PW / 2, PY + PH + 24, f"A4 page, 130 dpi: {num(W0)} {TIMES} {num(H0)} px", "label", anchor="middle")
fig.text(PX + PW / 2, PY + PH + 44, f"resized to {W1} {TIMES} {num(H1)}", "note", anchor="middle")
fig.text(PX + PW / 2, PY + PH + 68, f"{COLS} {TIMES} {ROWS} patches = {num(PAGE)} tokens", "value", anchor="middle")
fig.callout(g.cell(PATCH_ROW, 0), f"one 28 {TIMES} 28 patch, 1 token", side="left", length=24)

fig.arrow((PX - 8, y4 + BH / 2), (SEG_END + 8, y4 + BH / 2), label="image tokens", side="below")

# Totals under the stack.
fig.text(40, Y0 + 6 * PITCH + 16, f"Input of the call: {num(TEXT_IN)} tokens of text + {num(PAGE)} of image "
         f"= {num(TEXT_IN + PAGE)}", "value")
fig.legend(40, Y0 + 6 * PITCH + 48, [dict(color="ink-muted", label="text, illustrative sizes", mark="dashed-outline"),
                                      dict(color="turn", label="page image, computed", mark="outline")],
           direction="row")

fig.caption("The page is priced and budgeted like the text around it: same window, same rate per token.")
fig.write()
