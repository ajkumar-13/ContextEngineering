"""Post 17, section 4: MaxSim keeps a rare-term match that one pooled vector loses.

Run from the series root:  uv run python posts/17-advanced-retrieval/diagrams/src/02-maxsim.py
Writes posts/17-advanced-retrieval/diagrams/02-maxsim.svg.

Every number is computed by snippets/maxsim.py (imported): the cosine similarity of each query token with each
chunk token, each row's maximum, their sum (the MaxSim score) and the single-vector score of the pooled vectors.
The values are rounded to two decimals as the snippet prints them, and the scores are asserted against index.md.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
POST = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(POST / "snippets"))
from figkit import Figure  # noqa: E402
import maxsim as ms  # noqa: E402

Q = ms.QUERY
(NA, A), (NB, B) = ms.CHUNKS.items()
panels = []
for name, doc in ((NA, A), (NB, B)):
    grid = ms.similarity_grid(Q, doc)
    best = [max(range(len(doc)), key=lambda j, r=row: r[j]) for row in grid]
    maxima = [row[j] for row, j in zip(grid, best)]
    panels.append(dict(name=name, doc=doc, grid=grid, best=best, maxima=maxima,
                       maxsim=ms.maxsim(Q, doc), single=ms.single_vector_score(Q, doc)))
pa, pb = panels
assert abs(pa["maxsim"] - sum(pa["maxima"])) < 1e-12
assert [f"{v:.2f}" for v in pa["maxima"]] == ["0.45", "0.98", "1.00"]
assert [f"{v:.2f}" for v in pb["maxima"]] == ["1.00", "1.00", "0.28"]
assert (f"{pa['maxsim']:.2f}", f"{pb['maxsim']:.2f}") == ("2.43", "2.28")
assert (f"{pa['single']:.2f}", f"{pb['single']:.2f}") == ("0.51", "0.55")
assert pb["single"] > pa["single"] and pa["maxsim"] > pb["maxsim"]

BODY = (POST / "index.md").read_text(encoding="utf-8")
for phrase in ("A                         0.51     2.43", "B                         0.55     2.28",
               "The figure below shows where the difference comes from.", "\"error\" through \"stops\" (0.98)"):
    assert phrase in BODY, phrase


def f2(v):
    return f"{v:.2f}"


desc = ("Two grids of cosine similarities between the query tokens fix, error and E-4012 (rows) and the tokens of a "
        "chunk (columns), each row's maximum outlined and printed at the right. Chunk A, which holds the answer "
        "(invoice export stops with E-4012 when currency missing): maxima 0.45 (stops), 0.98 (stops) and 1.00 "
        "(E-4012), MaxSim 2.43, single-vector score 0.51. Chunk B, a generic page (how to fix common error "
        "messages): maxima 1.00 (fix), 1.00 (error) and 0.28 (error), MaxSim 2.28, single-vector score 0.55. "
        "The single vector ranks B first; MaxSim ranks A first.")

fig = Figure("02-maxsim", "MaxSim counts the rare-term match in full", desc,
             subtitle="Query \u201cfix error E-4012\u201d. Cosine similarity per token pair, toy vectors from "
                      "snippets/maxsim.py.", height=720, data_w=True)

GX, CW, CH = 128, 64, 40
tops = [168, 408]
heads = ["Chunk A: holds the answer", "Chunk B: a generic page"]
VERDICT = ["MaxSim ranks A first", "single vector ranks B first"]
for p, top, head, verdict in zip(panels, tops, heads, VERDICT):
    fig.text(40, top - 40, head, "head")
    g = fig.grid(GX, top, len(Q), len(p["doc"]), cell_w=CW, cell_h=CH, values=p["grid"], decimals=2, font=14,
                 strong={(i, j): "ink" for i, j in enumerate(p["best"])})
    g.col_labels(p["doc"])
    g.row_labels(Q)
    for i, j in enumerate(p["best"]):
        g.outline(i, j, 1, 1, color="ink", width=1.5, form="grid")
    right = GX + CW * len(p["doc"])
    mx = fig.strip(right + 24, top, len(Q), cell_w=CW, cell_h=CH, vertical=True, values=p["maxima"],
                   decimals=2, font=14)
    mx.col_labels(["max"])
    sx = right + 24 + CW // 2
    fig.text(sx, top + CH * len(Q) + 24, f"sum {f2(p['maxsim'])}", "value", anchor="middle")
    lx = right + 24 + CW + 32
    fig.text(lx, top + 28, f"MaxSim {f2(p['maxsim'])}", "value")
    fig.text(lx, top + 56, f"single vector {f2(p['single'])}", "label")
    fig.text(lx, top + 96, verdict, "note")

fig.text(40, 600, "Outlined: the row\u2019s best match. MaxSim sums the three maxima.", "note")
fig.caption("Pooled, chunk B scores higher; token by token, chunk A\u2019s exact E-4012 match decides.")
fig.write()
