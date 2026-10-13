"""Post 17, hero (sections 1, 2 and 7): a router sends each question to the retriever its shape needs.

Run from the series root:  uv run python posts/17-advanced-retrieval/diagrams/src/00-hero-router.py
Writes posts/17-advanced-retrieval/diagrams/00-hero-router.svg.

No number is drawn. The five shapes, the technique each is routed to, and the cue words on the left come from
snippets/router.py (imported): every cue must match its own rule and no earlier one, and every example question
of a shape must route to the technique drawn beside it. The phrases are asserted against index.md.
"""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
POST = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(POST / "snippets"))
from figkit import Figure, Box  # noqa: E402
import router  # noqa: E402

BODY = (POST / "index.md").read_text(encoding="utf-8")

# shape as router.py names it, heading drawn, cue line drawn, what the route puts into layer 04
ROWS = [
    ("multi-hop", "Multi-hop", "\u201cdownstream of\u201d, \u201cdepend on\u201d", "chunks behind the edges walked"),
    ("whole document", "Whole document", "\u201csummarise\u201d, \u201cmain themes\u201d", "the whole document, cached"),
    ("structured", "Structured data", "\u201chow many\u201d, \u201caverage\u201d", "rows a SQL query returns"),
    ("rare exact term", "Rare exact term", "E-4012, AX-7731", "chunks ranked by MaxSim"),
    ("local lookup", "Anything else", "local lookups", "fused, reranked top-k chunks"),
]
TECH = {"local lookup": "Hybrid RAG (default)"}

# the cues are what the snippet's rules fire on, in the snippet's order
patterns = dict(router.RULES)
order = [s for s, _ in router.RULES]
for shape, _, cue, _ in ROWS[:4]:
    words = [w.strip("\u201c\u201d") for w in cue.split(", ")]
    for w in words:
        assert re.search(patterns[shape], w), (shape, w)
        for earlier in order[:order.index(shape)]:
            assert not re.search(patterns[earlier], w), (shape, w, earlier)
for q, shape in router.QUESTIONS:
    if shape != "local lookup" or "How many" not in q:     # question 15 is the snippet's one misroute
        assert router.route(q) == router.ROUTES[shape], q

for phrase in ("with hybrid RAG as the default", "layer 04, retrieved chunks",
               "The figure at the top of the post is the answer in one picture.",
               "| Multi-hop |", "| Whole document |", "| Structured data |", "| Rare exact term |",
               "GraphRAG", "Long-context load", "Text-to-SQL", "Late interaction"):
    assert phrase.lower() in BODY.lower(), phrase

desc = ("A routing diagram in four columns. On the left, five question shapes with the cue words the post's toy "
        "router reads: multi-hop (downstream of, depend on), whole document (summarise, main themes), structured "
        "data (how many, average), rare exact term (identifiers such as E-4012 and AX-7731), and anything else "
        "(local lookups). Each enters one router box, which checks its rules in order. The router sends them to "
        "GraphRAG, which packs the chunks behind the edges walked; a long-context load of the whole document, "
        "cached; text-to-SQL, which returns rows; late interaction, which ranks chunks by MaxSim; and the default, "
        "hybrid RAG with fused, reranked top-k chunks. All five routes fill one box, 04 Retrieved chunks, drawn in "
        "the per-turn colour.")

fig = Figure("00-hero-router", "Route each question to the retriever its shape needs", desc,
             subtitle="Cue words from the post's toy router, snippets/router.py. Hybrid RAG takes every question "
                      "no rule claims.", height=720, data_w=True)

SX, SW = 40, 216          # shapes
RX, RW = 296, 112         # router
TX, TW = 448, 256         # techniques
LX, LW = 744, 176         # layer 04
Y0, H, STEP = 136, 80, 104

ys = [Y0 + k * STEP for k in range(len(ROWS))]
top, bottom = ys[0], ys[-1] + H

fig.text(SX, Y0 - 16, "Question shape", "head")
fig.text(TX, Y0 - 16, "Route", "head")
fig.card(RX, top, RW, bottom - top, heading="Router", lines=["rules, or a", "small model", "call"])
fig.card(LX, top, LW, bottom - top, lines=["04 Retrieved", "chunks", "", "filled by", "every route"], color="turn")

for (shape, head, cue, fills), y in zip(ROWS, ys):
    fig.card(SX, y, SW, H, heading=head, lines=[cue], style="note")
    tech = TECH.get(shape, router.ROUTES[shape])
    tech = tech[0].upper() + tech[1:] if tech != "text-to-SQL" else "Text-to-SQL"
    fig.card(TX, y, TW, H, heading=tech, lines=[fills], style="note")
    cy = y + H // 2
    fig.arrow((SX + SW, cy), (RX, cy))
    fig.arrow((RX + RW, cy), (TX, cy))
    fig.arrow((TX + TW, cy), (LX, cy))

fig.caption("The router decides which kind of thing enters layer 04: a path, a document, rows, or passages.")
fig.write()
