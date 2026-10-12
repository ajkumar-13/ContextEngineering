"""Post 10, section 3: three PDF strategies, tried in order, and the evidence that escalates from one to the next.

Run from anywhere:  python posts/10-data-ingestion-pipelines/diagrams/src/02-pdf-decision.py
Writes posts/10-data-ingestion-pipelines/diagrams/02-pdf-decision.svg.
No numbers are drawn. The order, the two questions and the risk of each strategy are section 3 of index.md,
whose sentences are asserted below.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("**try born-digital extraction; if the text layer is empty or the page is an image, fall back to OCR; "
               "if reading order or tables come out mangled, escalate to a layout-aware parser.**",
               "It is close to free, so it is tried first.",
               "On a two-column page, a reader that goes top to bottom and left to right crosses the gutter",
               "OCR brings its own class of error (\"rn\" read as \"m\", a dropped decimal point)",
               "a parser still errs on hard tables and unusual layouts",
               "A single corpus often needs all three, because it contains all three kinds of PDF."):
    assert phrase in BODY, phrase

# spine: (heading, note, kind) and the strategy each "yes" leads to: (heading, note)
SPINE = [
    ("Try born-digital extraction", "read the text layer; risk: two columns interleave", "step"),
    ("Is the text layer empty, or the page an image?", None, "question"),
    ("Are reading order or tables mangled?", None, "question"),
    ("Index the born-digital text", "after reading a sample of it", "end"),
]
YES = {1: ("OCR", "risk: character errors, rn read as m"),
       2: ("Layout-aware parser", "risk: still errs on hard tables")}

desc = ("A decision walk for one PDF down a spine of four boxes. First, try born-digital extraction: read the text "
        "layer; its risk is that two columns interleave. Then ask: is the text layer empty, or the page an image? Yes "
        "leads right to OCR, whose risk is character errors, rn read as m. No leads down to: are reading order or "
        "tables mangled? Yes leads right to a layout-aware parser, whose risk is that it still errs on hard tables. "
        "No leads to: index the born-digital text, after reading a sample of it.")

fig = Figure("02-pdf-decision", "Start with the text layer; escalate on evidence", desc,
             subtitle="Three kinds of PDF, three extractors; each question is answered by reading the extracted text.",
             data_w=True)

S_X, S_W, BOX_H, GAP = 40, 432, 64, 32
R_X, R_W = 568, 352
tops = [104 + i * (BOX_H + GAP) for i in range(len(SPINE))]
for i, (head, note, kind) in enumerate(SPINE):
    b = Box(S_X, tops[i], S_W, BOX_H)
    if kind == "question":
        fig.fill(b, "neutral-soft", radius=8, fit=False)
        fig.outline(b, "border", radius=8)
        fig.text(S_X + 16, tops[i] + 38, head, "label")
    else:
        fig.outline(b, "rule", radius=8)
        fig.text(S_X + 16, tops[i] + 28, head, "head")
        fig.text(S_X + 16, tops[i] + 50, note, "note")
    if i in YES:
        r = Box(R_X, tops[i], R_W, BOX_H)
        fig.outline(r, "rule", radius=8)
        fig.text(R_X + 16, tops[i] + 28, YES[i][0], "head")
        fig.text(R_X + 16, tops[i] + 50, YES[i][1], "note")
        fig.arrow((b.right + 8, b.cy), (r.x - 8, r.cy), label="yes")
    if i < len(SPINE) - 1:
        fig.arrow((S_X + 64, b.bottom + 2), (S_X + 64, tops[i + 1] - 2))
        if kind == "question":
            fig.text(S_X + 76, b.bottom + 20, "no", "note")

fig.caption("One corpus often needs all three, because it holds all three kinds of PDF.")
fig.write()
