# 09 · RAG in depth

> **TL;DR.** Retrieval-augmented generation is the document-corpus instance of the Select operation ([Post 08](../08-select-strategies/index.md)). The four-stage pipeline — query, candidates, re-rank, pack — is the same; what is specific to RAG is the *offline preparation* of the corpus, the *evaluation* of end-to-end answer quality, and a small bag of techniques (contextual retrieval, reciprocal rank fusion, cross-encoder reranking) that account for most of the difference between a demo RAG and a production one.
>
> **Reading time:** ~13 minutes.
>
> **After reading this you will be able to:**
> - Walk through every stage of a production RAG pipeline and name what fails when.
> - Apply the three techniques that consistently lift quality (contextual retrieval, hybrid + RRF, cross-encoder reranking).
> - Wire up the minimum eval harness that tells you whether a change actually helped.

![The RAG pipeline](../../assets/diagrams/exports/04-rag-pipeline.svg)

---

## 1. The two halves

Every RAG system has an **offline** half — collection, cleaning, chunking, enrichment, embedding, indexing — and an **online** half — query construction, candidate generation, re-ranking, packing, generation. The offline half decides the ceiling on quality; the online half decides how close you get to it.

This post focuses on the engineering choices in each half that actually move the metric, in roughly the order their impact compounds.

---

## 2. Offline: chunking is more than half the battle

A chunk is the unit retrieval returns. It is the granularity at which the system says "this is what was relevant". Get it wrong and no amount of fancy retrieval will recover.

**Chunk size.** The empirical sweet spot for prose is 400–600 tokens with 10–20 % overlap. Smaller chunks (100–200) win on precision but lose self-containment — the model gets a fragment without enough surrounding context to use it. Larger chunks (1 000+) waste budget — the prompt fills up with paragraphs that touch the answer rather than carrying it.

**Splitter choice.** Three families, in order of preference:

1. **Structure-aware** — split on Markdown headings, HTML sections, source-code symbols, PDF page boundaries. Best when the source has structure.
2. **Sentence-aware** — split on sentence boundaries with a token budget per chunk. The default for free-form prose; libraries like `langchain.RecursiveCharacterTextSplitter` and `llama-index`'s sentence splitter do this well.
3. **Fixed-length** — split every *N* characters or tokens. Last resort. Will cut sentences in half.

For code, split by symbol (function, class, module). A 1 200-token function is one chunk; a 50-token helper is one chunk. Splitting code in the middle of a function is almost always a mistake.

**Overlap.** Adjacent chunks share 10–20 % of their tokens so a fact that lives at a chunk boundary survives in at least one chunk in full. Overlap is cheap (it grows the index linearly) and prevents a category of "the answer is right there but split across two chunks" misses.

**Contextual retrieval.** Anthropic's name for a single offline trick: prepend each chunk with a one-or-two-sentence summary of *the document it came from*. The chunk now carries enough context to make sense in isolation. The cost is one cheap LLM call per chunk at index time (one-off; cacheable). The reported lift on Anthropic's benchmark was ~35 % reduction in retrieval failures — the largest single offline improvement most teams will ever ship.

The header looks like this:

```
[Document: refunds-policy.md, Section 4]
[Summary: Defines escalation thresholds for the customer-support agent.
 Refunds over $1 000 require manager approval.]

When a customer requests a refund of more than $1 000, the agent must…
```

Adding the document title and section path is free; adding the summary costs one LLM call per chunk; both should be in the index for any RAG you intend to ship.

---

## 3. Offline: embedding model and index

**Embedding model.** Three reasonable defaults today: `text-embedding-3-small` (OpenAI), `voyage-3-lite` (Voyage), `bge-large-en-v1.5` (open-weight). The differences are smaller than they used to be. The decision rule: if your corpus is in a language or domain (legal, medical, code) where one of these has a specialised variant, use it; otherwise the choice is mostly cost and operational preference.

**Vector database.** For prototypes: `Chroma` or `FAISS` in-process. For single-server production: `pgvector` on the Postgres you already operate. For scale (>10 M vectors, multi-tenant, hosted): `Pinecone`, `Weaviate`, `Qdrant`, `Milvus`. The decision rule: pick the lowest-operational-burden option that meets your scale; the retrieval quality will be dominated by chunking and re-ranking, not by the database.

**Sparse index alongside.** An Elasticsearch / OpenSearch / tantivy index over the same corpus, populated at the same time. Hybrid retrieval ([Post 08](../08-select-strategies/index.md), §3) needs both. The cost of running both is small compared to the recall lift from fusing them.

**Manifest table.** A row per source document — its hash, its chunks' ids, the embedding-model version, the timestamp. Without this you cannot answer "what changed in the index since last week", which is the question every production debugging session opens with.

---

## 4. Online: the four levers (recap)

The online pipeline is described in detail in [Post 08](../08-select-strategies/index.md). The summary in pipeline order:

1. **Query** — rewrite the user turn into a self-contained search query, optionally generate a hypothetical answer (HyDE) or 3–5 paraphrases (multi-query).
2. **Candidates** — hybrid retrieval (dense top-30 + BM25 top-30 + metadata filter) merged by **reciprocal rank fusion** into a top-50 candidate set.
3. **Re-rank** — a cross-encoder (Cohere `rerank`, Voyage `rerank-2`, `bge-reranker-v2`) scores each candidate against the query; keep the top-5.
4. **Pack** — bookend layout (best chunk first, second-best last), deduplicate near-identical chunks, optionally trim within a chunk, attach a citation header per chunk, respect the per-layer budget.

Three sub-points worth surfacing because they are RAG-specific:

- **Query construction must include conversation context.** A naïve embedding of "and the second one?" against your knowledge base returns garbage. Either rewrite using the last 2–3 turns or concatenate them into the query string.
- **Candidate fusion order doesn't matter to RRF.** RRF is symmetric in its inputs; this is half the reason it works without tuning.
- **Re-ranking is the #1 quality lever.** If a team has built every other piece and skipped this one, fix this first.

---

## 5. Generation — what the prompt should look like

The model sees the packed chunks, a system prompt that instructs it how to use them, and the user's question. The system prompt does more work than people expect. A skeleton that consistently behaves well:

```
You are answering a question using the provided sources.

Rules:
1. Use only the sources below. If the answer is not in them, say
   "I could not find that in the provided sources."
2. Cite the source in [brackets] after every claim, e.g. [refunds.md §4].
3. If sources disagree, surface the disagreement and cite both.

Sources:
[refunds.md §4] When a customer requests a refund over $1 000…
[refunds.md §5] The manager queue is staffed 24/5…
[escalations.md §2] All escalations require a written summary…

Question: {user_question}
```

Three details to notice:

- **The "if you don't know, say so" instruction.** Without it the model fills gaps from parametric memory and the citations become decorative.
- **Citations are mandatory and machine-parseable.** This makes it possible to verify, after the fact, that the cited chunk really contained the asserted fact.
- **The disagreement clause.** Cheaper than building a pre-retrieval consistency checker; lets the human reader catch the conflict.

---

## 6. Evaluation — the harness without which nothing improves

A RAG system that is not measured will degrade. The minimum eval harness has three pieces.

**A gold-question set.** 50–200 question/answer pairs curated by domain experts. Each pair carries the *ground-truth source chunk* (which document and which section the answer comes from). 100 questions is enough to detect a 5 % regression with reasonable confidence.

**Three metrics, computed on every change:**

- **Recall@N (retrieval-only).** Out of the gold questions, what fraction had the gold chunk in the top-N candidates? Cheapest to compute; predicts the ceiling on end-to-end quality.
- **Citation accuracy (retrieval + packing).** Did the chunk the model cited contain the fact it asserted? An LLM-as-judge can evaluate this if you do not want to pay for human labels every run.
- **End-to-end answer correctness.** Did the model's final answer match the gold answer (semantically)? An LLM-as-judge with a rubric works; full human review on a sample for ground truth.

**A regression gate in CI.** Any change to chunker, embedding model, retrieval, re-ranker, prompt template runs the eval. A drop greater than the noise floor blocks the merge. This is the discipline that distinguishes RAG systems that improve over time from RAG systems that decay.

---

## 7. Where production RAGs go wrong

A short tour of the failure modes, in roughly descending frequency.

- **No re-ranker.** Most demo-grade RAGs ship without one. Adding one is the single highest-ROI fix.
- **Chunks too big.** The retrieved chunk is 1 500 tokens; the answer-bearing sentence is 30. Half the budget is paid to wrap a fact.
- **No structural metadata.** All chunks live in one undifferentiated pool. Queries that should be filtered to one document are searched against the entire corpus.
- **Embedding stale chunks.** A document changed two months ago. The vector still points to the old chunks. The agent confidently cites an outdated policy.
- **Citations drop on the floor.** The model cites; the application does not surface the citation; the user has no way to verify; trust collapses on the first wrong answer.
- **Retrieval but no generation guard.** No "if you don't know, say so" instruction. The model hallucinates with confident citations.
- **No eval set.** Every change feels good; quality drifts; nobody can tell.
- **Reaching for the latest embedding model before fixing chunking.** The most common form of premature optimisation in this space.

---

## 8. When *not* to use RAG

RAG is a tool, not a religion. Three situations where it is the wrong tool:

- **The corpus fits in the context window.** A 50-page handbook fits in 100 k tokens. Just include it. Cache it. Skip the pipeline.
- **The query needs *all* of the corpus.** Summarisation of a single 30-page document does not benefit from retrieval; it needs the whole document.
- **The information is structured.** A query like "list all customers in California with churn risk > 0.7" should hit a database, not a vector index. RAG is for unstructured text; SQL is for tables.

Hybrid systems — *route* to RAG, SQL, or full-document depending on the query type — outperform pure-RAG systems on every realistic benchmark.

---

## Common pitfalls

- **Skipping contextual retrieval.** The single largest one-off offline win.
- **Skipping re-ranking.** The single largest online win.
- **Embedding the user message verbatim.** Query construction is not optional.
- **Treating "more chunks" as the fix for any quality problem.** Usually it is the cause.
- **Using RAG when the data is structured or already fits.** SQL, full-document, and RAG each have a niche.
- **Shipping without an eval set.** You will not be able to tell if your next change helped.

---

## Further reading

- Anthropic Engineering, *"Contextual Retrieval"* (2024) — the chunk-enrichment trick.
- Cormack, G. V. *et al.*, *"Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"* (2009).
- Lewis, P. *et al.*, *"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"* (2020) — the original paper.
- Khattab, O. & Zaharia, M., *"ColBERT"* (2020) — late-interaction retrieval, covered in [Post 15](../15-advanced-retrieval/index.md).
- Saad-Falcon, J. *et al.*, *"ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation"* (2023).

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 10 — Compress strategies](../10-compress-strategies/index.md)** — keeping retrieved context within budget.
- **[Post 15 — Advanced retrieval](../15-advanced-retrieval/index.md)** — graph RAG, late interaction, structured retrieval.
- **[Post 16 — Evaluation](../16-evaluation/index.md)** — the eval harness in detail.
