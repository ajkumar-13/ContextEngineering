"""Post 30, figure 2 (section 6): the drafter's request for thread t-001, in tokens by layer.

Run from the series root:  uv run python posts/30-capstone-email-reply-agent/diagrams/src/02-drafter-request.py
Writes posts/30-capstone-email-reply-agent/diagrams/02-drafter-request.svg.
Every number is computed here by importing the post's snippet snippets/drafter_request.py, which assembles the
request with the companion's own functions and counts tokens with tiktoken's o200k_base; the counts are asserted
against the values section 6 of index.md quotes. Bars take the role colour of their layer's lifetime class
(01 and 02 stable, 03 and 04 turn, 05 history, 06 user), as ctx_fig_design.md Sections 0 and 5 fix.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
POST = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(POST / "snippets"))
from figkit import Box, Figure  # noqa: E402
import drafter_request as dr  # noqa: E402

BODY = (POST / "index.md").read_text(encoding="utf-8")
ROWS = dr.rows
SYSTEM_TOKENS, USER_TOKENS = dr.n(dr.SYSTEM), dr.n(dr.user)
STATED = {"01 System prompt": 313, "02 Tools and MCP descriptions": 0, "03 Memory and state": 62,
          "04 Retrieved chunks": 144, "05 Conversation history": 72, "06 User instruction": 10}
assert dict(ROWS) == STATED, ROWS
assert (SYSTEM_TOKENS, USER_TOKENS, sum(STATED.values())) == (313, 289, 601)
for name, k in ROWS:
    assert f"  {name:32s}{k:5d}" in BODY, name
assert "(system message 313, user message 289)" in BODY

ROLES = ["stable", "stable", "turn", "turn", "history", "user"]
desc = ("Six horizontal bars, one per layer, of the tokens in the drafter's request for thread t-001 as the "
        "companion assembles it, counted with tiktoken o200k_base: 01 System prompt 313, 02 Tools and MCP "
        "descriptions 0 because the skeleton's drafter has no tools, 03 Memory and state 62, 04 Retrieved chunks "
        "144, 05 Conversation history 72, 06 User instruction 10; 601 in all. A bracket marks 01 as the system "
        "message of 313 tokens and 03 to 06 as one user message of 289 tokens.")
fig = Figure("02-drafter-request", "The drafter reads 601 tokens, not the mailbox", desc,
             subtitle="Thread t-001 as the companion assembles it; tokens counted by the post's snippet with o200k_base.",
             data_w=True)
rows = [(name, [k if j == i else 0 for j in range(6)]) for i, (name, k) in enumerate(ROWS)]
ax = fig.stacked_bars(Box(40, 112, 680, 344), rows, ROLES, 0, 320,
                      [0, 100, 200, 300], label_w=240, value_w=56, axis_label="tokens, o200k_base")
fig.text(ax.sx(0) + 40, ax.sy(1) + 5, "(no tools in the skeleton)", "note")
BX = 744
fig.brace(ax.sy(0) - 12, ax.sy(0) + 12, BX, side="right", kind="bracket", vertical=True)
fig.text(BX + 20, ax.sy(0) - 4, "system message", "note")
fig.text(BX + 20, ax.sy(0) + 16, f"{SYSTEM_TOKENS} tokens", "note")
fig.brace(ax.sy(2) - 12, ax.sy(5) + 12, BX, side="right", vertical=True)
fig.text(BX + 20, (ax.sy(2) + ax.sy(5)) / 2 - 4, "one user message", "note")
fig.text(BX + 20, (ax.sy(2) + ax.sy(5)) / 2 + 16, f"{USER_TOKENS} tokens", "note")
fig.caption("More than half of the request is the system prompt; the reply-specific context is under 300 tokens.")
fig.write()
