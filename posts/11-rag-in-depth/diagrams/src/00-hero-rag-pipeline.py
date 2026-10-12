"""Post 11, hero (sections 1, 4 and 6): the offline lane that sets the ceiling and the online lane that approaches it.

Run from the series root:  uv run python posts/11-rag-in-depth/diagrams/src/00-hero-rag-pipeline.py
Writes posts/11-rag-in-depth/diagrams/00-hero-rag-pipeline.svg.
No measured number is drawn. top-50 and top-5 are the series' starting defaults as section 4 of index.md states
them (illustrative values to tune), and recall@50 and precision@5 are the notation guide's names for the metrics of
those two stages; every phrase is asserted against the body below.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("The **offline** half runs once per document: chunk, add context, embed, index.",
               "The **online** half runs on every user turn: construct the query, generate candidates, re-rank, pack, generate.",
               "merged by reciprocal rank fusion (RRF) into a top-50 candidate set",
               "keep the top-5", "Bookend layout", "give each chunk a citation header",
               "**Recall@N** (retrieval)", "**Citation accuracy**", "**Answer correctness**",
               "**Manifest table.**", "layer 04, retrieved chunks"):
    assert phrase in BODY, phrase

desc = ("A two-lane pipeline. The offline lane, run once per document: documents parsed upstream, chunk "
        "(sentence-aware), add context (a header per chunk), embed and index (dense and BM25), into an index that "
        "holds the chunks and a manifest. An arrow carries the index down to the online lane, run on every user "
        "turn: query (rewrite the user turn), candidates (dense plus BM25, fused by RRF, top-50), re-rank "
        "(cross-encoder, top-5), pack (bookends and citations, filling 04 Retrieved chunks, drawn in the per-turn "
        "colour), and the model. Under the online stages sit the metrics that measure them: recall@50 under "
        "candidates, precision@5 under re-rank, citation accuracy and answer correctness under the model.")

fig = Figure("00-hero-rag-pipeline", "Offline work sets the ceiling; online work approaches it", desc,
             subtitle="Offline runs once per document; online runs on every user turn. Top-50 and top-5 are starting "
                      "defaults.", data_w=True)

COLS = [40 + i * 184 for i in range(5)]        # five columns, 144 wide, 40 apart
CW = 144

fig.text(40, 128, "Offline, once per document", "head")
off_y, off_h = 144, 108
offline = [("Documents", ["parsed text", "(post 10)"]),
           ("Chunk", ["sentence-aware,", "with overlap"]),
           ("Add context", ["a header", "per chunk"]),
           ("Embed, index", ["dense vectors", "and BM25"]),
           ("Index", ["chunks and", "manifest"])]
off_boxes = []
for x, (head, lines) in zip(COLS, offline):
    fig.card(x, off_y, CW, off_h, heading=head, lines=lines)
    off_boxes.append(Box(x, off_y, CW, off_h))
# the index holds layer 04's content: a thin band in the per-turn colour across its top
fig.fill(Box(COLS[4] + 8, off_y, CW - 16, 4), "turn", fit=False)
fig.chain(off_boxes)

on_y, on_h = 320, 108
fig.text(40, on_y - 16, "Online, every user turn", "head")
online = [("Query", ["rewrite the", "user turn"], None),
          ("Candidates", ["dense + BM25,", "RRF, top-50"], None),
          ("Re-rank", ["cross-encoder,", "top-5"], None),
          ("Pack", ["into 04 Retrieved", "chunks"], "turn"),
          ("Model", ["answers with", "citations"], None)]
on_boxes = []
for x, (head, lines, color) in zip(COLS, online):
    fig.card(x, on_y, CW, on_h, heading=head, lines=lines, color=color)
    on_boxes.append(Box(x, on_y, CW, on_h))
fig.chain(on_boxes)

# the index is searched by the candidates stage on every turn
idx, cand = off_boxes[4], on_boxes[1]
fig.arrow((idx.cx, idx.bottom), (cand.cx, cand.y), via=((idx.cx, 280), (cand.cx, 280)))
fig.text(cand.cx + 12, 272, "searched on every turn", "note")

# what measures each online stage
MY = on_y + on_h + 24
fig.text(on_boxes[1].x, MY, "recall@50", "note")
fig.text(on_boxes[2].x, MY, "precision@5", "note")
fig.text(on_boxes[4].x, MY, "citation accuracy,", "note")
fig.text(on_boxes[4].x, MY + 20, "answer correctness", "note")
fig.text(on_boxes[0].x, MY, "measured by:", "note")

fig.caption("A miss in the index caps every answer; a miss online shows in the metric under its stage.")
fig.write()
