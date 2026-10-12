"""Post 11, section 4: reciprocal rank fusion of two rankings of the toy corpus for one golden question.

Run from the series root:  uv run python posts/11-rag-in-depth/diagrams/src/03-rrf-fusion.py
Writes posts/11-rag-in-depth/diagrams/03-rrf-fusion.svg.
Every rank and score is computed here with the snippet's own rankers (BM25 over the headed chunks, from the
companion, and the character-trigram stand-in) and the companion's rrf with k = 60, for the snippet's third golden
question. Each fused score is recomputed from the formula and asserted against rrf's output; the chunks that carry
the gold phrase are marked "answer".
"""
import contextlib
import io
import runpy
import sys
from fractions import Fraction
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, rich, var  # noqa: E402

POST = Path(__file__).resolve().parents[2]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(str(POST / "snippets" / "toy_rag.py"), run_name="snippet")

K = 60
QUESTION, PHRASE = ns["GOLDEN"][2]
headed, chunks = ns["headed"], ns["chunks"]
LEX = [i for i, _ in ns["bm25_headed"].search(QUESTION, top_k=len(headed))]
FUZ = ns["trigram_ranking"](headed, QUESTION)
assert ns["rankings"](QUESTION)["BM25, headed chunks"] == LEX and ns["rankings"](QUESTION)["trigram, headed chunks"] == FUZ
FUSED = ns["rrf"]([LEX, FUZ], k=K)
rank = lambda lst, d: lst.index(d) + 1 if d in lst else None  # noqa: E731
for d, score in FUSED:
    want = sum(1 / (K + r) for r in (rank(LEX, d), rank(FUZ, d)) if r)
    assert abs(score - want) < 1e-12

N = 4
TOP_L, TOP_F, TOP_U = LEX[:N], FUZ[:N], [d for d, _ in FUSED[:N]]
gold = {i for i in range(len(chunks)) if PHRASE in chunks[i]}
assert TOP_L[0] not in gold and TOP_F[0] in gold and TOP_U[0] in gold and TOP_U[0] == TOP_F[0] == LEX[1]
assert QUESTION == "Can I get a refund on a gift card?"
# the caption's "ranks 2 and 1 beat ranks 1 and 3": the answer chunk against BM25's first chunk
assert (rank(LEX, TOP_U[0]), rank(FUZ, TOP_U[0])) == (2, 1) and (rank(LEX, TOP_L[0]), rank(FUZ, TOP_L[0])) == (1, 3)
section = lambda d: headed[d].split(" > ")[1].split("]")[0]  # noqa: E731

BODY = (POST / "index.md").read_text(encoding="utf-8")
for phrase in ("$\\mathrm{RRF}(d) = \\sum_i 1/(k + r_i(d))$", "60 in Cormack et al. (2009)",
               "uses a character-trigram ranker as an offline stand-in for the dense half"):
    assert phrase in BODY, phrase


def label(d):
    return f"chunk {d}, {section(d)}" + (" (answer)" if d in gold else "")


def frac_line(d):
    rs = [r for r in (rank(LEX, d), rank(FUZ, d)) if r]
    total = float(sum(Fraction(1, K + r) for r in rs))
    return " + ".join(f"1/{K + r}" for r in rs) + f" = {total:.4f}"


fused_lines = {d: frac_line(d) for d in TOP_U}
desc = ("Three ranked lists for the toy question 'Can I get a refund on a gift card?'. Left, BM25 over the headed "
        "chunks: " + ", ".join(label(d) for d in TOP_L) + ". Right, the character-trigram ranker: "
        + ", ".join(label(d) for d in TOP_F) + ". Centre, reciprocal rank fusion with k = 60, each score the sum of "
        "1 over 60 plus the chunk's rank in each list: " + "; ".join(f"{label(d)}, {fused_lines[d]}" for d in TOP_U)
        + ". Lines join each chunk's places in the lists.")

fig = Figure("03-rrf-fusion", "Fusion rewards a chunk ranked high in both lists", desc,
             subtitle="The toy question \u201cCan I get a refund on a gift card?\u201d, ranked by snippets/toy_rag.py.",
             height=540, data_w=True)

CW, BH, STEP, Y0 = 256, 56, 72, 144
COL = {"lex": 40, "fus": 352, "fuz": 664}
fig.text(COL["lex"], 128, "BM25 ranking", "head")
fig.text(COL["fus"], 128, rich("RRF, ", var("k"), f" = {K}"), "head")
fig.text(COL["fuz"], 128, "Trigram ranking", "head")


def entry(col, i, d, second=None):
    b = Box(COL[col], Y0 + i * STEP, CW, BH)
    fig.card(b.x, b.y, b.w, b.h)
    fig.text(b.x + 12, b.y + (24 if second else 34), f"{i + 1}. {label(d)}", "label")
    if second:
        fig.text(b.x + 12, b.y + 44, second, "note")
    return b


boxes = {}
for i, d in enumerate(TOP_L):
    boxes[("lex", d)] = entry("lex", i, d)
for i, d in enumerate(TOP_F):
    boxes[("fuz", d)] = entry("fuz", i, d)
for i, d in enumerate(TOP_U):
    boxes[("fus", d)] = entry("fus", i, d, fused_lines[d])

# join each chunk's place in an input list to its place in the fused list
for (col, d), b in list(boxes.items()):
    if col == "fus" or ("fus", d) not in boxes:
        continue
    f = boxes[("fus", d)]
    p0, p1 = ((b.right, b.cy), (f.x, f.cy)) if col == "lex" else ((b.x, b.cy), (f.right, f.cy))
    with fig.data():
        fig.edge(p0, p1, color="ink" if d in gold else "rule", width=1.5 if d in gold else 1)

hidden = [(d, "BM25", rank(LEX, d)) for d in TOP_U if d not in TOP_L] +     [(d, "trigram", rank(FUZ, d)) for d in TOP_U if d not in TOP_F]
assert hidden == [(1, "BM25", 7), (16, "trigram", 5)]
fig.text(COL["fus"], Y0 + N * STEP + 16, "Score: 1/(60 + BM25 rank) + 1/(60 + trigram rank).", "note")
fig.text(COL["fus"], Y0 + N * STEP + 36, f"Chunk {hidden[0][0]} is BM25's {hidden[0][2]}th; chunk {hidden[1][0]} the "
         f"trigram ranker's {hidden[1][2]}th.", "note")
fig.caption("BM25's first chunk is not the answer; ranks 2 and 1 beat ranks 1 and 3, so the answer leads.")
fig.write()
