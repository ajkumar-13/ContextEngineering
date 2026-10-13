"""Post 22, figure 2 (section 4): the mean and the median barely move while the p95 doubles.

Run from the series root:  uv run python posts/22-observability/diagrams/src/02-mean-hides-tail.py
Writes posts/22-observability/diagrams/02-mean-hides-tail.svg.

Where every number comes from: snippets/dashboard.py, imported and run with its seed (week, p95, SLOW_SHARE);
every plotted value is recomputed here and asserted against the table that section 4 quotes. The traffic is
synthetic and illustrative, and the subtitle says so.
"""
import random
import runpy
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Box, Figure  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "dashboard.py"
M = runpy.run_path(str(SNIP), run_name="snippet")
rng = random.Random(22)
WEEKS = [M["week"](rng, share) for share in M["SLOW_SHARE"].values()]
assert list(M["SLOW_SHARE"].values()) == [0.02, 0.08]
p95 = M["p95"]
LAT = [
    ("mean", [statistics.mean(w[0]) for w in WEEKS]),
    ("median", [statistics.median(w[0]) for w in WEEKS]),
    ("p95", [p95(w[0]) for w in WEEKS]),
]
COST = [
    ("median", [statistics.median(w[1]) for w in WEEKS]),
    ("p95", [p95(w[1]) for w in WEEKS]),
]
assert [[f"{v:.2f}" for v in vs] for _, vs in LAT] == [["4.63", "5.03"], ["4.55", "4.59"], ["5.58", "11.18"]]
assert [[f"{v:.3f}" for v in vs] for _, vs in COST] == [["0.100", "0.102"], ["0.169", "0.184"]]
MEAN_DRIFT = LAT[0][1][1] / LAT[0][1][0] - 1
assert f"{MEAN_DRIFT:.0%}" == "9%"  # the caption and section 4

fig = Figure(
    "02-mean-hides-tail", "The p95 doubles while the median holds",
    "Two dot plots for two weeks of 1,000 synthetic sessions each; week A has 2% of sessions on a slow path "
    "and week B 8%. Circles are week A, diamonds week B. Latency per session in seconds: mean "
    "4.63 and 5.03, median 4.55 and 4.59, p95 5.58 and 11.18. Cost per session in dollars: median 0.100 and "
    "0.102, p95 0.169 and 0.184.",
    subtitle="1,000 synthetic sessions a week from snippets/dashboard.py; slow path 2% in week A, 8% in week B.",
    data_w=True)

left, right = fig.row([3, 2])
STYLE = dict(colors=("ink-muted", "ink"), shapes=("circle", "diamond"), values=True, label_w=80)
lb = fig.panel(left, "Latency per session, seconds")
fig.dot_plot(Box(lb.x, lb.y, lb.w, lb.h - 48), [(n, v) for n, v in LAT], 4, 12, [4, 6, 8, 10, 12],
             fmt_tick=lambda v: f"{v:g}", fmt_value=lambda v: f"{v:.2f}", pad_right=56, **STYLE)
rb = fig.panel(right, "Cost per session, dollars")
fig.dot_plot(Box(rb.x, rb.y, rb.w, rb.h - 48), [(n, v) for n, v in COST], 0.08, 0.20, [0.08, 0.14, 0.20],
             fmt_tick=lambda v: f"{v:.2f}", fmt_value=lambda v: f"{v:.3f}", pad_right=56, **STYLE)
fig.legend(40, 456, [
    dict(color="ink-muted", label="week A, 2% slow", mark="circle"),
    dict(color="ink", label="week B, 8% slow", mark="diamond"),
], direction="row")
fig.caption("A dashboard of means shows a 9% drift where the p95 shows a broken path.")
fig.write()
