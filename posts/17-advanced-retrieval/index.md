# 17 · Advanced retrieval

> **TL;DR.** Standard hybrid-RAG (retrieval-augmented generation; see [Post 11](../11-rag-in-depth/index.md)) handles the large majority of production retrieval needs. The remainder, corpora with rich relationships, queries that span multiple documents, structured data, very-long-context single sources, are where the **advanced** techniques earn their cost. This post covers the four that recur in production: **GraphRAG**, **late-interaction retrieval (ColBERT)**, **structured / SQL retrieval**, and **long-context routing**. Each comes with its sweet spot and its overhead. Query-side patterns (query rewriting, HyDE, multi-query) live in [Post 11](../11-rag-in-depth/index.md); this post is the corpus-shape half.
>
> **After reading this you will be able to:**
> - Recognise the corpus shapes that defeat vanilla RAG.
> - Pick the right advanced technique for each shape.
> - Estimate the engineering and inference-cost overhead before committing.

![A router diagram: a query enters a small classifier that branches to text-to-SQL, GraphRAG, late-interaction ColBERT retrieval, long-context load, and standard hybrid RAG, each selected by the shape of the question.](diagrams/00-hero-advanced-retrieval.svg)
*Advanced retrieval is mostly routing: send each query to the retriever its shape demands.*

---

## 1. When standard RAG hits its ceiling

Vanilla RAG (chunk, embed, hybrid retrieve, rerank, pack) handles factoid questions over collections of independent documents extremely well. As a rule of thumb it covers most production retrieval needs, and the advanced techniques below earn their keep on the residue. (The exact split is illustrative and depends entirely on your corpus and query mix.) ![Four question shapes vanilla RAG cannot serve, each with an example, why it fails, and the technique it needs](diagrams/01-four-ceilings.svg)

*The hero shows the router from the technique side. This is the same picture from the problem side.*

It runs into trouble in four recurring shapes:

1. **Multi-hop questions.** *"Which suppliers are downstream of vendors that failed our 2024 audit?"* The answer requires *joining* facts from multiple documents; no single chunk contains it.
2. **Long-document questions.** *"Summarise the key risks raised in this 200-page filing."* The answer needs the *whole* document, not the best 5 chunks.
3. **Structured-data questions.** *"How many tickets did the Bangalore team close last quarter?"* The data is in a table; embeddings are the wrong tool.
4. **Domain corpora with rare exact terms.** A question about a specific gene, SKU, contract id, or Sanskrit term where the embedding model has never seen the token.

Each of these has a specialised technique. None of them replace vanilla RAG; they augment it. A serious production system has a *router* that picks the technique by query type.

This post deliberately covers *corpus-shape* techniques. The complementary *query-shape* patterns, query rewriting, decomposition, HyDE, and the iterative agentic loops (Self-RAG, Corrective RAG), are covered on the query side of the pipeline in [Post 11](../11-rag-in-depth/index.md); the two halves compose.

---

## 2. GraphRAG: when the corpus has structure

**The problem.** A corpus of company filings, internal wiki pages, or a research literature where the answer to many questions is a *path* through related entities. Vanilla retrieval pulls the right *nodes* but not the *edges*; the model gets isolated facts and cannot synthesise.

**The technique.** Build a knowledge graph from the corpus offline. Entities (companies, people, products, concepts) become nodes; mentions, ownership, references become edges. At retrieval time, the query is parsed for entities; the graph is traversed *N* hops from each entity; the relevant subgraph (plus the source chunks for each edge) is packed into the prompt. Hop depth is the main cost/quality knob: most systems traverse only one or two hops, because each extra hop expands the subgraph roughly by the average node degree, and an unbounded traversal quickly blows the token budget on a densely connected graph.

**What works in practice.** Microsoft Research's GraphRAG (Edge et al., 2024) is the most widely cited reference implementation. The key engineering choice is the *entity-extraction quality*: the graph is only as good as the upstream entity recognition. Edge et al. report that their graph approach substantially improves the comprehensiveness and diversity of answers to global, query-focused summarisation questions over vanilla vector RAG; treat any specific percentage lift you see quoted as workload-dependent rather than a fixed number.

**Cost.** Significant. The offline graph build is a one-off LLM-heavy pass over the entire corpus, and for that reason it typically costs several times more than plain embedding (illustrative: a small multiple, not a fixed factor). The online retrieval adds a graph traversal step. The win is large where the corpus has real structure; the loss is large where the corpus is just a pile of independent documents, and a month of graph engineering buys nothing.

**When to use.** Multi-hop questions are a meaningful fraction of the traffic; the corpus has named entities the questions reference; the offline build is affordable.

---

## 3. Late-interaction retrieval: when chunks are not the right unit

