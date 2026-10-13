"""Post 25, section 7: one illustrative workload priced per day under long context, a hybrid and RAG.

Run from the series root:  uv run python posts/25-long-context-vs-rag/diagrams/src/02-cost-per-day.py
Writes posts/25-long-context-vs-rag/diagrams/02-cost-per-day.svg.

Where every number comes from: snippets/cost_latency.py (rates, sizes, long_call, rag_call, day), imported and
asserted against the values that script prints and section 7 quotes. The sizes are illustrative, so every
segment has a dashed outline and the subtitle says so. Prices: Claude Opus 4.6, Anthropic "Pricing" and
"Prompt caching", as of early 2026 (consulted October 2026, as post 05 quotes them). The axis is broken for
the uncached bar, whose value is printed.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
M = runpy.run_path(str(POST / "snippets" / "cost_latency.py"), run_name="snippet")
BODY = (POST / "index.md").read_text(encoding="utf-8")

assert (M["IN"], M["OUT"], M["WRITE"], M["READ"]) == (5.00, 25.00, 1.25, 0.10)
assert (M["CORPUS"], M["QUERIES"], M["WRITES"], M["LONG_SHARE"]) == (200_000, 1_000, 10, 0.10)
Q, W = M["QUERIES"], M["WRITES"]
uncached = Q * sum(M["long_call"]("none"))
full, cached = M["day"](Q, W)
long_n = round(Q * M["LONG_SHARE"])
h_full, h_cached = M["day"](long_n, W)
h_rag = (Q - long_n) * M["rag_call"]()
rag = Q * M["rag_call"]()
prefill_long = (M["CORPUS"] + M["QUESTION"]) * M["PREFILL_MS"] / 1000
prefill_rag = M["RAG_IN"] * M["PREFILL_MS"] / 1000

# the values the snippet prints and section 7 quotes
assert [f"{v:.2f}" for v in (uncached, full + cached, full, cached)] == ["1013.00", "124.50", "25.50", "99.00"]
assert [f"{v:.2f}" for v in (h_full + h_cached + h_rag, h_full, h_cached, h_rag, rag)] == \
    ["57.45", "13.80", "9.00", "34.65", "38.50"]
assert (h_full + h_cached + h_rag) / rag < 1.5
assert [f"{v:.2f}" for v in (prefill_long, prefill_rag)] == ["80.04", "2.00"]
for phrase in ("1013.00", "124.50", "57.45", "38.50", "80.04 seconds", "2.00 seconds",
               "The figure below draws the four days to one scale."):
    assert phrase in BODY, phrase

ROWS = [  # label, [(value, role, segment name)], printed total
    ("Long context, uncached", [(uncached, "neutral", "full")], uncached),
    ("Long context, cached", [(full, "neutral", "full"), (cached, "stable", "cache")], full + cached),
    ("Hybrid, 10% long", [(h_full, "neutral", "full"), (h_cached, "stable", "cache"), (h_rag, "turn", "rag")],
     h_full + h_cached + h_rag),
    ("RAG", [(rag, "turn", "rag")], rag),
]

desc = ("Four horizontal bars of dollars per day for 1,000 queries over a 200,000-token corpus on Claude Opus 4.6, "
        "prices as of early 2026, every size illustrative and every segment dashed. Long context, uncached: "
        "1,013.00, past a broken axis. Long context, cached, with 10 cache writes a day: 124.50, of which 25.50 is "
        "paid in full (the writes, the questions and the answers) and 99.00 is read from the cache. Hybrid, 10% "
        "of queries on long context: 57.45, made of 13.80 in full, 9.00 from the cache and 34.65 of RAG calls. "
        "RAG alone: 38.50. A note gives the prefill before the first token, uncached, at post 04's illustrative "
        "rates: 80.04 seconds for the corpus and 2.00 seconds for a RAG call.")

fig = Figure("02-cost-per-day", "Caching cuts the corpus bill; retrieval removes it", desc,
             subtitle="Dollars per day, 1,000 queries, Claude Opus 4.6 prices as of early 2026. Dashed: "
                      "illustrative sizes.",
             data_w=True)

X0, X1, HI = 240, 800, 140            # plot from 0 to HI dollars
SCALE = (X1 - X0) / HI
Y0, STEP, BAR_H = 152, 60, 36
FORM = {"neutral": ("neutral-soft", "ink"), "stable": ("stable-soft", "stable"), "turn": ("turn-soft", "turn")}

fig.legend(40, 124, [dict(color="ink", label="paid in full", mark="dashed-outline", dash="proj"),
                     dict(color="stable", label="corpus read from the cache", mark="dashed-outline", dash="proj"),
                     dict(color="turn", label="RAG calls", mark="dashed-outline", dash="proj")],
           direction="row")

AXIS_Y = Y0 + 4 * STEP - 8
for t in range(0, HI + 1, 20):
    x = X0 + t * SCALE
    if t:
        fig.edge((x, Y0 - 8), (x, AXIS_Y), color="grid", width=0.75)
    fig.text(x, AXIS_Y + 20, f"{t}", "tick", anchor="middle")
fig.edge((X0, Y0 - 8), (X0, AXIS_Y), color="rule")
fig.edge((X0, AXIS_Y), (X1, AXIS_Y), color="rule")
fig.text((X0 + X1) // 2, AXIS_Y + 44, "dollars per day", "note", anchor="middle")

for k, (label, segs, total) in enumerate(ROWS):
    y = Y0 + k * STEP
    fig.text(40, y + 23, label, "label")
    x = X0
    with fig.data():
        for value, role, _ in segs:
            fillc, line = FORM[role]
            w = value * SCALE
            if x + w > X1:                                  # the broken bar: run to the axis end, gap, stub
                fig.fill(Box(x, y, X1 - 16 - x, BAR_H), fillc, fit=False)
                fig.outline(Box(x, y, X1 - 16 - x, BAR_H), line, width=1.5, dash="proj")
                fig.fill(Box(X1 - 8, y, 24, BAR_H), fillc, fit=False)
                fig.outline(Box(X1 - 8, y, 24, BAR_H), line, width=1.5, dash="proj")
                x = X1 + 16
                break
            fig.fill(Box(x, y, w, BAR_H), fillc, fit=False)
            fig.outline(Box(x, y, w, BAR_H), line, width=1.5, dash="proj")
            if w >= 64:
                fig.text(x + w / 2, y + 23, f"{value:.2f}", "label", anchor="middle", snap=False)
            x += w
        end = x + 12
        if len(segs) == 3:
            fig.text(end, y + 23, f"{total:.2f} = {segs[0][0]:.2f} + {segs[1][0]:.2f} + {segs[2][0]:.2f}", "value",
                     snap=False)
        else:
            fig.text(end, y + 23, f"{total:,.2f}", "value",
                     bold=(k == 0), snap=False)

fig.text(40, 468, f"Prefill before the first token, uncached, at post 04's illustrative rates: corpus "
                  f"{prefill_long:.2f} s, RAG call {prefill_rag:.2f} s.", "note")
fig.caption("The hybrid stays within 1.5 times of RAG while whole-document queries still get the whole document.")
fig.write()
