"""Post 08, section 5: the offline write path of an embedding index, with the chunk metadata each step records.

Run from anywhere:  python posts/08-write-strategies/diagrams/src/03-index-write-pipeline.py
Writes posts/08-write-strategies/diagrams/03-index-write-pipeline.svg.
No numbers are drawn. The steps are section 5's numbered list (the manifest is drawn as its own row), the six
metadata fields are section 5's list (asserted: the figure draws exactly those six), and the step that records
each field is the step at which the value first exists. The index box takes the role of layer 04, which it fills.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("1. **Source collection.**", "2. **Cleaning.**", "3. **Chunking.**", "4. **Enrichment.**",
               "5. **Embedding.**", "6. **Indexing.**", "7. **Manifest.** Write one manifest row per source: its hash, "
               "the chunks it produced, the embedding model version and the timestamp."):
    assert phrase in BODY, phrase
FIELDS_LINE = ("**Metadata on every chunk**, besides the vector and the text: `source_id`, `source_url`, "
               "`chunk_index`, `tokens`, `created_at`, `embedding_model`.")
assert FIELDS_LINE in BODY

# (step, what it does, metadata it records)
STEPS = [("Collect", "keep a hash", ["source_id", "source_url"]),
         ("Clean", "strip boilerplate", []),
         ("Chunk", "self-contained", ["chunk_index", "tokens"]),
         ("Enrich", "add context", []),
         ("Embed", "vector per chunk", ["embedding_model"]),
         ("Index", "vector and BM25", ["created_at"])]
drawn = sorted(f for _, _, fs in STEPS for f in fs)
assert drawn == sorted(["source_id", "source_url", "chunk_index", "tokens", "created_at", "embedding_model"])

desc = "A chain of six boxes from left to right: "
desc += ", ".join(f"{s} ({w})" for s, w, _ in STEPS)
desc += ". The index box is coloured as layer 04, which it fills. Under four of the boxes, the chunk metadata that step records: "
desc += "; ".join(f"{', '.join(fs)} at {s.lower()}" for s, _, fs in STEPS if fs)
desc += (". Below, a manifest card: one row per source with its hash, the chunks produced, the embedding model version "
         "and the time. An arrow labelled select at query time runs from the index down to a box for 04 Retrieved chunks.")

fig = Figure("03-index-write-pipeline", "The write path records provenance as it goes", desc,
             subtitle="The offline write path of an embedding index, and the step that records each chunk field.",
             data_w=True)

BW, BG, BX, BY, BH = 128, 20, 52, 128, 72
boxes = []
for i, (step, what, _) in enumerate(STEPS):
    b = Box(BX + i * (BW + BG), BY, BW, BH)
    last = i == len(STEPS) - 1
    fig.fill(b, "turn-soft" if last else "neutral-soft", radius=8, fit=False)
    fig.outline(b, "turn-line" if last else "border", radius=8)
    fig.text(b.x + 12, BY + 32, step, "head")
    fig.text(b.x + 12, BY + 56, what, "note")
    boxes.append(b)
fig.chain(boxes)

TAG_Y = BY + BH + 60                       # first tag baseline
for b, (_, _, fs) in zip(boxes, STEPS):
    if fs:
        fig.leader((b.cx, b.bottom + 4), (b.cx, TAG_Y - 20))
    for j, f in enumerate(fs):
        fig.text(b.cx, TAG_Y + j * 24, f, "code", anchor="middle")
fig.text(BX, TAG_Y + 72, "Chunk metadata: each field is recorded at the step where its value first exists.", "note")

man = Box(BX, 376, 612, 72)
fig.fill(man, "neutral-soft", radius=8, fit=False)
fig.outline(man, "border", radius=8)
fig.text(man.x + 16, man.y + 30, "Manifest: one row per source", "head")
fig.text(man.x + 16, man.y + 54, "its hash, the chunks produced, the embedding model version, the time", "label")

l4 = Box(728, 376, 188, 72)
fig.fill(l4, "turn-soft", radius=8, fit=False)
fig.outline(l4, "turn-line", radius=8)
fig.text(l4.x + 16, l4.y + 30, "04 Retrieved", "label")
fig.text(l4.x + 16, l4.y + 54, "chunks", "label")
ax = boxes[-1].right - 12
fig.arrow((ax, BY + BH + 4), (ax, l4.y - 4))
fig.text(ax - 12, 360, "select at query time", "note", anchor="end")

fig.caption("Provenance is written along the way, so every chunk can say where it came from.")
fig.write()
