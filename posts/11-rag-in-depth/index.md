# 11 · RAG in depth

> **TL;DR.** Retrieval-augmented generation is the document-corpus instance of the Select operation ([Post 09](../09-select-strategies/index.md)). The four-stage pipeline — query, candidates, re-rank, pack — is the same; what is specific to RAG is the *offline preparation* of the corpus, the *evaluation* of end-to-end answer quality, and a small bag of techniques (contextual retrieval, reciprocal rank fusion, cross-encoder reranking) that account for most of the difference between a demo RAG and a production one.
>
> **After reading this you will be able to:**
> - Walk through every stage of a production RAG pipeline and name what fails when.
> - Apply the three techniques that consistently lift quality (contextual retrieval, hybrid + RRF, cross-encoder reranking).
> - Wire up the minimum eval harness that tells you whether a change actually helped.

![The RAG pipeline](diagrams/04-rag-pipeline.svg)

*The RAG pipeline: an offline half (chunk, enrich, embed, index) that sets the quality ceiling, and an online half (query, retrieve, re-rank, pack, generate) that decides how close you get to it.*

---

## 1. The two halves

Every RAG system has an **offline** half (collection, cleaning, chunking, enrichment, embedding, indexing) and an **online** half (query construction, candidate generation, re-ranking, packing, generation). The offline half decides the ceiling on quality; the online half decides how close you get to it.

This post focuses on the engineering choices in each half that actually move the metric, in roughly the order their impact compounds.

---

## 2. Offline: chunking is more than half the battle

A chunk is the unit retrieval returns. It is the granularity at which the system says "this is what was relevant". Get it wrong and no amount of fancy retrieval will recover.

![Three splitter families in order of preference, chunk size as three zones, and overlap drawn as two genuinely overlapping bars](diagrams/01-chunking-choices.svg)

*Splitter first, then size, then overlap. The vector database is nowhere on this figure because it barely moves the outcome.*

**Chunk size.** The empirical sweet spot for prose is 400–600 tokens with 10–20 % overlap. Smaller chunks (100–200) win on precision but lose self-containment: the model gets a fragment without enough surrounding context to use it. Larger chunks (1 000+) waste budget: the prompt fills up with paragraphs that touch the answer rather than carrying it.

**Splitter choice.** Three families, in order of preference:

1. **Structure-aware**: split on Markdown headings, HTML sections, source-code symbols, PDF page boundaries. Best when the source has structure.
2. **Sentence-aware**: split on sentence boundaries with a token budget per chunk. The default for free-form prose; libraries like `langchain.RecursiveCharacterTextSplitter` and `llama-index`'s sentence splitter do this well.
3. **Fixed-length**: split every *N* characters or tokens. Last resort. Will cut sentences in half.

For code, split by symbol (function, class, module). A 1 200-token function is one chunk; a 50-token helper is one chunk. Splitting code in the middle of a function is almost always a mistake.

**Overlap.** Adjacent chunks share 10–20 % of their tokens so a fact that lives at a chunk boundary survives in at least one chunk in full. Overlap is cheap (it grows the index linearly) and prevents a category of "the answer is right there but split across two chunks" misses.

**Parent-child and late chunking.** Two refinements that decouple the unit that is *retrieved* from the unit that is *embedded*. Parent-child (small-to-big) retrieval embeds and searches small child chunks for precision, then hands the model the larger parent chunk they belong to for context. Late chunking (Günther et al., 2024) runs the whole document through a long-context embedding model first and only splits the token embeddings into chunks afterwards, so each chunk vector already reflects its neighbours. Both trade a little index complexity for better recall on boundary-spanning facts; reach for them once fixed chunking has plateaued.

![A chunk carrying a document and summary prefix, beside three bars showing 35, 49 and 67 per cent reductions in retrieval failures](diagrams/02-contextual-retrieval.svg)

*One cheap call per chunk at index time, and the three published numbers it buys.*

**Contextual retrieval.** Anthropic's name for a single offline trick: prepend each chunk with a one-or-two-sentence summary of *the document it came from*. The chunk now carries enough context to make sense in isolation. The cost is one cheap LLM call per chunk at index time (one-off; cacheable). The reported lift is about 35% fewer retrieval failures with contextual embeddings alone, about 49% when combined with a contextual BM25 keyword index (BM25 is the classic sparse lexical ranker), and about 67% once a reranker is added (Anthropic, 2024). The contextual-embeddings step alone is the largest single offline improvement most teams will ever ship.

The header looks like this:

```
[Document: refunds-policy.md, Section 4]
[Summary: Defines escalation thresholds for the customer-support agent.
 Refunds over $1 000 require manager approval.]

When a customer requests a refund of more than $1 000, the agent must…
```

Adding the document title and section path is free; adding the summary costs one LLM call per chunk; both belong in the index for any production RAG.

---

## 3. Offline: embedding model and index

**Embedding model.** Three reasonable defaults as of early 2026: `text-embedding-3-small` (OpenAI), `voyage-3-lite` (Voyage), `bge-large-en-v1.5` (open-weight). Specific models turn over fast, so treat these as examples and check a current ranking such as the MTEB leaderboard (Muennighoff et al., 2022) before committing. The differences between top general-purpose models are smaller than they used to be. The decision rule: for a corpus in a language or domain (legal, medical, code) where one of these has a specialised variant, use it; otherwise the choice is mostly cost and operational preference.

**Vector database.** For prototypes: `Chroma` or `FAISS` in-process. For single-server production: `pgvector` on an existing Postgres instance. For scale (many millions of vectors, multi-tenant, hosted; roughly north of ten million as a rule of thumb): `Pinecone`, `Weaviate`, `Qdrant`, `Milvus`. The decision rule: pick the lowest-operational-burden option that meets the scale; retrieval quality is dominated by chunking and re-ranking, not by the database.

