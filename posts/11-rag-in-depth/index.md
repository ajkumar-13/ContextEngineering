# 11 - RAG in depth

> **TL;DR.** Retrieval-augmented generation (RAG) is the select operation of [post 09](../09-select-strategies/index.md) run over documents, and it fills layer 04, retrieved chunks. The gap between a demo and a production system is mostly a handful of choices: chunks that keep each fact whole, contextual retrieval, hybrid search fused by reciprocal rank fusion, a cross-encoder reranker, a prompt that demands citations, and an evaluation harness that says whether a change helped. The offline half sets the ceiling on quality; the online half decides how close each answer gets.
>
> **Prerequisites:** [Post 09](../09-select-strategies/index.md), [Post 10](../10-data-ingestion-pipelines/index.md).
> **Safe to skip?** Skip it if a RAG pipeline can already be built and debugged stage by stage, with contextual chunk headers, fused hybrid retrieval, reranking, cited answers and a regression gate.
>
> **After reading, you will be able to:**
>
> - Walk through every stage of a production RAG pipeline, offline and online, and name what fails at each.
> - Choose a splitter family, a chunk size and an overlap, and check that chunking keeps every fact whole.
> - Apply contextual retrieval, hybrid search with reciprocal rank fusion, and cross-encoder reranking, and say what each fixes.
> - Wire a minimum evaluation harness (golden set, recall@N, citation accuracy, answer correctness, regression gate) and read whether a change helped.
> - Decide when RAG is the wrong tool: a corpus that fits the window, a task that needs all of it, or data in tables.

