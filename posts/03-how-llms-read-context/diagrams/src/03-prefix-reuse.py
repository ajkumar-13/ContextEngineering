"""Post 03, section 7: what an identical-prefix cache reuses, measured in tokens by snippets/prefix_reuse.py.

Run from the series root:  uv run python posts/03-how-llms-read-context/diagrams/src/03-prefix-reuse.py
Writes posts/03-how-llms-read-context/diagrams/03-prefix-reuse.svg.
Every token count is computed here with the snippet's own blocks and tokeniser (tiktoken, o200k_base) and asserted
against the lines the snippet prints, which section 7 of the post quotes. Segment widths are proportional to tokens.
"""
import contextlib
import io
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, text_width  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "prefix_reuse.py"
out = io.StringIO()
with contextlib.redirect_stdout(out):
    ns = runpy.run_path(str(SNIP), run_name="snippet")
printed = out.getvalue()
enc, SYSTEM, TOOLS, CALL_1, CALL_2 = ns["enc"], ns["SYSTEM"], ns["TOOLS"], ns["CALL_1"], ns["CALL_2"]
TIME_1, TIME_2 = "Current time: 09:14:05.\n", "Current time: 09:16:42.\n"
SOURCE = SNIP.read_text(encoding="utf-8")
assert all(f'"{t[:-1]}\\n" + SYSTEM' in SOURCE for t in (TIME_1, TIME_2))   # the snippet's layout B


def layer_tokens(system, call):
    """Tokens per layer (01 to 06), block by block as the snippet tokenises them."""
    n = lambda s: len(enc.encode(s))  # noqa: E731
    return {1: n(system), 2: n(TOOLS), 3: n(call["memory"]), 4: n(call["chunks"]),
            5: sum(n(h) for h in call["history"]), 6: n(call["question"])}


LAYOUTS = {
    "A": dict(s1=SYSTEM, s2=SYSTEM),
    "B": dict(s1=TIME_1 + SYSTEM, s2=TIME_2 + SYSTEM),
}
for k, lay in LAYOUTS.items():
    t1, _ = ns["tokens"](lay["s1"], CALL_1)
    t2, stable = ns["tokens"](lay["s2"], CALL_2)
    lay.update(c1=layer_tokens(lay["s1"], CALL_1), c2=layer_tokens(lay["s2"], CALL_2),
               same=ns["shared_prefix"](t1, t2), stable=stable, total=len(t2))
    lay["reused"] = stable if lay["same"] >= stable else 0
    assert sum(lay["c2"].values()) == len(t2) and sum(lay["c1"].values()) == len(t1)
A, B = LAYOUTS["A"], LAYOUTS["B"]
# the snippet's printed lines, which the post quotes
assert "call 2: 166 tokens; layers 01 and 02: 99 tokens" in printed and (A["total"], A["stable"]) == (166, 99)
assert "leading tokens identical to call 1: 109" in printed and A["same"] == 109
assert "99 read from the cache, 67 computed" in printed and A["reused"] == 99
assert "call 2: 176 tokens; layers 01 and 02: 109 tokens" in printed and (B["total"], B["stable"]) == (176, 109)
assert "leading tokens identical to call 1: 6" in printed and B["same"] == 6
assert "0 read from the cache, 176 computed" in printed and B["reused"] == 0

ROLE = {1: "stable", 2: "stable", 3: "turn", 4: "turn", 5: "history", 6: "user"}
NAME = {1: "01 System prompt", 2: "02 Tools"}
X0, X1 = 120, 920
PX = (X1 - X0) / max(A["total"], B["total"])        # pixels per token, the same scale in both panels
SH = 48                                             # strip height

fig = Figure(
    "03-prefix-reuse", "A cache reuses an identical prefix, or nothing",
    "Two panels, each drawing two consecutive calls as strips of the six layers, widths proportional to tokens "
    "as printed by snippets/prefix_reuse.py. Layout A, stable layers first: call 2 has 166 tokens; its first "
    "109 tokens match call 1, and with the cache breakpoint after layer 02 its 99 tokens of layers 01 and 02 are "
    "read from the cache and 67 are computed. Layout B, the time of the call at the top of the system prompt: "
    "only the first 6 tokens match, so nothing is read from the cache and all 176 tokens of call 2 are computed.",
    subtitle="Token counts printed by snippets/prefix_reuse.py (tiktoken, o200k_base); widths are to scale.",
    height=720, data_w=True)


def strip(y, counts, label, mark_x):
    fig.text(40, y + 28, label, "label")
    x = X0
    with fig.data():
        for k in range(1, 7):
            w = counts[k] * PX
            if w == 0:
                continue
            b = Box(x, y, w, SH)
            fig.fill(b, f"{ROLE[k]}-soft", radius=4, fit=False)
            fig.outline(b, f"{ROLE[k]}-line", radius=4)
            name = NAME.get(k, f"{k:02d}")
            tx = x + 8
            if x < mark_x < x + 8 + text_width(name, 14, weight=400):   # keep the name clear of the mark
                tx = mark_x + 8
            if tx + text_width(name, 14, weight=400) + 8 > x + w:
                name = f"{k:02d}"
            fig.text(tx, y + 28, name, "label", snap=False)
            x += w


def mark(x, y0, y1, text, color):
    with fig.data():
        fig.outline(Box(x, y0, 0.01, y1 - y0), color, width=1.5, dash="lead")
    fig.text(x + 6 if x < 700 else x - 6, y0 - 8, text, "note", anchor="start" if x < 700 else "end",
             color=None if color == "ink-muted" else f"{color}-ink")


def panel(top, heading, lay, broken):
    fig.text(40, top, heading, "head")
    y1, y2 = top + 52, top + 120
    xs = X0 + lay["same"] * PX
    strip(y1, lay["c1"], "call 1", xs)
    strip(y2, lay["c2"], "call 2", xs)
    mark(xs, y1 - 4, y2 + SH + 4, f"identical to call 1 up to token {lay['same']}",
         "error" if broken else "ink-muted")
    yb = y2 + SH + 8
    xe = X0 + lay["total"] * PX
    if lay["reused"]:
        xr = X0 + lay["reused"] * PX
        fig.brace(X0, xr, yb, f"{lay['reused']} read from the cache", kind="bracket", color="stable")
        fig.brace(xr, xe, yb, f"{lay['total'] - lay['reused']} computed", kind="bracket")
    else:
        fig.brace(X0, xe, yb, f"nothing read from the cache: all {lay['total']} computed", kind="bracket",
                  color="error")


panel(136, "A. Stable layers first", A, broken=False)
panel(432, "B. The time of the call written at the top of the system prompt", B, broken=True)

fig.caption("The breakpoint after layer 02 reuses all of layers 01 and 02 or none of it, never a part.")
fig.write()