**Sparse index alongside.** An Elasticsearch / OpenSearch / tantivy index over the same corpus, populated at the same time. Hybrid retrieval ([Post 09](../09-select-strategies/index.md), §3) needs both. The cost of running both is small compared to the recall lift from fusing them.

**Manifest table.** A row per source document: its hash, its chunks' ids, the embedding-model version, the timestamp. Without this there is no way to answer "what changed in the index since last week", which is the question every production debugging session opens with.

---

## 4. Online: the four levers (recap)

The online pipeline is described in detail in [Post 09](../09-select-strategies/index.md). The summary in pipeline order:

1. **Query**: rewrite the user turn into a self-contained search query, optionally generate a hypothetical answer (HyDE, hypothetical-document embeddings: embed a drafted answer rather than the raw question) or 3–5 paraphrases (multi-query).
2. **Candidates**: hybrid retrieval (dense top-30 + BM25 top-30 + metadata filter; top-*k* means keeping the *k* best-scoring results) merged by **reciprocal rank fusion** (RRF) into a top-50 candidate set.
3. **Re-rank**: a cross-encoder (for example Cohere `rerank`, Voyage `rerank-2`, or the open-weight `bge-reranker-v2`; see Further reading) scores each candidate against the query; keep the top-5.
4. **Pack**: bookend layout (best chunk first, second-best last), deduplicate near-identical chunks, optionally trim within a chunk, attach a citation header per chunk, respect the per-layer budget.

Three sub-points worth surfacing because they are RAG-specific:

- **Query construction must include conversation context.** A naïve embedding of "and the second one?" against your knowledge base returns garbage. Either rewrite using the last 2–3 turns or concatenate them into the query string.
- **Candidate fusion order doesn't matter to RRF.** RRF scores each candidate by summing `1 / (k + rank)` across the result lists (a small constant `k`, often 60, damps the top ranks); because it sums over lists, it is symmetric in its inputs, which is half the reason it works without tuning. Post 09 (§3) defines it in full.
- **Re-ranking is the single highest-ROI online fix.** If a team has built every other piece and skipped this one, fix this first. (The same lever is called out in §7 and in Common pitfalls.)

---

## 5. Generation: what the prompt should look like

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

## 6. Evaluation: the harness without which nothing improves

A RAG system that is not measured will degrade. The minimum eval harness has three pieces.

**A gold-question set.** 50–200 question/answer pairs curated by domain experts. Each pair carries the *ground-truth source chunk* (which document and which section the answer comes from). As a rough rule of thumb, on the order of a hundred questions is enough to notice a few-percent regression without drowning in per-run labelling cost; treat the exact number as illustrative and grow the set until results stop moving between runs.

**Three metrics, computed on every change:**

- **Recall@N (retrieval-only).** Out of the gold questions, what fraction had the gold chunk in the top-N candidates? Cheapest to compute; predicts the ceiling on end-to-end quality.
- **Citation accuracy (retrieval + packing).** Did the chunk the model cited contain the fact it asserted? An LLM-as-judge can evaluate this when paying for human labels every run is not worth it.
- **End-to-end answer correctness.** Did the model's final answer match the gold answer (semantically)? An LLM-as-judge with a rubric works; full human review on a sample for ground truth.

**A regression gate in CI.** Any change to chunker, embedding model, retrieval, re-ranker, prompt template runs the eval. A drop greater than the noise floor blocks the merge. This is the discipline that distinguishes RAG systems that improve over time from RAG systems that decay.

---

## 7. Where production RAGs go wrong

A short tour of the failure *symptoms* seen in the field, in roughly descending frequency. (Common pitfalls, below, lists the upstream *decisions* that cause them; the two lists are meant to be read together, not as duplicates.)

- **No re-ranker.** Most demo-grade RAGs ship without one; adding one is the highest-ROI online fix (the same lever named in §4).
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

Hybrid systems, which *route* to RAG, SQL, or full-document depending on the query type, outperform pure-RAG systems on every realistic benchmark.

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

- Anthropic, *"Introducing Contextual Retrieval"* (Sept 2024): the chunk-enrichment trick and the ~35%/49%/67% figures.
- Cormack, G. V. *et al.*, *"Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"* (2009): the RRF formula used in §4.
- Lewis, P. *et al.*, *"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"* (2020): the original RAG (retrieval-augmented generation) paper.
- Muennighoff, N. *et al.*, *"MTEB: Massive Text Embedding Benchmark"* (2022): the leaderboard for choosing an embedding model (§3). See [huggingface.co/spaces/mteb/leaderboard](https://huggingface.co/spaces/mteb/leaderboard) for the current ranking.
- Cohere, Voyage AI, and BAAI reranker documentation: the cross-encoder models named in §4.
- Günther, M. *et al.*, *"Late Chunking: Contextual Chunk Embeddings Using Long-Context Embedding Models"* (2024): the late-chunking method in §2.
- Khattab, O. & Zaharia, M., *"ColBERT"* (2020): late-interaction retrieval, covered in [Post 17](../17-advanced-retrieval/index.md).
- Saad-Falcon, J. *et al.*, *"ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems"* (NAACL 2024; arXiv 2311.09476, 2023).

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 12 — Compress strategies](../12-compress-strategies/index.md)**: keeping retrieved context within budget.
- **[Post 17 — Advanced retrieval](../17-advanced-retrieval/index.md)**: graph RAG, late interaction, structured retrieval.
- **[Post 20 — Evaluation](../20-evaluation/index.md)**: the eval harness in detail.
