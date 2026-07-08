# 28 · Build #1 — RAG chatbot from scratch

> **TL;DR.** This post turns the whole series into one runnable RAG (retrieval-augmented generation) chatbot in roughly 250 lines of Python, where every function traces back to an earlier principle. It delivers corpus ingestion with contextual chunk headers, a hybrid retriever (dense + BM25 + reranker), five-block prompt assembly, citation-checked generation, an eval harness with the four Ragas metrics, and a deployment path from local run to CI gate.
>
> **After reading this you will be able to:**
> - Assemble an end-to-end RAG pipeline: ingest, retrieve, prompt, generate, evaluate.
> - Recognise the connection between every code block and an earlier post.
> - Take the build as a starter and harden it for real traffic.
>
> **Companion code:** `code/28-rag-chatbot/`. Full sources, tests, `.env.example`.

![End-to-end RAG architecture split into an offline indexing lane and an online query lane, with an evaluation gate on deploy.](diagrams/00-hero-build-rag-chatbot.svg)
*A production-leaning RAG chatbot is two pipelines: build the index offline, answer online.*

---

## 1. Goals and scope

The goal is a small RAG chatbot that does the right things, not a monolith that does everything. "Right" here means:

- **Hybrid retrieval** with reciprocal rank fusion ([Post 09](../09-select-strategies/index.md), §3).
- **Cross-encoder reranking** ([Post 09](../09-select-strategies/index.md), §4).
- **Contextual chunk headers** ([Post 11](../11-rag-in-depth/index.md), §2).
- **Bookend packing** with citation tags ([Post 09](../09-select-strategies/index.md), §5).
- **A system prompt** with the five blocks ([Post 14](../14-system-prompt-as-software/index.md), §2).
- **An eval harness** with faithfulness, answer relevance, context precision, context recall ([Post 20](../20-evaluation/index.md), §5).

What is *not* in scope: streaming UI, multi-tenant auth, GraphRAG, fine-tuning, distributed indexing. Those are extensions; the core works without them.

---

## 2. Architecture and layout

Before the code, the shape. The system has two phases. **Offline (ingest)** runs once per corpus change: read each document, split it into overlapping chunks, prepend a contextual header to each chunk, embed the chunks, and write them to both a dense vector index and a sparse BM25 (Best Match 25, a keyword-ranking function) index. **Online (a chat turn)** runs on every question: embed the query, run dense and sparse retrieval in parallel, fuse the two rankings with reciprocal rank fusion (RRF), rerank the survivors with a cross-encoder, pack the top few into a bookended prompt, call the generator, and return the answer with its source citations. The eval harness replays a fixture set of questions through the same online path and scores the results.

The five modules map one-to-one onto that flow: `ingest.py` is the offline phase; `retrieve.py`, `prompt.py`, and `chat.py` are the online phase; `eval.py` wraps the online phase in a scorer. A `llm.py` helper holds the shared model clients (including the cheap model used for headers).

```
code/28-rag-chatbot/
├── README.md
├── pyproject.toml
├── .env.example
├── data/
│   └── corpus/                    # drop .md / .txt / .pdf here
├── src/rag/
│   ├── __init__.py
│   ├── llm.py                     # shared model clients (incl. cheap header model)
│   ├── ingest.py                  # chunk + header + embed + index
│   ├── retrieve.py                # hybrid + RRF + rerank
│   ├── prompt.py                  # five-block system prompt
│   ├── chat.py                    # the chat loop
│   └── eval.py                    # the four metrics
├── prompts/
│   ├── system.md
│   └── chunk_header.md
└── tests/
    ├── fixtures.json              # eval question/answer pairs
    ├── test_chunker.py
    └── test_retriever.py
```

A single `pyproject.toml` declares the dependencies: `openai`, `voyageai` (or any embedding provider), `cohere` (rerank), `chromadb`, `rank-bm25`, `pypdf`, `pydantic`, `ragas`, `pytest`. Install can take several minutes on a fresh machine, depending on whether large transitive dependencies such as `torch` (pulled in by the cross-encoder stack) are already cached.

`llm.py` is a thin wrapper around the provider SDKs: it constructs the clients once and exposes `small_llm(prompt)`, a single-call helper backed by a cheap, fast model (for example Claude Haiku 4.5 or a small OpenAI model) that `ingest.py` uses to write chunk headers. Keeping it in one place means the header model, the generator model, and the embedding client are all configured together.

---

## 3. Ingestion: chunking and headers

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