**The problem.** Bi-encoder retrieval (the standard: one neural encoder embeds the chunk and query independently into single vectors, introduced in [Post 09](../09-select-strategies/index.md)) embeds the entire chunk into one vector. The query also collapses to one vector. The match is a single dot product. Information about *which tokens* in the chunk match *which tokens* in the query is lost. This loses recall on questions where the answer-bearing span is small relative to the chunk.

**The technique.** **ColBERT** (Khattab & Zaharia, 2020) and its successors keep one vector *per token* in both the chunk and the query, then score by **sum-of-max similarity** (called MaxSim) at retrieval time. Concretely: for each *query* token, take the maximum similarity against every token in the candidate chunk (the best single match that query token finds anywhere in the chunk), then sum those per-token maxima across the query. A single-vector bi-encoder instead compares one averaged chunk vector to one averaged query vector, so a strong match on one rare term can be washed out by the rest of the chunk; MaxSim rewards it. The newer **ColBERTv2** (Santhanam et al., 2022) and **JaColBERT** variants are practical at scale.

**What works in practice.** ColBERT-style retrievers consistently win on benchmarks where the relevant span is short (definitional questions, exact-phrase lookups, technical terminology). Over a well-tuned bi-encoder followed by a cross-encoder rerank (a heavier model that scores each query-chunk *pair* jointly, from [Post 09](../09-select-strategies/index.md)), the marginal lift on general factoid retrieval tends to be modest and can be larger on technical corpora with rare exact terms; measure it on your own gold set rather than trusting a headline number, since results vary widely by domain.

**Cost.** Storing one vector per token rather than one per chunk multiplies index size by roughly the average tokens-per-chunk (illustrative: one to two orders of magnitude, not a fixed factor), and retrieval latency grows with it. Mitigations exist (PLAID, an optimised late-interaction engine; plus vector compression) but the engineering complexity is real. Treat ColBERT as a target for the next iteration, not as the default first build.

**When to use.** Technical or domain-specific corpora; queries with rare exact tokens; a sub-second latency budget that can absorb the extra retrieval cost; a team that has already shipped a vanilla pipeline and is hunting for the next increment of recall.

---

## 4. Structured / SQL retrieval: when the data is a table

**The problem.** "How many enterprise customers in EMEA churned last quarter?" The data is in a database. Embedding individual rows and retrieving by similarity is the *wrong tool*; SQL is the right one.

**The technique.** **Text-to-SQL.** A small LLM call translates the user's natural-language question into a SQL query against a known schema; the application executes the query; the result rows are formatted and returned to the user (optionally also packed into the main agent's context).

**What works in practice.** The pattern that consistently outperforms naïve text-to-SQL:

1. **Schema-aware prompt.** The translation prompt includes only the *tables and columns relevant to this query*, retrieved by (yes) RAG over a schema documentation corpus. A schema with 500 tables overwhelms the LLM if all of it goes in the prompt.
2. **Few-shot examples.** Two or three (question → SQL) pairs that look like this query, retrieved from a curated bank.
3. **Validation pass.** The generated SQL is parsed (not executed) and checked against the schema; errors are fed back to the LLM for one repair attempt.
4. **Read-only execution role.** The SQL runs as a database user that *cannot write*. Defence in depth against an injection attack via the model.

**Cost.** Modest. One LLM call for translation, one for any repair. The latency is dominated by the SQL execution. The main risk is *correctness* on complex joins; production systems use a **router** that sends ambiguous or complex queries to a human-curated query template instead of free-form translation.

**When to use.** Any time the underlying answer source is structured. The single most-skipped advanced technique; teams reach for vector RAG over what was always a SQL question.

---

## 5. Long-context routing: when the model can hold the whole document

**The problem.** A 50-page contract. The user asks "summarise the risks" and "what is the termination notice period". One question wants *all* the document; the other wants *one paragraph*. Retrieval is wrong for the first; loading the whole document is wasteful for the second.

**The technique.** **Route by query type.** A small classifier, itself an LLM call with a short rubric, labels the query as `whole_document` or `local_lookup`. Whole-document queries load the full source (within budget) and skip retrieval. Local-lookup queries go through the standard RAG pipeline.

**What works in practice.** The classifier is the entire engineering surface. A two-shot rubric ("global if the answer requires the entire document; local if a single paragraph would suffice") is usually enough to route the great majority of queries correctly; the exact hit rate depends on your query distribution, so treat any percentage as illustrative and measure it against a gold set. Hybrid handling for the unsure cases: load the document *and* run RAG, pack the top RAG chunks (top-k, the k highest-scoring retrieved chunks) as a "table of contents" before the full document.

