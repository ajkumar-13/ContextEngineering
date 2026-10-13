"""Post 20, section 4: the companion's gate on the twenty-case golden set, each change's drop against the tolerance.

Run from the series root:  uv run python posts/20-evaluation/diagrams/src/02-gate-run.py
Writes posts/20-evaluation/diagrams/02-gate-run.svg.
Every value is computed here by running snippets/eval_gate.py (loaded with runpy, its print captured): the baseline
and the three changed runs are rescored with the snippet's own functions, the gate is rerun, and the drops are
asserted against the table the snippet printed and against the copy of that table in index.md.
"""
import contextlib
import io
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
out = io.StringIO()
with contextlib.redirect_stdout(out):
    S = runpy.run_path(str(POST / "snippets" / "eval_gate.py"))
printed = out.getvalue()
for line in printed.strip().splitlines():
    assert line in BODY, line                     # the body quotes the snippet's output verbatim

RECALL, TOL = S["RECALL"], S["DEFAULT_TOLERANCE"]
assert TOL == 0.05
saved, _ = S["run"](S["baseline"])
CHANGES = [("BM25 dropped", S["bm25_dropped"]), ("headers dropped", S["headers_dropped"]),
           ("both dropped", S["both_dropped"])]
rows, verdicts = [], []
for name, system in CHANGES:
    scores, _ = S["run"](system)
    gate = S["check_regression"](scores, saved)
    verdicts.append((name, gate.passed))
    for metric, label in ((RECALL, "recall@3"), ("answer_match", "answer match")):
        drop = round(saved[metric] - scores[metric], 3)
        blocked = metric in gate.regressions
        rows.append((f"{name}, {label}", drop, "error" if blocked else "ink-muted"))
assert [v for _, v in verdicts] == [True, False, False]
assert [r[1] for r in rows] == [0.025, 0.0, 0.075, 0.05, 0.15, 0.05]
for phrase in ("recall falls by 0.075", "falls by exactly 0.05, one net case, and that metric passes"):
    assert phrase in BODY, phrase

desc = ("A horizontal bar chart of the drop from the baseline, computed by snippets/eval_gate.py on twenty golden "
        "cases, with a dashed vertical line at the gate's tolerance of 0.05. "
        + "; ".join(f"{lab} {v:.3f}" for lab, v, _ in rows)
        + ". Red bars are the metrics that block the change: recall@3 for headers dropped and for both dropped. "
        "The answer match drops of 0.050 sit exactly on the line and pass. BM25 dropped passes; the other two changes "
        "are blocked.")

fig = Figure("02-gate-run", "A drop must pass the tolerance line to block a change", desc,
             subtitle="Drop from the baseline on twenty golden cases, printed by snippets/eval_gate.py; tolerance 0.05.",
             data_w=True)
fig.legend(40, 120, [dict(color="error", label="blocks the change"), dict(color="ink-muted", label="within tolerance")],
           direction="row")
plot = fig.bar_chart(Box(40, 144, 800, 320), rows, 0, 0.16, [0, 0.05, 0.1, 0.15],
                     fmt=lambda v: f"{v:.2f}", fmt_value=lambda v: f"{v:.3f}", label_w=232, value_w=64,
                     ref_lines=[dict(x=TOL, label="tolerance 0.05")], axis_label="drop from the baseline")
step = plot.h / len(rows)
for k, (name, passed) in enumerate(verdicts):
    y = plot.y + step * (2 * k + 1)
    fig.text(920, y + 5, "pass" if passed else "blocked", "head", anchor="end",
             color=None if passed else "error-ink")

fig.caption("One case on twenty is 0.05, so these one-case drops sit on the line and pass.")
fig.write()