Three things to notice. The chunker is sentence-aware with overlap ([Post 11](../11-rag-in-depth/index.md), §2); the target of ~500 tokens with ~80 tokens of overlap sits inside the series default of 400–600 tokens for prose with 10–20% overlap. Each chunk gets a *contextual header* generated by a cheap model: prepend each chunk with a one-sentence summary of its source document so the chunk still makes sense in isolation. This is Anthropic's contextual-retrieval technique ([Post 11](../11-rag-in-depth/index.md), §2), which cut retrieval failures by ~35% with contextual embeddings alone (Anthropic, 2024). The chunk's id is a hash of its source coordinates, so re-ingesting an unchanged file is idempotent.

The BM25 side is built lazily from the same `documents` array on first query and cached in memory; for a large corpus, persist it (`pickle` is fine for the starter; `tantivy` if you have it).

**A note on model ids.** The version strings in this build (`voyage-3-lite` for embeddings, `rerank-english-v3.0` for reranking, and a small OpenAI generator below) are current examples as of early 2026, and providers turn these over quickly, so check each vendor's model cards before committing (Voyage AI; Cohere). Each id is a single line to change; nothing else in the pipeline depends on it.

---

## 4. Retrieval: hybrid + RRF + rerank

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

The pipeline is the four-stage shape from [Post 09](../09-select-strategies/index.md), §1. Dense and sparse retrieval run independently and see different things (semantics versus exact keywords); RRF fuses their two rankings into one without needing to compare raw scores; the cross-encoder then re-scores each candidate against the query jointly, which is accurate but expensive, so it only sees the fused shortlist. The two parameters worth surfacing, `top_n=50` for the candidate set and `k=5` for the final pack, are the main quality/cost dials.

---

## 5. Prompt assembly: bookend packing with citations

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

`SYSTEM` is the five-block structure literally, the same shape from [Post 14](../14-system-prompt-as-software/index.md), §2. `pack` implements the bookend layout from [Post 09](../09-select-strategies/index.md), §5: the best chunk goes first and the second-best goes last because the first and last positions are the best-attended, the lost-in-the-middle U-curve from [Post 03](../03-how-llms-read-context/index.md). Citations are the bracketed document titles, machine-parseable downstream.

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

The complete chat loop. The generator model here is a small OpenAI chat model, chosen as a cheap, fast default; swap it for any instruction-tuned model (see the note on model ids in §3). `temperature=0.0` keeps answers reproducible for the eval harness. Conversation history is omitted from the starter; for a multi-turn version, append the last *N* turns to `msgs` and add a query-rewrite step at the top of `answer` ([Post 09](../09-select-strategies/index.md), §2).

---

## 7. Eval: the four Ragas metrics

The harness reads a fixture file of question/answer pairs. The schema is two keys per row:

```json
[
  {"question": "How much does a refund over the limit need?",
   "answer": "Refunds over $1 000 require manager approval."},
  {"question": "What are Acme's office hours?",
   "answer": "9:00 to 18:00 IST; out-of-hours requests get a next-business-day reply."}
]
```

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

A `tests/fixtures.json` of 50 question/answer tuples is enough to start; grow it to 100 over the first few weeks. Running `python -m rag.eval` prints the mean of each metric, for example:

```json
{
  "faithfulness": 0.91,
  "answer_relevancy": 0.88,
  "context_precision": 0.79,
  "context_recall": 0.83
}
```

Those values are illustrative, not a benchmark; the absolute numbers matter less than the trend across builds. The CI gate is one extra YAML file ([Post 20](../20-evaluation/index.md), §4) that runs `python -m rag.eval` and fails the build if any of the four metrics drops more than 5% below baseline, a reasonable default threshold you should tune to how noisy your fixture set is.

---

## 8. Deployment

The starter runs as a script; a small amount of packaging turns it into a service.

**Secrets and config.** Every provider key lives in the environment, never in code. `.env.example` lists the variables (`OPENAI_API_KEY`, `VOYAGE_API_KEY`, `COHERE_API_KEY`, and the chosen model ids); copy it to `.env` for local runs and load it with `python-dotenv`. In production, inject the same variables from your platform's secret store rather than shipping a file. `llm.py` reads them once at import.

**Running the service.** Wrap `answer` in a thin HTTP layer, for example a FastAPI app exposing `POST /chat` that calls `answer(query)` and returns the JSON payload (answer, sources, usage). Ingestion stays a separate offline job (`python -m rag.ingest <path>`), run on a schedule or a webhook whenever the corpus changes, so the serving path never blocks on embedding.

