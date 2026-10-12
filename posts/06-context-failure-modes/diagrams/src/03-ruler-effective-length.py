"""Post 06, section 5: claimed context window against effective length, as RULER measured them.

Run from anywhere:  python posts/06-context-failure-modes/diagrams/src/03-ruler-effective-length.py
Writes posts/06-context-failure-modes/diagrams/03-ruler-effective-length.svg.

Every value is cited, none is measured here. Source: Hsieh, C.-P. et al., "RULER: What's the Real Context Size of
Your Long-Context Language Models?", arXiv:2404.06654v3 (6 August 2024), Table 3 ("Long Context Performance (%)
of selected models evaluated at length from 4K to 128K"). The effective length is the longest tested length whose
13-task average stays above 85.6%, the score of Llama2 (7B) at 4K. TABLE3 below copies the whole main table (claimed
length, effective length, and the scores at 4K, 8K, 16K, 32K, 64K, 128K); the script recomputes every effective
length from the scores and the threshold, and the counts that section 5 of index.md states, and asserts them.
Lengths are in thousands of tokens as the paper labels them (4K, 128K, 1M); 1M is placed at 1,000.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

LENGTHS = [4, 8, 16, 32, 64, 128]
THRESHOLD = 85.6
# model as the paper names it: (claimed, effective as printed, scores at LENGTHS)
TABLE3 = {
    "Gemini-1.5-Pro": ("1M", ">128K", [96.7, 95.8, 96.0, 95.9, 95.9, 94.4]),
    "GPT-4": ("128K", "64K", [96.6, 96.3, 95.2, 93.2, 87.0, 81.2]),
    "Llama3.1 (70B)": ("128K", "64K", [96.5, 95.8, 95.4, 94.8, 88.4, 66.6]),
    "Qwen2 (72B)": ("128K", "32K", [96.9, 96.1, 94.9, 94.1, 79.8, 53.7]),
    "Command-R-plus (104B)": ("128K", "32K", [95.6, 95.2, 94.2, 92.0, 84.3, 63.1]),
    "GLM4 (9B)": ("1M", "64K", [94.7, 92.8, 92.1, 89.9, 86.7, 83.1]),
    "Llama3.1 (8B)": ("128K", "32K", [95.5, 93.8, 91.6, 87.4, 84.7, 77.0]),
    "GradientAI/Llama3 (70B)": ("1M", "16K", [95.1, 94.4, 90.8, 85.4, 80.9, 72.1]),
    "Mixtral-8x22B (39B/141B)": ("64K", "32K", [95.6, 94.9, 93.4, 90.9, 84.7, 31.7]),
    "Yi (34B)": ("200K", "32K", [93.3, 92.2, 91.3, 87.5, 83.2, 77.3]),
    "Phi3-medium (14B)": ("128K", "32K", [93.3, 93.2, 91.1, 86.8, 78.6, 46.1]),
    "Mistral-v0.2 (7B)": ("32K", "16K", [93.6, 91.2, 87.2, 75.4, 49.0, 13.8]),
    "LWM (7B)": ("1M", "<4K", [82.3, 78.4, 73.7, 69.1, 68.1, 65.0]),
    "DBRX (36B/132B)": ("32K", "8K", [95.1, 93.8, 83.6, 63.1, 2.4, 0.0]),
    "Together (7B)": ("32K", "4K", [88.2, 81.1, 69.4, 63.0, 0.0, 0.0]),
    "LongChat (7B)": ("32K", "<4K", [84.7, 79.9, 70.8, 59.3, 0.0, 0.0]),
    "LongAlpaca (13B)": ("32K", "<4K", [60.6, 57.0, 56.6, 43.6, 0.0, 0.0]),
}
assert len(TABLE3) == 17


def k(label):
    """'128K' -> 128, '1M' -> 1000 (thousands of tokens, as the paper labels them)."""
    return 1000 if label == "1M" else int(label.rstrip("K"))


def effective(scores):
    """The longest tested length whose score passes the threshold, printed as the paper prints it."""
    passing = [n for n, s in zip(LENGTHS, scores) if s > THRESHOLD]
    if not passing or passing[0] != 4:
        return "<4K"
    run = 0
    for n, s in zip(LENGTHS, scores):     # the paper's lengths pass from 4K up to the effective one
        if s <= THRESHOLD:
            break
        run = n
    return ">128K" if run == 128 else f"{run}K"


for name, (claimed, eff, scores) in TABLE3.items():
    assert effective(scores) == eff, (name, effective(scores), eff)

# the counts section 5 states
shorter = [n for n, (c, e, _) in TABLE3.items() if not e.startswith(">") and (e.startswith("<") or k(e) < k(c))]
assert len(shorter) == 16 and "Gemini-1.5-Pro" not in shorter
between = [n for n, (_, e, _) in TABLE3.items() if e in ("16K", "32K", "64K")]
assert len(between) == 11

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("16 of the 17 long-context models reach that threshold only at a length shorter than the window "
               "they claim", "85.6%, the score of Llama 2 7B at 4K", "11 of its 17 models between 16K and 64K tokens",
               "The figure below draws eight of them."):
    assert phrase in BODY, phrase

# the eight rows drawn: every model whose two lengths are exact values (no < or >), chosen to span the range
DRAWN = ["GPT-4", "Llama3.1 (70B)", "GLM4 (9B)", "Qwen2 (72B)", "Yi (34B)", "GradientAI/Llama3 (70B)",
         "Mistral-v0.2 (7B)", "DBRX (36B/132B)"]
LABEL = {"DBRX (36B/132B)": "DBRX (132B)"}
rows = [(LABEL.get(n, n), [k(TABLE3[n][0]), k(TABLE3[n][1])]) for n in DRAWN]
ratios = [c / e for _, (c, e) in rows]
assert min(ratios) == 2 and max(ratios) > 60      # the caption's "a factor of two to more than sixty"


def fmt(v):
    return "1M" if v == 1000 else f"{v:g}K"


desc = ("A dumbbell chart on a logarithmic axis of context length from 4K to 1M tokens, one row per model, cited "
        "from RULER Table 3 (Hsieh et al., 2024): a hollow circle at the claimed window, a hollow diamond at the "
        "effective length, where the 13-task average stays above 85.6%, joined by a red line. "
        + "; ".join(f"{lab}, claimed {fmt(c)}, effective {fmt(e)}" for lab, (c, e) in rows) + ".")

fig = Figure("03-ruler-effective-length", "Advertised windows outrun the length models use well", desc,
             subtitle="Cited: RULER, Table 3 (Hsieh et al., 2024). Effective: the 13-task average stays above 85.6%.",
             data_w=True)

fig.legend(40, 120, [dict(color="ink", label="effective length", mark="diamond", hollow=True),
                     dict(color="ink-muted", label="claimed window", mark="circle", hollow=True),
                     dict(color="red", label="claimed, past the effective length", mark="line")], direction="row")
fig.dot_plot(Box(40, 144, 880, 332), rows, 4, 1000, [4, 16, 64, 256, 1000],
             colors=("ink-muted", "ink"), shapes=("circle", "diamond"), connect="red", hollow=True,
             x_log=True, fmt_tick=fmt, fmt_value=fmt, values=True, label_w=208, pad_right=48,
             axis_label="context length in tokens (log scale)")

fig.caption("Every model drawn holds its accuracy over a shorter span than its advertised window.")
fig.write()
