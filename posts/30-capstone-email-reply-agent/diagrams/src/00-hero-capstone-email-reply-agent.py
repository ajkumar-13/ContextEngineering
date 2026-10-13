"""Post 30 hero: the email reply agent's pipeline, with what the companion has and what a deployment adds.

Run from the series root:  uv run python posts/30-capstone-email-reply-agent/diagrams/src/00-hero-capstone-email-reply-agent.py
Writes posts/30-capstone-email-reply-agent/diagrams/00-hero-capstone-email-reply-agent.svg.
No numbers are drawn. The components, the four buckets and the order (review, then the gate, then send) are
sections 2, 8 and 9 of index.md, asserted below; what is in the companion is read from its files. Solid
outlines are parts the companion implements; dashed outlines are live steps it does not include. Store cards
carry the role band of the layer they fill (01 stable blue, 03 and 04 turn orange); a blocked draft is red.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Box, Figure  # noqa: E402

POST = Path(__file__).resolve().parents[2]
ROOT = POST.parents[1]
BODY = (POST / "index.md").read_text(encoding="utf-8")
SRC = ROOT / "code" / "30-email-reply-agent" / "src" / "emailbot"
for phrase in ("`GmailMailbox` is a stub", "only a `reply_needed` thread goes to the **drafter**",
               "a person approves, edits or rejects each draft in an approval interface",
               "only an approved draft reaches the send path, where the gate runs again",
               "`run.py` runs the gate as each draft is written"):
    assert phrase in BODY, phrase
assert "raise NotImplementedError" in (SRC / "mailbox" / "gmail.py").read_text(encoding="utf-8")
assert "class FakeMailbox" in (SRC / "mailbox" / "fake.py").read_text(encoding="utf-8")
RUN = (SRC / "run.py").read_text(encoding="utf-8")
assert 'if triage_out["bucket"] != "reply_needed":' in RUN and "decision = send_gate(body, msgs, known_urls=known_urls_from_env())" in RUN
assert "send_email" not in RUN and "messages().send" not in RUN

desc = ("A pipeline. A mailbox, the fake mailbox on disk in the companion or the Gmail driver as a live step, "
        "feeds the triager, which sorts each thread into four buckets with no tools; info_only, promotional and "
        "automated threads get no draft. reply_needed threads go to the drafter, which reads three stores: the "
        "system prompt file for layer 01, the memory store for layer 03 and the prior replies index for layer 04, "
        "and writes a draft. The draft goes to human review, a live step; approved drafts go to the send gate in "
        "code and then to send, a live step; a blocked draft goes back to review with its reason. Solid outlines "
        "are in the companion, dashed outlines are live steps.")
fig = Figure("00-hero-capstone-email-reply-agent", "The agent drafts; a person and a gate decide what is sent",
             desc, subtitle="Only reply_needed threads reach the drafter, and nothing leaves without review and the gate.",
             height=720, data_w=True)


def box(b, heading, lines=(), live=False, band=None, emphasis=False):
    fig.fill(b, "surface" if live else "neutral-soft", radius=8, fit=False)
    if emphasis:
        fig.outline(b, "ink-muted", width=2.5, radius=8)
    else:
        fig.outline(b, "rule" if live else "border", width=1.5 if live else 1, dash="proj" if live else None, radius=8)
    top = b.y
    if band:
        fig.fill(Box(b.x + 8, b.y + 8, b.w - 16, 8), band, radius=4, fit=False)
        top += 8
    fig.text(b.x + 16, top + 32, heading, "head")
    for i, s in enumerate(lines):
        fig.text(b.x + 16, top + 56 + 24 * i, s, "label" if i == 0 else "note")
    return b


# row A: mailbox, triager, drafter, draft
fake = box(Box(40, 128, 152, 88), "Mailbox", ["fake, on disk"])
gmail = box(Box(40, 264, 152, 88), "Gmail driver", ["stub; live step"], live=True)
tri = box(Box(240, 128, 152, 88), "Triager", ["four buckets", "no tools"])
dra = box(Box(504, 128, 176, 88), "Drafter", ["layers 01 to 06", "one request"], emphasis=True)
dft = box(Box(728, 128, 192, 88), "Draft", ["JSON, for review"])
fig.arrow((fake.right + 2, fake.cy), (tri.x - 2, fake.cy))
fig.arrow((gmail.right + 2, gmail.cy), (tri.x - 2, tri.y + 76), dash="proj")
fig.arrow((tri.right + 2, tri.cy), (dra.x - 2, dra.cy), label="reply_needed")
fig.arrow((dra.right + 2, dra.cy), (dft.x - 2, dft.cy))
fig.text(tri.x, tri.bottom + 28, "other three buckets:", "note")
fig.text(tri.x, tri.bottom + 52, "no draft", "note")

# row B: the drafter's stores, each with the role band of the layer it fills
stores = [box(Box(240 + 152 * k, 440, 136, 112), h, lines, band=r) for k, (h, lines, r) in enumerate([
    ("Prompt", ["layer 01", "five blocks"], "stable"),
    ("Memory", ["layer 03", "SQLite tables"], "turn"),
    ("Replies", ["layer 04", "Chroma index"], "turn")])]
for k, s in enumerate(stores):
    fig.arrow((s.cx, s.y - 2), (dra.x + 32 + 56 * k, dra.bottom + 2))

# right column: review, gate, send
rev = box(Box(728, 288, 192, 88), "Human review", ["approve, edit, reject"], live=True)
gate = box(Box(728, 448, 192, 88), "Send gate", ["three checks in code"], emphasis=True)
snd = box(Box(728, 592, 192, 56), "Send", [], live=True)
fig.text(snd.x + 72, snd.y + 32, "Gmail; live step", "note")
fig.arrow((dft.cx, dft.bottom + 2), (rev.cx, rev.y - 2), dash="proj")
fig.arrow((rev.cx, rev.bottom + 2), (gate.cx, gate.y - 2), label="approved", dash="proj")
fig.arrow((gate.x - 2, gate.cy), (rev.x - 2, rev.cy), via=[(696, gate.cy), (696, rev.cy)], color="error")
fig.text(688, (gate.cy + rev.cy) // 2 + 4, "blocked", "note", anchor="end", color="error")
fig.arrow((gate.cx, gate.bottom + 2), (snd.cx, snd.y - 2), label="passes", dash="proj")

fig.legend(40, 608, [dict(color="border", label="in the companion", mark="outline"),
                     dict(color="rule", label="live step", mark="dashed-outline")], direction="row")
fig.caption("The model only writes drafts; review and the gate sit between every draft and the outbox.")
fig.write()
