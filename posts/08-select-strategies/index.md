# 08 · Select strategies

> **TL;DR.** *Select* is the operation that decides what enters the per-turn payload. The same machinery that powers RAG also powers tool selection, memory recall, and few-shot example picking — and the same four engineering levers (**query construction**, **candidate generation**, **re-ranking**, **packing**) decide how well each of them works. This post is the unifying account: one mental model, four levers, applied to four different read paths.
>
> **Reading time:** ~12 minutes.
>
> **After reading this you will be able to:**
> - Recognise that RAG, tool selection, memory recall, and few-shot picking are all instances of the same operation.
> - Reason about each in terms of recall, precision, latency, and cost on a single template.
> - Pick the lever (query, candidates, re-rank, pack) most likely to fix a given Select failure.

---

## 1. Why "Select" generalises

A naïve reading of the WSCI framework treats Select and RAG as synonyms. They are not. **RAG is one application of Select**; Select is the operation. Once you can see the family resemblance, three things stop being separate problems:

- *Tool selection*: out of 100 tools, which 5 schemas should this turn see? ([Post 13](../13-tools-and-mcp/index.md))
- *Memory recall*: out of thousands of stored facts about this user, which handful go in this prompt? ([Post 14](../14-memory-systems/index.md))
- *Few-shot example selection*: out of dozens of curated examples, which two or three best resemble this query?

Each of these is a Select. Each can be analysed as a four-stage pipeline:

![The four-stage Select pipeline: query, candidates, re-rank, pack](../../assets/diagrams/exports/04-rag-pipeline.svg)

```
       query                    candidates            re-rank             pack
user → construct → embed → ANN → top-N (~50) → cross-encoder → top-k (~5) → into prompt
```

The same four boxes appear regardless of whether the corpus is documents, tool schemas, memory rows, or labelled examples. The technology in each box differs; the *engineering questions* are the same.

---

## 2. Lever 1 — query construction

A retrieval system can only return results that match the query you give it. The default — "embed the user's last message verbatim" — is also the worst-performing default in most production stacks. Three patterns reliably beat it.

**Query rewriting.** A small LLM call rewrites the user turn into a self-contained search query, expanding pronouns, adding context from the conversation, and removing chatter. The user says *"and the second one?"*; the rewritten query is *"What was the closing price of NVIDIA on the second trading day of January 2024?"* Embedding the rewritten form against a financial-news index returns dramatically better results than the original.

**HyDE — Hypothetical Document Embeddings.** Counter-intuitively, you can get better retrieval by asking the model to write the *answer* it expects, then embedding *that* and retrieving against it. The model's hypothetical answer is wrong in detail but right in vocabulary, and vocabulary is what the embedding model matches on. HyDE costs one extra LLM call; it routinely lifts recall by 10–20 %.

**Multi-query expansion.** Generate 3–5 paraphrases of the query, retrieve top-N for each, take the union, deduplicate. Trades a little latency for a meaningful jump in recall on questions whose phrasing is non-canonical.

The choice among the three is empirical: query rewriting is universally cheap; HyDE shines on technical or jargon-heavy corpora; multi-query expansion is the safest default for "I have no idea what the user will ask" assistants.

---

## 3. Lever 2 — candidate generation

The job of candidate generation is **recall**: get every plausibly-relevant chunk into a candidate set that is small enough to re-rank. There are three families of techniques in production, and the strong recommendation is to use *all three at once* (hybrid search).

**Dense retrieval.** Embed the query; embed the corpus offline; retrieve by approximate nearest-neighbour search (FAISS, HNSW, IVF-PQ). Strong on paraphrase and concept matching. Weak when the query contains an exact identifier (a SKU, a product code, a function name) the embedding model has never specifically encoded.

**Sparse retrieval.** Classical BM25 over a Lucene-family index (Elasticsearch, OpenSearch, tantivy). Strong on exact-token and rare-term matches. Weak on paraphrase ("car" vs. "automobile").

