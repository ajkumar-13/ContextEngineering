"""Post 17: a two-hop question that single-hop retrieval misses, answered by a graph built from the corpus.

Run from the series root:  uv run python posts/17-advanced-retrieval/snippets/two_hop.py
Standard library only; no network, no model, no API key.

The corpus is eight one-sentence documents about a made-up supply chain. The question needs two facts
that no single document holds together: which vendors failed the 2024 audit (one document), and who buys
from those vendors (two other documents, which never mention the audit). Three strategies run:
  - single hop: BM25 over the question, top-3 packed;
  - two-step: retrieve, read the vendor names out of the top document, retrieve again with them (the
    decomposition pattern of post 09);
  - graph: relations are extracted offline into edges "supplier -> buyer" (a regular expression stands in
    for the model call that extracts entities and relations), the failed vendors are read off the audit
    document, and the graph is walked one hop downstream; the documents behind the edges walked are packed.
A second part measures how fast a traversal grows with its hop depth on a synthetic graph in which every
entity has four neighbours. All sizes are toy sizes; the numbers show the mechanism, not real effect sizes.
"""
import math
import random
import re
from collections import Counter

CORPUS = {
    "d1": "The 2024 supplier audit failed two vendors: Acme Metals and Borealis Plastics.",
    "d2": "Foxglove Textiles passed the 2024 supplier audit with no findings.",
    "d3": "Corvid Tools buys steel castings from Acme Metals.",
    "d4": "Delta Assembly buys resin pellets from Borealis Plastics.",
    "d5": "Echo Motors passed its 2024 safety inspection.",
    "d6": "Acme Metals opened a second foundry in 2023.",
    "d7": "Our supplier scorecard is reviewed by procurement every quarter.",
    "d8": "Gamma Freight carries pallets for Delta Assembly.",
}
QUESTION = "Which suppliers are downstream of vendors that failed our 2024 audit?"
GOLD = {"d3", "d4"}          # the documents that name the buyers of the failed vendors
TOP_K = 3
STOP = {"the", "a", "of", "that", "our", "which", "are", "is", "by", "with", "no", "and", "for", "from", "every"}


def words(text):
    """Lower-cased words without stop words, with a plural s stripped (suppliers and supplier match)."""
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w not in STOP:
            out.append(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w)
    return out


class BM25:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.ids = list(docs)
        self.tok = {d: words(t) for d, t in docs.items()}
        self.avg = sum(len(t) for t in self.tok.values()) / len(self.tok)
        df = Counter(w for t in self.tok.values() for w in set(t))
        n = len(docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self.k1, self.b = k1, b

    def rank(self, query):
        q = words(query)
        scores = {}
        for d in self.ids:
            tf = Counter(self.tok[d])
            norm = self.k1 * (1 - self.b + self.b * len(self.tok[d]) / self.avg)
            scores[d] = sum(self.idf.get(w, 0) * tf[w] * (self.k1 + 1) / (tf[w] + norm) for w in q if tf[w])
        return sorted((d for d in self.ids if scores[d] > 0), key=lambda d: (-scores[d], d))


ENTITY = r"([A-Z][a-z]+ [A-Z][a-z]+)"
BUYS = re.compile(ENTITY + r" buys [a-z ]+ from " + ENTITY)
FAILED = re.compile(r"failed \w+ vendors: " + ENTITY + " and " + ENTITY)


def extract_edges(docs):
    """Offline: one edge supplier -> buyer per 'X buys ... from Y' sentence, with the document it came from."""
    return [(m.group(2), m.group(1), d) for d, t in docs.items() for m in [BUYS.search(t)] if m]


def recall(packed):
    return len(GOLD & set(packed)) / len(GOLD)


def grow(n_nodes=2000, degree=4, seed=17, hops=4):
    """Entities reached within h hops of one entity, on a graph where every entity links to `degree` others."""
    rng = random.Random(seed)
    nbrs = {v: rng.sample([u for u in range(n_nodes) if u != v], degree) for v in range(n_nodes)}
    seen, frontier, sizes = {0}, {0}, []
    for _ in range(hops):
        frontier = {u for v in frontier for u in nbrs[v]} - seen
        seen |= frontier
        sizes.append(len(seen) - 1)
    return sizes


if __name__ == "__main__":
    bm25 = BM25(CORPUS)
    print("question:", QUESTION)
    print(f"gold documents: {', '.join(sorted(GOLD))}; packed top-k = {TOP_K}\n")

    single = bm25.rank(QUESTION)[:TOP_K]
    print(f"single hop   packed {', '.join(single)}   recall {recall(single):.2f}")

    first = bm25.rank(QUESTION)[0]
    vendors = FAILED.search(CORPUS[first]).groups()
    second = bm25.rank(" ".join(vendors))
    second = [d for d in second if d != first][:TOP_K - 1]
    two_step = [first] + second
    print(f"two-step     packed {', '.join(two_step)}   recall {recall(two_step):.2f}"
          f"   (second query: {' '.join(vendors)})")

    edges = extract_edges(CORPUS)
    failed = FAILED.search(CORPUS["d1"]).groups()
    walked = [(s, b, d) for s, b, d in edges if s in failed]
    graph = ["d1"] + [d for _, _, d in walked]
    print(f"graph        packed {', '.join(graph)}   recall {recall(graph):.2f}")
    print(f"  {len(edges)} edges extracted offline; walked: "
          + "; ".join(f"{s} -> {b} ({d})" for s, b, d in walked))
    print(f"  answer: {', '.join(b for _, b, _ in walked)}")

    print("\nhop depth on a 2,000-entity graph, 4 links per entity")
    for h, n in enumerate(grow(), start=1):
        print(f"  within {h} hop{'s' if h > 1 else ' '}  {n:5d} entities")
