# 15 · Advanced retrieval

> **TL;DR.** Standard hybrid-RAG ([Post 09](../09-rag-in-depth/index.md)) handles 70 % of production retrieval needs. The remaining 30 % — corpora with rich relationships, queries that span multiple documents, structured data, very-long-context single sources — are where the **advanced** techniques earn their cost. This post covers the four that recur in production: **GraphRAG**, **late-interaction retrieval (ColBERT)**, **structured / SQL retrieval**, and **long-context routing**. Each comes with its sweet spot and its overhead.
>
> **Reading time:** ~12 minutes.
>
> **After reading this you will be able to:**
> - Recognise the corpus shapes that defeat vanilla RAG.
> - Pick the right advanced technique for each shape.
> - Estimate the engineering and inference-cost overhead before committing.

---

## 1. When standard RAG hits its ceiling

Vanilla RAG — chunk, embed, hybrid retrieve, rerank, pack — handles factoid questions over collections of independent documents extremely well. It runs into trouble in four recurring shapes:

1. **Multi-hop questions.** *"Which suppliers are downstream of vendors that failed our 2024 audit?"* The answer requires *joining* facts from multiple documents; no single chunk contains it.
2. **Long-document questions.** *"Summarise the key risks raised in this 200-page filing."* The answer needs the *whole* document, not the best 5 chunks.
3. **Structured-data questions.** *"How many tickets did the Bangalore team close last quarter?"* The data is in a table; embeddings are the wrong tool.
4. **Domain corpora with rare exact terms.** A question about a specific gene, SKU, contract id, or Sanskrit term where the embedding model has never seen the token.

Each of these has a specialised technique. None of them replace vanilla RAG; they augment it. A serious production system has a *router* that picks the technique by query type.

---

## 2. GraphRAG — when the corpus has structure

**The problem.** A corpus of company filings, internal wiki pages, or a research literature where the answer to many questions is a *path* through related entities. Vanilla retrieval pulls the right *nodes* but not the *edges*; the model gets isolated facts and cannot synthesise.

**The technique.** Build a knowledge graph from the corpus offline. Entities (companies, people, products, concepts) become nodes; mentions, ownership, references become edges. At retrieval time, the query is parsed for entities; the graph is traversed *N* hops from each entity; the relevant subgraph (plus the source chunks for each edge) is packed into the prompt.

**What works in practice.** Microsoft Research's GraphRAG (2024) is the most widely cited reference implementation. The key engineering choice is the *entity-extraction quality* — the graph is only as good as the upstream entity recognition. Reported lifts on multi-hop benchmarks are 25–60 % over vanilla RAG, with the larger gains on questions that explicitly require traversal.

**Cost.** Significant. The offline graph build is a one-off LLM-heavy pass over the entire corpus (often 5–10× the embedding cost). The online retrieval adds a graph traversal step. The win is large where the corpus has real structure; the loss is large where the corpus is just a pile of independent documents and you spent a month building a graph nobody needed.

**When to use.** Multi-hop questions are a real fraction (>10 %) of your traffic; the corpus has named entities the questions reference; you can afford the offline build.

---

## 3. Late-interaction retrieval — when chunks are not the right unit

**The problem.** Bi-encoder retrieval (the standard) embeds the entire chunk into one vector. The query also collapses to one vector. The match is a single dot product. Information about *which tokens* in the chunk match *which tokens* in the query is lost. This loses recall on questions where the answer-bearing span is small relative to the chunk.

**The technique.** **ColBERT** (Khattab & Zaharia, 2020) and its successors keep one vector *per token* in both the chunk and the query, then score by sum-of-max similarity at retrieval time. The model gets credit for matches at the token level, not just the chunk level. The newer **ColBERTv2** and **JaColBERT** variants are practical at scale.

**What works in practice.** ColBERT-style retrievers consistently win on benchmarks where the relevant span is short (definitional questions, exact-phrase lookups, technical terminology). On general factoid retrieval, the lift over a good bi-encoder + rerank pipeline is small (5–10 %); on technical corpora it can be substantial (15–30 %).

**Cost.** Index size grows roughly 50–100× compared to a bi-encoder index (one vector per token, not per chunk). Retrieval latency grows similarly. Mitigations exist (PLAID, compression) but the engineering complexity is real. Treat ColBERT as a target for the next iteration, not as the default first build.

**When to use.** Technical or domain-specific corpora; queries with rare exact tokens; sub-second latency budget that can afford 50 ms more for retrieval; team that has already shipped a vanilla pipeline and is hunting for the next 10 %.

---

## 4. Structured / SQL retrieval — when the data is a table

**The problem.** "How many enterprise customers in EMEA churned last quarter?" The data is in a database. Embedding individual rows and retrieving by similarity is the *wrong tool*; SQL is the right one.

**The technique.** **Text-to-SQL.** A small LLM call translates the user's natural-language question into a SQL query against a known schema; the application executes the query; the result rows are formatted and returned to the user (optionally also packed into the main agent's context).

**What works in practice.** The pattern that consistently outperforms naïve text-to-SQL:

1. **Schema-aware prompt.** The translation prompt includes only the *tables and columns relevant to this query*, retrieved by — yes — RAG over a schema documentation corpus. A schema with 500 tables overwhelms the LLM if all of it goes in the prompt.
2. **Few-shot examples.** Two or three (question → SQL) pairs that look like this query, retrieved from a curated bank.
3. **Validation pass.** The generated SQL is parsed (not executed) and checked against the schema; errors are fed back to the LLM for one repair attempt.
4. **Read-only execution role.** The SQL runs as a database user that *cannot write*. Defence in depth against an injection attack via the model.

