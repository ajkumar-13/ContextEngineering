"""Post 20, section 6: position bias and verbosity bias of LLM judges, as Zheng et al. (2023) measured them.

Run from the series root:  uv run python posts/20-evaluation/diagrams/src/03-judge-biases.py
Writes posts/20-evaluation/diagrams/03-judge-biases.svg.

Every value is cited, none is measured here. Source: Zheng, L. et al., "Judging LLM-as-a-Judge with MT-Bench and
Chatbot Arena", NeurIPS 2023 Datasets and Benchmarks, arXiv:2306.05685v4 (24 December 2023).
Table 2 ("Position bias of different LLM judges"), default prompt: consistency (same verdict after the two answers
swap places) and the share biased toward the first answer. Section 3.4 ("Few-shot judge"): few-shot examples raised
GPT-4's consistency "from 65.0% to 77.5%". Table 3: failure rate under the "repetitive list" attack on 23 answers
(the padded answer judged better). Values asserted against index.md.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

# Table 2, default prompt: judge -> (consistency %, biased toward first %)
TABLE2 = {"Claude-v1": (23.8, 75.0), "GPT-3.5": (46.2, 50.0), "GPT-4": (65.0, 30.0)}
FEW_SHOT_GPT4 = 77.5          # section 3.4
TABLE3 = {"Claude-v1": 91.3, "GPT-3.5": 91.3, "GPT-4": 8.7}   # repetitive-list attack, 23 answers

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("GPT-4 kept its verdict after the swap in 65.0% of cases and favoured the first answer in 30.0%",
               "Claude-v1 was consistent in 23.8% and favoured the first in 75.0% (Table 2)",
               "raised GPT-4's consistency to 77.5%", "padded 23 answers",
               "91.3% of cases for Claude-v1 and GPT-3.5 and 8.7% for GPT-4 (Table 3)", "46.2 for GPT-3.5"):
    assert phrase in BODY, phrase

left_rows = [(j, [c]) for j, (c, _) in TABLE2.items()] + [("GPT-4, few-shot", [FEW_SHOT_GPT4])]
right_rows = [(j, [v]) for j, v in TABLE3.items()]

desc = ("Two cited dot charts from Zheng et al. (2023), hollow diamonds on axes from 0 to 100 percent. Left, position "
        "bias, Table 2, default prompt: the share of verdicts unchanged when the two answers swap places, "
        + ", ".join(f"{j} {v[0]:.1f}%" for j, v in left_rows)
        + " (few-shot, section 3.4). Right, verbosity bias, Table 3: the share of 23 answers where the judge preferred "
        "a copy padded with a rephrased list, " + ", ".join(f"{j} {v[0]:.1f}%" for j, v in right_rows) + ".")

fig = Figure("03-judge-biases", "Judges flip under a swap and fall for padding", desc,
             subtitle="Cited: Zheng et al. (2023), Tables 2 and 3 and section 3.4. Hollow marks are the paper's values.",
             data_w=True)
left, right = fig.row(2, y=136, h=320)
fig.text(left.x, 128, "Position bias: verdict kept after a swap", "head")
fig.text(right.x, 128, "Verbosity bias: padded answer preferred", "head")
pct = lambda v: f"{v:g}"  # noqa: E731
fig.dot_plot(Box(left.x, 144, left.w, 296), left_rows, 0, 100, [0, 50, 100], colors=("ink",), shapes=("diamond",),
             connect=None, hollow=True, values=True, unit="%", label_w=136, pad_right=64, fmt_tick=pct,
             fmt_value=lambda v: f"{v:.1f}", axis_label="percent of pairs, both orders")
fig.dot_plot(Box(right.x, 144, right.w, 296), right_rows, 0, 100, [0, 50, 100], colors=("ink",), shapes=("diamond",),
             connect=None, hollow=True, values=True, unit="%", label_w=104, pad_right=64, fmt_tick=pct,
             fmt_value=lambda v: f"{v:.1f}", axis_label="percent of 23 padded answers")

fig.caption("Mitigate both before trusting a judge: swap the order, and test it on padded answers.")
fig.write()
