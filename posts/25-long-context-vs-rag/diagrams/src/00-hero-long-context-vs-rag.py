"""Post 25, hero (sections 1, 2 and 6): four questions, asked in order, decide between loading and retrieving.

Run from the series root:  uv run python posts/25-long-context-vs-rag/diagrams/src/00-hero-long-context-vs-rag.py
Writes posts/25-long-context-vs-rag/diagrams/00-hero-long-context-vs-rag.svg.

No number is drawn. The four questions and the exit each answer takes are section 2's, in its order; the
phrases are asserted against index.md. Colours follow the series roles: orange (turn) for the retrieval
exits, which fill layer 04 afresh on every call; blue (stable) for the cached load; ink for the router.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")

# question heading, its note, and its exits: (arrow label, outcome, role)
QUESTIONS = [
    ("1. Does it fit, with room to spare?", "corpus, prompt, history and output in one window",
     [("no", "RAG", "turn")]),
    ("2. Is it stable enough to cache?", "the prefix stays identical between calls",
     [("no", "RAG, indexed incrementally", "turn")]),
    ("3. Does each query need most of it?", "a global question, not a local slice",
     [("a slice", "Small slice: RAG", "turn"), ("mix", "A mix: route per query", None)]),
    ("4. Can the model use it at that length?", "on the application's own evaluation",
     [("no", "RAG over a curated subset", "turn")]),
]
FINAL = "Load the corpus once and cache it"

for phrase in ("**Question 1. Does the corpus fit in one window, with room to spare for everything else?**",
               "**Question 2. Is the corpus stable enough to cache?**",
               "**Question 3. Does each query need most of the corpus, or a small slice?**",
               "**Question 4. Can the model actually use the long context for this task?**",
               "RAG absorbs change through incremental indexing", "the answer is a router (section 6)",
               "the answer for one application comes from its own evaluation", "RAG over a curated subset",
               "The figure at the top of the post is the answer in one picture."):
    assert phrase in BODY, phrase

desc = ("A decision chain of four question cards stacked down the left, joined by arrows labelled yes. "
        "1, does the corpus fit one window with room to spare for the prompt, history and output; no leads to "
        "RAG. 2, is it stable enough to cache, the prefix staying identical between calls; no leads to RAG "
        "indexed incrementally. 3, does each query need most of it; a small slice leads to RAG and a mix of "
        "query kinds to a per-query router. 4, can the model use it at that length, judged on the "
        "application's own evaluation; no leads to RAG over a curated subset. Four yes answers lead to loading "
        "the corpus once and caching it. Retrieval exits are drawn in the per-turn colour, the cached load in "
        "the stable-prefix colour, the router in ink.")

fig = Figure("00-hero-long-context-vs-rag", "Four questions decide between loading and retrieving", desc,
             subtitle="Asked in order. An answer that leaves the spine settles the workload, or that kind of query.",
             height=720, data_w=True)

QX, QW, QH = 40, 408, 96        # question cards
OX, OW = 560, 360               # outcome cards
Y0, STEP = 112, 120             # rows; 24 between cards for the yes arrows

for k, (head, note, exits) in enumerate(QUESTIONS):
    y = Y0 + k * STEP
    fig.card(QX, y, QW, QH, heading=head, lines=[note], style="note")
    cx = QX + QW // 2
    fig.arrow((cx, y + QH), (cx, y + STEP))                       # yes, down the spine
    fig.text(cx + 12, y + QH + 16, "yes", "note")
    if len(exits) == 1:
        label, outcome, role = exits[0]
        cy = y + QH // 2
        fig.arrow((QX + QW, cy), (OX, cy), label=label)
        fig.card(OX, y + 20, OW, 56, heading=outcome, color=role)
    else:
        for j, (label, outcome, role) in enumerate(exits):
            top = y + j * 52
            cy = top + 22
            fig.arrow((QX + QW, cy), (OX, cy), label=label)
            fig.card(OX, top, OW, 44, heading=outcome, color=role)

fy = Y0 + 4 * STEP
fig.card(QX, fy, QW, 56, heading=FINAL, color="stable")
fig.legend(OX, fy + 20, [dict(color="turn", label="retrieval fills layer 04 on each call"),
                         dict(color="stable", label="a cached prefix, read on every hit")])

fig.caption("A workload with both whole-corpus and local queries answers question 3 with a router.")
fig.write()
