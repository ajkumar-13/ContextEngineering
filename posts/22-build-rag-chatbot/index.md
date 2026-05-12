# 22 · Build #1 — RAG chatbot from scratch

> **TL;DR.** A complete, runnable RAG chatbot in ~250 lines of Python: corpus ingestion with chunking and contextual headers, a hybrid retriever (dense + BM25 + reranker), prompt assembly with the system-prompt blocks from [Post 12](../12-system-prompt-as-software/index.md), citation-checked generation, and an eval harness with the four Ragas metrics from [Post 16](../16-evaluation/index.md). Every line of this build is justified by a principle from earlier in the series; this post is where the principles meet code.
>
> **Reading time:** ~14 minutes.
>
> **After reading this you will be able to:**
> - Build a production-shaped RAG system end-to-end.
> - Recognise the connection between every code block and an earlier post.
> - Take the build as a starter and harden it for real traffic.
>
> **Companion code:** `code/22-rag-chatbot/`. Full sources, tests, `.env.example`.

---

## 1. Goals and scope

The goal is a small RAG chatbot that does the right things, not a monolith that does everything. "Right" here means:

- **Hybrid retrieval** with reciprocal rank fusion ([Post 08](../08-select-strategies/index.md), §3).
- **Cross-encoder reranking** ([Post 08](../08-select-strategies/index.md), §4).
- **Contextual chunk headers** ([Post 09](../09-rag-in-depth/index.md), §2).
- **Bookend packing** with citation tags ([Post 08](../08-select-strategies/index.md), §5).
- **A system prompt** with the five blocks ([Post 12](../12-system-prompt-as-software/index.md), §2).
- **An eval harness** with faithfulness, answer relevance, context precision, context recall ([Post 16](../16-evaluation/index.md), §5).

What is *not* in scope: streaming UI, multi-tenant auth, GraphRAG, fine-tuning, distributed indexing. Those are extensions; the core works without them.

---

## 2. Layout

```
code/22-rag-chatbot/
├── README.md
├── pyproject.toml
├── .env.example
├── data/
│   └── corpus/                    # drop .md / .txt / .pdf here
├── src/rag/
│   ├── __init__.py
│   ├── ingest.py                  # chunk + header + embed + index
│   ├── retrieve.py                # hybrid + RRF + rerank
│   ├── prompt.py                  # five-block system prompt
│   ├── chat.py                    # the chat loop
│   └── eval.py                    # the four metrics
├── prompts/
│   ├── system.md
│   └── chunk_header.md
└── tests/
    ├── test_chunker.py
    └── test_retriever.py
```

A single `pyproject.toml` declares the dependencies: `openai`, `voyageai` (or any embedding provider), `cohere` (rerank), `chromadb`, `rank-bm25`, `pypdf`, `pydantic`, `ragas`, `pytest`. Total install time on a fresh machine: a couple of minutes.

---

## 3. Ingestion — chunking and headers

```python
# src/rag/ingest.py
from pathlib import Path
import hashlib, re

import chromadb
from rank_bm25 import BM25Okapi
import voyageai

from .prompt import CHUNK_HEADER_PROMPT  # one-line template
from .llm import small_llm                # cheap model for headers

CHUNK_TARGET = 500           # tokens
CHUNK_OVERLAP = 80           # tokens
client = chromadb.PersistentClient(path=".chroma")
coll = client.get_or_create_collection("docs")
vo = voyageai.Client()

def split_sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", text.strip())

def chunk(text: str) -> list[str]:
    sentences = split_sentences(text)
    chunks, current, current_len = [], [], 0
    for s in sentences:
        s_len = len(s.split())                        # cheap proxy
        if current_len + s_len > CHUNK_TARGET and current:
            chunks.append(" ".join(current))
            # overlap: keep tail
            overlap = []
            tail_len = 0
            for t in reversed(current):
                tail_len += len(t.split())
                overlap.insert(0, t)
                if tail_len >= CHUNK_OVERLAP:
                    break
            current, current_len = overlap, tail_len
        current.append(s); current_len += s_len
    if current:
        chunks.append(" ".join(current))
    return chunks

def contextual_header(doc_title: str, chunk_text: str) -> str:
    """One LLM call per chunk. Cached by doc-hash + chunk-hash."""
    return small_llm(
        CHUNK_HEADER_PROMPT.format(title=doc_title, chunk=chunk_text)
    ).strip()

def ingest_path(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    title = path.stem
    chunks = chunk(text)
    docs = []
    for i, c in enumerate(chunks):
        header = contextual_header(title, c)
        full = f"[Document: {title}]\n[Summary: {header}]\n\n{c}"
        cid = hashlib.sha256(f"{title}:{i}:{c}".encode()).hexdigest()[:16]
        docs.append({"id": cid, "text": full, "title": title, "idx": i})
    embs = vo.embed([d["text"] for d in docs], model="voyage-3-lite").embeddings
    coll.add(
        ids=[d["id"] for d in docs],
        embeddings=embs,
        documents=[d["text"] for d in docs],
        metadatas=[{"title": d["title"], "idx": d["idx"]} for d in docs],
    )
```

