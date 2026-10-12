"""Post 09, section 6: the same select pipeline over four corpora.

Run from anywhere:  python posts/09-select-strategies/diagrams/src/02-four-corpora.py
Writes posts/09-select-strategies/diagrams/02-four-corpora.svg.
No numbers are drawn. Each cell is a phrase of section 6 (asserted below); the packed-into column names the layer
in the series' words, shaded in that layer's role colour (02 stable, 03 and 04 per-turn).
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("the surviving handful is packed into layer 02, tools and MCP descriptions",
               "the rewritten user turn retrieves candidates by hybrid search over the schemas",
               "The query is built from the intent of the turn",
               "Re-ranking mixes relevance with recency and confidence",
               "Packing respects layer 03's small budget",
               "Retrieval is dense within a filter",
               "they travel with the retrieved material in layer 04, after the cached prefix",
               "maximal marginal relevance (MMR",
               "layer 02 belongs to the stable prefix, and a catalogue that changes per turn changes the prefix"):
    assert phrase in BODY, phrase

HEAD = ["Corpus", "One item", "Query built from", "Re-rank on", "Packed into"]
ROWS = [
    ("Documents", "a chunk", "the rewritten user turn", "relevance", "04 Retrieved chunks", "turn"),
    ("Tool schemas", "a tool schema", "the rewritten user turn", "relevance", "02 Tools and MCP descriptions",
     "stable"),
    ("Memory rows", "a memory row", "the intent of the turn", "relevance, recency, confidence",
     "03 Memory and state", "turn"),
    ("Examples", "a labelled example", "the query, label-filtered", "relevance and diversity (MMR)",
     "04 Retrieved chunks", "turn"),
]
WIDTHS = [120, 152, 168, 216, 224]
X, Y, RH = 40, 120, 56
assert sum(WIDTHS) == 880

desc = ("A table of the same select pipeline over four corpora, with columns corpus, one item, query built from, "
        "re-rank on and packed into. ")
for c, item, q, rr, layer, _ in ROWS:
    desc += f"{c}: {item}; query from {q}; re-rank on {rr}; packed into {layer}. "
desc += "The packed-into cells are shaded in the colour of the layer: per-turn for 03 and 04, stable for 02."

fig = Figure("02-four-corpora", "One pipeline, four corpora", desc,
             subtitle="Per corpus, the item, the query, the re-rank signal and the layer filled change; the stages do not.",
             data_w=True)

col_x = [X + sum(WIDTHS[:j]) for j in range(len(WIDTHS))]
for i, row in enumerate(ROWS, start=1):
    fig.fill(Box(col_x[4] + 4, Y + i * RH + 8, WIDTHS[4] - 4, RH - 16), f"{row[5]}-soft", radius=4, fit=False)
table = fig.table(X, Y, [HEAD] + [list(r[:5]) for r in ROWS], WIDTHS, row_h=RH)

fig.text(X, table.bottom + 40, "A catalogue chosen per turn changes layer 02, which sits in the cached prefix.", "note")
fig.caption("Swap the corpus and tune the stage that changes most; the pipeline stays.")
fig.write()
