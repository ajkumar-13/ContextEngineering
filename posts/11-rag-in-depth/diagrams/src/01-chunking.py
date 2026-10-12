"""Post 11, section 2: one section of the toy corpus split two ways, fixed-length and sentence-aware with overlap.

Run from the series root:  uv run python posts/11-rag-in-depth/diagrams/src/01-chunking.py
Writes posts/11-rag-in-depth/diagrams/01-chunking.svg.
Every count is computed here: the section text is the snippet's CORPUS["refunds-policy.md"]["Approval limits"], the
sentences come from the companion's split_sentences, the two chunks from its chunk(target_tokens=30,
overlap_tokens=8) exactly as snippets/toy_rag.py calls it, and the fixed-length split is every 30 words. Widths are
proportional to words (the companion approximates tokens by words). The counts the body states are asserted.
"""
import contextlib
import io
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(str(POST / "snippets" / "toy_rag.py"), run_name="snippet")
from ragkit import split_sentences  # noqa: E402  (the snippet put the companion on sys.path)

TEXT = ns["CORPUS"]["refunds-policy.md"]["Approval limits"]
SENTS = split_sentences(TEXT)
SW = [len(s.split()) for s in SENTS]                       # words per sentence
WORDS = TEXT.split()
assert " ".join(SENTS) == TEXT and sum(SW) == len(WORDS)  # the splitter kept every word of this section
CHUNKS = ns["chunk"](TEXT, target_tokens=30, overlap_tokens=8)
FIXED = 30
PIECES = [WORDS[:FIXED], WORDS[FIXED:]]

# chunk spans in words (first word index, end index), from each chunk's start sentence and length
start = [sum(SW[:i]) for i in range(len(SW))]
spans = [(start[c.start_sentence], start[c.start_sentence] + c.n_tokens) for c in CHUNKS]
assert SW == [11, 10, 11, 6] and len(WORDS) == 38
assert [c.n_tokens for c in CHUNKS] == [21, 27] and spans == [(0, 21), (11, 38)]
overlap = (spans[1][0], spans[0][1])                       # sentence 2, words 11 to 21
assert overlap == (start[1], start[2])
cut_sentence = next(i for i in range(len(SW)) if start[i] < FIXED < start[i] + SW[i])
assert cut_sentence == 2 and WORDS[FIXED - 1] == "8:00" and WORDS[FIXED] == "to"

BODY = (POST / "index.md").read_text(encoding="utf-8")
for phrase in ("one 38-word section of the toy corpus", 'A fixed 30-word split cuts "8:00 to 18:00" in two',
               "with a 30-word target and 8 words of overlap, keeps every sentence whole and repeats the second "
               "sentence in both chunks"):
    assert phrase in BODY, phrase

desc = ("One 38-word section of the post's toy corpus, drawn to scale at one width per word, split two ways. Top, its "
        "four sentences of 11, 10, 11 and 6 words. Middle, a fixed-length split every 30 words: a piece of 30 words "
        "and one of 8, with the cut, marked in red, inside sentence 3 between 8:00 and to 18:00. Bottom, the "
        "companion's sentence-aware chunker with a 30-word target and 8 words of overlap: chunk 1 holds sentences 1 "
        "and 2, 21 words, and chunk 2 holds sentences 2 to 4, 27 words; sentence 2, 10 words, is in both.")

fig = Figure("01-chunking", "A fixed-length split cuts a fact; whole sentences keep it", desc,
             subtitle='The "Approval limits" section of the toy corpus, drawn one unit of width per word.', data_w=True)

X0, PX, H = 232, 18, 48
xw = lambda w: X0 + w * PX  # noqa: E731


def seg(w0, w1, y, label, color="ink-muted", fill="neutral-soft", width=1, dash=None):
    b = Box(xw(w0), y, (w1 - w0) * PX, H)
    fig.fill(b, fill, radius=4, fit=False)
    fig.outline(b, color, radius=4, width=width, dash=dash)
    fig.text(b.x + 12, y + 30, label, "label")
    return b


ROW = {"sent": 112, "fixed": 208, "c1": 312, "c2": 372}
LABEL = {"sent": "Sentences", "fixed": "Fixed, 30 words", "c1": "Sentence-aware,", "c2": ""}

# the sentence boundaries, carried down through every row as faint guides
for w in start[1:]:
    fig.edge((xw(w), ROW["sent"] + H), (xw(w), ROW["c2"] + H + 8), color="border", dash="lead")

# the overlap of the two chunks: one band behind both chunk rows
ob = Box(xw(overlap[0]) - 8, ROW["c1"] - 12, (overlap[1] - overlap[0]) * PX + 16, ROW["c2"] + H + 12 - (ROW["c1"] - 12))
fig.fill(ob, "neutral-soft", radius=8, fit=False)
fig.outline(ob, "ink-muted", radius=8, dash="lead")

fig.text(40, ROW["sent"] + 30, "Sentences (words)", "head")
for i, w in enumerate(SW):
    seg(start[i], start[i] + w, ROW["sent"], f"{i + 1} ({w})")

fig.text(40, ROW["fixed"] + 30, LABEL["fixed"], "head")
seg(0, FIXED, ROW["fixed"], f"piece 1, {len(PIECES[0])} words")
seg(FIXED, len(WORDS), ROW["fixed"], f"piece 2, {len(PIECES[1])}")
fig.edge((xw(FIXED), ROW["fixed"] - 8), (xw(FIXED), ROW["fixed"] + H + 8), color="error", width=2.5)
fig.text(xw(FIXED) - 8, ROW["fixed"] + H + 28, f"cut: \u2026from {WORDS[FIXED - 1]} | {WORDS[FIXED]} "
         f"{WORDS[FIXED + 1]}", "label", anchor="end", color="error-ink")

fig.text(40, ROW["c1"] + 30, "Sentence-aware", "head")
fig.text(40, ROW["c1"] + 56, "target 30,", "note")
fig.text(40, ROW["c1"] + 76, "overlap 8", "note")
seg(spans[0][0], spans[0][1], ROW["c1"], f"chunk 1: sentences 1 to 2, {CHUNKS[0].n_tokens} words", fill="surface")
seg(spans[1][0], spans[1][1], ROW["c2"], f"chunk 2: sentences 2 to 4, {CHUNKS[1].n_tokens} words", fill="surface")
fig.text(ob.cx, ROW["c2"] + H + 40, f"overlap: sentence 2, {SW[1]} words", "note", anchor="middle")

fig.caption("The sentence-aware chunks cut no sentence, and the boundary sentence is in both of them.")
fig.write()