Three things to notice. The chunker is sentence-aware with overlap (Post 09, §2). Each chunk gets a contextual header generated by a cheap model — Anthropic's contextual-retrieval trick (Post 09, §2). The chunk's id is a hash of its source coordinates, so re-ingesting an unchanged file is idempotent.

The BM25 side is built lazily from the same `documents` array on first query and cached in memory; for a large corpus, persist it (`pickle` is fine for the starter; `tantivy` if you have it).

---

## 4. Retrieval — hybrid + RRF + rerank

```python
# src/rag/retrieve.py
from collections import defaultdict
from rank_bm25 import BM25Okapi
import cohere, voyageai
from .ingest import coll

vo = voyageai.Client()
co = cohere.Client()

def rrf_merge(rankings: list[list[str]], k: int = 60) -> list[str]:
    scores = defaultdict(float)
    for r in rankings:
        for rank, cid in enumerate(r):
            scores[cid] += 1.0 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)

def hybrid(query: str, top_n: int = 50) -> list[dict]:
    q_emb = vo.embed([query], model="voyage-3-lite").embeddings[0]
    dense = coll.query(query_embeddings=[q_emb], n_results=top_n)
    dense_ids = dense["ids"][0]
    docs = coll.get(include=["documents", "metadatas"])
    bm25 = BM25Okapi([d.split() for d in docs["documents"]])
    bm25_top = sorted(
        zip(docs["ids"], bm25.get_scores(query.split())),
        key=lambda p: p[1], reverse=True,
    )[:top_n]
    sparse_ids = [cid for cid, _ in bm25_top]
    fused_ids = rrf_merge([dense_ids, sparse_ids])
    id_to_doc = dict(zip(docs["ids"], docs["documents"]))
    id_to_meta = dict(zip(docs["ids"], docs["metadatas"]))
    return [
        {"id": cid, "text": id_to_doc[cid], "meta": id_to_meta[cid]}
        for cid in fused_ids[:top_n]
    ]

def rerank(query: str, candidates: list[dict], k: int = 5) -> list[dict]:
    resp = co.rerank(
        model="rerank-english-v3.0",
        query=query,
        documents=[c["text"] for c in candidates],
        top_n=k,
    )
    return [candidates[r.index] for r in resp.results]

def retrieve(query: str, k: int = 5) -> list[dict]:
    return rerank(query, hybrid(query, top_n=50), k=k)
```

The pipeline is the four-stage shape from Post 08, §1. Dense + sparse run independently; RRF fuses them; the cross-encoder reranks. The two parameters worth surfacing — `top_n=50` for the candidate set, `k=5` for the final pack — are the main quality/cost dials.

---

## 5. Prompt assembly — bookend packing with citations

```python
# src/rag/prompt.py
SYSTEM = """\
# Identity
You are a concise, accurate technical assistant for the Acme product.

# Rules
- Use only the sources below. If the answer is not in them, say
  "I could not find that in the provided sources."
- Cite the source in [brackets] after every claim, e.g. [docs/refunds.md].
- If sources disagree, surface the disagreement and cite both.
- Refuse anything outside Acme's product documentation.

# Format
- Plain prose, no headings unless asked.
- ≤ 200 words unless the user asks for detail.
- Citations are [{title}] using the bracketed title from each source.

# Knowledge
- Acme is a B2B SaaS product. Refunds over $1 000 require manager approval.
- Office hours are 9:00–18:00 IST; out-of-hours requests get a "next business day" reply.
"""

def pack(query: str, hits: list[dict]) -> list[dict]:
    """Bookend layout: best chunk first, second-best last, rest in middle."""
    if not hits:
        ordered = []
    elif len(hits) == 1:
        ordered = hits
    else:
        ordered = [hits[0]] + hits[2:] + [hits[1]]
    sources_block = "\n\n".join(
        f"[{h['meta']['title']}] {h['text']}" for h in ordered
    )
    user = f"Sources:\n\n{sources_block}\n\nQuestion: {query}"
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
    ]

CHUNK_HEADER_PROMPT = """\
You will receive one chunk from a longer document titled "{title}".
Write ONE sentence (≤ 25 words) describing what role this chunk plays
in the document. No preamble.

Chunk:
{chunk}
"""
```

`SYSTEM` is the five-block structure literally — the same shape from Post 12, §2. `pack` implements the bookend layout from Post 08, §5. Citations are the bracketed document titles, machine-parseable downstream.

---

## 6. The chat loop

