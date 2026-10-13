"""Post 20, hero (section 2): the four-tier evaluation pyramid, the CI gate on the golden set, and the feedback loop.

Run from the series root:  uv run python posts/20-evaluation/diagrams/src/00-hero-evaluation.py
Writes posts/20-evaluation/diagrams/00-hero-evaluation.svg.
No number is drawn: frequency and cost are an order, not values (section 2 says so). Every tier name and every
"runs" clause is the body's wording, asserted against index.md below.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("**Unit.**", "run on every commit", "**Component.**", "Run on every pull request that touches the component",
               "**End-to-end.**", "Run on every pull request that touches what the answer depends on",
               "**Online.** Production traffic and its signals (section 7): the source of truth, and the slowest loop",
               "every production incident becomes a new case", "Frequency and cost in the figure are an order, not numbers",
               "blocks a drop larger than its tolerance"):
    assert phrase in BODY, phrase

# (tier, what it checks, when it runs), top of the pyramid first
TIERS = [
    ("Online", "production traffic and its signals", "always on; the slowest loop"),
    ("End-to-end", "the full pipeline on golden tasks", "every pull request touching the answer"),
    ("Component", "retriever, reranker, classifier, each alone", "every pull request touching it"),
    ("Unit", "deterministic code: chunker, parser, schema", "every commit"),
]

desc = ("A step pyramid of four tiers, narrow at the top: Online, production traffic and its signals, always on, the "
        "slowest loop; End-to-end, the full pipeline on golden tasks, every pull request touching the answer; Component, "
        "retriever, reranker and classifier each alone, every pull request touching it; Unit, deterministic code such "
        "as the chunker, parser and schema, every commit. An arrow up the side reads rarer and costlier per run. A "
        "dashed line separates the online tier from the three offline tiers. Below, a golden set card feeds a CI gate "
        "card that blocks a drop larger than its tolerance, and an arrow carries every online incident back into the "
        "golden set as a new case. No numbers are drawn.")

fig = Figure("00-hero-evaluation", "Four tiers, one gate, and a loop back from production", desc,
             subtitle="Up the pyramid each tier runs less often and costs more per run: an order, not numbers.",
             height=720, data_w=True)

CX, ROW_H, GAP, TOP = 304, 72, 16, 128
WIDTHS = [160, 240, 320, 400]
COL = 568
bands = []
for i, ((name, what, when), w) in enumerate(zip(TIERS, WIDTHS)):
    y = TOP + i * (ROW_H + GAP)
    b = Box(CX - w // 2, y, w, ROW_H)
    fig.fill(b, "neutral-soft", fit=False)
    fig.outline(b, "border", radius=0)
    fig.text(CX, y + 42, name, "head", anchor="middle")
    fig.text(COL, y + 30, what, "label")
    fig.text(COL, y + 54, when, "note")
    bands.append(b)

# online above, offline below
div_y = TOP + ROW_H + GAP // 2
fig.edge((80, div_y), (920, div_y), color="ink-muted", dash="lead")
fig.text(80, div_y - 12, "online", "note")
fig.text(80, div_y + 24, "offline", "note")

# the order: rarer and costlier going up
AX = 528
fig.arrow((AX, bands[3].bottom), (AX, bands[0].y))
fig.text(AX, bands[3].bottom + 24, "frequent, cheap", "note", anchor="middle")
fig.text(AX, bands[0].y - 8, "rarer, costlier", "note", anchor="middle")

# golden set and gate
CY = 520
gold = fig.card(40, CY, 400, 96, heading="Golden set",
                lines=["human-checked cases with expected outputs", "under the component and end-to-end tiers"])
gate = fig.card(520, CY, 400, 96, heading="CI gate",
                lines=["blocks a drop larger than its tolerance", "on every pull request"])
fig.arrow((440, CY + 48), (520, CY + 48))

# the loop back: every online incident becomes a new case
lx = 64
fig.arrow((bands[0].x, bands[0].y + 36), (lx, CY), via=[(lx, bands[0].y + 36)])
fig.text(lx + 16, bands[0].y + 28, "incident", "note")

fig.caption("Every online incident becomes a golden case, so the gate guards against it from then on.")
fig.write()
