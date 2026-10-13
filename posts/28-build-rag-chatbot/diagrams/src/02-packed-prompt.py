"""Post 28, section 5: the two messages pack() builds, with the layer each part fills and the bookend order.

Run from the series root:  uv run python posts/28-build-rag-chatbot/diagrams/src/02-packed-prompt.py
Writes posts/28-build-rag-chatbot/diagrams/02-packed-prompt.svg.
The packed order, the message roles, the system prompt's blocks and its token count are read from what the post's
snippet (snippets/offline_core.py, which runs the companion's own pack) prints, and asserted. The ranks are
ranks, not measurements. The question is the one the snippet packs.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
ROOT = POST.parents[1]
BODY = (POST / "index.md").read_text(encoding="utf-8")
OUT = subprocess.run([sys.executable, str(POST / "snippets" / "offline_core.py")], cwd=ROOT, capture_output=True,
                     text=True, encoding="utf-8", check=True).stdout

ORDER = [int(x) for x in re.search(r"five hits in rank order 1 to 5 are packed as: ([\d, ]+)", OUT).group(1).split(", ")]
ROLES = re.search(r"messages: \[(.*)\]", OUT).group(1).replace("'", "").split(", ")
m = re.search(r"system prompt blocks: \[(.*)\]; (\d+) tokens", OUT)
BLOCKS, SYS_TOKENS = m.group(1).replace("'", "").split(", "), int(m.group(2))
QUESTION = re.search(r"^\s+(Question: .+)$", OUT, re.M).group(1)
assert ORDER == [1, 3, 4, 5, 2] and ROLES == ["system", "user"]
assert BLOCKS == ["Identity", "Rules", "Format", "Knowledge"] and SYS_TOKENS == 187
assert QUESTION == "Question: How long is a workspace invite valid?"
for phrase in ("Five hits ranked 1 to 5 are packed as 1, 3, 4, 5, 2", "The snippet counts the file at 187 tokens",
               "Layers 02, 03 and 05 are empty: no tools, no memory, no history",
               "The system message is layer 01, the system prompt",
               "the sources as layer 04, retrieved chunks", "the `Question:` line as layer 06, the user instruction"):
    assert phrase in BODY, phrase

desc = ("The two messages the companion's pack() builds, sent top to bottom. The system message is layer 01, the "
        f"system prompt: prompts/system.md with the blocks {', '.join(BLOCKS)}, {SYS_TOKENS} tokens. The user "
        "message holds the label Sources, then five retrieved chunks in the order "
        f"{', '.join(map(str, ORDER))}, layer 04, each opening with its bracketed title tag and the stored "
        "document and summary lines, and last the line Question: How long is a workspace invite valid?, layer 06. "
        "Chunk 2, outlined, has moved from second place to the end of the sources. Layers 02, 03 and 05 are empty "
        "in the starter: no tools, no memory, no history.")

fig = Figure("02-packed-prompt", "Two messages, three layers, the best chunks at the ends", desc,
             subtitle="The messages pack() builds for five re-ranked chunks; ranks run from 1, the best, to 5.",
             height=720, data_w=True)

SX, SW = 232, 464                      # the stack
LX = 40                                # layer labels
RX = SX + SW + 40                      # message brackets and notes

# layer 01: the system message
sys_box = Box(SX, 112, SW, 104)
fig.fill(sys_box, "stable-soft", radius=8, fit=False)
fig.outline(sys_box, "stable-line", radius=8)
fig.text(SX + 16, 144, "prompts/system.md", "code")
fig.text(SX + 16, 172, ", ".join(BLOCKS), "label")
fig.text(SX + 16, 200, f"{SYS_TOKENS} tokens", "label")
fig.text(LX, 160, "01 System", "head", color="stable-ink")
fig.text(LX, 184, "prompt", "head", color="stable-ink")

# the user message: sources (layer 04) then the question (layer 06)
user_box = Box(SX - 16, 240, SW + 32, 400)
fig.outline(user_box, "ink-muted", width=1, radius=8)
fig.text(SX, 272, "Sources:", "code")
CH, CG, CY = 44, 12, 288
for i, rank in enumerate(ORDER):
    b = Box(SX, CY + i * (CH + CG), SW, CH)
    fig.fill(b, "turn-soft", radius=6, fit=False)
    fig.outline(b, "turn" if rank == 2 else "turn-line", radius=6, width=2.5 if rank == 2 else 1)
    fig.text(b.x + 16, b.y + 28, str(rank), "cell18")
    fig.text(b.x + 56, b.y + 28, "[title] [Document: title] [Summary: ...]", "code")
    if rank == 2:
        last_chunk = b
chunks_top, chunks_bottom = CY, CY + 5 * CH + 4 * CG
fig.brace(chunks_top, chunks_bottom, SX - 32, label=None, side="left", kind="bracket", vertical=True, color="turn")
fig.text(LX, 412, "04 Retrieved", "head", color="turn-ink")
fig.text(LX, 436, "chunks", "head", color="turn-ink")

q_box = Box(SX, 572, SW, 48)
fig.fill(q_box, "user-soft", radius=6, fit=False)
fig.outline(q_box, "user-line", radius=6)
fig.text(SX + 16, 602, QUESTION, "code")
fig.text(LX, 592, "06 User", "head", color="user-ink")
fig.text(LX, 616, "instruction", "head", color="user-ink")

# message roles on the right
fig.brace(sys_box.y, sys_box.bottom, RX, label=None, side="right", kind="bracket", vertical=True)
fig.text(RX + 24, 168, f'role "{ROLES[0]}"', "label")
fig.brace(user_box.y, user_box.bottom, RX, label=None, side="right", kind="bracket", vertical=True)
fig.text(RX + 24, 440, f'role "{ROLES[1]}"', "label")
fig.text(RX + 24, 528, "rank 2 moved", "note")
fig.text(RX + 24, 548, "to the end", "note")
fig.text(RX + 24, 296, "02, 03, 05 empty:", "note")
fig.text(RX + 24, 316, "no tools, memory", "note")
fig.text(RX + 24, 336, "or history", "note")
assert last_chunk.y + 16 <= 528 <= last_chunk.bottom + 8

fig.caption("The stable system prompt leads; the second-best chunk closes the sources; the question comes last.")
fig.write()
