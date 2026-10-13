# 17 - Advanced retrieval

> **TL;DR.** Hybrid retrieval-augmented generation (RAG), as [post 11](../11-rag-in-depth/index.md) builds it, answers a question from a few passages. Four shapes of question defeat it: multi-hop, whole-document, tabular, and those that hinge on a rare exact term. Each has its own technique (GraphRAG, long-context loading, text-to-SQL, late interaction) and its own cost, and a small router sends each question to the one its shape needs, with hybrid RAG as the default.
>
> **Prerequisites:** [Post 11](../11-rag-in-depth/index.md).
> **Safe to skip?** Skip it if failing questions can already be sorted by shape and routed to their technique, with each technique's cost estimated first.
>
> **After reading, you will be able to:**
>
> - Recognise the four question shapes that defeat hybrid RAG: multi-hop, whole document, structured data and rare exact terms.
> - Pick GraphRAG, late interaction, text-to-SQL or long-context loading for each shape, and say why hybrid RAG fails there.
> - Compute a MaxSim score from token similarities and explain why it keeps a rare-term match that one pooled vector loses.
> - Estimate a technique's overhead before committing to it: offline build calls, index size, and tokens and dollars per question.
> - Design a router that sends each question to its technique, with hybrid RAG as the default and a labelled set to catch misroutes.

![A router sends multi-hop questions to GraphRAG, whole-document ones to a long-context load, structured ones to text-to-SQL, rare exact identifiers to late interaction, and the rest to hybrid RAG; every route fills layer 04.](diagrams/00-hero-router.svg)

*Advanced retrieval is mostly routing: each question goes to the retriever its shape needs, and everything else stays on hybrid RAG.*

---

## 1. The question: which questions defeat hybrid RAG?

[Post 11](../11-rag-in-depth/index.md) built the standard pipeline: chunk, add context and index offline; rewrite the query, fuse dense and BM25 (Best Matching 25, a keyword ranking function) candidates by reciprocal rank fusion (RRF), rerank, and pack the top-k into layer 04, retrieved chunks. It answers a question whose answer sits in one or two passages that resemble the question.

This post asks which questions that pipeline cannot answer however well it is tuned, and which technique serves each at what cost. All four techniques are still the select operation of [post 07](../07-write-select-compress-isolate/index.md), filling layer 04 for one call; what changes is the unit retrieved (a path, a row, a document, a token). The figure at the top of the post is the answer in one picture.

The query-side patterns (rewriting, HyDE, decomposition) are in [post 09](../09-select-strategies/index.md), section 2. Loops in which the model decides when to retrieve and grades the results, such as Self-RAG (Asai et al., 2023) and Corrective RAG (Yan et al., 2024), are named here, not taught; they wrap any retriever below.

---

## 2. Four shapes, four ceilings

A ceiling is a limit no tuning of the default pipeline removes, because the answer is not the kind of thing it returns:

| Shape | Example question | Why hybrid RAG fails | Technique |
|---|---|---|---|
| Multi-hop | "Which suppliers are downstream of vendors that failed our 2024 audit?" | The documents holding the second fact never mention the first | GraphRAG |
| Whole document | "Summarise the key risks raised in this 200-page filing." | The answer needs all of it, not the best five chunks | Long-context load |
| Structured data | "How many tickets did the Bangalore team close last quarter?" | A count over rows is computed, not found in a passage | Text-to-SQL |
| Rare exact term | "What does error E-4012 mean when exporting invoices?" | One pooled vector per chunk washes out a match on one rare token | Late interaction |

None of the four replaces the default, and only a labelled sample of real questions says how much traffic each shape takes. A useful exercise: twelve questions, three per shape, run through hybrid RAG, with the failures routed to their technique; sections 3, 4 and 7 do it at toy scale.

---

## 3. GraphRAG: when the answer is a path

**The ceiling.** The multi-hop question needs two facts: which vendors failed the audit, and who buys from them. The second sits in documents that never mention the audit, and each document is scored against the question alone.

