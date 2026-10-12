"""Post 13, hero and section 2: a parent delegates to a worker, and only the validated result comes back.

Run from anywhere:  uv run python posts/13-isolate-strategies/diagrams/src/01-subagent-isolation.py
Writes posts/13-isolate-strategies/diagrams/01-subagent-isolation.svg.
Every number is computed here by running snippets/orchestrator.py (orchestrate() and tokens(), o200k_base) and
asserted against the output that section 2 of index.md quotes. Row colours follow the series roles: a system
prompt is the stable prefix (blue), the triggering message the user instruction (purple), and what a loop appends
(tool calls, tool results, replies) the growing tail (green).
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
SNIP = runpy.run_path(str(POST / "snippets" / "orchestrator.py"), run_name="figure")
parent, worker_window, before, report = SNIP["orchestrate"]()
tok = SNIP["tokens"]
per = lambda m: tok([m])  # noqa: E731
log_lines = sum(len(SNIP["run_tests"](p).splitlines()) for p in SNIP["SUITE"])

W_TOTAL, P_BEFORE, P_AFTER = tok(worker_window), before, tok(parent)
BODY = (POST / "index.md").read_text(encoding="utf-8")
assert f"worker window: {len(worker_window)} messages, {W_TOTAL} tokens (3 test logs, {log_lines} log lines)" in BODY
assert f"parent window: {P_BEFORE} tokens before the call, {P_AFTER} after (+{P_AFTER - P_BEFORE})" in BODY
assert (len(worker_window), W_TOTAL, P_BEFORE, P_AFTER, log_lines) == (9, 1418, 26, 59, 85)

ROLE = {"system": "stable", "user": "user", "assistant": "history", "tool": "history"}
files = [p.split("/")[-1] for p in SNIP["SUITE"]]
w_labels = ["system: test-runner sub-agent", "task: 3 test files"]
for f in files:
    w_labels += [f"call: run_tests({f})", f"tool: log of {f}"]
w_labels.append("reply: passed and failed")
p_labels = ["system: release agent", "user: Can release 2.4 ship?", "tool: validated result"]
assert len(w_labels) == len(worker_window) and len(p_labels) == len(parent)

desc = (f"Two context windows drawn as lists of messages with their token counts. The parent window, on the left, "
        f"holds a system prompt and the user question, {P_BEFORE} tokens before the call. A typed task goes right to "
        f"a worker window, which holds its own system prompt, the task, three run_tests calls and three verbose test "
        f"logs, and a JSON reply: {len(worker_window)} messages and {W_TOTAL} tokens. Only the validated result "
        f"returns to the parent, which grows by {P_AFTER - P_BEFORE} tokens to {P_AFTER}; none of the {log_lines} "
        f"log lines reaches it.")
fig = Figure("01-subagent-isolation", "Only the structured result crosses back to the parent", desc,
             subtitle="One delegated test run. Tokens per message, counted with o200k_base by snippets/orchestrator.py.",
             height=540, data_w=True)

ROW_H, GAP = 32, 4


def window(x, w, top, heading, msgs, labels):
    fig.text(x, top - 12, heading, "head")
    boxes = []
    for i, (m, lab) in enumerate(zip(msgs, labels)):
        b = Box(x, top + i * (ROW_H + GAP), w, ROW_H)
        role = ROLE[m["role"]]
        fig.fill(b, f"{role}-soft", radius=4, fit=False)
        fig.outline(b, f"{role}-line", radius=4)
        fig.text(b.x + 12, b.y + 21, lab, "label")
        fig.text(b.right - 12, b.y + 21, f"{per(m):,}", "value", anchor="end", color=f"{role}-ink")
        boxes.append(b)
    return boxes


wb = window(592, 328, 128, f"Worker window: {W_TOTAL:,} tokens", worker_window, w_labels)
pb = window(40, 296, 128, f"Parent window: {P_BEFORE} + {P_AFTER - P_BEFORE} tokens", parent, p_labels)

# task out (top), result back (bottom)
fig.arrow((pb[1].right + 8, pb[1].cy), (wb[1].x - 8, wb[1].cy), label="typed task (TestTask)")
X_UP = pb[2].right - 24
fig.arrow((wb[-1].x - 8, wb[-1].cy), (X_UP, pb[2].bottom + 2), via=[(X_UP, wb[-1].cy)])
fig.text((X_UP + wb[-1].x) / 2, wb[-1].cy - 12, "validated result only", "note", anchor="middle")

# the two sizes to one scale, under the parent window
SCALE = 200 / W_TOTAL
fig.text(40, 304, "Drawn to one scale", "head")
for i, (lab, n) in enumerate([("worker window", W_TOTAL), ("added to the parent", P_AFTER - P_BEFORE)]):
    y = 336 + i * 64
    fig.text(40, y, lab, "note")
    fig.fill(Box(40, y + 8, max(n * SCALE, 2), 16), "ink-muted", fit=False)
    fig.text(40 + n * SCALE + 8, y + 21, f"{n:,}", "value", color="ink")
fig.legend(384, 248, [dict(color="stable", label="system prompt"), dict(color="user", label="trigger"),
                     dict(color="history", label="appended by the loop")])

fig.caption(f"None of the {log_lines} log lines reaches the parent, which grows by {P_AFTER - P_BEFORE} tokens.")
fig.write()
