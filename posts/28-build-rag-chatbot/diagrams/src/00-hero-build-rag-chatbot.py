"""Post 28, hero (sections 1 and 2): the companion's offline lane, online lane and evaluation lane.

Run from the series root:  uv run python posts/28-build-rag-chatbot/diagrams/src/00-hero-build-rag-chatbot.py
Writes posts/28-build-rag-chatbot/diagrams/00-hero-build-rag-chatbot.svg.
Every number is read from the companion code/28-rag-chatbot and asserted: the chunk target and overlap from
ingest.py, top_n and k from retrieve.py's signatures, the RRF constant from rrf_merge, the fixture count from
tests/fixtures.json. The gate's 0.05 is post 20's tolerance as index.md states it; the gate is drawn dashed
because the companion does not have one. Each phrase is asserted against the body.
"""
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
COMP = POST.parents[1] / "code" / "28-rag-chatbot"
BODY = (POST / "index.md").read_text(encoding="utf-8")
ING = (COMP / "src" / "rag" / "ingest.py").read_text(encoding="utf-8")
RET = (COMP / "src" / "rag" / "retrieve.py").read_text(encoding="utf-8")

TARGET = int(re.search(r"^CHUNK_TARGET = (\d+)", ING, re.M).group(1))
OVERLAP = int(re.search(r"^CHUNK_OVERLAP = (\d+)", ING, re.M).group(1))
TOP_N = int(re.search(r"def hybrid\(query: str, \*, top_n: int = (\d+)\)", RET).group(1))
K = int(re.search(r"def rerank\(query: str, candidates: list\[dict\], \*, k: int = (\d+)\)", RET).group(1))
RRF_K = int(re.search(r"def rrf_merge\(rankings: list\[list\[str\]\], \*, k: int = (\d+)\)", RET).group(1))
N_FIX = len(json.loads((COMP / "tests" / "fixtures.json").read_text(encoding="utf-8")))
assert (TARGET, OVERLAP, TOP_N, K, RRF_K, N_FIX) == (500, 80, 50, 5, 60, 3)
for phrase in ("`CHUNK_TARGET = 500` and `CHUNK_OVERLAP = 80` count words",
               "`python -m rag.ingest` splits each file into overlapping chunks",
               "fuses them with RRF, re-ranks the fused list with Cohere's hosted cross-encoder, packs the best five",
               "`tests/fixtures.json` holds three pairs",
               "fail when any metric falls by more than an absolute 0.05 below its baseline",
               "**There is no gate.**", "embedded with Voyage AI", "`gpt-4o-mini` for headers and answers"):
    assert phrase in BODY, phrase

desc = (f"Three lanes of the companion code/28-rag-chatbot. Offline, run by python -m rag.ingest: corpus files "
        f"(.md and .txt), chunk ({TARGET} words, {OVERLAP} overlap), header (one sentence, OpenAI), embed (Voyage AI), "
        f"into a Chroma collection that holds the chunks of layer 04. The collection is searched on every question "
        f"by the online lane, run by answer(): candidates (dense with Voyage AI and BM25, top-{TOP_N} each), fuse "
        f"(RRF, k = {RRF_K}, top-{TOP_N}), re-rank (Cohere, top-{K}), pack (layers 01, 04 and 06 in bookend order, in "
        f"the per-turn colour) and generate (OpenAI, answer and sources). The evaluation lane: {N_FIX} fixtures, "
        f"eval.py replaying them through answer(), Ragas computing four means with an OpenAI judge, and a regression "
        f"gate on an absolute drop of 0.05, drawn dashed because the companion does not have it.")

fig = Figure("00-hero-build-rag-chatbot", "Two lanes build and answer; a third replays them", desc,
             subtitle="Offline runs once per corpus change, online once per question. Dashed: not in the companion.",
             height=720, data_w=True)

COLS = [40 + i * 180 for i in range(5)]        # five columns, 160 wide, 20 apart
CW, CH = 160, 104


def lane(y, cards):
    boxes = []
    for x, (head, lines, color) in zip(COLS, cards):
        fig.card(x, y, CW, CH, heading=head, lines=lines, color=color)
        boxes.append(Box(x, y, CW, CH))
    return boxes


fig.text(40, 128, "Offline: python -m rag.ingest", "head")
off = lane(144, [("Corpus files", ["data/corpus/,", ".md and .txt"], None),
                 ("Chunk", [f"{TARGET} words,", f"{OVERLAP} overlap"], None),
                 ("Header", ["one sentence,", "OpenAI"], None),
                 ("Embed", ["headed chunks,", "Voyage AI"], None),
                 ("Chroma", ["ids, texts,", "vectors"], None)])
fig.fill(Box(COLS[4] + 8, 144, CW - 16, 4), "turn", fit=False)     # the store holds layer 04's content
fig.chain(off)

fig.text(40, 336, "Online: answer()", "head")
on = lane(352, [("Candidates", ["dense + BM25,", f"top-{TOP_N} each"], None),
                ("Fuse", [f"RRF, k = {RRF_K},", f"top-{TOP_N}"], None),
                ("Re-rank", [f"top-{K},", "Cohere"], None),
                ("Pack", ["01, 04, 06,", "bookend order"], "turn"),
                ("Generate", ["answer, sources,", "OpenAI"], None)])
fig.chain(on)

# the collection is searched on every question
store, cand = off[4], on[0]
fig.arrow((store.cx, store.bottom), (cand.right - 24, cand.y), via=((store.cx, 296), (cand.right - 24, 296)))
fig.text(cand.right - 8, 288, "searched on every question (dense embedding: Voyage AI)", "note")

fig.text(40, 512, "Evaluation: python -m rag.eval", "head")
ev = lane(528, [("Fixtures", [f"{N_FIX} questions", "with answers"], None),
                ("eval.py", ["each question", "through answer()"], None),
                ("Ragas", ["four means,", "OpenAI judge"], None)])
fig.chain(ev)
gate = Box(COLS[3], 528, CW, CH)
fig.outline(gate, "ink-muted", width=1.5, dash="proj", radius=8)
fig.text(gate.x + 16, gate.y + 32, "Gate", "head")
fig.text(gate.x + 16, gate.y + 64, "fail on a drop", "label")
fig.text(gate.x + 16, gate.y + 88, "over 0.05", "label")
fig.arrow((ev[2].right, ev[2].cy), (gate.x, gate.cy), dash="proj")
fig.text(COLS[4], 560, "post 20's gate,", "note")
fig.text(COLS[4], 580, "not yet in the", "note")
fig.text(COLS[4], 600, "companion", "note")

fig.caption("The index is written once per change; every question, live or replayed, runs the online lane.")
fig.write()
