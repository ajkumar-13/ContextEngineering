"""Post 17, section 3: single-hop retrieval misses a two-hop answer that one hop along an extracted edge finds.

Run from the series root:  uv run python posts/17-advanced-retrieval/diagrams/src/01-two-hop.py
Writes posts/17-advanced-retrieval/diagrams/01-two-hop.svg.

Every document id, entity name and recall value is computed by snippets/two_hop.py (imported) and asserted here:
the single-hop top-3, the failed vendors read from the audit report, the edges walked, and both recalls. The
short glosses of d2 and d7 paraphrase those documents' text, which is asserted to contain the drawn words.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
POST = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(POST / "snippets"))
from figkit import Figure  # noqa: E402
import two_hop as th  # noqa: E402

bm25 = th.BM25(th.CORPUS)
single = bm25.rank(th.QUESTION)[:th.TOP_K]
failed = th.FAILED.search(th.CORPUS["d1"]).groups()
walked = [(s, b, d) for s, b, d in th.extract_edges(th.CORPUS) if s in failed]
graph = ["d1"] + [d for _, _, d in walked]
assert single == ["d1", "d2", "d7"] and th.recall(single) == 0.0
assert failed == ("Acme Metals", "Borealis Plastics")
assert walked == [("Acme Metals", "Corvid Tools", "d3"), ("Borealis Plastics", "Delta Assembly", "d4")]
assert th.recall(graph) == 1.0
for d in ("d3", "d4"):                    # the caption: no buyer document shares a word with the question
    assert not set(th.words(th.CORPUS[d])) & set(th.words(th.QUESTION)), d

GLOSS = {"d1": "the 2024 audit failed two vendors", "d2": "Foxglove passed the 2024 audit",
         "d7": "supplier scorecard reviewed quarterly"}
for d, words in [("d1", ["2024", "audit", "failed", "two vendors"]), ("d2", ["Foxglove", "passed", "2024", "audit"]),
                 ("d7", ["supplier scorecard", "reviewed", "quarter"])]:
    assert all(w in th.CORPUS[d] for w in words), d

BODY = (POST / "index.md").read_text(encoding="utf-8")
for phrase in ("single hop   packed d1, d2, d7   recall 0.00", "graph        packed d1, d3, d4   recall 1.00",
               "as the figure below draws", "one hop along an extracted edge does"):
    assert phrase in BODY, phrase

desc = ("Two panels for the question: which suppliers are downstream of vendors that failed our 2024 audit? Left, "
        "single hop: BM25 packs d1 (the 2024 audit failed two vendors), d2 (Foxglove passed the 2024 audit) and d7 "
        "(supplier scorecard reviewed quarterly); neither buyer is packed, recall 0.00. Right, the graph: d1 names "
        "Acme Metals and Borealis Plastics as failed; one hop along edges extracted offline reaches Corvid Tools, "
        "which buys from Acme Metals (d3), and Delta Assembly, which buys from Borealis Plastics (d4). The graph "
        "packs d1, d3 and d4, recall 1.00.")

fig = Figure("01-two-hop", "The buyers are one hop from the audit, not near its words", desc,
             subtitle="\u201cWhich suppliers are downstream of vendors that failed our 2024 audit?\u201d "
                      "Toy corpus, top-3.", data_w=True)

left, right = fig.row(2)
lb = fig.panel(left, "Single hop: BM25 top-3")
rb = fig.panel(right, "Graph: one hop downstream")

# left: the three documents single hop packs, each packed into layer 04 (per-turn colour)
y = lb.y
for d in single:
    fig.card(lb.x, y, lb.w, 56, lines=[f"{d}: {GLOSS[d]}"], color="turn")
    y += 80
fig.text(lb.x, y + 8, f"no buyer packed: recall {th.recall(single):.2f}", "label", color="error-ink")

# right: d1, the two failed vendors it names, then their buyers one hop down
fig.card(rb.x, rb.y, rb.w, 56, lines=["d1: the 2024 audit failed two vendors"], color="turn")
half = (rb.w - 32) // 2
xs = [rb.x, rb.x + half + 32]
vy, by = rb.y + 112, rb.y + 240
for x, (vendor, buyer, d) in zip(xs, walked):
    fig.card(x, vy, half, 56, lines=[vendor])
    fig.card(x, by, half, 56, lines=[f"{buyer} ({d})"], color="turn")
    cx = x + half // 2
    fig.arrow((cx, rb.y + 56), (cx, vy), label="failed", side="right")
    fig.arrow((cx, vy + 56), (cx, by), label="supplies", side="right")
fig.text(rb.x, by + 88, f"packed d1, d3, d4: recall {th.recall(graph):.2f}", "label")
# key: the card form of a packed document, with its meaning beside it
fig.card(lb.x, by + 68, 32, 24, color="turn", radius=4)
fig.text(lb.x + 48, by + 88, "a document packed into 04 Retrieved chunks", "note")

fig.caption("Each buyer document shares no word with the question; an edge extracted offline links it to a vendor d1 names.")
fig.write()
