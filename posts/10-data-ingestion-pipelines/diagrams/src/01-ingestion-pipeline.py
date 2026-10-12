"""Post 10, hero (sections 1 and 2): the six ingestion stages, which of them decide what text exists, and where
the index meets the window.

Run from anywhere:  python posts/10-data-ingestion-pipelines/diagrams/src/01-ingestion-pipeline.py
Writes posts/10-data-ingestion-pipelines/diagrams/01-ingestion-pipeline.svg.
No numbers are drawn. The stage names and what each produces are section 2 of index.md; the split between this
post and post 11, the select step into layer 04 and the dropped cell are sections 1 and 2. Asserted below.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")

# (stage, what it produces, the bold bullet of section 2 it summarises)
STAGES = [
    ("Source", ["raw bytes", "and origin"], "- **Source**: fetch the raw bytes and record where they came from"),
    ("Parse", ["text, order,", "tables"], "- **Parse**: turn bytes into structured text, keeping reading order, headings and tables."),
    ("Clean", ["content only"], "- **Clean**: remove what is not content"),
    ("Enrich", ["plus", "provenance"], "- **Enrich**: attach metadata"),
    ("Chunk", ["retrieval", "units"], "- **Chunk**: split the cleaned, enriched text into the units retrieval returns."),
    ("Index", ["dense and", "BM25"], "- **Index**: embed each chunk and write it to the dense (vector) index and the sparse index, a BM25 index"),
]
for _, _, bullet in STAGES:
    assert bullet in BODY, bullet
for phrase in ("the first four decide which text exists at all",
               "The last two stages are the subject of [post 11]",
               "every later select into layer 04 reads from that store",
               "cannot recover a fact destroyed at parse time",
               "the answer sits in a cell the parser dropped",
               "It costs almost nothing at ingest and cannot be backfilled afterwards."):
    assert phrase in BODY, phrase

desc = ("Six stage boxes joined by arrows, left to right. " +
        " ".join(f"{name}: {' '.join(what)}." for name, what, _ in STAGES) +
        " A brace over source, parse, clean and enrich reads: this post, decides which text exists. A brace over "
        "chunk and index reads: post 11, decides how it is found. An arrow labelled select, each turn, leads from "
        "the index down to a box for layer 04, retrieved chunks. A red arrow points at parse from a red note: a cell "
        "dropped here never reaches layer 04. A second red arrow points at enrich from a red note: provenance not "
        "written here cannot be backfilled.")

fig = Figure("01-ingestion-pipeline", "What parsing keeps is all that retrieval can find", desc,
             subtitle="The six ingestion stages, from raw files to the index that select reads into layer 04.",
             data_w=True)

X0, W, STEP, Y, H = 40, 120, 152, 160, 112
boxes = []
for i, (name, what, _) in enumerate(STAGES):
    b = Box(X0 + i * STEP, Y, W, H)
    fig.fill(b, "neutral-soft", radius=8, fit=False)
    fig.outline(b, "border", radius=8)
    fig.text(b.x + 16, b.y + 32, name, "head")
    for k, line in enumerate(what):
        fig.text(b.x + 16, b.y + 64 + 20 * k, line, "note")
    boxes.append(b)
fig.chain(boxes)

fig.brace(boxes[0].x, boxes[3].right, Y - 16, label="this post: decides which text exists", side="above")
fig.brace(boxes[4].x, boxes[5].right, Y - 16, label="post 11: decides how it is found", side="above")

parse = boxes[1]
fig.arrow((parse.cx, 352), (parse.cx, parse.bottom + 2), color="error")
fig.text(parse.cx, 376, "a cell dropped here never", "label", anchor="middle", color="error")
fig.text(parse.cx, 396, "reaches layer 04", "label", anchor="middle", color="error")
enrich = boxes[3]
fig.arrow((enrich.cx, 352), (enrich.cx, enrich.bottom + 2), color="error")
fig.text(enrich.cx, 376, "provenance not written here", "label", anchor="middle", color="error")
fig.text(enrich.cx, 396, "cannot be backfilled", "label", anchor="middle", color="error")

index = boxes[5]
layer = Box(760, 360, 160, 56)
fig.card(layer.x, layer.y, layer.w, layer.h, color="turn")
fig.text(layer.x + 16, layer.y + 33, "04 Retrieved chunks", "label")
fig.arrow((index.cx, index.bottom + 2), (index.cx, layer.y), label="select, each turn", side="left")

fig.caption("recall@N is measured at select; it cannot recover what parse dropped.")
fig.write()