**Metadata filtering.** Restrict candidates to chunks whose metadata matches a structured filter — date range, source, language, customer id. Free recall improvement: you stop trying to retrieve from the 99 % of the corpus that is irrelevant by definition.

**Hybrid retrieval** combines the three by running them in parallel and merging the result sets. The merger is usually **reciprocal rank fusion** (RRF): each candidate's final score is the sum of the reciprocals of its ranks across the result lists. RRF is hyper-parameter-free, robust, and reliably outperforms either dense or sparse alone by 10–25 % on public benchmarks.

A reasonable default for a new system: dense (top-30) + BM25 (top-30) + metadata filter, fused by RRF, into a top-50 candidate set.

---

## 4. Lever 3 — re-ranking

Candidate generation optimises recall; re-ranking optimises **precision**. The candidate set has 50 items; the prompt budget can spare 5. The re-ranker chooses which 5.

The dominant technology is the **cross-encoder**: a small model that takes the query and one candidate at a time and outputs a relevance score. Cross-encoders are slow per pair (10–30 ms) and brilliant per pair, because they get to see the query and the chunk *together*, which a bi-encoder embedding match cannot do. Running a cross-encoder over 50 candidates costs ~1 second; running it over 1 M would cost 10 hours, which is exactly why we have a candidate-generation step.

Common production choices: Cohere `rerank`, Voyage `rerank-2`, the open-weight `bge-reranker-v2`. All three are usable through one-line API or library calls.

The lift from re-ranking is often the biggest single quality jump in the entire pipeline. Going from "top-5 by ANN distance" to "top-5 by cross-encoder over top-50 candidates" frequently halves the rate at which the model cites the wrong source.

---

## 5. Lever 4 — packing

The re-ranker has chosen 5 chunks. They will not necessarily fit. Packing decides *what actually lands in the prompt* given the budget.

**Order matters.** Recall the lost-in-the-middle U-curve from [Post 03](../03-how-llms-read-context/index.md): the first and last positions are best attended. The standard tactic is the **bookend layout**: put the highest-scored chunk first and the second-highest last; the rest go in the middle. A small but reliable improvement over "best-to-worst, top-to-bottom".

**Deduplicate.** Two chunks from the same paragraph contribute almost nothing beyond the first. Cosine similarity > 0.9 between two surviving chunks → drop the lower-ranked one.

**Trim within a chunk.** A chunk may be 800 tokens and the relevant span may be 100. A second pass — sometimes called *contextual compression* — uses a tiny model to extract just the relevant span, citing line numbers if they help downstream debugging.

**Cite as you pack.** Format each chunk with a stable, model-readable header (`[source: docs/refunds.md, chunk 3]`). The model will quote those headers back in the answer, giving the application a citation it can render to the user and a debug trail it can grep.

**Respect the budget.** If five chunks would exceed the per-layer RAG budget ([Post 04](../04-tokens-windows-budgets/index.md), §6), drop the lowest-ranked rather than truncating the highest. Truncation half-way through a useful chunk is the worst outcome.

---

## 6. The same pipeline, four times

The same four levers apply to the three other Select problems with small adaptations.

**Tool selection.** The "corpus" is the tool catalog. Each tool's schema (name, description, parameters) is one document; embed it offline. At inference time, embed the user turn (after query rewriting), retrieve top-50 candidates by hybrid search over tool schemas, re-rank, and pack the surviving 3–8 schemas into the tools layer. The Slack MCP example in [Post 13](../13-tools-and-mcp/index.md) — 3 000 tools, 8 surviving — is exactly this pipeline. Without it, the agent's prompt is unusable; with it, the agent always has a small, focused toolbox.

**Memory recall.** The corpus is the memory store. Each memory row is one document. The query is constructed from the *intent* of the current turn ("what does this user usually want when they say X?") rather than its surface text. Re-ranking can mix relevance with **recency** and **confidence** — a 0.9-relevance memory from two years ago may rank below a 0.7-relevance one from yesterday. Packing should respect the memory layer's small budget (Post 04: 5–10 %).

