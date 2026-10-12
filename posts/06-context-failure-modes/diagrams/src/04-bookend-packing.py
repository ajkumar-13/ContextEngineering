"""Post 06, section 5: the same five ranked chunks packed in score order and in the bookend layout.

Run from anywhere:  python posts/06-context-failure-modes/diagrams/src/04-bookend-packing.py
Writes posts/06-context-failure-modes/diagrams/04-bookend-packing.svg.
No measured numbers are drawn: the digits are ranks (1 is the best-scored chunk). The bookend rule is section 5's
first fix (best first, second-best last, the weaker chunks in the middle, the user instruction last), asserted
below; the shaded middle marks where Liu et al. found models used information least reliably, drawn as a region,
not as a curve.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("Place the highest-ranked retrieved chunk first and the second-highest last, with the weaker chunks "
               "in the middle, and keep the user instruction as the very last thing the model reads",
               "dropped significantly when it sat in the middle"):
    assert phrase in BODY, phrase

N = 5
SCORE_ORDER = list(range(1, N + 1))
BOOKEND = [1] + list(range(3, N + 1)) + [2]          # best first, second-best last, the rest between
assert sorted(BOOKEND) == SCORE_ORDER and BOOKEND[0] == 1 and BOOKEND[-1] == 2
MIDDLE = range(1, N - 1)                              # slots 2 to 4 of 5 (0-based 1..3)
for order in (SCORE_ORDER, BOOKEND):
    assert {order[0], order[-1]} == ({1, 5} if order is SCORE_ORDER else {1, 2})

ROWS = [("Score order", SCORE_ORDER), ("Bookend", BOOKEND)]
desc = ("Two strips of five retrieved chunks, labelled by rank from 1 (best) to 5, each followed by the user "
        "instruction, sent left to right, over a shaded band that marks the middle of the input. Score order runs "
        "1, 2, 3, 4, 5, so chunks 2, 3 and 4 sit in the middle. Bookend runs 1, 3, 4, 5, 2, so the two best chunks "
        "hold the start and the end and chunks 3, 4 and 5 fill the middle. The user instruction is last in both.")

fig = Figure("04-bookend-packing", "Bookend packing keeps the two best chunks at the ends", desc,
             subtitle="Five retrieved chunks, ranked 1 (best) to 5, then the user instruction, sent left to right.",
             data_w=True)

LAB_X, X0, CW, CG = 40, 200, 88, 16         # row label, first chunk, chunk width, gap
U_X, U_W = X0 + N * (CW + CG) + 16, 200     # the user instruction box
ROW_TOP = {0: 200, 1: 336}
BOX_H = 64
slot_x = [X0 + i * (CW + CG) for i in range(N)]

# the middle of the input, behind both strips
mid = Box(slot_x[MIDDLE[0]] - 8, 176, slot_x[MIDDLE[-1]] + CW + 8 - (slot_x[MIDDLE[0]] - 8), 248)
fig.fill(mid, "error-soft", radius=8, fit=False)
fig.text(mid.cx, mid.bottom + 24, "middle of the input: used least reliably (Liu et al.)", "note", anchor="middle")

# what each part is, above the first strip
fig.brace(X0, slot_x[-1] + CW, 152, label="04 Retrieved chunks", side="above", kind="bracket", color="turn")
fig.brace(U_X, U_X + U_W, 152, label="06 User instruction", side="above", kind="bracket", color="user")

for r, (name, order) in enumerate(ROWS):
    top = ROW_TOP[r]
    fig.text(LAB_X, top + 38, name, "head")
    for i, rank in enumerate(order):
        b = Box(slot_x[i], top, CW, BOX_H)
        fig.fill(b, "turn-soft", radius=6, fit=False)
        if rank == 2:                                  # the one chunk that moves: the emphasis
            fig.outline(b, "turn", radius=6, width=2.5)
        else:
            fig.outline(b, "turn-line", radius=6)
        fig.text(b.cx, top + 40, str(rank), "cell18", anchor="middle")
    u = Box(U_X, top, U_W, BOX_H)
    fig.fill(u, "user-soft", radius=6, fit=False)
    fig.outline(u, "user-line", radius=6)
    fig.text(u.cx, top + 38, "question", "label", anchor="middle")

fig.caption("Nothing is dropped: the second-best chunk, outlined, moves from the middle to the end.")
fig.write()