The trick that makes this affordable is **prompt caching** ([Post 14](../14-system-prompt-as-software/index.md), §5). A 50-page document loaded into context costs full price on the first (cache-write) call; on subsequent cache hits, an Anthropic cache read is billed at roughly 10 % of the base input price (Anthropic, "Prompt caching"; see [Post 04](../04-tokens-windows-budgets/index.md)). Cache pricing is provider- and time-specific, so check the vendor's page. Many production assistants for long-document review now keep the document cached for the duration of the session and route every query through the same prefix.

**Cost.** Highest *per-call* of the techniques in this post (the long context is paid for in full on the cache miss). Lowest *engineering* overhead: most teams can ship this in a day. Choose when latency budget allows the larger calls and the corpus is genuinely document-shaped.

---

## 6. The router

![The four techniques compared on what they fix, offline cost, online cost, engineering overhead, and when to ship](diagrams/02-technique-costs.svg)

*Lined up, three of the four are visibly not first builds, and the cheapest one is the one teams skip.*

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

The router is two things: a small LLM classifier (or a rules engine, if the categories are clear) and an orchestrator that dispatches to the right pipeline. The end-to-end answer-quality lift from getting routing right is often larger than any single technique improvement, because the *wrong* technique on the *wrong* query is not just suboptimal; it is the difference between an answer and "I could not find that".

---

## 7. What *not* to do

A short, opinionated list.

- **Replace standard RAG with GraphRAG everywhere.** GraphRAG on a flat corpus is engineering overhead with no payoff.
- **Reach for ColBERT before fixing chunking.** The extra index and retrieval cost rarely beats a chunker pass that captures the right span in the first place.
- **Try to text-to-SQL a 500-table warehouse without schema retrieval.** The LLM cannot pick the right tables from a schema dump that is tens of thousands of tokens long.
- **Load every long document into context.** Cache helps but cannot rescue a workload of 200 different long documents.
- **Skip the router.** Without it the team builds three pipelines and uses the wrong one half the time.

---

## 8. The shape of a production retrieval stack

A reference assembly, useful as a sanity check against a real system.

| Stage | Technology | Role |
|---|---|---|
| Router | LLM classifier (small) | Picks the pipeline |
| Standard RAG | Hybrid (dense embeddings + BM25 keyword scoring + metadata filter) → cross-encoder rerank → packed with citations | Default |

(BM25 is the classic keyword-ranking function that scores documents by term frequency and rarity; it and the dense/cross-encoder terms are introduced in [Post 09](../09-select-strategies/index.md).)
| GraphRAG | Entity extraction → knowledge graph → traversal | Multi-hop questions |
| Text-to-SQL | Schema retrieval → SQL generation → validation → read-only execution | Structured queries |
| Long-context | Long-context model + prompt caching | Whole-document queries |
| Eval harness | Gold question set per pipeline | Regression gate in CI |

The total picture is more elaborate than vanilla RAG; the gain over vanilla RAG on a real production workload is usually large. Build it incrementally: vanilla first, eval harness, then add the routes one at a time as the unanswered-questions metric tells you which route is missing.

---

## Common pitfalls

- **Reaching for advanced techniques before standard RAG is well-tuned.** Most "we need GraphRAG" reflexes come from skipping reranking.
- **No router.** Each pipeline is built; the wrong one runs half the time.
- **GraphRAG on a flat corpus.** The graph is a wiring diagram with no signal.
- **Text-to-SQL with write access.** Defence in depth missing.
- **Long-context without caching.** Every repeat query re-pays for the full document, so the bill balloons.
- **No per-pipeline eval set.** There is no way to tell which technique is helping.

---

## Further reading

- Edge, D. *et al.*, *"From Local to Global: A Graph RAG Approach to Query-Focused Summarization"* (Microsoft Research, 2024): the GraphRAG paper.
- Khattab, O. & Zaharia, M., *"ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT"* (2020): the late-interaction / MaxSim formulation.
- Santhanam, K. *et al.*, *"ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction"* (2022): compression plus the PLAID engine.
- Clavié, B., *"JaColBERT and Hard Negatives"* (2023): a practical ColBERT variant at scale.
- Pourreza, M. & Rafiei, D., *"DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction"* (2023).
- Anthropic, *"Prompt caching"* (documentation, 2024–25): the cache-read discount used by the long-context route.
- Anthropic Engineering, *"Long context prompting for Claude 2.1"* (2023): early long-context routing guidance; the mechanics still apply to current 200k–1M-token models.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 25 — Long context vs RAG](../25-long-context-vs-rag/index.md)**: making the long-context route affordable, when the router gets to choose "just send the whole document", and when to fall back to RAG.
- **[Post 20 — Evaluation](../20-evaluation/index.md)**: the per-pipeline eval harness.
- **[Post 11 — RAG in depth](../11-rag-in-depth/index.md)** (back): the vanilla pipeline and the query-side patterns (rewriting, HyDE, multi-query) these techniques build on.
