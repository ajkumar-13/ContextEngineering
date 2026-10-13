"""Post 14, section 6: the CI gate passing rules 1.2.0 and blocking rules 1.3.0.

Run from anywhere:  python posts/14-system-prompt-as-software/diagrams/src/03-ci-gate.py
Writes posts/14-system-prompt-as-software/diagrams/03-ci-gate.svg.
Every result drawn is printed by snippets/prompt_ci.py, which this script runs and parses (asserted): the lint
lines, the pass counts, the failing case numbers with their expected and returned tools, and the two gate
verdicts. Amounts are drawn with thousands separators (1,000), as the body writes them in prose.
"""
import contextlib
import io
import re
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
    runpy.run_path(str(POST / "snippets" / "prompt_ci.py"), run_name="__main__")
printed = out.getvalue()
v1, v2 = printed.split("\nprompt v2 ")
assert "lint: no findings" in v1 and "regression: 10/10 cases pass" in v1 and "gate: pass" in v1
m = re.search(r"lint: rules #(\d+) and #(\d+) disagree on refunds above (\d+) dollars up to (\d+) dollars", v2)
assert m and m.groups() == ("412", "481", "1000", "2000")
assert "regression: 8/10 cases pass" in v2
fails = re.findall(r"case (\d\d) \"[^\"]+\": expected (\w+), got (\w+)", v2)
assert fails == [("04", "escalate_to_manager", "refund_order"), ("05", "escalate_to_manager", "refund_order")]
assert "gate: blocked (1 lint finding, 2 failing cases)" in v2
for chunk in (v1.split("sha256")[1], "sha256" + v2.split("sha256")[1]):
    for line in chunk.strip().splitlines()[1:]:
        assert line in BODY, line          # the body quotes these lines verbatim

ROWS = [
    ("Rules 1.2.0", "neutral",
     [("Pull request", ["rules 1.2.0"], None),
      ("Lint", ["no findings"], None),
      ("Regression", ["10/10 cases pass"], None),
      ("Gate", ["pass"], None)]),
    ("Rules 1.3.0 adds rule #481", "error",
     [("Pull request", ["rules 1.3.0", "adds #481"], None),
      ("Lint", ["#412 and #481 disagree on", "refunds above 1,000 dollars", "up to 2,000 dollars"], "error"),
      ("Regression", ["8/10 cases pass", "cases 04 and 05 return", "refund_order"], "error"),
      ("Gate", ["blocked"], "error")]),
]

desc = ("Two rows of the same CI pipeline, each a chain of four boxes: pull request, lint, regression and gate. "
        "Row one, rules 1.2.0: lint has no findings, 10/10 cases pass, the gate passes. Row two, rules 1.3.0 adds "
        "rule #481: lint reports that #412 and #481 disagree on refunds above 1,000 dollars up to 2,000 dollars, "
        "8/10 cases pass, cases 04 and 05 returning refund_order where escalate_to_manager was expected, and "
        "the gate blocks the merge. The failing boxes are outlined in red.")

fig = Figure("03-ci-gate", "The gate blocks the contradictory rule twice over", desc,
             subtitle="Both runs as snippets/prompt_ci.py prints them: a static lint, then ten regression cases.",
             data_w=True)

WID = [160, 264, 248, 136]
GAP = 24
XS = [40]
for w in WID[:-1]:
    XS.append(XS[-1] + w + GAP)
assert XS[-1] + WID[-1] == 920
BH = 128
for r, (head, _, boxes) in enumerate(ROWS):
    top = 144 + r * 184
    fig.text(40, top - 16, head, "head")
    row = []
    for (name, lines, role), x, w in zip(boxes, XS, WID):
        b = Box(x, top, w, BH)
        fig.fill(b, "neutral-soft" if role is None else "error-soft", radius=8, fit=False)
        fig.outline(b, "border" if role is None else "error", radius=8, width=1 if role is None else 1.5)
        fig.text(x + 12, top + 28, name, "head")
        for i, line in enumerate(lines):
            style = "code" if "_" in line else "label"
            fig.text(x + 12, top + 56 + 24 * i, line, style, color=None if role is None else "error")
        row.append(b)
    fig.chain(row)

fig.caption("The linter sees the overlap without a model; cases 04 and 05 see it because they sit inside it.")
fig.write()
