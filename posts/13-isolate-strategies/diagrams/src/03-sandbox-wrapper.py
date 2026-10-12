"""Post 13, section 6: a sandbox wrapper keeps the install log on disk and passes five fields to the model.

Run from anywhere:  uv run python posts/13-isolate-strategies/diagrams/src/03-sandbox-wrapper.py
Writes posts/13-isolate-strategies/diagrams/03-sandbox-wrapper.svg.
Every number and every log line drawn is produced here by running snippets/sandbox.py (run_sandboxed on its
stand-in install command, tokens counted with o200k_base) and asserted against the output section 6 quotes.
The log card is neutral (a file); the result card carries the history role, as a tool result the loop appends
(the hero of this post uses the same role for tool results).
"""
import json
import runpy
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
SNIP = runpy.run_path(str(POST / "snippets" / "sandbox.py"), run_name="figure")
with tempfile.TemporaryDirectory() as tmp:
    log_path = Path(tmp) / "install.log"
    result = SNIP["run_sandboxed"]([sys.executable, "-c", SNIP["FAKE_INSTALL"]], log_path)
    full = log_path.read_text(encoding="utf-8")
ENC = SNIP["ENC"]
lines = full.splitlines()
returned = json.dumps(result)
N_LINES, N_FULL, N_RET = len(lines), len(ENC.encode(full)), len(ENC.encode(returned))
RATIO = round(N_FULL / N_RET)

BODY = (POST / "index.md").read_text(encoding="utf-8")
assert f"full log: {N_LINES} lines, {N_FULL} tokens (kept in install.log)" in BODY
assert f"returned to the model: {returned}" in BODY
assert f"{N_RET} tokens, {RATIO} times fewer than the full log" in BODY
assert (N_LINES, N_FULL, N_RET, RATIO, len(result)) == (133, 2385, 38, 63, 5)

desc = (f"A child process running a stand-in install command prints a log of {N_LINES} lines and {N_FULL:,} tokens; "
        f"its first four lines and its last line are shown. The whole log goes to install.log on disk. A wrapper "
        f"reads the run and passes five fields to the model's window: ok true, exit_code 0, warnings "
        f"{result['warnings']}, the summary line and the log file name, {N_RET} tokens, {RATIO} times fewer than the "
        f"full log.")
fig = Figure("03-sandbox-wrapper", "The log stays on disk; five fields reach the model", desc,
             subtitle="One sandboxed run of a stand-in install. Lines and tokens (o200k_base) from snippets/sandbox.py.",
             height=540, data_w=True)

# 1. the child process and its output
shown = lines[:4] + [f"... {N_LINES - 5} more lines ...", lines[-1]]
proc = Box(40, 120, 552, 208)
fig.fill(proc, "neutral-soft", radius=8, fit=False)
fig.outline(proc, "border", radius=8)
fig.text(proc.x + 16, proc.y + 32, "Child process: stand-in install", "head")
assert max(map(len, shown)) <= 56
fig.code_block(proc.x + 16, proc.y + 56, shown, size=13, leading=24)

# 2. the log file
logb = Box(656, 120, 264, 96)
fig.fill(logb, "neutral-soft", radius=8, fit=False)
fig.outline(logb, "border", radius=8)
fig.text(logb.x + 16, logb.y + 32, "install.log on disk", "head")
fig.text(logb.x + 16, logb.y + 56, f"{N_LINES} lines, {N_FULL:,} tokens", "label")
fig.text(logb.x + 16, logb.y + 80, "kept for a human to read", "note")
fig.arrow((proc.right + 8, logb.cy), (logb.x - 8, logb.cy))

# 3. the wrapper
wrap = Box(656, 272, 264, 56)
fig.fill(wrap, "neutral-soft", radius=8, fit=False)
fig.outline(wrap, "border", radius=8)
fig.text(wrap.x + 16, wrap.y + 34, "wrapper:", "label")
fig.text(wrap.x + 80, wrap.y + 34, "run_sandboxed", "code")
fig.arrow((logb.cx, logb.bottom + 2), (logb.cx, wrap.y - 2))

# 4. the model's window
res = Box(40, 376, 552, 96)
fig.fill(res, "history-soft", radius=8, fit=False)
fig.outline(res, "history-line", radius=8)
fig.text(res.x + 16, res.y + 32, f"Into the model's window: {N_RET} tokens", "head")
cut = returned.index('"summary"')
json_lines = [returned[:cut].rstrip(), " " + returned[cut:]]
assert "".join(s.strip() + (" " if i == 0 else "") for i, s in enumerate(json_lines)) == returned
fig.code_block(res.x + 16, res.y + 56, json_lines, size=13, leading=24)
fig.arrow((wrap.cx, wrap.bottom + 2), (res.right + 2, res.cy), via=[(wrap.cx, res.cy)])
fig.text(wrap.cx - 12, 364, f"{RATIO} times fewer tokens", "note", anchor="end")

fig.caption("For the model the rest of the output does not exist; for a human it is one file away.")
fig.write()
