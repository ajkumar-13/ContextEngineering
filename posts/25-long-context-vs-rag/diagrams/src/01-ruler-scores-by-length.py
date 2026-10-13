"""Post 25, section 3: RULER's 13-task average against context length, with its 85.6% threshold.

Run from the series root:  uv run python posts/25-long-context-vs-rag/diagrams/src/01-ruler-scores-by-length.py
Writes posts/25-long-context-vs-rag/diagrams/01-ruler-scores-by-length.svg.

Every value is cited, none is measured here. Source: Hsieh, C.-P. et al., "RULER: What's the Real Context Size of
Your Long-Context Language Models?", arXiv:2404.06654v3 (6 August 2024), Table 3. The rows below are copied from
the table for the five models drawn (claimed length, effective length as printed, scores at 4K to 128K); post 06's
figure script (03-ruler-effective-length.py) holds the whole table, and the rows are asserted equal to it. The
effective length (the longest tested length whose average stays above 85.6%, the score of Llama2 7B at 4K) is
recomputed from the scores and asserted against the printed one. Lengths are evenly spaced on a doubling axis.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")

LENGTHS = [4, 8, 16, 32, 64, 128]
THRESHOLD = 85.6
TABLE3 = {   # model as the paper names it: (claimed, effective as printed, scores at LENGTHS)
    "Gemini-1.5-Pro": ("1M", ">128K", [96.7, 95.8, 96.0, 95.9, 95.9, 94.4]),
    "GPT-4": ("128K", "64K", [96.6, 96.3, 95.2, 93.2, 87.0, 81.2]),
    "GradientAI/Llama3 (70B)": ("1M", "16K", [95.1, 94.4, 90.8, 85.4, 80.9, 72.1]),
    "Llama3.1 (70B)": ("128K", "64K", [96.5, 95.8, 95.4, 94.8, 88.4, 66.6]),
    "Qwen2 (72B)": ("128K", "32K", [96.9, 96.1, 94.9, 94.1, 79.8, 53.7]),
}

# the same rows as post 06's full copy of Table 3
src06 = (POST.parent / "06-context-failure-modes" / "diagrams" / "src" / "03-ruler-effective-length.py").read_text(
    encoding="utf-8")
for name, (claimed, eff, scores) in TABLE3.items():
    row = f'"{name}": ("{claimed}", "{eff}", [{", ".join(f"{s}" for s in scores)}]),'
    assert row in src06, row


def effective(scores):
    run = 0
    for n, s in zip(LENGTHS, scores):
        if s <= THRESHOLD:
            break
        run = n
    return ">128K" if run == 128 else (f"{run}K" if run else "<4K")


for name, (_, eff, scores) in TABLE3.items():
    assert effective(scores) == eff, name

# the phrases and numbers the body and its alt text state
for phrase in ("13 tasks in all, run on 17 models at lengths from 4K to 128K tokens",
               "85.6%, the score of Llama 2 7B at 4K", "The figure below draws the scores themselves.",
               "falls from 96.7 to 94.4", "falls from 96.6 to 81.2", "falls from 95.1 to 72.1",
               "falls from 96.5 to 66.6", "falls from 96.9 to 53.7", "four of the five cross it inside the window"):
    assert phrase in BODY, phrase
inside = [n for n, (c, e, _) in TABLE3.items() if not e.startswith(">")]
assert len(inside) == 4

SHORT = {"GradientAI/Llama3 (70B)": "Gradient Llama3 70B", "Llama3.1 (70B)": "Llama3.1 70B",
         "Qwen2 (72B)": "Qwen2 72B"}
SHAPES = ["circle", "square", "triangle", "diamond", "circle"]
COLOURS = ["ink", "ink", "ink-muted", "ink", "ink-muted"]

series = []
for (name, (claimed, eff, scores)), shape, colour in zip(TABLE3.items(), SHAPES, COLOURS):
    label = f"{SHORT.get(name, name)}, claims {claimed}"
    series.append(dict(xs=list(range(len(LENGTHS))), ys=scores, color=colour, label=label, shape=shape,
                       hollow=True))

desc = ("A line chart cited from RULER Table 3 (Hsieh et al., 2024): the 13-task average score in percent against "
        "context length on a doubling axis from 4K to 128K tokens, with a dashed reference line at the 85.6% "
        "threshold that defines effective length and the band below it shaded red. Hollow marks, one line per "
        "model: Gemini-1.5-Pro, claiming 1M, 96.7 at 4K to 94.4 at 128K, above the threshold throughout; GPT-4, "
        "claiming 128K, 96.6 to 81.2, below it after 64K; GradientAI/Llama3 (70B), claiming 1M, 95.1 to 72.1, "
        "below it after 16K; Llama3.1 (70B), claiming 128K, 96.5 to 66.6, below it after 64K; Qwen2 (72B), "
        "claiming 128K, 96.9 to 53.7, below it after 32K.")

fig = Figure("01-ruler-scores-by-length", "Most scores cross the threshold inside the claimed window", desc,
             subtitle="Cited: RULER, Table 3 (Hsieh et al., 2024). Effective length ends where the 13-task "
                      "average drops below 85.6%.",
             height=720, data_w=True)

fig.line_chart(Box(40, 120, 880, 520), series, x=(0, 5, list(range(6))), y=(50, 100, [50, 60, 70, 80, 90, 100]),
               x_label="context length in tokens (doubling scale)", y_label="RULER average, %",
               fmt_x=lambda i: f"{LENGTHS[int(i)]}K", fmt_y=lambda v: f"{v:g}", label_w=240,
               hbands=[(50, THRESHOLD, "error")],
               ref_lines=[dict(y=THRESHOLD, label="85.6%, threshold", at="left")])

fig.caption("Four of the five drop below the threshold by 128K; one of the four claims 1M.")
fig.write()
