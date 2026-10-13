"""Post 20, section 3: the three metric families placed on the four tiers, and the two scoring shapes.

Run from the series root:  uv run python posts/20-evaluation/diagrams/src/01-metric-families.py
Writes posts/20-evaluation/diagrams/01-metric-families.svg.
No numbers. Every metric named in a cell is one the body names for that tier and family; the phrases are asserted
against index.md below.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("schema validators", "recall@N", "nDCG@5", "an intent classifier by its agreement with human labels, a prompt block with free-text output by a judge",
               "citation validity", "Faithfulness", "Answer relevancy", "a judge over sampled transcripts",
               "fifty to a hundred outputs per release", "Thumbs up and down", "Refusal rate", "Cost per session",
               "Absolute scoring", "Pairwise scoring", "A regression gate needs absolute scores",
               "picks between two variants pairwise and guards the winner absolutely"):
    assert phrase in BODY, phrase

ROWS = [
    ["Tier", "Deterministic", "LLM judge", "Human"],
    ["Unit", "schema validity, parser output", "not needed", "not needed"],
    ["Component", "recall@N, nDCG@5", "free-text prompt blocks", "labels the golden set"],
    ["End-to-end", "answer match, citation validity", "faithfulness, relevancy", "a sample per release"],
    ["Online", "refusal rate, cost, p95", "sampled transcripts", "thumbs up and down"],
]

desc = ("A table with the four tiers as rows and the three metric families as columns. Unit: deterministic schema "
        "validity and parser output; judge and human not needed. Component: recall@N and nDCG@5; a judge for free-text "
        "prompt blocks; people label the golden set. End-to-end, the shaded row: answer match and citation "
        "validity; faithfulness and answer relevancy from the judge; a human sample per release. Online: refusal rate, "
        "cost per session and p95 latency; a judge over sampled transcripts; thumbs up and down. Below, two cards: "
        "absolute scoring rates one output and can gate a build; pairwise scoring compares two outputs and picks a "
        "variant.")

fig = Figure("01-metric-families", "Each tier takes the cheapest family that can judge it", desc,
             subtitle="The end-to-end row is where the judge does the bulk of the work, calibrated by people.",
             data_w=True)

fig.fill(Box(40, 112 + 3 * 40, 880, 40), "neutral-soft", fit=False)   # the end-to-end row
fig.table(40, 112, ROWS, [160, 256, 224, 240], row_h=40)

CY = 344
fig.card(40, CY, 424, 112, heading="Absolute: one output, one score",
         lines=["\u201cfaithful: yes or no\u201d", "a number to threshold: it can gate a build"])
fig.card(496, CY, 424, 112, heading="Pairwise: two outputs, which is better",
         lines=["steadier across judge models", "picks a variant; carries position bias"])

fig.caption("Choose the family by tier and the shape by job: absolute to gate, pairwise to choose.")
fig.write()
