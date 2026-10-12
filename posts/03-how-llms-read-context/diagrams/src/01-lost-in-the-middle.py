"""Post 03 hero (section 5): the lost-in-the-middle curve, drawn only from numbers Liu et al. report.

Run from anywhere:  python posts/03-how-llms-read-context/diagrams/src/01-lost-in-the-middle.py
Writes posts/03-how-llms-read-context/diagrams/01-lost-in-the-middle.svg.

Every plotted value is cited, not measured by this series. Source: Liu, N. F. et al., "Lost in the Middle: How
Language Models Use Long Contexts" (arXiv:2307.03172v3, 2023; TACL 2024):
  - Table 6 (Appendix G.2): multi-document question answering accuracy with 20 total retrieved documents, the
    document with the answer at index 0, 4, 9, 14 and 19 (positions 1st, 5th, 10th, 15th and 20th).
  - Table 1: closed-book accuracy (no documents in the input) of the same models.
The points are joined by straight segments only; nothing between the reported positions is drawn as data.
"""
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

# Liu et al. (2023), Table 6 (20 documents) and Table 1 (closed-book), in percent, as printed.
POSITIONS = [1, 5, 10, 15, 20]                     # index 0, 4, 9, 14, 19 in the paper
CITED = {
    "GPT-3.5-Turbo": {"acc": [75.8, 57.2, 53.8, 55.4, 63.2], "closed_book": 56.1},
    "Claude-1.3": {"acc": [59.9, 55.9, 56.8, 57.2, 60.1], "closed_book": 48.3},
}
gpt = CITED["GPT-3.5-Turbo"]
assert gpt["acc"] == [75.8, 57.2, 53.8, 55.4, 63.2] and gpt["closed_book"] == 56.1
assert CITED["Claude-1.3"]["acc"] == [59.9, 55.9, 56.8, 57.2, 60.1]
# the claims the post makes from these numbers (section 5)
assert min(gpt["acc"]) == gpt["acc"][2] == 53.8 < gpt["closed_book"]       # middle below no documents
assert max(gpt["acc"]) == gpt["acc"][0] and gpt["acc"][-1] > gpt["acc"][2]  # both ends above the middle
claude = CITED["Claude-1.3"]["acc"]
assert claude[-1] == max(claude) and min(claude) == claude[1]                # flatter, still lowest inside
assert round(gpt["acc"][0] - gpt["acc"][2], 1) == 22.0                       # the drop the post states

fig = Figure(
    "01-lost-in-the-middle", "The middle of a long input is used least",
    "A line chart of accuracy against the position of the document that holds the answer among 20 retrieved "
    "documents, cited from Liu et al. (2023), Table 6. GPT-3.5-Turbo, hollow circles: 75.8% at position 1, "
    "57.2% at 5, 53.8% at 10, 55.4% at 15 and 63.2% at 20. Claude-1.3, hollow squares: 59.9%, 55.9%, 56.8%, "
    "57.2% and 60.1%. A dotted line marks GPT-3.5-Turbo with no documents at all, 56.1% (Table 1). A red band "
    "shades the middle positions 5 to 15, where both models score lowest.",
    subtitle="Multi-document question answering, 20 documents. Cited: Liu et al. (2023), Tables 1 and 6.",
    data_w=True)

body = Box(40, 104, 880, 372)
ax = fig.line_chart(
    body,
    [dict(xs=POSITIONS, ys=gpt["acc"], color="ink", label="GPT-3.5-Turbo", shape="circle", hollow=True,
          size=10),
     dict(xs=POSITIONS, ys=claude, color="ink-muted", label="Claude-1.3", shape="square", hollow=True,
          size=10)],
    x=(1, 20, POSITIONS), y=(50, 80, [50, 60, 70, 80]),
    x_label="position of the document with the answer (1st to 20th)", y_label="accuracy (%)",
    fmt_x=lambda v: f"{v}th" if v not in (1,) else "1st",
    label_w=152,
    bands=[(5, 15, "error")],
    ref_lines=[dict(y=gpt["closed_book"])])
ax.text(20, gpt["closed_book"], "GPT-3.5-Turbo,", "note", dx=12, dy=5)
ax.text(20, gpt["closed_book"], f"no documents: {gpt['closed_book']}", "note", dx=12, dy=25)

# the three values the post quotes, next to their points
ax.text(1, gpt["acc"][0], "75.8", "value", dx=12, dy=5)
ax.text(10, gpt["acc"][2], "53.8", "value", anchor="middle", dy=24, color="error-ink")
ax.text(20, gpt["acc"][-1], "63.2", "value", anchor="middle", dy=-14)
ax.text(10, 78, "the middle", "label", anchor="middle", color="error-ink")

fig.caption("GPT-3.5-Turbo with the answer in 10th place does worse than with no documents at all.")
fig.write()
