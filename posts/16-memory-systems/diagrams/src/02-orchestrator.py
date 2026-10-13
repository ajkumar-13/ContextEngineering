"""Post 16, section 7: one turn through the three retrieval paths of the orchestrator, merged into a MemoryContext.

Run from anywhere:  python posts/16-memory-systems/diagrams/src/02-orchestrator.py
Writes posts/16-memory-systems/diagrams/02-orchestrator.svg.
Every id, confidence and word count is computed here by snippets/memory_layer.py (loaded with runpy): the second
turn's retrieve(), confidence_on() on 12 October, and words() for the overlap. The result is asserted against the
layer 03 block the body quotes from the snippet's output.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
M = runpy.run_path(str(POST / "snippets" / "memory_layer.py"))
TODAY, conf, words = M["TODAY"], M["confidence_on"], M["words"]
layer = M["MemoryLayer"](TODAY)
for r in M["ROWS"]:
    assert layer.write(r) is None
turn = M["TURNS"][1]
ctx = layer.retrieve(turn)
rows = {r.id: r for r in layer.rows}
assert [r.id for r in ctx.procedural] == ["mem-09"]
assert [r.id for r in ctx.semantic] == ["mem-02", "mem-01", "mem-03"]
assert [r.id for r in ctx.episodic] == ["mem-05"]
assert M["render"](ctx, TODAY) in BODY          # the layer 03 block section 9 quotes is this turn's
assert "The second is the turn of section 7." in BODY
assert M["PAST"].search(turn["text"]).group(0) == "back"

COLD, ASK = M["COLD_BELOW"], M["ASK_BELOW"]
proc = [(r.id, r.trigger, r in ctx.procedural) for r in layer.rows if r.kind == "procedural"]
sem = [(r.id, conf(r, TODAY), r in ctx.semantic) for r in layer.rows if r.kind == "semantic"]
sem.sort(key=lambda p: -p[1])
epi = [(r.id, len(words(turn["text"]) & words(r.content)), conf(r, TODAY), r in ctx.episodic)
       for r in layer.rows if r.kind == "episodic"]
assert [s for _, s, _, _ in epi] == [4, 0, 0] and conf(rows["mem-07"], TODAY) < COLD


def sem_state(c, packed):
    return ("packed, ask" if c < ASK else "packed") if packed else "cold"


desc = (f"The turn \"{turn['text']}\", with intent=escalate, runs through three paths in order. "
        "1 Procedural, trigger match: " + "; ".join(f"{i} {t} {'fires' if f else 'false'}" for i, t, f in proc) + ". "
        "2 Semantic, background ranking: " + "; ".join(f"{i} {c:.2f} {sem_state(c, p)}" for i, c, p in sem) + ". "
        "3 Episodic, reference recall, run because the turn says back: "
        + "; ".join(f"{i} {f'{c:.2f} cold' if c < COLD else f'{s} shared words'}{', recalled' if p else ''}" for i, s, c, p in epi)
        + ". The three lists merge into MemoryContext(procedural=[mem-09], semantic=[mem-02, mem-01, mem-03], "
        "episodic=[mem-05]), which enters 03 Memory and state.")

fig = Figure("02-orchestrator", "One turn, three retrieval paths, one context", desc,
             subtitle="The second turn of snippets/memory_layer.py on 12 October; confidence after decay on read.",
             height=720, data_w=True)

# the turn
tb = Box(40, 104, 880, 56)
fig.fill(tb, "neutral-soft", radius=8, fit=False)
fig.outline(tb, "border", radius=8)
fig.text(56, 138, "Turn 2", "head")
fig.text(136, 138, f"\u201c{turn['text']}\u201d", "label")
fig.text(904, 138, "intent=escalate", "code", anchor="end")

# three paths
CW, CG, CY, CH = 272, 32, 216, 240
cards = []
heads = [("1 Procedural", "trigger match, unranked"), ("2 Semantic", "background, top-3 by confidence"),
         ("3 Episodic", "the turn says \u201cback\u201d: recall runs")]
for i, (h, n) in enumerate(heads):
    x = 40 + i * (CW + CG)
    b = Box(x, CY, CW, CH)
    fig.fill(b, "surface", radius=8, fit=False)
    fig.outline(b, "border", radius=8)
    fig.text(x + 16, CY + 32, h, "head")
    fig.text(x + 16, CY + 56, n, "note")
    cards.append(b)
    fig.arrow((x + CW // 2, tb.bottom + 4), (x + CW // 2, CY - 4))


def item(card, k, ident, value, state, kind):
    y = CY + 100 + 36 * k
    style = {"in": ("label", None), "out": ("note", None), "cold": ("label", "error-ink")}[kind]
    fig.text(card.x + 16, y, ident, "code")
    fig.text(card.x + 96, y, value, style[0], color=style[1])
    if state:
        fig.text(card.right - 16, y, state, style[0], anchor="end", color=style[1])


for k, (i, t, f) in enumerate(sorted(proc, key=lambda p: not p[2])):
    item(cards[0], k, i, t, "fires" if f else "false", "in" if f else "out")
for k, (i, c, p) in enumerate(sem):
    item(cards[1], k, i, f"{c:.2f}", sem_state(c, p), "in" if p else "cold")
for k, (i, s, c, p) in enumerate(sorted(epi, key=lambda e: -e[1])):
    if c < COLD:
        item(cards[2], k, i, f"{c:.2f}", "cold", "cold")
    else:
        item(cards[2], k, i, f"{s} shared words", "recalled" if p else "", "in" if p else "out")

# merge
mb = Box(40, 504, 880, 56)
fig.fill(mb, "turn-soft", radius=8, fit=False)
fig.outline(mb, "turn-line", radius=8)
fig.text(480, 538, "MemoryContext(procedural=[mem-09], semantic=[mem-02, mem-01, mem-03], episodic=[mem-05])",
         "code", anchor="middle")
for b in cards:
    fig.arrow((b.cx, b.bottom + 4), (b.cx, mb.y - 4))
lb = Box(40, 600, 880, 48)
fig.fill(lb, "turn-soft", radius=6, fit=False)
fig.outline(lb, "turn", radius=6, width=2.5)
fig.text(56, 630, "03 Memory and state", "label")
fig.text(904, 630, "the layer 03 block of section 9", "note", anchor="end")
fig.arrow((480, mb.bottom + 4), (480, lb.y - 4))

fig.caption("Rules first, facts second, events last and only when the turn points at the past.")
fig.write()
