"""Post 30, figure 1 (section 12): every part of the email reply agent, the lever it uses, the post that
teaches it, and how much of it the companion has built.

Run from the series root:  uv run python posts/30-capstone-email-reply-agent/diagrams/src/01-every-lever.py
Writes posts/30-capstone-email-reply-agent/diagrams/01-every-lever.svg.
No numbers are drawn except post numbers. Every post named in a row is one index.md links for that part (the
link is asserted), every post exists in posts/, and every "in the companion" cell is checked against the
companion's files below. Layer cells take the role colour of their lifetime class (ctx_fig_design.md Section 0);
operations and disciplines are ink.
"""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, rich, span  # noqa: E402

POST = Path(__file__).resolve().parents[2]
ROOT = POST.parents[1]
BODY = (POST / "index.md").read_text(encoding="utf-8")
C = ROOT / "code" / "30-email-reply-agent"
SRC = C / "src" / "emailbot"
read = lambda p: p.read_text(encoding="utf-8")  # noqa: E731

# part, (lever, role or None), posts, in the companion, check of that cell
ROWS = [
    ("Five-block system prompt", ("01 System prompt", "stable"), [14], "yes",
     "{{USER_NAME}}" in read(C / "prompts" / "drafter_system.md") and '.replace("{{USER_NAME}}"' in read(SRC / "draft.py")),
    ("Gmail tools", ("02 Tools and MCP descriptions", "stable"), [15], "stub",
     "raise NotImplementedError" in read(SRC / "mailbox" / "gmail.py")),
    ("Recipient memory", ("03 Memory and state", "turn"), [8, 16], "yes; rules unread",
     "CREATE TABLE IF NOT EXISTS procedural" in read(SRC / "memory.py") and "FROM procedural" not in read(SRC / "memory.py")),
    ("Prior replies", ("04 Retrieved chunks", "turn"), [9, 11], "yes; word hashes offline",
     "hashlib.sha256(w.encode())" in read(SRC / "replies.py")),
    ("Bookend packing", ("select", None), [9], "yes",
     "ordered = [hits[0]] + hits[2:] + [hits[1]]" in read(SRC / "replies.py")),
    ("Thread compression", ("05 Conversation history", "history"), [12], "no",
     not any(w in read(SRC / "draft.py") for w in ("summar", "compress"))),
    ("Triager", ("isolate", None), [13], "yes",
     "VALID_BUCKETS" in read(SRC / "triage.py") and "max_tokens=200" in read(SRC / "triage.py")),
    ("JSON replies", ("structured output", None), [21], "JSON mode",
     '{"type": "json_object"}' in read(SRC / "draft.py")),
    ("Send gate", ("defences D1, D2", None), [23], "yes; three checks",
     "def send_gate(" in read(SRC / "send_gate.py")),
    ("Email as data", ("trust tag, D3", None), [23], "no",
     "external" not in read(SRC / "draft.py")),
    ("Trace per thread", ("observability", None), [22], "no",
     not any("span" in read(p) or "trace" in read(p) for p in SRC.rglob("*.py"))),
    ("Held-out evaluation", ("evaluation", None), [20], "scaffold",
     "def run(" in read(SRC / "eval.py") and not (C / "data" / "eval_fixtures.json").exists()),
]
SLUG = {p.name[:2]: p.name for p in (ROOT / "posts").iterdir() if p.is_dir()}
for part, _, posts, _, ok in ROWS:
    assert ok, part
    for n in posts:
        assert f"../{SLUG[f'{n:02d}']}/index.md" in BODY, (part, n)

desc = ("A table of twelve parts of the agent with the lever each uses, the posts that teach it and its state in "
        "the companion. Five-block system prompt: 01 System prompt, post 14, yes. Gmail tools: 02 Tools and MCP descriptions, post 15, a stub. Recipient memory: 03 Memory and "
        "state, posts 08 and 16, yes but the rules table is never read. Prior replies: 04 Retrieved chunks, posts "
        "09 and 11, yes, with a hashed bag of words standing in for embeddings offline. Bookend packing: select, post 09, yes. Thread compression: "
        "05 Conversation history, post 12, no. Triager: isolate, post 13, yes. JSON replies: structured output, "
        "post 21, JSON mode. Send gate: defences D1 and D2, post 23, yes with three checks. Email as data: trust "
        "tag and D3, post 23, no. Trace per thread: observability, post 22, no. Held-out evaluation: post 20, a "
        "scaffold.")
fig = Figure("01-every-lever", "Every part of the agent traces to an earlier post", desc,
             subtitle="Each row: what the part uses, where the series teaches it, and what the companion has built.",
             height=720, data_w=True)
table = [["Part of the agent", "Lever", "Posts", "In the companion"]]
for part, (lever, role), posts, state, _ in ROWS:
    table.append([part, rich(span(lever, color=role)) if role else lever,
                  ", ".join(f"{n:02d}" for n in posts), state])
fig.table(40, 112, table, [232, 280, 104, 264], row_h=40, col_align=["start", "start", "start", "start"])
fig.caption("A part whose reason cannot be named is the first candidate for removal.")
fig.write()