**Cost.** Modest. One LLM call for translation, one for any repair. The latency is dominated by the SQL execution. The main risk is *correctness* on complex joins; production systems use a **router** that sends ambiguous or complex queries to a human-curated query template instead of free-form translation.

**When to use.** Any time the underlying answer source is structured. The single most-skipped advanced technique; teams reach for vector RAG over what was always a SQL question.

---

## 5. Long-context routing — when the model can hold the whole document

**The problem.** A 50-page contract. The user asks "summarise the risks" and "what is the termination notice period". One question wants *all* the document; the other wants *one paragraph*. Retrieval is wrong for the first; loading the whole document is wasteful for the second.

**The technique.** **Route by query type.** A small classifier — itself an LLM call with a short rubric — labels the query as `whole_document` or `local_lookup`. Whole-document queries load the full source (within budget) and skip retrieval. Local-lookup queries go through the standard RAG pipeline.

**What works in practice.** The classifier is the entire engineering surface. A two-shot rubric — "global if the answer requires the entire document; local if a single paragraph would suffice" — is enough for >90 % accuracy on most corpora. Hybrid handling for the unsure cases: load the document *and* run RAG, pack the top RAG chunks as a "table of contents" before the full document.

The trick that makes this affordable is **prompt caching** ([Post 12](../12-system-prompt-as-software/index.md), §5). A 50-page document loaded into context costs full price the first time and ~10 % thereafter. Many production assistants for long-document review now keep the document cached for the duration of the session and route every query through the same prefix.

**Cost.** Highest *per-call* of the techniques in this post (the long context is paid for in full on the cache miss). Lowest *engineering* overhead — most teams can ship this in a day. Choose when latency budget allows the larger calls and the corpus is genuinely document-shaped.

---

## 6. The router

The pattern that ties this post together: **a small router in front of the retrieval system** that picks the technique per query.

```
user turn
  │
  ▼
classify(query)
  │
  ├─ is_structured       → text-to-SQL
  ├─ requires_traversal  → GraphRAG
  ├─ whole_document      → long-context load
  └─ default             → standard hybrid-RAG + rerank
```

The router is two things: a small LLM classifier (or a rules engine, if the categories are clear) and an orchestrator that dispatches to the right pipeline. The end-to-end answer-quality lift from getting routing right is often larger than any single technique improvement, because the *wrong* technique on the *wrong* query is not just suboptimal — it is the difference between an answer and "I could not find that".

---

## 7. What *not* to do

A short, opinionated list.

- **Replace standard RAG with GraphRAG everywhere.** GraphRAG on a flat corpus is engineering overhead with no payoff.
- **Reach for ColBERT before fixing chunking.** The 2× retrieval cost rarely beats a chunker pass that captures the right span in the first place.
- **Try to text-to-SQL a 500-table warehouse without schema retrieval.** The LLM cannot pick the right tables from a 50 k-token schema dump.
- **Load every long document into context.** Cache helps but cannot rescue a workload of 200 different long documents.
- **Skip the router.** Without it the team builds three pipelines and uses the wrong one half the time.

---

## 8. The shape of a production retrieval stack

A reference assembly — useful as a sanity check against your own system.

| Stage | Technology | Role |
|---|---|---|
| Router | LLM classifier (small) | Picks the pipeline |
| Standard RAG | Hybrid (dense + BM25 + filter) → cross-encoder rerank → packed with citations | Default |
| GraphRAG | Entity extraction → knowledge graph → traversal | Multi-hop questions |
| Text-to-SQL | Schema retrieval → SQL generation → validation → read-only execution | Structured queries |
| Long-context | Long-context model + prompt caching | Whole-document queries |
| Eval harness | Gold question set per pipeline | Regression gate in CI |

The total picture is more elaborate than vanilla RAG; the gain over vanilla RAG on a real production workload is usually large. Build it incrementally: vanilla first, eval harness, then add the routes one at a time as the unanswered-questions metric tells you which route is missing.

---

## Common pitfalls

- **Reaching for advanced techniques before standard RAG is well-tuned.** Most "we need GraphRAG" decisions come from skipping reranking.
- **No router.** Each pipeline is built; the wrong one runs half the time.
- **GraphRAG on a flat corpus.** The graph is a wiring diagram with no signal.
- **Text-to-SQL with write access.** Defence in depth missing.
- **Long-context without caching.** The bill quintuples.
- **No per-pipeline eval set.** You cannot tell which technique is helping.

---

## Further reading

- Edge, D. *et al.*, *"From Local to Global: A Graph RAG Approach to Query-Focused Summarization"* (Microsoft Research, 2024) — the GraphRAG paper.
- Khattab, O. & Zaharia, M., *"ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT"* (2020).
- Santhanam, K. *et al.*, *"ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction"* (2022).
- Pourreza, M. & Rafiei, D., *"DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction"* (2023).
- Anthropic Engineering, *"Long context prompting for Claude 2.1"* (2023) — long-context routing in practice.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 19 — Long context vs RAG](../19-long-context-vs-rag/index.md)** — making the long-context route affordable, and when to fall back to RAG.
- **[Post 16 — Evaluation](../16-evaluation/index.md)** — the per-pipeline eval harness.
- **[Post 19 — Long context vs RAG](../19-long-context-vs-rag/index.md)** — when the router gets to choose "just send the whole document".
