"""Post 20: the companion's regression gate (evalkit) run against post 11's toy RAG pipeline on a twenty-case golden set.

Run from the series root:  uv run python posts/20-evaluation/snippets/eval_gate.py
It imports evalkit from code/20-eval-ragas/src and loads post 11's toy pipeline (ragkit over a four-document
corpus) from posts/11-rag-in-depth/snippets/toy_rag.py, with that script's own print silenced. No model, no network.
The answer is a stand-in for a generator: the text of the top-ranked chunk. The numbers show the mechanism of
the gate, not the size of any effect on a real corpus.
"""
import contextlib
import io
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code" / "20-eval-ragas" / "src"))
from evalkit import DEFAULT_TOLERANCE, Case, check_regression, score_run  # noqa: E402

with contextlib.redirect_stdout(io.StringIO()):
    RAG = runpy.run_path(str(ROOT / "posts" / "11-rag-in-depth" / "snippets" / "toy_rag.py"))
chunks, bm25_bare, bm25_headed = RAG["chunks"], RAG["bm25_bare"], RAG["bm25_headed"]
trigram_ranking, rrf, headed = RAG["trigram_ranking"], RAG["rrf"], RAG["headed"]

ADDED = [  # ten more questions over the same corpus, each with a phrase only its answer-bearing chunks contain
    ("Which items earn only store credit?", "Sale items earn store credit only"),
    ("Do returned items need their original box?", "in their original packaging"),
    ("How fast does a bank transfer refund arrive?", "within three days"),
    ("How long does standard delivery take?", "three to five business days"),
    ("What is the cut-off time for express orders?", "placed before 14:00"),
    ("Is shipping free on a 60 dollar order?", "free on orders over 50 dollars"),
    ("What must an agent do before replacing a lost parcel?", "open a claim with the carrier"),
    ("When should a case go to escalation?", "threatens legal action"),
    ("Who should an escalated case be assigned to?", "not to a named person"),
    ("How long is order history kept after closing an account?", "kept for seven years"),
]
# Each case is labelled by its phrase; the chunk ids are derived from the phrase on every run, so a chunker
# change cannot leave the labels pointing at the wrong passage.
GOLDEN = [Case(f"g{n:02d}", q, phrase, [f"c{i:02d}" for i, c in enumerate(chunks) if phrase in c])
          for n, (q, phrase) in enumerate(RAG["GOLDEN"] + ADDED, start=1)]
assert all(case.relevant_chunk_ids for case in GOLDEN)


def baseline(q):  # post 11's pipeline: BM25 and the trigram ranker over headed chunks, fused by RRF
    lists = [[i for i, _ in bm25_headed.search(q, top_k=len(headed))], trigram_ranking(headed, q)]
    return [i for i, _ in rrf(lists, k=60)]


def headers_dropped(q):  # the same fusion over bare chunks: a refactor that loses the contextual headers
    lists = [[i for i, _ in bm25_bare.search(q, top_k=len(chunks))], trigram_ranking(chunks, q)]
    return [i for i, _ in rrf(lists, k=60)]


def bm25_dropped(q):  # the trigram ranker alone over headed chunks: a change that removes the BM25 half
    return trigram_ranking(headed, q)


def both_dropped(q):  # the trigram ranker alone over bare chunks: a change that loses BM25 and the headers
    return trigram_ranking(chunks, q)


def run(system, k=3):
    """Score one system on the golden set; return the aggregate scores and each case's scores."""
    outputs, per_case = {}, {}
    for case in GOLDEN:
        ranked = system(case.question)
        outputs[case.id] = {"answer": chunks[ranked[0]], "retrieved_ids": [f"c{i:02d}" for i in ranked[:k]]}
        per_case[case.id] = score_run([case], outputs, k=k)
    return score_run(GOLDEN, outputs, k=k), per_case


def flips(per_case, saved_cases, metric):
    """The cases whose score on one metric fell, and those whose score rose, against the baseline."""
    down = [c for c in per_case if per_case[c][metric] < saved_cases[c][metric]]
    up = [c for c in per_case if per_case[c][metric] > saved_cases[c][metric]]
    return f"fell on {' '.join(down) or 'none'}" + (f", rose on {' '.join(up)}" if up else "")


RECALL = "context_recall@3"
print(f"golden set: {len(GOLDEN)} cases ({len(RAG['GOLDEN'])} from post 11, {len(ADDED)} added), {len(chunks)} chunks")
saved, saved_cases = run(baseline)
print(f"{'run':<20}{RECALL:>17}{'answer_match':>14}  gate, tolerance {DEFAULT_TOLERANCE}")
print(f"{'baseline (post 11)':<20}{saved[RECALL]:>17.3f}{saved['answer_match']:>14.3f}  saved")
lost = []
for name, system in [("BM25 dropped", bm25_dropped), ("headers dropped", headers_dropped),
                     ("both dropped", both_dropped)]:
    scores, per_case = run(system)
    gate = check_regression(scores, saved)
    verdict = "pass" if gate.passed else "blocked by " + ", ".join(gate.regressions)
    print(f"{name:<20}{scores[RECALL]:>17.3f}{scores['answer_match']:>14.3f}  {verdict}")
    lost.append(f"{name}: recall {flips(per_case, saved_cases, RECALL)}; "
                f"match {flips(per_case, saved_cases, 'answer_match')}")
print("\n".join(lost))
print(f"one case on {len(GOLDEN)} moves a score by {1 / len(GOLDEN):.3f}")
# A drop of exactly one case sits on the tolerance: a naive comparison lets floating point decide which side,
# while the companion's gate compares the drop with the tolerance plus 1e-9.
edge = [(b / len(GOLDEN), (b - 1) / len(GOLDEN)) for b in range(1, len(GOLDEN) + 1)]
naive = [f"{b:.2f}" for b, c in edge if c < b - DEFAULT_TOLERANCE]
gated = [f"{b:.2f}" for b, c in edge if not check_regression({"m": c}, {"m": b}).passed]
print(f"one-case drops of {len(edge)} blocked by cur < base - {DEFAULT_TOLERANCE}: {', '.join(naive) or 'none'}; "
      f"by check_regression: {', '.join(gated) or 'none'}")
