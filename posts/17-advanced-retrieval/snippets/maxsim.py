"""Post 17: a late-interaction (MaxSim) score against a single-vector score, on toy token vectors.

Run from the series root:  uv run python posts/17-advanced-retrieval/snippets/maxsim.py
Standard library only; no network, no model, no API key.

The vectors are hand-written, not learned: six dimensions stand for "repair", "failure", "billing",
"data export", the identifier E-4012, and "function word". Every token vector is scaled to length 1,
so a dot product is a cosine similarity. A single-vector (bi-encoder) retriever pools each text into
one vector, here the mean of its token vectors, and scores the cosine of the two pooled vectors.
Late interaction (ColBERT's MaxSim) keeps every token vector and scores
    s(q, d) = sum over query tokens i of  max over document tokens j of  q_i . d_j.
The numbers show the mechanism on six words; they say nothing about effect sizes on a real corpus.
"""
import math

TOKENS = {  # repair, failure, billing, export, E-4012, function word
    "fix":      (1.0, 0.3, 0.0, 0.0, 0.0, 0.2),
    "error":    (0.2, 1.0, 0.0, 0.0, 0.0, 0.2),
    "E-4012":   (0.0, 0.3, 0.0, 0.0, 1.0, 0.0),
    "invoice":  (0.0, 0.0, 1.0, 0.3, 0.0, 0.2),
    "export":   (0.0, 0.0, 0.3, 1.0, 0.0, 0.2),
    "stops":    (0.1, 0.7, 0.0, 0.0, 0.0, 0.3),
    "with":     (0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
    "when":     (0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
    "currency": (0.0, 0.0, 1.0, 0.2, 0.0, 0.2),
    "missing":  (0.0, 0.6, 0.0, 0.2, 0.0, 0.4),
    "how":      (0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
    "to":       (0.0, 0.0, 0.0, 0.0, 0.0, 1.0),
    "common":   (0.0, 0.1, 0.0, 0.0, 0.0, 1.0),
    "messages": (0.0, 0.3, 0.0, 0.2, 0.0, 0.6),
}

QUERY = ["fix", "error", "E-4012"]
CHUNKS = {
    "A (holds the answer)": ["invoice", "export", "stops", "with", "E-4012", "when", "currency", "missing"],
    "B (generic page)": ["how", "to", "fix", "common", "error", "messages"],
}


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


VEC = {t: unit(v) for t, v in TOKENS.items()}


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def pooled(tokens):
    """One vector per text: the mean of its token vectors, scaled to length 1."""
    return unit([sum(VEC[t][i] for t in tokens) / len(tokens) for i in range(6)])


def single_vector_score(query, doc):
    return dot(pooled(query), pooled(doc))


def maxsim(query, doc):
    """Late interaction: each query token keeps its best match anywhere in the document; the maxima add up."""
    return sum(max(dot(VEC[q], VEC[d]) for d in doc) for q in query)


def similarity_grid(query, doc):
    return [[dot(VEC[q], VEC[d]) for d in doc] for q in query]


if __name__ == "__main__":
    print("query:", " ".join(QUERY))
    for name, doc in CHUNKS.items():
        print(f"\nchunk {name}: {' '.join(doc)}")
        grid = similarity_grid(QUERY, doc)
        for q, row in zip(QUERY, grid):
            best = max(range(len(doc)), key=lambda j: row[j])
            print(f"  {q:<7} " + " ".join(f"{s:4.2f}" for s in row) + f"   max {row[best]:.2f} ({doc[best]})")
    print("\nscore            single vector   MaxSim")
    for name, doc in CHUNKS.items():
        print(f"{name[:1]:<16} {single_vector_score(QUERY, doc):13.2f} {maxsim(QUERY, doc):8.2f}")
    sv = {n[:1]: single_vector_score(QUERY, d) for n, d in CHUNKS.items()}
    ms = {n[:1]: maxsim(QUERY, d) for n, d in CHUNKS.items()}
    print(f"single vector ranks {max(sv, key=sv.get)} first; MaxSim ranks {max(ms, key=ms.get)} first")
    a, b = CHUNKS["A (holds the answer)"], CHUNKS["B (generic page)"]
    print(f"vectors stored: single vector 1 per chunk; late interaction {len(a)} for A and {len(b)} for B")
