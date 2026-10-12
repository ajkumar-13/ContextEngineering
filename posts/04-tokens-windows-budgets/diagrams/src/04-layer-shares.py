"""Post 04, section 6: the support agent's share of the input budget per layer, against the default bands.

Run from the series root:  uv run python posts/04-tokens-windows-budgets/diagrams/src/04-layer-shares.py
Writes posts/04-tokens-windows-budgets/diagrams/04-layer-shares.svg.

Where every number comes from: snippets/envelope.py (imported): the layer token counts (LAYERS, illustrative)
give each share, and DEFAULT_SHARES gives each band (the section 6 table, illustrative defaults). The shares are
asserted against the snippet output that section 6 quotes. The bands are illustrative defaults, so they have
dashed outlines; a share outside its band is a red diamond, one inside an ink circle, so colour is never the only
signal.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, text_width  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "envelope.py"
ENV = runpy.run_path(str(SNIP), run_name="snippet")
LAYERS, BANDS = ENV["LAYERS"], ENV["DEFAULT_SHARES"]
TOTAL = sum(LAYERS.values())
SHARE = {k: 100 * v / TOTAL for k, v in LAYERS.items()}
assert [f"{v:.1f}" for v in SHARE.values()] == ["28.6", "15.2", "11.4", "23.8", "19.0", "1.9"]
OUTSIDE = {k: not (BANDS[k][0] <= SHARE[k] <= BANDS[k][1]) for k in LAYERS}
assert [k[:2] for k, o in OUTSIDE.items() if o] == ["01", "02", "03"]
ROLE = ["stable", "stable", "turn", "turn", "history", "user"]

fig = Figure(
    "04-layer-shares", "The agent breaks the defaults of layers 01 to 03",
    "One row per layer on a percent axis from 0 to 40. A dashed band in the layer's colour shows its default "
    "share of the input budget, and a mark shows the support agent's share of its 10,500 input tokens. Outside "
    "the band, as red diamonds: 01 System prompt 28.6 percent against 5 to 15, 02 Tools and MCP descriptions "
    "15.2 against 5 to 15, 03 Memory and state 11.4 against 5 to 10. Inside, as circles: 04 Retrieved chunks "
    "23.8 against 20 to 40, 05 Conversation history 19.0 against 10 to 30, 06 User instruction 1.9 against 1 to 5.",
    subtitle="Share of the 10,500 input tokens per layer; default bands and token counts illustrative.",
    data_w=True)

LBL, X0, X1, HI = 40, 288, 808, 40.0
sx = lambda v: X0 + (X1 - X0) * v / HI  # noqa: E731
fig.legend(LBL, 128, [dict(color="ink-muted", label="default share", mark="dashed-outline", dash="proj"),
                      dict(color="ink", label="agent, inside", mark="circle"),
                      dict(color="error", label="agent, outside", mark="diamond")],
           direction="row", gap=40)
TOP, STEP, BH = 160, 48, 24
AX = TOP + STEP * len(LAYERS)
with fig.data():
    for t in (0, 10, 20, 30, 40):
        fig.edge((sx(t), TOP), (sx(t), AX), color="grid", width=0.75)
        fig.text(sx(t), AX + 20, f"{t}%", "tick", anchor="middle", snap=False)
    for i, (name, n) in enumerate(LAYERS.items()):
        cy = TOP + STEP * i + STEP / 2
        lo, hi = BANDS[name]
        band = Box(sx(lo), cy - BH / 2, sx(hi) - sx(lo), BH)
        fig.fill(band, f"{ROLE[i]}-soft", fit=False)
        fig.outline(band, f"{ROLE[i]}-line", width=1, dash="proj")
        fig.text(LBL, cy + 5, name, "label", snap=False)
        out = OUTSIDE[name]
        fig.marker(sx(SHARE[name]), cy, "diamond" if out else "circle", "error" if out else "ink", size=10)
        label = f"{SHARE[name]:.1f}%"
        tx = sx(SHARE[name]) + 12
        if tx < band.right < tx + text_width(label, 14, weight=600) + 4:   # never across the band's edge
            tx = band.right + 8
        fig.text(tx, cy + 5, label, "value", color="error" if out else None, snap=False)
    fig.edge((X0, TOP), (X0, AX), color="ink-muted", width=1)

fig.caption("Layers 01 and 02 are cached, so the overrun costs little money but still takes window and attention.")
fig.write()
