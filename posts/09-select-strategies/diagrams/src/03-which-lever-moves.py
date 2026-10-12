"""Post 09, section 8: which lever moves which metric, measured on the snippet's toy corpus.

Run from anywhere:  python posts/09-select-strategies/diagrams/src/03-which-lever-moves.py
Writes posts/09-select-strategies/diagrams/03-which-lever-moves.svg.
Every plotted value is computed here by snippets/select_pipeline.py (evaluate), asserted against the table the post
quotes from its output. The values are measured on a toy corpus written to show the mechanism; the subtitle says so.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
M = runpy.run_path(str(POST / "snippets" / "select_pipeline.py"), run_name="snippet")
N, K = M["TOP_N"], M["TOP_K"]
assert (N, K, len(M["CORPUS"])) == (6, 3, 36)
ROWS = [(name, r, p) for name, r, p, _ in M["evaluate"]()]
assert [(n, f"{r:.2f}", f"{p:.2f}") for n, r, p in ROWS] == [
    ("BM25 only", "0.56", "0.44"), ("dense only", "0.94", "0.56"),
    ("hybrid (RRF)", "1.00", "0.67"), ("hybrid + re-rank", "1.00", "0.78")]
for n, r, p in ROWS:                                       # the post quotes the same printed table
    assert f"{n:<18}{r:>10.2f}{p:>14.2f}" in BODY, n

LABEL = {"BM25 only": "BM25 only", "dense only": "dense only", "hybrid (RRF)": "hybrid (RRF)",
         "hybrid + re-rank": "hybrid + re-rank"}
desc = (f"A dot chart, measured by select_pipeline.py on a toy corpus of 36 articles with six questions: for each of "
        f"four configurations, recall@{N} as a circle and precision@{K} as a diamond, on a scale from 0.4 to 1. ")
desc += "; ".join(f"{LABEL[n]}, recall {r:.2f} and precision {p:.2f}" for n, r, p in ROWS) + ". "
desc += ("Recall rises to 1.00 when the two lists are fused and stays there when the reranker is switched on; "
         "only precision moves with the reranker.")

fig = Figure("03-which-lever-moves", "Fusion lifts recall; the reranker lifts precision", desc,
             subtitle=f"Measured by select_pipeline.py on a toy corpus of 36 articles: mean of six questions.",
             data_w=True)

plot = Box(40, 136, 880, 272)
fig.dot_plot(plot, [(LABEL[n], [r, p]) for n, r, p in ROWS], 0.4, 1, [0.4, 0.6, 0.8, 1.0],
             colors=("ink", "ink-muted"), shapes=("circle", "diamond"), fmt=lambda v: f"{v:.2f}",
             label_w=176, pad_right=56, values=True, connect="rule")
fig.legend(40, 112, [dict(color="ink", label=f"recall@{N}: share of relevant articles in the top {N}", mark="circle"),
                     dict(color="ink-muted", label=f"precision@{K}: share of the {K} packed that are relevant",
                          mark="diamond")], direction="row", gap=40)
fig.text(40, 456, "The toy corpus shows which lever moves which number, not how much a real system gains.", "note")
fig.caption(f"The reranker only reorders the top {N}, so recall@{N} cannot move when it is switched on.")
fig.write()