**Few-shot example selection.** The corpus is the labelled-example bank. Each example is one document; the metadata records its label class. Retrieval is dense + filtered ("only examples of class C"). Pack 2–3 examples; more than 5 rarely improves quality and reliably hurts cost. The trick that distinguishes good few-shot pipelines is *diversity reranking*: pick examples that are individually relevant *and* collectively distinct, so the model sees varied templates rather than three near-identical ones.

In every case the four boxes above describe what to build; the implementation is a matter of swapping the corpus and tuning the parameters.

---

## 7. Tuning the system

A short list of dials, ordered by how often they are the right thing to turn:

1. **Re-ranker on/off.** The single largest quality lever. Always on for production search; optional for low-stakes lookups.
2. **`k` — number of packed items.** Default 5; tune down to 3 for terse retrievals and up to 10 for synthesis tasks. More than 10 almost always loses to better re-ranking.
3. **Top-N candidate set.** Default 50; raise to 100 if recall on long-tail queries is poor; lower to 20 if latency is tight.
4. **Hybrid weighting.** RRF works without tuning; weighted fusion can edge it out if you have offline labels.
5. **Chunk size.** 400–600 tokens is a strong default for prose; 200–300 for code. Tune by measuring the rate at which the answer's supporting fact is *fully inside* the retrieved chunk.
6. **Embedding model.** Switch only with an offline benchmark; the default `text-embedding-3-small` / `voyage-3-lite` / `bge-large` tier is good enough for almost everything.
7. **Query rewriting / HyDE.** On for jargon-heavy corpora; optional otherwise.

The mistake to avoid is tuning these in the wrong order. A team that switches the embedding model before turning on re-ranking is rearranging deck chairs.

---

## 8. Measuring whether it works

The two metrics worth wiring up before any of the above:

- **Recall@N (offline).** Out of a curated query/answer pair set, what fraction of queries have the gold passage somewhere in the top-N candidates? Cheap to compute and the single most predictive number for end-to-end quality.
- **Citation accuracy (online).** Does the chunk the model cited contain the fact it asserted? Sample 50 production answers a week; have a human label. This is the metric that exposes packing and re-ranking bugs that recall@N does not.

Adding a third — **end-to-end answer correctness on a held-out eval set** — closes the loop, and is the subject of [Post 16](../16-evaluation/index.md).

---

## Common pitfalls

- **Embedding the user message verbatim.** A query rewrite step is almost free and almost always helps.
- **Skipping re-ranking.** The single most under-used quality lever in the field.
- **Tuning embedding models before tuning chunking.** A 5 % chunker improvement beats a 1 % embedding improvement, every time.
- **Packing in score order.** Bookend layout is strictly better.
- **Optimising recall when the system is already over-stuffed.** The bug is precision, not recall.
- **Treating tool selection as a separate problem.** It is the same pipeline as RAG, with a different corpus.

---

## Further reading

- Karpukhin, V. *et al.*, *"Dense Passage Retrieval for Open-Domain Question Answering"* (2020).
- Robertson, S. & Zaragoza, H., *"The Probabilistic Relevance Framework: BM25 and Beyond"* (2009).
- Cormack, G. V. *et al.*, *"Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"* (2009) — the RRF paper.
- Gao, L. *et al.*, *"Precise Zero-Shot Dense Retrieval without Relevance Labels"* (2022) — HyDE.
- Anthropic Engineering, *"Contextual Retrieval"* (2024) — chunk-enrichment + hybrid + re-ranking.
- Cohere, *"Rerank"* docs; Voyage AI, *"rerank-2"* docs; BAAI, *"bge-reranker-v2"* model card.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 09 — RAG in depth](../09-rag-in-depth/index.md)** — the document-corpus instance, with concrete code.
- **[Post 13 — Tools and MCP](../13-tools-and-mcp/index.md)** — the tool-corpus instance.
- **[Post 14 — Memory systems](../14-memory-systems/index.md)** — the memory-corpus instance.
- **[Post 15 — Advanced retrieval](../15-advanced-retrieval/index.md)** — graph RAG, late-interaction models, structured retrieval.
