"""Post 21, section 3: constrained decoding as a mask, step by step, from the toy decoder's printed trace.

Run from anywhere:  uv run python posts/21-structured-output-guardrails/diagrams/src/02-token-mask.py
Writes posts/21-structured-output-guardrails/diagrams/02-token-mask.svg.
Every token, count and result drawn is printed by snippets/constrained_decoding.py, which this script runs and
parses; the body quotes the same print (asserted line by line). Masked steps are shaded in the error role (a
rejected item, ctx_fig_design.md Section 0) and also say "masked" in words; tokens are in the code face.
"""
import contextlib
import io
import re
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
out = io.StringIO()
with contextlib.redirect_stdout(out):
    runpy.run_path(str(POST / "snippets" / "constrained_decoding.py"), run_name="__main__")
printed = out.getvalue().splitlines()
for line in printed:
    assert line in BODY, line                      # the body quotes the whole print
rows = []
for line in printed:
    m = re.match(r"^\s+(\d) +(\d) {2}(.+?) {2,}(\S.*?)(  \(first choice masked\))?$", line)
    if m:
        rows.append((int(m[1]), int(m[2]), m[3].strip(), m[4].strip(), bool(m[5])))
assert [r[0] for r in rows] == list(range(1, 9)), rows
masked = [r[0] for r in rows if r[4]]
assert masked == [1, 3, 6, 7, 8] and "  the mask overrode the model at 5 of 8 steps" in printed
result = '{"category": "refund", "priority": 5}'
cut = '{"category": "refund", "priority":'
assert f"  parses: {result}" in printed and f"  {cut}" in printed
assert "  json.loads fails: Expecting value: line 1 column 36 (char 35)" in printed

desc = ("A table of the eight steps of a toy constrained decoder: step, number of allowed tokens, the model's first "
        "choice and the emitted token. " + " ".join(
            f"Step {s}: {n} allowed, first choice {f}, emitted {"end of output" if e == "<end>" else e}{', masked' if mk else ''}."
            for s, n, f, e, mk in rows)
        + f" The output {result} parses. With max_tokens = 5 the output stops at {cut} and does not parse.")
fig = Figure("02-token-mask", "The mask lets only the grammar's tokens through", desc,
             subtitle="snippets/constrained_decoding.py: a fixed ranking stands in for the model; the grammar allows one shape.",
             height=720, data_w=True)

X, Y, RH = 40, 120, 48
W = [72, 104, 320, 264, 120]
assert X + sum(W) == 920
header = [["Step", "Allowed", "Model's first choice", "Emitted", ""]]
body = [[str(s), str(n), "", "", "masked" if mk else ""] for s, n, _, _, mk in rows]
fig.table(X, Y, header + body, W, row_h=RH, col_align=["end", "end", "start", "start", "start"],
          highlight_row={i: "error" for i, r in enumerate(rows, start=1) if r[4]})
for i, (_, _, first, emitted, mk) in enumerate(rows, start=1):
    base = Y + i * RH + 28
    fig.text(X + W[0] + W[1] + 8, base, first, "code", color="error" if mk else None)
    if emitted == "<end>":   # the kit measures "<end>" as markup (width 0), so the end token is drawn in words
        fig.text(X + sum(W[:3]) + 8, base, "end of output", "label")
    else:
        fig.text(X + sum(W[:3]) + 8, base, emitted, "code")

YB = Y + 9 * RH + 48
fig.text(X, YB, "output", "label")
fig.text(X + 152, YB, result, "code")
fig.text(X + 560, YB, "parses", "label")
fig.text(X, YB + 32, "max_tokens = 5", "label")
fig.text(X + 152, YB + 32, cut, "code")
fig.text(X + 560, YB + 32, "json.loads fails", "label", color="error")

fig.caption("Every finished output parses; the mask cannot say whether 5 is the right priority.")
fig.write()
