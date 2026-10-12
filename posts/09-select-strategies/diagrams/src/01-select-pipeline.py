"""Post 09, hero (section 1): the four stages of select, from the user turn to layer 04.

Run from anywhere:  python posts/09-select-strategies/diagrams/src/01-select-pipeline.py
Writes posts/09-select-strategies/diagrams/01-select-pipeline.svg.
The only numbers drawn are the series' illustrative starting sizes, top-50 candidates and top-5 packed, which
section 1 states as illustrative; they are drawn in dashed boxes and asserted against the body. The stage names,
what each serves and its techniques are the words of sections 2 to 5, asserted below.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
N, K = 50, 5
for phrase in (f"The series' illustrative starting values are top-{N} and top-{K}",
               "N is set for recall and k is bounded by the budget",
               "## 2. Lever 1: query construction", "## 3. Lever 2: candidate generation",
               "## 4. Lever 3: re-ranking", "## 5. Lever 4: packing",
               "The job of candidate generation is **recall**", "re-ranking optimises **precision**",
               "**Query rewriting.**", "**HyDE (Hypothetical Document Embeddings).**",
               "**Multi-query expansion and decomposition.**", "**Dense retrieval.**", "**Sparse retrieval.**",
               "**Hybrid retrieval**", "**cross-encoder**", "**bookend layout**", "**Deduplicate.**",
               "**Cite while packing.**", "layer 04's budget"):
    assert phrase in BODY, phrase

STAGES = [
    ("Construct the query", "so the index can match", ["rewrite the user turn", "HyDE", "expand or decompose"]),
    ("Generate candidates", "for recall", ["dense (ANN)", "sparse (BM25)", "hybrid, fused by RRF"]),
    ("Re-rank", "for precision", ["a cross-encoder reads", "query and candidate", "together"]),
    ("Pack", "for the budget", ["bookend order", "deduplicate, trim", "cite while packing"]),
]
OUT = [f"one search query", f"top-N: {N} candidates", f"top-k: {K} kept"]

desc = ("A pipeline of four stages in a row, left to right, starting from the user turn. Construct the query, so the "
        "index can match: rewrite the user turn, HyDE, expand or decompose. Generate candidates, for "
        "recall: dense (ANN), sparse (BM25), hybrid fused by RRF. Re-rank, for precision: a cross-encoder reads the "
        "query and each candidate together. Pack, for the budget: bookend order, deduplicate and trim, cite while "
        "packing. Under the first three stages, boxes give what each passes on: one search query, then, dashed as "
        f"illustrative sizes, top-N of {N} candidates and top-k of {K} kept. The pack stage, in the per-turn colour, writes "
        "into layer 04, retrieved chunks.")

fig = Figure("01-select-pipeline", "Select is four stages from the user turn to the window", desc,
             subtitle=f"Recall is won in the candidates, precision in the re-rank. Sizes are illustrative.",
             data_w=True)

X0, W, GAP = 40, 196, 32
TOP, H = 160, 160
xs = [X0 + i * (W + GAP) for i in range(4)]
boxes = []
fig.text(xs_c := X0 + W / 2, 120, "user turn", "note", anchor="middle")
fig.arrow((xs_c, 128), (xs_c, TOP - 2))
for i, (name, serves, how) in enumerate(STAGES):
    b = Box(xs[i], TOP, W, H)
    last = i == len(STAGES) - 1
    fig.fill(b, "turn-soft" if last else "neutral-soft", radius=8, fit=False)
    fig.outline(b, "turn-line" if last else "border", radius=8)
    fig.text(b.x + 16, TOP + 32, f"{i + 1}  {name}", "head")
    fig.text(b.x + 16, TOP + 56, serves, "note")
    for j, line in enumerate(how):
        fig.text(b.x + 16, TOP + 92 + j * 24, line, "label")
    boxes.append(b)
fig.chain(boxes)

OUT_TOP, OUT_H = 376, 48
for i, s in enumerate(OUT):
    ob = Box(xs[i] + 16, OUT_TOP, W - 32, OUT_H)
    fig.outline(ob, "ink-muted", radius=6, dash=None if i == 0 else "lead")
    fig.text(ob.cx, OUT_TOP + 29, s, "label", anchor="middle")
    fig.arrow((ob.cx, TOP + H + 4), (ob.cx, OUT_TOP - 2))
win = Box(xs[3] + 16, OUT_TOP, W - 32, OUT_H)
fig.fill(win, "turn-soft", radius=6, fit=False)
fig.outline(win, "turn", radius=6, width=1.5)
fig.text(win.cx, OUT_TOP + 29, "04 Retrieved chunks", "label", anchor="middle")
fig.arrow((win.cx, TOP + H + 4), (win.cx, OUT_TOP - 2))

fig.text(X0, 464, f"Dashed: illustrative sizes. N is set for recall and k by the budget.", "note")
fig.caption("The same four stages select documents, tool schemas, memory rows and few-shot examples.")
fig.write()