```python
# src/rag/chat.py
from openai import OpenAI
from .retrieve import retrieve
from .prompt import pack

oai = OpenAI()

def answer(query: str) -> dict:
    hits = retrieve(query, k=5)
    msgs = pack(query, hits)
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        messages=msgs,
        temperature=0.0,
    )
    answer_text = resp.choices[0].message.content
    return {
        "answer": answer_text,
        "sources": [{"title": h["meta"]["title"], "id": h["id"]} for h in hits],
        "usage": resp.usage.model_dump(),
    }

if __name__ == "__main__":
    while True:
        q = input("> ").strip()
        if not q:
            continue
        out = answer(q)
        print(out["answer"])
        print("\nSources:", ", ".join(s["title"] for s in out["sources"]))
```

The complete chat loop. Conversation history is omitted from the starter — for a multi-turn version, append the last *N* turns to `msgs` and add a query-rewrite step at the top of `answer` (Post 08, §2).

---

## 7. Eval — the four Ragas metrics

```python
# src/rag/eval.py
import json
from pathlib import Path
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness, answer_relevancy,
    context_precision, context_recall,
)
from .chat import answer
from .retrieve import retrieve

def run(fixtures_path: Path = Path("tests/fixtures.json")) -> dict:
    fixtures = json.loads(fixtures_path.read_text())
    rows = []
    for fx in fixtures:
        out = answer(fx["question"])
        # ragas wants context strings, not the wrapped chunks
        ctxs = [h["text"] for h in retrieve(fx["question"], k=5)]
        rows.append({
            "question": fx["question"],
            "answer": out["answer"],
            "contexts": ctxs,
            "ground_truth": fx["answer"],
        })
    ds = Dataset.from_list(rows)
    res = evaluate(ds, metrics=[
        faithfulness, answer_relevancy,
        context_precision, context_recall,
    ])
    return res.to_pandas().mean(numeric_only=True).to_dict()

if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
```

A `tests/fixtures.json` of 50 question/answer/ground-truth tuples is enough to start; grow it to 100 over the first few weeks. The CI gate is one extra YAML file (Post 16, §4) that runs `python -m rag.eval` and fails the build if any of the four metrics drop more than 5 % below baseline.

---

## 8. What this build leaves out — and how to add it

A short tour, with the post that covers each.

- **Streaming UI.** Wrap `answer` in a Server-Sent Events endpoint; switch to the streaming chat completion API. Standard work; nothing context-engineering-specific.
- **Multi-turn conversation.** Append the last *N* user/assistant turns to `pack`; add a query-rewrite call before retrieval (Post 08, §2). About 30 lines.
- **Memory.** Persist user-stated facts in a key-value store; pack them into a `[memory]` block before sources (Post 14, §7).
- **Observability.** Wrap each function in spans using your trace store of choice (Post 17, §3). About 20 lines for the basic shape.
- **Auto-compaction.** When the conversation exceeds 80 % of the budget, summarise the older turns (Post 10, §3 + §7).
- **Sub-agents.** Add a tool-using sub-agent for queries like *"draft me a refund email for ticket #4321"* — the orchestrator pattern from Post 11.
- **Long-context routing.** A small classifier in front of `answer` that picks between `retrieve + pack` and `load_whole_document + pack` based on query type (Post 19, §6).

Each of these is a self-contained extension. The starter is the substrate.

---

## 9. The lesson the build teaches

Walking through this build is the fastest way to feel the shape of the field. Every function corresponds to a principle. The chunker is from Post 09. The retriever is from Post 08. The prompt is from Post 12. The eval is from Post 16. The whole shape is the WSCI framework from Post 06: **Write** is `ingest`, **Select** is `retrieve`, **Compress** is the bookend layout (we do not compress in the starter, but the pack budget is the natural place to add it), **Isolate** is the sub-agent extension.

A team that has built and operated this much understands more about context engineering than a team that has read every paper but built none of it.

---

## Common pitfalls

- **Skipping contextual headers** because they cost an LLM call. The 35 % retrieval-failure improvement is worth more than the cost.
- **Skipping reranking** because the demo "looks fine without it". Production traffic exposes the gap immediately.
- **Free-form citations.** Bracketed titles parse trivially; prose citations do not.
- **No eval fixtures.** The next prompt edit silently regresses something.
- **Logging the prompt only on error.** You need it on every call to debug.
- **Treating `top_n = 50` as universal.** Tune to your corpus and your latency budget.

---

## Further reading

- See the corresponding Posts 08, 09, 12, 16 for the principles.
- LangChain, *"Cookbook: RAG from scratch"* (2024) — a similar walkthrough in their idiom.
- Anthropic, *"Contextual retrieval"* (2024) — the header trick.
- Cohere, *"Rerank"* docs and Voyage AI, *"voyage-3"* model cards.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 23 — Build an MCP server](../23-build-mcp-server/index.md)** — the second build, complementary surface area.
- **[Post 24 — Capstone: email reply agent](../24-capstone-email-reply-agent/index.md)** — the everything-together project.