**The eval gate.** The CI step from §7 is the deployment safety net: it runs `python -m rag.eval` on every pull request and blocks merge if any metric regresses past the threshold, so a prompt or chunking change that quietly hurts retrieval cannot ship. This is the build's one non-negotiable piece of automation.

**Hosting.** The stateless serving process fits any container host; the state is the Chroma directory and the corpus, both of which want a persistent volume or a managed vector store. For a single-server deployment, `pgvector` on an existing Postgres instance ([Post 11](../11-rag-in-depth/index.md), §3) removes the extra moving part.

---

## 9. What this build leaves out, and how to add it

A short tour, with the post that covers each.

- **Streaming UI.** Wrap `answer` in a Server-Sent Events endpoint; switch to the streaming chat completion API. Standard work; nothing context-engineering-specific.
- **Multi-turn conversation.** Append the last *N* user/assistant turns to `pack`; add a query-rewrite call before retrieval (Post 09, §2). About 30 lines.
- **Memory.** Persist user-stated facts in a key-value store; pack them into a `[memory]` block before sources (Post 16, §7).
- **Observability.** Wrap each function in spans using your trace store of choice (Post 22, §3). About 20 lines for the basic shape.
- **Auto-compaction.** When the conversation exceeds a set share of the budget (for example 80%), summarise the older turns (Post 12, §3 + §7).
- **Sub-agents.** Add a tool-using sub-agent for queries like *"draft me a refund email for ticket #4321"*: the orchestrator pattern from Post 13.
- **Long-context routing.** A small classifier in front of `answer` that picks between `retrieve + pack` and `load_whole_document + pack` based on query type (Post 25, §6).

Each of these is a self-contained extension. The starter is the substrate.

---

## 10. The lesson the build teaches

Walking through this build is the fastest way to feel the shape of the field. Every function corresponds to a principle. The chunker is from [Post 11](../11-rag-in-depth/index.md). The retriever is from [Post 09](../09-select-strategies/index.md). The prompt is from [Post 14](../14-system-prompt-as-software/index.md). The eval is from [Post 20](../20-evaluation/index.md). The whole shape is the WSCI (write, select, compress, isolate) framework from [Post 07](../07-write-select-compress-isolate/index.md): **Write** is `ingest`, **Select** is `retrieve`, **Compress** is the bookend layout (the starter omits compression, but the pack budget is the natural place to add it), **Isolate** is the sub-agent extension.

A team that has built and operated this much understands more about context engineering than a team that has read every paper but built none of it.

---

## Common pitfalls

- **Skipping the contextual header call** to save one cheap LLM call per chunk. Anthropic reports ~35% fewer retrieval failures from contextual embeddings alone (Anthropic, 2024); the header cost is a one-off at ingest time, not per query.
- **Re-embedding the corpus on every run** instead of keying chunks by content hash. The hash id makes re-ingest idempotent; drop it and cost and latency balloon on unchanged files.
- **Free-form citations.** Bracketed titles parse trivially; prose citations do not.
- **No eval fixtures.** The next prompt edit silently regresses something, and without `fixtures.json` the CI gate has nothing to check.
- **Logging the prompt only on error.** You need the assembled prompt on every call to debug a bad answer after the fact.
- **Treating `top_n = 50` as universal.** Tune the candidate-set size and the final `k` to your corpus and your latency budget.

---

## Further reading

- The principle sources this build implements: [Post 09](../09-select-strategies/index.md) (hybrid + RRF + rerank), [Post 11](../11-rag-in-depth/index.md) (chunking, contextual retrieval), [Post 14](../14-system-prompt-as-software/index.md) (system-prompt blocks), [Post 20](../20-evaluation/index.md) (Ragas metrics).
- LangChain, *"RAG from scratch"* cookbook, 2024: a similar walkthrough in their idiom.
- Anthropic, *"Introducing Contextual Retrieval"*, September 2024: the chunk-header trick and the ~35%/49%/67% figures.
- Cohere, *"Rerank"* documentation (model cards, latest): reranker model ids.
- Voyage AI, *"voyage-3"* model cards (latest): embedding model ids.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 29 — Build an MCP server](../29-build-mcp-server/index.md)**: the second build, complementary surface area.
- **[Post 30 — Capstone: email reply agent](../30-capstone-email-reply-agent/index.md)**: the everything-together project.
- **Back to the principles:** [Post 11 — RAG in depth](../11-rag-in-depth/index.md) for the retrieval theory this build implements, and [Post 20 — Evaluation](../20-evaluation/index.md) for the eval harness behind the CI gate.
