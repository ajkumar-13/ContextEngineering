"""Post 19, section 2: one A4 page at three resolutions, in visual tokens, on Anthropic's two resolution tiers.

Run from the series root:  uv run python posts/19-multimodal-context/diagrams/src/02-tokens-by-resolution.py
Writes posts/19-multimodal-context/diagrams/02-tokens-by-resolution.svg.

Every number is computed by snippets/image_tokens.py (a4, resized, visual_tokens, TIERS), imported and asserted
against what it prints and the post quotes. The rule and the two tiers' caps are Anthropic's "Vision" and
"Coordinates and bounding boxes" pages, consulted October 2026.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, num, TIMES  # noqa: E402

POST = Path(__file__).resolve().parents[2]
S = runpy.run_path(str(POST / "snippets" / "image_tokens.py"), run_name="snippet")
TIERS = S["TIERS"]
assert TIERS == {"standard": (1568, 1568), "high-res": (2576, 4784)}

DPIS = (72, 130, 300)
TOK = {t: [S["image_tokens"](*S["a4"](d), t) for d in DPIS] for t in TIERS}
SIZE = {t: [S["resized"](*S["a4"](d), t) for d in DPIS] for t in TIERS}
assert TOK == {"standard": [682, 1551, 1551], "high-res": [682, 2145, 4756]}
assert SIZE["standard"][2] == (924, 1307) and SIZE["high-res"][1] == (1075, 1520) and SIZE["high-res"][2] == (1623, 2296)

fig = Figure(
    "02-tokens-by-resolution", "More pixels cost more tokens, up to the tier's cap",
    "Two horizontal bar charts of the visual tokens of one A4 page on a shared axis from 0 to 5,000. On the "
    "standard tier, capped at 1,568 tokens: 72 dpi costs 682 tokens, 130 dpi 1,551 and 300 dpi 1,551, because "
    "both are resized to 924 by 1,307 pixels. On the high-resolution tier, capped at 4,784 tokens: 72 dpi costs "
    "682, 130 dpi 2,145, sent unchanged, and 300 dpi 4,756, resized to 1,623 by 2,296. A dotted line marks "
    "each cap.",
    subtitle="One A4 page, computed by snippets/image_tokens.py with Anthropic's Vision rule (October 2026).",
    data_w=True)

left, right = fig.row(2, y=120, h=304)
NOTES = {"standard": f"130 and 300 dpi both shrink to 924 {TIMES} 1,307 px",
         "high-res": f"300 dpi shrinks to 1,623 {TIMES} 2,296 px"}
HEADS = {"standard": "Standard tier: Opus 4.6, Sonnet 4.5, Haiku 4.5",
         "high-res": "High-resolution tier: Claude 4.7 and later"}
for box, tier in ((left, "standard"), (right, "high-res")):
    body = fig.panel(box, HEADS[tier])
    cap = TIERS[tier][1]
    fig.bar_chart(body, [(f"{d} dpi", v, "ink") for d, v in zip(DPIS, TOK[tier])], 0, 5000,
                  [0, 2500, 5000], label_w=72, value_w=56,
                  ref_lines=[dict(x=cap, label=f"cap {num(cap)}")])
    fig.text(body.x, 464, NOTES[tier], "note")

fig.caption("Past the cap the page is shrunk before it is read: the extra pixels are neither paid for nor seen.")
fig.write()
