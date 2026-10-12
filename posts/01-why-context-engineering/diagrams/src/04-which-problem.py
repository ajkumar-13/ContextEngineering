"""Post 01, section 5: two questions sort a failing LLM feature into a prompt, context or model problem.

Run from anywhere:  python posts/01-why-context-engineering/diagrams/src/04-which-problem.py
Writes posts/01-why-context-engineering/diagrams/04-which-problem.svg.
No numbers are drawn. The two questions and the three outcomes with their fixes are section 5 of index.md,
asserted below; the order of the questions is the one section 5 gives.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")
for phrase in ("**It might be a prompt problem.**", "rewording the instruction fixes the answer",
               "**It might be a model problem.**", "The fix is a stronger model, not more context.",
               "in the wrong place, or in the wrong amount. Those are context problems",
               "the order of the two questions matters"):
    assert phrase in BODY, phrase

fig = Figure(
    "04-which-problem", "Check the window first, then the wording, then the model",
    "A decision chart of two questions and three outcomes. The first question asks whether the right information "
    "is in the window, in a sensible place and in the right amount. No leads down to a context problem: change "
    "what the window holds, the subject of this series. Yes leads right to the second question, whether rewording "
    "the instruction fixes the answer. Yes leads down to a prompt problem: reword the instruction. No leads right "
    "to a model problem: use a stronger model.",
    subtitle="The two questions of section 5, asked in this order, sort a failing LLM feature into one of three problems.",
    data_w=True)

q1 = Box(40, 152, 288, 136)
q2 = Box(424, 152, 248, 136)
model = Box(744, 152, 176, 136)
ctx = Box(40, 344, 288, 112)
prompt = Box(424, 344, 248, 112)

fig.card(q1.x, q1.y, q1.w, q1.h, heading="Question 1",
         lines=["Is the right information in the", "window, in a sensible place", "and in the right amount?"])
fig.card(q2.x, q2.y, q2.w, q2.h, heading="Question 2",
         lines=["Does rewording the", "instruction fix the answer?"])
fig.card(ctx.x, ctx.y, ctx.w, ctx.h, heading="Context problem", style="note",
         lines=["Change what the window holds.", "The subject of this series."])
fig.card(prompt.x, prompt.y, prompt.w, prompt.h, heading="Prompt problem", style="note",
         lines=["Reword the instruction."])
fig.card(model.x, model.y, model.w, model.h, heading="Model problem", style="note",
         lines=["Use a stronger model."])

fig.arrow((q1.right + 8, q1.cy), (q2.x - 8, q2.cy), label="yes")
fig.arrow((q1.cx, q1.bottom + 8), (q1.cx, ctx.y - 8), label="no")
fig.arrow((q2.right + 8, q2.cy), (model.x - 8, model.cy), label="no")
fig.arrow((q2.cx, q2.bottom + 8), (q2.cx, prompt.y - 8), label="yes")

fig.caption("Question 1 needs the request the application actually sent, not a guess about what it held.")
fig.write()
