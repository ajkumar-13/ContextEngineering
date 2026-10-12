"""Post 11, section 2: what contextual retrieval adds to a chunk, and the failure rates Anthropic reports for it.

Run from the series root:  uv run python posts/11-rag-in-depth/diagrams/src/02-contextual-retrieval.py
Writes posts/11-rag-in-depth/diagrams/02-contextual-retrieval.svg.

Every value is cited, none is measured here. Source: Anthropic, "Introducing Contextual Retrieval", published
19 September 2024, https://www.anthropic.com/news/contextual-retrieval (consulted 12 October 2026). The page reports
the top-20-chunk retrieval failure rate (1 minus recall@20), averaged across its knowledge domains with its best
embedding configuration, as 5.7% for the baseline, 3.7% with contextual embeddings, 2.9% with contextual embeddings
and contextual BM25, and 1.9% with reranking added; and the reductions as 35%, 49% and 67%. The script recomputes each
reduction from the two rates and asserts it against the stated percentage and against index.md. The example chunk
and its contextualised form are quoted verbatim from the page.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BASE = 5.7
CITED = [  # (step as the post names it, failure rate %, reduction % as the page states it)
    ("Contextual embeddings", 3.7, 35),
    ("+ contextual BM25", 2.9, 49),
    ("+ reranking", 1.9, 67),
]
for _, rate, red in CITED:
    assert round((BASE - rate) / BASE * 100) == red, (rate, red)

ORIGINAL = "The company's revenue grew by 3% over the previous quarter."
CONTEXT = ("This chunk is from an SEC filing on ACME corp's performance in Q2 2023; the previous quarter's revenue "
           "was $314 million.")

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ('Anthropic\'s "Introducing Contextual Retrieval" (September 2024)',
               "contextual embeddings cut it by 35% (5.7% to 3.7%), adding contextual BM25 by 49% (to 2.9%), and "
               "adding a reranker by 67% (to 1.9%)", "1 minus recall@20"):
    assert phrase in BODY, phrase

desc = ("Two parts, cited from Anthropic's page Introducing Contextual Retrieval (September 2024). Top, the page's "
        "example: the chunk 'The company's revenue grew by 3% over the previous quarter.' and the same chunk with a "
        "model-written context prepended, naming a U.S. Securities and Exchange Commission (SEC) filing on ACME "
        "corp's performance in Q2 2023 and a previous-quarter revenue of $314 million. Bottom, a dumbbell chart of "
        "the top-20 retrieval failure rate, 1 minus recall@20, each row from the 5.7% baseline, hollow circle, to "
        "the rate with the technique, hollow diamond: contextual embeddings 3.7% (minus 35%), plus contextual BM25 "
        "2.9% (minus 49%), plus reranking 1.9% (minus 67%).")

fig = Figure("02-contextual-retrieval", "Chunk context plus reranking cut failed retrievals by 67%", desc,
             subtitle='Cited: Anthropic, "Introducing Contextual Retrieval" (September 2024). Values as the page '
                      "states them.", height=720, data_w=True)

# top: the page's example chunk, before and after
fig.text(40, 128, "The page's example chunk", "head")
CARD_Y, CARD_H = 144, 156
fig.card(40, CARD_Y, 312, CARD_H, heading="Before", lines=["The company's revenue grew by", "3% over the previous quarter."])
ax0, aw = 384, 536
context_lines = ["This chunk is from an SEC filing on ACME corp's", "performance in Q2 2023; the previous quarter's",
                 "revenue was $314 million."]
assert " ".join(context_lines) == CONTEXT
fig.card(ax0, CARD_Y, aw, CARD_H, heading="After: model-written context first")
# the added context, shaded, then the original chunk unchanged on the last line
fig.fill(Box(ax0 + 8, 188, aw - 16, 76), "border", radius=4, fit=False)
for k, line in enumerate(context_lines + [ORIGINAL]):
    fig.text(ax0 + 16, 208 + 24 * k, line, "label")

# bottom: the cited failure rates
fig.text(40, 360, "Top-20 retrieval failure rate (1 minus recall@20), cited", "head")
fig.legend(40, 392, [dict(color="ink-muted", label=f"baseline, {BASE}%", mark="circle", hollow=True),
                     dict(color="ink", label="with the technique", mark="diamond", hollow=True)], direction="row")
rows = [(f"{name}, \u2212{red}%", [BASE, rate]) for name, rate, red in CITED]
fig.dot_plot(Box(40, 416, 880, 208), rows, 0, 6, [0, 2, 4, 6], colors=("ink-muted", "ink"),
             shapes=("circle", "diamond"), connect="rule", hollow=True, values=True, unit="%", label_w=272,
             pad_right=56, fmt_value=lambda v: f"{v:.1f}", fmt_tick=lambda v: f"{v:g}",
             axis_label="failure rate: percent of relevant chunks not retrieved in the top 20")

fig.caption("Each reduction is from the same 5.7% baseline: the techniques stack.")
fig.write()
