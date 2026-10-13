"""Post 26, section 7: the window at every model call of one session, with and without compaction.

Run from the series root:  uv run python posts/26-modern-agentic-workflow/diagrams/src/03-session-window.py
Writes posts/26-modern-agentic-workflow/diagrams/03-session-window.svg.
Every plotted value is computed by snippets/session_cost.py (imported; its run() returns the window at each call),
from the illustrative sizes the post states. The numbers drawn are asserted against the snippet and the body.
The run without compaction is red (a wasted budget, ctx_fig_design.md section 0); the compacted run is ink.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
SNIP = runpy.run_path(str(POST / "snippets" / "session_cost.py"), run_name="snippet")
plain, compact = SNIP["run"](), SNIP["run"](SNIP["LIMIT"])
CALLS, LIMIT = SNIP["CALLS"], SNIP["LIMIT"]
calls = list(range(1, CALLS + 1))

assert (CALLS, LIMIT, SNIP["PREFIX"]) == (120, 100_000, 18_000)
assert plain["peak"] == 315_500 and compact["peak"] == 95_500 and compact["compactions"] == 3
after = [w for prev, w in zip(compact["windows"], compact["windows"][1:]) if w < prev]
assert after == [23_000] * 3
for phrase in ("climb from 18,000 to 315,500", "up to 95,500 and back to 23,000, three times",
               "dotted 100,000-token limit", "Three compactions keep every call under 100,000 tokens"):
    assert phrase in BODY, phrase


def fmt(v):
    return f"{v:,.0f}"


fig = Figure(
    "03-session-window", "Without compaction, every call reads more",
    "A line chart of the window in tokens at each of 120 model calls of one illustrative session. Without "
    "compaction, in red, the window climbs in a straight line from 18,000 to 315,500 tokens. With compaction at "
    "100,000 tokens, in ink, it climbs to 95,500, falls back to 23,000 and climbs again, three times. A dotted line "
    "marks the 100,000-token limit. The caption gives the session's input: 20,010,000 tokens without compaction "
    "and 7,254,000 with it. Values computed by snippets/session_cost.py.",
    subtitle="Window at each model call, illustrative sizes. Computed by snippets/session_cost.py.",
    height=540, data_w=True)

body = fig.panel(fig.row(1)[0])
fig.line_chart(
    body,
    [dict(xs=calls, ys=plain["windows"], color="error", label="no compaction", points=False),
     dict(xs=calls, ys=compact["windows"], color="ink", label="compacted", points=False)],
    x=(0, 120, [0, 40, 80, 120]), y=(0, 320_000, [0, 100_000, 200_000, 300_000]),
    x_label="model call", y_label="tokens in the window", fmt_x=fmt, fmt_y=fmt,
    ref_lines=[dict(y=LIMIT, label="limit", at="left")])

assert (plain["tokens_in"], compact["tokens_in"]) == (20_010_000, 7_254_000)
assert "20{,}010{,}000" in BODY and "7,254,000" in BODY
fig.caption(f"Summed over the session: {fmt(plain['tokens_in'])} input tokens without compaction, "
            f"{fmt(compact['tokens_in'])} with it.")
fig.write()