![Two lanes. Offline: documents, chunk, add context, embed and index, into an index of chunks and a manifest. Online: query, candidates (top-50), re-rank (top-5), pack into 04 Retrieved chunks, then the model, with three stages' metrics under them.](diagrams/00-hero-rag-pipeline.svg)

*The offline lane decides what any query can find; the online lane decides what this query does find. The metric under each stage says where to look when an answer is wrong.*

---

## 1. The question: what separates a demo RAG from a production one?

Retrieval-augmented generation was named by Lewis et al. (2020): retrieve passages relevant to a question at query time and give them to the model with it. In this series' terms RAG is the select operation of [post 09](../09-select-strategies/index.md) over a corpus of documents, and its output is layer 04, retrieved chunks. A first version, which embeds the documents and fetches the nearest few, takes an afternoon. This post asks which offline and online choices account for most of the gap between that demo and a system that holds up on real traffic.

Every RAG system has two halves, drawn in the figure above. The **offline** half runs once per document: chunk, add context, embed, index. It decides what any query can find, so it sets the ceiling. The **online** half runs on every user turn: construct the query, generate candidates, re-rank, pack, generate. It decides how close an answer gets to the ceiling.

---

## 2. Offline: chunking and contextual retrieval

A chunk is the unit retrieval returns. If a fact is cut in half, or buried in a chunk about something else, no later stage can recover it.

**Splitter family.** Three families, in order of preference:

1. **Structure-aware**: split on Markdown headings, HTML (HyperText Markup Language) sections, code symbols or PDF (Portable Document Format) pages. Best whenever the source has structure. For code, one function is one chunk, whatever its length.
2. **Sentence-aware**: group whole sentences under a token budget. The default for prose; LlamaIndex's `SentenceSplitter` is one implementation, the companion's `chunk` another.
3. **Fixed-length**: cut every *N* characters or tokens. The last resort, because it cuts sentences, and the facts in them, in half.

**Chunk size.** The series' starting default for prose is 400 to 600 tokens with 10 to 20 percent overlap ([post 09](../09-select-strategies/index.md)): illustrative values to tune with the harness of section 6, not measurements. Small chunks (100 to 200 tokens, illustrative) are precise but often not self-contained. Large ones (over 1,000 tokens, illustrative) fill layer 04 with paragraphs that touch the answer rather than carry it, the distraction failure mode of [post 06](../06-context-failure-modes/index.md).

**Overlap.** Adjacent chunks share their boundary sentences, so a fact on a boundary survives whole in at least one chunk, at the cost of a proportionally larger index.

The figure below runs both kinds of splitter over one 38-word section of the toy corpus that ships with this post. A fixed 30-word split cuts "8:00 to 18:00" in two; the companion's `chunk`, with a 30-word target and 8 words of overlap, keeps every sentence whole and repeats the second sentence in both chunks.

![A section of four sentences of 11, 10, 11 and 6 words, to scale. A fixed 30-word split cuts sentence 3 between 8:00 and to 18:00, marked in red. The sentence-aware chunker makes chunk 1 from sentences 1 and 2 (21 words) and chunk 2 from sentences 2 to 4 (27 words); sentence 2 is the overlap.](diagrams/01-chunking.svg)

*Same text, same budget: the fixed-length split breaks a fact; the sentence-aware split keeps every sentence whole and shares one across the boundary.*

**Parent-child and late chunking.** Parent-child retrieval searches small child chunks and hands the model the larger parent they belong to. Late chunking (Günther et al., 2024) embeds the whole document with a long-context model and only then pools the token embeddings into chunk vectors, so each vector reflects its neighbours. Both add complexity; they pay once plain chunking stops improving the golden set.

**Contextual retrieval.** Anthropic's "Introducing Contextual Retrieval" (September 2024) prepends "chunk-specific explanatory context to each chunk before embedding", and builds the keyword index over the same contextualised chunks. A model reads the whole document and one chunk and writes a sentence or two that situate the chunk, usually 50 to 100 tokens; the page puts the one-time cost at $1.02 per million document tokens with prompt caching, under its stated assumptions (800-token chunks, 8,000-token documents).

BM25 (Best Matching 25; Robertson and Zaragoza, 2009) is the classic lexical ranking function: it scores a chunk by the query words it contains, weighted by their rarity. The page measures the effect as the top-20 retrieval failure rate (1 minus recall@20, averaged over its four knowledge domains with its best embedding configuration): contextual embeddings cut it by 35% (5.7% to 3.7%), adding contextual BM25 by 49% (to 2.9%), and adding a reranker by 67% (to 1.9%). The figure below draws the page's example chunk and its numbers.

![Top, Anthropic's example chunk before and after a sentence naming the company and quarter is prepended. Bottom, cited from the page, the top-20 retrieval failure rate falling from 5.7% to 3.7% with contextual embeddings (minus 35%), to 2.9% with contextual BM25 (minus 49%), and to 1.9% with reranking (minus 67%).](diagrams/02-contextual-retrieval.svg)

*Every number is the page's own; each reduction is measured from the same 5.7% baseline, and the steps stack.*

Part of a header costs nothing: the document title and section path are known at ingest ([post 10](../10-data-ingestion-pipelines/index.md) records them as provenance). The toy snippet prepends that free part to each chunk and keeps a bare copy for comparison:

```python
chunks, headed = [], []
for doc, sections in CORPUS.items():
    for section, text in sections.items():
        for c in chunk(text, target_tokens=30, overlap_tokens=8):
            chunks.append(c.text)
            headed.append(f"[{doc} > {section}] {c.text}")
```

The model-written sentences need a model call per chunk, so the offline snippet leaves them out. Either way, the header is also what the prompt of section 5 shows the model, so one string serves retrieval and citation.

---

## 3. Offline: embedding model and index

**Embedding model.** Choose a kind before a name, because names turn over fast: a hosted general model (OpenAI's `text-embedding-3-small`), a hosted family with domain variants (Voyage AI's documentation, consulted October 2026, lists models for law, finance and code), or an open-weight model (BAAI's `bge-large-en-v1.5`). Shortlist from a current ranking such as the MTEB leaderboard (Massive Text Embedding Benchmark; Muennighoff et al., 2022), then decide on the golden set of section 6, because a leaderboard averages over tasks that are not this corpus. Where a specialised variant exists for the domain or language, try it first.

**Vector database.** In-process (Chroma, FAISS) for a prototype; `pgvector` on an existing Postgres for one production server; a dedicated store (Pinecone, Weaviate, Qdrant, Milvus) for many millions of vectors or many tenants (roughly ten million vectors and up, an illustrative threshold). Pick the lowest-burden option that meets the scale.

**Sparse index alongside.** A BM25 index over the same chunks (Elasticsearch, OpenSearch, or the companion's `BM25` class), because hybrid retrieval needs both rankings.

**Manifest table.** One row per source document: its hash, its chunk ids, the embedding-model version, the ingest time. Without it, "what changed in the index since last week?" has no answer. [Post 10](../10-data-ingestion-pipelines/index.md) shows how the hash drives incremental re-indexing.

---

## 4. Online: the four levers, recapped

[Post 09](../09-select-strategies/index.md) describes the online pipeline in full. In order, with the series' starting defaults (illustrative values to tune):

1. **Query.** Rewrite the user turn into a self-contained query; optionally embed a drafted answer instead (HyDE, hypothetical document embeddings; Gao et al., 2022) or issue a few paraphrases.
2. **Candidates.** Dense top-30 plus BM25 top-30 plus any metadata filter, merged by reciprocal rank fusion (RRF) into a top-50 candidate set.
3. **Re-rank.** A cross-encoder reads the query and each candidate together and scores the pair; keep the top-5. Cohere Rerank and Voyage AI's rerankers are hosted; BAAI's `bge-reranker-v2-m3` is open-weight.
4. **Pack.** Bookend layout (best first, second-best last; [post 06](../06-context-failure-modes/index.md)), drop near-duplicates, give each chunk a citation header, and keep to the budget of layer 04.

Top-5 is a starting point: Anthropic's tests passed the top 20 chunks and found 20 more effective than 10 or 5. The golden set decides. Three points are specific to RAG.

**The query must carry the conversation.** Embedded alone, "and the second one?" retrieves nothing useful; rewrite it from the last few turns.

**RRF takes ranks, not scores.** A candidate $d$ scores $\mathrm{RRF}(d) = \sum_i 1/(k + r_i(d))$ over the lists $i$ it appears in, where $r_i(d)$ is its rank in list $i$ and $k$ is a damping constant, 60 in Cormack et al. (2009) and unrelated to top-k. A cosine similarity and a BM25 score never have to share a scale, and the order in which lists are passed changes no score (the companion's `rrf` breaks exact ties by first appearance). The figure below fuses two rankings from the toy snippet, which uses a character-trigram ranker as an offline stand-in for the dense half.

![For a toy question, BM25 ranks chunk 2 first and chunk 0, which holds the answer, second; the trigram ranker ranks chunk 0 first. Summed RRF scores put chunk 0 first.](diagrams/03-rrf-fusion.svg)

*BM25's first chunk is not the answer; the answer's ranks of 2 and 1 beat ranks of 1 and 3, and no score is rescaled.*

**Re-ranking is this post's first online fix.** In Anthropic's numbers, a reranker on top of contextual embeddings and contextual BM25 took the failure rate from 2.9% to 1.9%, a further third, without touching the index.

---

## 5. Generation: what the prompt should look like

The model sees the packed chunks in layer 04, rules for using them in layer 01, the system prompt, and the question last, as layer 06, the user instruction. A skeleton, each part labelled with its layer:

```text
[layer 01, the system prompt]
Answer using only the sources given with the question.
1. If the answer is not in them, say
   "I could not find that in the provided sources."
2. After every claim, cite its source in brackets,
   e.g. [refunds-policy.md > Approval limits].
3. If two sources disagree, say so and cite both.

[layer 04, retrieved chunks]
[refunds-policy.md > Approval limits] Support agents can approve up to 1,000 dollars ...
[refunds-policy.md > Payment method] Card payments take five to ten business days ...

[layer 06, the user instruction]
Who signs off on a refund of 2,000 dollars?
```

The **"say so" rule** stops the model filling gaps from training. **Machine-parseable citations** let the application check that the cited chunk contains the claim, and show the source. The **disagreement rule** is a cheap defence against the conflict failure mode of [post 06](../06-context-failure-modes/index.md): it lets the reader see the clash.

---

## 6. Evaluation: the harness without which nothing improves

Every component change moves quality in some direction, and without measurement no one sees which. The minimum harness has three parts.

**A golden set.** Questions and answers written by people who know the domain, each with the passage the answer comes from; 50 to 200 pairs is a common start (illustrative). Size it with arithmetic: a score measured on $n$ questions estimates the score on all traffic with a standard error of $\sqrt{p(1-p)/n}$, which for $n = 100$ and $p = 0.8$ is 0.04, four percentage points. A 2-point drop on 100 questions cannot be told from noise; reading which questions flipped between two configurations is more sensitive than comparing their totals.

**Three metrics on every change.**

- **Recall@N** (retrieval): the share of questions whose gold passage is in the top-N candidates. Cheapest, and the ceiling on everything downstream; Anthropic's failure rate is 1 minus recall@20.
- **Citation accuracy** (retrieval to generation): does each cited chunk contain its claim? An LLM (large language model) judge can grade it when human labels on every run cost too much; ARES (Saad-Falcon et al., 2023) builds such judges.
- **Answer correctness** (end to end): does the answer agree with the gold answer? An LLM judge with a rubric, checked against human review on a sample.

**A regression gate in CI** (continuous integration): every change runs the harness, and a drop larger than the noise blocks the merge. [Post 20](../20-evaluation/index.md) builds the full harness.

The toy snippet is the harness in miniature: ten questions phrased as a user would type them, each with a phrase only its answer-bearing chunks contain, scored at recall@1 and recall@3 for five retrievers over 17 chunks. It prints:

```text
4 documents, 10 sections, 17 chunks
retriever                 recall@1  recall@3  missed at 3
BM25, bare chunks              0.6       0.9  6
BM25, headed chunks            0.6       0.9  6
trigram, bare chunks           0.6       0.7  4, 6, 7
trigram, headed chunks         0.7       0.9  7
RRF of the two, headed         0.7       0.9  6
```

The headers lift the trigram ranker from 0.7 to 0.9 at recall@3, because "Lost parcels" and "refunds-policy.md > Approval limits" give the answer chunks more of the query's trigrams. They do nothing for BM25, whose exact-word match does not connect "refund" with "refunds"; a stemmer would. Fusion ties for the best recall@1 but misses question 6 ("Can a big refund be approved on a Saturday?") at 3: its answer chunk says "Weekend requests wait" and shares no word with "Saturday", so only the header reaches it, and the fused list puts it fourth. Linking Saturday to weekend is what an embedding model is for. The toy's numbers say nothing about effect sizes on a real corpus; the habit of reading which questions each change won and lost is the point.

---

## 7. Where production RAG goes wrong

Common symptoms, each with the failure mode of [post 06](../06-context-failure-modes/index.md) it produces and its first fix:

| Symptom | Cause | Failure mode | First fix |
|---|---|---|---|
| Fluent, confident, off-topic answers | No reranker; near-miss chunks packed | Distraction | Add a cross-encoder; lower top-k |
| A 30-word answer inside a 1,500-token chunk (illustrative) | Chunks too big | Distraction | Smaller chunks, or parent-child |
| A question about one document answered from another | No metadata filter | Distraction | Filter by document, product or date |
| An outdated policy, cited with confidence | Stale chunks left in the index | Conflict | Stamp provenance and recency, then replace chunks when a hash changes |
| Confident answers with decorative citations | No "say so" rule in layer 01 | Confusion | Add the rule; check the citations |
| Quality drifts and no one can say when | No golden set | none: not a context fault | Build the harness of section 6 |

---

## 8. When not to use RAG

Three cases where retrieval is the wrong tool:

- **The corpus fits.** Anthropic's contextual-retrieval page draws the line at a knowledge base "smaller than 200,000 tokens (about 500 pages of material)": below it, put the whole corpus in the prompt and cache it ([post 05](../05-economics-of-context/index.md) prices the cache).
- **The task needs all of it.** Summarising one 30-page document gains nothing from retrieval.
- **The data lives in tables.** "All customers in California with a churn risk above 0.7" is a query for a database in SQL (Structured Query Language), not a vector index.

A production system can route between RAG, a database query and whole-document loading by query type; [post 17](../17-advanced-retrieval/index.md) covers the router and [post 25](../25-long-context-vs-rag/index.md) the long-context decision.

---

## 9. Make it run

The companion [`code/11-rag-from-scratch`](../../code/11-rag-from-scratch/) holds `ragkit`, a dependency-free offline core (`read_corpus`, `chunk`, `BM25`, `rrf`, `bookend_pack`) plus an online `generate` adapter that needs an API (application programming interface) key and is not run here. Its seven tests run offline from the series root:

```text
uv run --with pytest python -m pytest -q code/11-rag-from-scratch/tests
```

They end with `7 passed` in under a second. The toy snippet imports the same package from `code/11-rag-from-scratch/src`, with no install, and prints the table of section 6 in under a second:

```text
uv run python posts/11-rag-in-depth/snippets/toy_rag.py
```

Its last lines bookend-pack the fused top-5 for the first question. Rewording a question in `GOLDEN` or changing `target_tokens` shows which questions each change wins and loses; a real dense ranking joins `rrf` as one more list.

---

## 10. What can go wrong?

- **Gold labels tied to chunk ids.** The golden set records "chunk 412". After a chunker change chunk 412 is another passage, recall collapses, and a good change is reverted. Label the answer by a phrase or source span, as the toy does.
- **A splitter that loses text.** A splitter that treats every full stop as a sentence end breaks "4.95 dollars" or "example.com", and a careless one drops the fragment: the answer is in the document and in no chunk. Check that each document's chunks, joined, contain every word of the source.
- **Context written without the document.** To save tokens, the context call sees only the chunk, and the model invents a plausible context. The call needs the whole document (cached) and the chunk.
- **Fusing scores instead of ranks.** Cosine similarities near 0.8 are added to BM25 scores near 12, and BM25 decides every ranking.
- **A recall gain read as an answer gain.** Recall@50 rises, the change ships, and answer correctness falls because weaker chunks now reach the top-5. Each metric guards only its own stage.

---

## Common pitfalls

1. **Embedding the user message verbatim.** Past the first turn, query construction is not optional.
2. **Treating "more chunks" as the fix for every quality problem.** A bigger top-k often causes the distraction it was meant to cure.
3. **Reaching for a newer embedding model before fixing chunking.** A better vector of a broken chunk is still a broken chunk.
4. **Using RAG where the data is structured or already fits.** A database query, whole-document loading and RAG each have their place.
5. **Shipping without a golden set.** Then no change can be shown to help.

---

## Further reading

- Lewis, P. *et al.*, ["Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"](https://arxiv.org/abs/2005.11401) (NeurIPS 2020).
- Anthropic, ["Introducing Contextual Retrieval"](https://www.anthropic.com/news/contextual-retrieval) (September 2024).
- Cormack, G. V. *et al.*, ["Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"](https://doi.org/10.1145/1571941.1572114) (SIGIR 2009).
- Günther, M. *et al.*, ["Late Chunking: Contextual Chunk Embeddings Using Long-Context Embedding Models"](https://arxiv.org/abs/2409.04701) (2024).
- Muennighoff, N. *et al.*, ["MTEB: Massive Text Embedding Benchmark"](https://arxiv.org/abs/2210.07316) (2022).
- [Cohere](https://docs.cohere.com/docs/rerank), [Voyage AI](https://docs.voyageai.com/) and [BAAI](https://huggingface.co/BAAI/bge-reranker-v2-m3) reranker documentation.
- Saad-Falcon, J. *et al.*, ["ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems"](https://arxiv.org/abs/2311.09476) (NAACL 2024).
- Khattab, O. and Zaharia, M., ["ColBERT"](https://arxiv.org/abs/2004.12832) (SIGIR 2020): late interaction, in [post 17](../17-advanced-retrieval/index.md).

---

## What to read next

- **[Post 12 - Compress strategies](../12-compress-strategies/index.md):** what to do when retrieved chunks and history outgrow the budget.
- **[Post 20 - Evaluation](../20-evaluation/index.md):** the full harness that section 6 sketches, with its judges and CI gate.