**The technique.** Offline, a model extracts entities as nodes and relations (supplies, owns, cites) as edges from each chunk, each edge keeping its source chunk. At query time the graph is walked a fixed number of hops from the entities in the question or the first documents retrieved, and the chunks behind the edges walked are packed into layer 04. The snippet `snippets/two_hop.py` runs this on an eight-document toy corpus, with a regular expression standing in for the extraction call:

```text
single hop   packed d1, d2, d7   recall 0.00
two-step     packed d1, d4, d3   recall 1.00   (second query: Acme Metals Borealis Plastics)
graph        packed d1, d3, d4   recall 1.00
```

Single-hop BM25 packs the audit report and two documents that share its words, and neither buyer; the graph walks from the two failed vendors to their buyers, as the figure below draws.

![Single hop packs d1, d2 and d7, recall 0.00. The graph starts from the failed vendors named in d1 and walks one hop to Corvid Tools (d3) and Delta Assembly (d4), recall 1.00.](diagrams/01-two-hop.svg)

*The buyer documents never mention the audit, so no score against the question finds them; one hop along an extracted edge does.*

The two-step run is the other fix: read the vendor names from the first document and retrieve again with them (post 09's decomposition). One bridge needs no graph; a graph pays where the same relations are asked repeatedly, or a chain is too long to follow one query at a time.

**Hop depth is the cost dial.** Each hop multiplies what is reached by roughly the links per entity: on a synthetic graph of 2,000 entities with four links each, the snippet reaches 4 entities within one hop, 20 within two, 82 within three and 308 within four, each bringing its source chunks into layer 04. Walking further than the question needs packs relations nobody asked about, the distraction failure mode of [post 06](../06-context-failure-modes/index.md).

**What Edge et al. measured.** Microsoft Research's GraphRAG (Edge et al., "From Local to Global", arXiv v2, February 2025) also groups related entities into communities, pre-writes a summary of each, and answers a global question ("what are the main themes?") by combining partial answers from every summary. On corpora of about 1 million and 1.7 million tokens, in 600-token chunks with 100-token overlap, pairwise comparisons judged by a model gave the global approaches win rates over vector RAG of 72 to 83% (podcast transcripts) and 72 to 80% (news articles) for comprehensiveness, and 75 to 82% and 62 to 71% for diversity. Vector RAG gave the most direct answers, and answering from the top-level summaries took over 97% fewer tokens than summarising the source text. These are numbers for global questions; a factoid lookup stays on the default.

**Cost.** A model call per chunk offline, plus the summaries, repeated as the corpus changes; section 8 prices it. A relation the extraction missed is an edge no walk can take. Memory stores face the same choice: [post 16](../16-memory-systems/index.md) covers Zep's temporal knowledge graph (Rasmussen et al., 2025).

---

## 4. Late interaction: when one rare token decides

**The ceiling.** A bi-encoder, the dense half of hybrid retrieval ([post 09](../09-select-strategies/index.md)), embeds a chunk into one vector and the query into another and scores their similarity. Pooling averages away which token matched which. When the answer turns on one rare token (an error code, a part number, a gene name) inside a chunk about other things, a generic chunk that matches the query's common words can score higher. BM25 helps only when the corpus spells the term exactly as the query does.

**The technique.** ColBERT (Khattab and Zaharia, SIGIR 2020) keeps one vector per token for query and document and scores them with MaxSim: for each query token, its highest similarity to any document token, summed over the query, $s(q, d) = \sum_i \max_j \mathbf{q}_i \cdot \mathbf{d}_j$. A strong match on one rare token counts in full however long the chunk is. The snippet `snippets/maxsim.py` computes it on hand-written token vectors:

```python
def maxsim(query, doc):
    """Late interaction: each query token keeps its best match anywhere in the document; the maxima add up."""
    return sum(max(dot(VEC[q], VEC[d]) for d in doc) for q in query)
```

For the query "fix error E-4012" against chunk A, an eight-token sentence that holds the answer, and chunk B, a generic page on fixing error messages, it prints:

```text
score            single vector   MaxSim
A                         0.51     2.43
B                         0.55     2.28
single vector ranks B first; MaxSim ranks A first
```

The figure below shows where the difference comes from.

![Similarity grids of the query tokens against each chunk, row maxima outlined. Chunk A: maxima 0.45, 0.98, 1.00, MaxSim 2.43, single vector 0.51. Chunk B: maxima 1.00, 1.00, 0.28, MaxSim 2.28, single vector 0.55.](diagrams/02-maxsim.svg)

*Chunk B wins on the two common words; chunk A's exact match on E-4012 counts in full under MaxSim and decides the ranking.*

B matches "fix" and "error" exactly but E-4012 at best 0.28; A matches E-4012 exactly and "error" through "stops" (0.98). Pooling hides that. The vectors are toy ones; on a real corpus the effect is measured on its golden set.

**What the papers measured.** On the MS MARCO passage-ranking development set, ColBERT reranking BM25's top 1,000 scored an MRR@10 (mean reciprocal rank of the first relevant passage in the top 10) of 34.9 against 34.7 and 36.0 for two BERT-base cross-encoders, at 61 milliseconds against 10,700 per query (Khattab and Zaharia, Table 1). The price is storage. ColBERTv2 (Santhanam et al., NAACL 2022) compresses each 256-byte vector to 20 or 36 bytes, shrinking the MS MARCO index from 154 GiB to 16 or 25 GiB, and the PLAID engine (Santhanam et al., CIKM 2022) cuts its search latency by up to 7 times on a GPU and 45 times on a CPU.

**When to use it.** A technical corpus whose rare-term questions still fail after the default is tuned. Fix chunking first: a short chunk around the answer-bearing span removes much of the pooling problem.

---

## 5. Structured retrieval: when the data is a table

**The ceiling.** "How many enterprise customers in Europe, the Middle East and Africa (EMEA) churned last quarter?" is answered by counting rows. The nearest few rows need not include every qualifying one, and the model counts what it is shown.

**The technique.** Text-to-SQL: a model call translates the question into SQL (Structured Query Language) against a known schema, the application runs it, and the result rows go into layer 04. Four practices make it dependable:

1. **Retrieve the schema.** The prompt holds only the tables relevant to this question, found by retrieval over schema descriptions. A 500-table warehouse at 60 tokens a table (illustrative sizes) is 30,000 tokens of mostly irrelevant schema per call.
2. **A few worked examples.** Two or three pairs of question and SQL resembling this one, picked as post 09 picks few-shot examples.
3. **Validate before running.** The SQL is parsed and checked against the schema; an error goes back to the model for one repair.
4. **Run it read-only.** A database user that cannot write turns an injected `DROP TABLE` into an error ([post 23](../23-security/index.md) covers prompt injection).

**What the paper measured.** DIN-SQL (Pourreza and Rafiei, NeurIPS 2023) splits translation into schema linking, classification by complexity, generation and self-correction. It reports execution accuracy of 85.3% on the Spider holdout test set, against a previous best of 79.9%, and 55.9% on BIRD's, and that decomposition improved few-shot performance by roughly 10%. Schema linking is practice 1 under another name.

**Cost and risk.** One call per question, a second for a repair, and the query's run time. The risk is a wrong query returning a plausible number, so high-stakes questions can go to a human-written template. Its only offline build is the schema descriptions.

---

## 6. Long-context routing: when the question needs the whole document

**The ceiling.** A 50-page contract is asked "summarise the risks" and "what is the termination notice period?". Five chunks give the summary five fragments; loading all 50 pages for the notice period pays for the whole to read one clause.

**The technique.** Route by question type: a rule or a short model call labels each question whole-document or local. Whole-document questions load the full source into layer 04 and skip retrieval; local ones take the default pipeline. Google's "Long context" page for the Gemini API (last updated 22 June 2026, consulted October 2026) notes windows of "1 million or more tokens", advises putting the query at the end, as this series places layer 06, the user instruction, and warns that accuracy is lower when several pieces of information must be found. A window that holds a document does not guarantee the model uses all of it ([post 06](../06-context-failure-modes/index.md)).

**Caching makes it affordable.** A document unchanged across a session goes at the front of layer 04, so the prefix up to and including it is identical on every call and can be cached ([post 05](../05-economics-of-context/index.md)). On Claude Sonnet 4.5 at 3 dollars per million input tokens as of early 2026 (Anthropic, "Pricing" and "Prompt caching", consulted October 2026), a five-minute cache write costs 1.25 times the input price and a read 0.1 times, the rate for most models. For the contract at an illustrative 500 tokens a page, 25,000 tokens, the first call pays $25{,}000 \times 3 \times 1.25 / 10^6 = 0.09375$ dollars for the document and each later read $25{,}000 \times 3 \times 0.1 / 10^6 = 0.0075$, against 0.075 uncached.

**When to use it.** The questions need whole documents, the document fits with room to spare, and it is asked about often enough to stay cached; many documents each asked about once get no cache reads.

---

## 7. The router

The router picks one retriever per question, with hybrid RAG as the fall-through. Its classifier is rules where the shapes are crisp, or a small model call with a rubric (one line and one example per route) where they are not. The snippet `snippets/router.py` is the rule version:

```python
RULES = [  # (shape, pattern), checked in this order; the first match wins
    ("rare exact term", r"\b[A-Z]{1,4}-?\d{3,}\b"),
    ("structured", r"(?i)\b(how many|average|total|count of|per region|per month)\b"),
    ("multi-hop", r"(?i)\b(downstream|upstream|depend on|maintained by|who manages|managed by)\b"),
    ("whole document", r"(?i)\b(summari[sz]e|main themes|key risks|whole|from start to end)\b"),
]
```

It routes fifteen labelled questions, three per shape and three ordinary lookups, and ends:

```text
15  local lookup      text-to-SQL        How many days of notice does the termination clause require?   <- misrouted

routed as labelled: 14 of 15
questions per route: late interaction 3, text-to-SQL 4, GraphRAG 3, long-context load 3, hybrid RAG 2
```

"How many" signals a count over rows in questions 7 and 9, but in question 15 it asks for one number in one clause, a local lookup. The rules were written with these questions in view, so 14 of 15 overstates their accuracy on new traffic. A router is evaluated like any component ([post 20](../20-evaluation/index.md)): labelled real questions, routing accuracy, and each misroute read.

A wrong route costs more than a weaker answer: a count sent to vector search returns a confident number from whatever rows were retrieved, and a multi-hop question sent to the default returns "I could not find that" with the answer one hop away.

---

## 8. Estimating the overhead before committing

Each cost's order of magnitude can be estimated before anything is built. The snippet `snippets/route_costs.py` uses cited rates (Claude Sonnet 4.5 at 3 dollars per million input tokens and 15 per million output, as of early 2026; section 6's cache multipliers; 256 and 36 bytes per ColBERT and ColBERTv2 vector; GraphRAG's chunking) and the snippet's illustrative sizes, with a 1,000,000-token corpus. It prices only the retrieved material and the calls a route adds:

```text
dollars per question, retrieved material only (Claude Sonnet 4.5, as of early 2026)
  hybrid RAG     2,000 tokens        0.00600
  long context   25,000 tokens       uncached 0.07500, write 0.09375, read 0.00750
  text-to-SQL    one call 0.00870, with a repair 0.01740; full schema 0.09000
  10 questions   RAG 0.06000; long context uncached 0.75000, cached 0.16125
offline, 1,000,000-token corpus
  GraphRAG       2,000 extraction calls, 18.60 dollars (summaries not included)
  index          per chunk 7.68 MB; per token: ColBERT 256 MB (33.3 times), ColBERTv2 36 MB (4.7 times)
```

The figure below lays the routes side by side.

![A table of five routes, offline work and cost per question at illustrative sizes: hybrid RAG 7.68 MB, 0.006 dollars; GraphRAG 18.60 dollars of extraction; late interaction 256 MB or 36 MB; text-to-SQL 0.0087 dollars a call; long context 0.075 dollars uncached, 0.0075 cached.](diagrams/03-route-costs.svg)

*Every number is computed at stated sizes; whether a cost falls offline or on every question is what carries over to a real system.*

Uncached, the long-context route costs most per question; cached, a ten-question session costs 0.16125 dollars against 0.06 for RAG and 0.75 uncached. Text-to-SQL is cheap only with schema retrieval: the full schema alone costs more per call than the uncached contract. And the offline costs differ in kind: GraphRAG's is model calls, repeated as the corpus changes; late interaction's is storage, 33 times the single-vector index, or about 5 times compressed.

---

## 9. The shape of a production retrieval stack

A stack that serves all four shapes, in the order it is built:

| Stage | Built from | Serves |
|---|---|---|
| Default | Hybrid retrieval, RRF, reranking, citations | Every question no route claims |
| Evaluation | A golden set per route and a routing set | Every change, as a regression gate |
| Router | Rules or a small model call | Picks the route |
| Text-to-SQL | Schema retrieval, generation, validation, read-only run | Structured questions |
| Long-context load | A long-context model and prompt caching | Whole-document questions |
| GraphRAG | Extraction, a graph, a bounded walk | Multi-hop and global questions |
| Late interaction | A per-token index (ColBERTv2 with PLAID) | Rare exact terms |

Routes are added in the order the unanswered questions demand, cheapest first. Every route writes into layer 04, so post 09's packing rules (budget, bookend order, citation headers) apply to rows, subgraphs and documents too.

---

## 10. Make it run

The four snippets use the standard library only and each runs from the series root in under a second:

```text
uv run python posts/17-advanced-retrieval/snippets/two_hop.py
uv run python posts/17-advanced-retrieval/snippets/maxsim.py
uv run python posts/17-advanced-retrieval/snippets/router.py
uv run python posts/17-advanced-retrieval/snippets/route_costs.py
```

Adding a question to `QUESTIONS` in `router.py`, or changing a size in `route_costs.py`, shows which route or cost moves.

---

## 11. What can go wrong?

- **GraphRAG over a flat corpus.** Independent FAQ pages are built into a graph with few relations that questions follow; the answers match the default's.
- **An unbounded walk.** Hop depth is left open "to be safe"; layer 04 fills with unasked relations and answers drift.
- **Late interaction before chunking is fixed.** A per-token index is built for questions whose answer was split across two chunks; storage grows by an order of magnitude and the fact is still split.
- **A schema dump and write access.** The whole schema goes into every prompt, the model picks plausible wrong tables, and the query runs as a user that could drop one.
- **Long context without a stable prefix.** A timestamp or the question sits before the document, the prefix changes on every call, and every question pays the cache write.

---

## Common pitfalls

1. **Reaching for an advanced technique before the default is tuned.** A "we need GraphRAG" request can be a missing reranker or a poor chunker.
2. **No router.** Three pipelines get built and each question still goes to the default.
3. **Sending table questions to a vector index.** A count needs a database query, not the nearest rows.
4. **Long context without caching.** Every repeat question pays for the whole document again.
5. **One score for every route.** A drop cannot be traced to the router or to one route without a labelled set per route.

---

## Further reading

- Edge, D. *et al.*, *"From Local to Global: A Graph RAG Approach to Query-Focused Summarization"* (Microsoft Research, arXiv 2024, v2 2025).
- Khattab, O. and Zaharia, M., *"ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT"* (SIGIR 2020).
- Santhanam, K. *et al.*, *"ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction"* (NAACL 2022), and *"PLAID: An Efficient Engine for Late Interaction Retrieval"* (CIKM 2022).
- Pourreza, M. and Rafiei, D., *"DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction"* (NeurIPS 2023).
- Google, *"Long context"* (Gemini API documentation, consulted October 2026).
- Anthropic, *"Long context prompting for Claude 2.1"* (December 2023): one sentence added to the start of the answer raised a needle-in-a-haystack score from 27% to 98%.
- Asai, A. *et al.*, *"Self-RAG"* (2023), and Yan, S.-Q. *et al.*, *"Corrective Retrieval Augmented Generation"* (2024).

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 18 - Context for reasoning models](../18-reasoning-model-context/index.md):** how thinking tokens change the budget that every route here fills.
- **[Post 25 - Long context vs. RAG: a decision framework](../25-long-context-vs-rag/index.md):** the long-context route of section 6 grown into a full decision, with the benchmarks behind it.
