# 09 - Select strategies

> **TL;DR.** Select decides which items enter the window for one call. Retrieval-augmented generation (RAG), tool selection, memory recall and few-shot picking are all select over different corpora, and all run the same four stages: construct a query, generate a broad candidate set for recall, re-rank it for precision, and pack the survivors into the layer they fill. Two numbers measure the pipeline, recall@N on the candidates and precision@k on what is packed, and a toy run shows which lever moves which.
>
> **Prerequisites:** [Post 07](../07-write-select-compress-isolate/index.md).
> **Safe to skip?** Skip it if a retrieval failure can already be traced to the query, the candidate set, the reranker or the packing, with recall@N and precision@k measured to show which.
>
> **After reading, you will be able to:**
>
> - Recognise RAG, tool selection, memory recall and few-shot picking as one select operation, and name the corpus, the query and the layer packed for each.
> - Explain what each of the four levers (query, candidates, re-rank, pack) does, and what it trades among recall, precision, latency and cost.
> - Compute recall@N and precision@k for a retrieval run, and say which lever can move each.
> - Fuse ranked lists with reciprocal rank fusion and pack the survivors in bookend order.
> - Pick the lever most likely to fix a given select failure, and tune the dials in a defensible order.

![Four stages in a row from the user turn: construct the query, generate candidates for recall, re-rank for precision, pack for the budget, with their techniques. Under them, what each passes on: one search query, top-N of 50 candidates, top-k of 5 kept (illustrative), and layer 04, retrieved chunks.](diagrams/01-select-pipeline.svg)

*The select pipeline. N is set for recall and k for the budget; the same four stages serve documents, tools, memory rows and examples.*

---

## 1. The question: why is select one operation?

A first reading of write, select, compress, isolate (WSCI, the operations of [post 07](../07-write-select-compress-isolate/index.md)) treats select and retrieval-augmented generation (RAG: fetching relevant text at query time and adding it to the prompt of a large language model, LLM) as synonyms. They are not: RAG is one application of select. Three other problems are select too:

- **Tool selection.** Out of a catalogue of, say, 100 tools, which five schemas should this turn see (illustrative counts; [post 15](../15-tools-and-mcp/index.md))?
- **Memory recall.** Out of thousands of stored facts about this user, which handful go into this prompt ([post 16](../16-memory-systems/index.md))?
- **Few-shot example selection.** Out of dozens of curated examples, which two or three best resemble this query?

Each is a select, and each runs the four-stage pipeline the figure at the top of the post draws. Two numbers run through it. **Top-N** is the candidate-set size, how many plausibly relevant items candidate generation passes on; **top-k** is the packed count, how many survive re-ranking and land in the window. N is set for recall and k is bounded by the budget. The series' illustrative starting values are top-50 and top-5; Anthropic's "Introducing Contextual Retrieval" (September 2024) re-ranked 150 candidates and passed 20 to the model, which shows how far real settings range.

The technology in each stage differs between documents, tool schemas, memory rows and examples; the engineering questions are the same.

---

## 2. Lever 1: query construction

A retrieval system can only return what matches the query it is given. Embedding the user's last message verbatim fails whenever that message is a poor search query: a follow-up turn with a pronoun, a question full of chatter, a phrasing the corpus never uses. Three patterns address it.

**Query rewriting.** A small LLM call rewrites the user turn into a self-contained query, resolving pronouns, adding context from the conversation and removing chatter. *"And the second one?"* becomes *"What was the closing price of NVIDIA on the second trading day of January 2024?"*: the first gives an index nothing to match, the second a company, a date and a quantity.

**HyDE (Hypothetical Document Embeddings).** The model first writes the answer it expects, and that text, rather than the question, is embedded and searched. The hypothetical answer may be wrong in detail, but it is written in the vocabulary of an answer, which is what the indexed documents contain. Gao et al. (arXiv, December 2022) report that HyDE, with no relevance labels, outperformed the unsupervised dense retriever Contriever and performed comparably to fine-tuned retrievers across web search, question answering and fact verification, in several languages. It costs one extra LLM call per query.

**Multi-query expansion and decomposition.** Expansion generates a few paraphrases, retrieves top-N for each and takes the deduplicated union, trading a little latency for recall. Decomposition splits a question with several parts ("compare the refund rules of the annual and the monthly plan") into one sub-query per part.

The choice is empirical: rewriting is the cheapest and fixes follow-up turns; HyDE suits corpora whose answers use another vocabulary than the questions; expansion and decomposition suit unpredictable or many-part questions.

---

## 3. Lever 2: candidate generation

The job of candidate generation is **recall**: get every plausibly relevant item into a candidate set small enough to re-rank. Three families of technique are in use, and this series combines them.

**Dense retrieval.** Embed the corpus offline and the query at run time, and retrieve by approximate nearest-neighbour (ANN) search in a vector index, which this series treats as a black box with a recall and latency profile (Karpukhin et al., 2020, showed dense passage retrieval for open-domain question answering). It is strong on paraphrase and weak when the query hinges on an exact identifier (an error code, a product code, a function name) that the embedding model never learned to tell apart.

**Sparse retrieval.** BM25 (Best Match 25, a ranking function built on term frequency, inverse document frequency and document length; Robertson and Zaragoza, 2009) over an inverted index such as Elasticsearch, OpenSearch or tantivy. It is strong on exact tokens and rare terms, and weak on paraphrase ("cancel" against "terminate").

**Metadata filtering.** Restrict candidates to items whose metadata matches a structured filter: date range, source, language, customer id. Items excluded by definition can no longer crowd out the relevant ones, provided the metadata was written at ingest ([post 10](../10-data-ingestion-pipelines/index.md)).

**Hybrid retrieval** runs dense and sparse retrieval in parallel, within the filter, and merges the ranked lists; this series uses **reciprocal rank fusion** (RRF; Cormack, Clarke and Büttcher, 2009): an item $d$ scores $\mathrm{RRF}(d) = \sum_i 1/(k + r_i(d))$ over the lists it appears in, where $r_i(d)$ is its rank in list $i$. The constant $k$ damps the weight of the very top ranks and is unrelated to top-k. The paper fixed $k = 60$ in a pilot experiment, found the choice not critical, and reported that RRF beat Condorcet fusion and, in most of its test collections, the best individual ranking. Because it uses only ranks, RRF needs no calibration between dense and sparse scores. The snippet of section 8 implements it:

```python
def rrf(*ranked_lists, k=RRF_K):
    """Reciprocal rank fusion: each item scores the sum of 1 / (k + rank) over the lists it is in."""
    score = Counter()
    for ranked in ranked_lists:
        for rank, d in enumerate(ranked, start=1):
            score[d] += 1 / (k + rank)
    return sorted(score, key=lambda d: (-score[d], d))
```

An item ranked first by BM25 and fourth by the dense retriever scores $1/61 + 1/64 \approx 0.0320$; an item ranked second by one list only scores $1/62 \approx 0.0161$. Agreement between the retrievers counts for more than a high rank in one. The series' illustrative starting default: dense top-30 and BM25 top-30, within the filter, fused into a top-50.

One offline technique sharpens both halves at once. **Contextual retrieval**, Anthropic's name for it, prepends each chunk before indexing with a short, model-written note on where it sits in its document, so the context travels into both the embedding and the BM25 index. Anthropic's post reports the top-20-chunk retrieval failure rate (one minus recall@20) on its benchmarks falling from 5.7 percent to 3.7 percent with contextual embeddings, a 35 percent reduction, and to 2.9 percent with contextual BM25 added, a 49 percent reduction. [Post 11](../11-rag-in-depth/index.md) implements it.

---

## 4. Lever 3: re-ranking

Candidate generation optimises recall; re-ranking optimises **precision**. The candidate set holds 50 items, the budget has room for 5 (illustrative), and the reranker chooses which 5.

The usual reranker is a **cross-encoder**: a model that reads the query and one candidate together and outputs a relevance score. Seeing both at once lets it judge whether the candidate answers the query, which a bi-encoder, embedding each separately and comparing two vectors, cannot. The price is speed. At an illustrative 20 milliseconds per pair, 50 candidates take $50 \times 20 = 1,000$ milliseconds, one second, while a corpus of 1,000,000 items would take 20,000 seconds, about 5.6 hours. That gap is why candidate generation exists.

Rerankers as of early 2026 include Cohere's Rerank, Voyage AI's rerankers and BAAI's open-weight `bge-reranker-v2` models; names and versions change quickly, so the provider's current list is the reference.

Anthropic's post measured this step too: re-ranking 150 candidates over contextual embeddings and contextual BM25 lowered the failure rate of the 20 passed on (its k) from 2.9 to 1.9 percent, 67 percent below the 5.7 percent baseline. Re-ranking cannot recover an item that candidate generation missed: it reorders the top-N, so it moves precision@k and leaves recall@N where it was.

---

## 5. Lever 4: packing

Packing decides what of the top-k lands in the window, in what order and form.

**Order matters.** Liu et al. ("Lost in the Middle", 2023) found that models used information at the start and the end of a long input more reliably than information in its middle ([post 03](../03-how-llms-read-context/index.md)). The **bookend layout** follows: the highest-ranked chunk first, the second-highest last, the rest in between. It puts the two best passages where use is most reliable; how much it helps a given system is measured, not assumed ([post 06](../06-context-failure-modes/index.md) draws the layout). The snippet's version:

```python
def bookend(ranked):
    """Best first, second-best last, the rest in between in rank order."""
    if len(ranked) < 3:
        return list(ranked)
    return [ranked[0]] + ranked[2:] + [ranked[1]]
```

**Deduplicate.** Two near-identical chunks add little beyond the first and vote twice. When two survivors are near duplicates (an illustrative rule: cosine similarity above 0.9), drop the lower-ranked one.

**Trim within a chunk.** A chunk may be 800 tokens and the relevant span 100 (illustrative sizes); a small model can extract the span first (contextual compression).

**Cite while packing.** Give each chunk a stable header such as `[source: docs/refunds.md, chunk 3]`. Instructed to, the model quotes the headers in its answer, giving the application a citation to show and a trail to debug. This is not reliable: a model can attach the wrong header or invent one, so citation accuracy is measured (section 8).

**Respect the budget.** If the top-k would exceed layer 04's budget ([post 04](../04-tokens-windows-budgets/index.md), section 6, gives 20 to 40 percent of the input as an illustrative default), drop the lowest-ranked chunk rather than truncating a higher one.

---

## 6. The same pipeline, four times

The four levers apply to the other three select problems with small adaptations, which the table below lays out.

![A table of four corpora. Documents: a chunk, queried from the rewritten user turn, re-ranked on relevance, packed into 04 Retrieved chunks. Tool schemas: the same query and signal, packed into 02 Tools and MCP descriptions. Memory rows: the intent of the turn, relevance with recency and confidence, 03 Memory and state. Examples: the query with a label filter, relevance and diversity (MMR), 04 Retrieved chunks.](diagrams/02-four-corpora.svg)

*Swap the corpus and tune the stage that changes most; the pipeline stays. Only tool selection writes into the cached prefix.*

**Tool selection.** The corpus is the tool catalogue, one schema (name, description, parameters) per item, embedded offline. At run time the rewritten user turn retrieves candidates by hybrid search over the schemas, a reranker orders them, and the surviving handful is packed into layer 02, tools and MCP descriptions (MCP is the Model Context Protocol, the open protocol through which external tools reach a host application). Selecting the few relevant tools per turn keeps the catalogue the model reads small, tool-storm's first fix in post 06 and the pattern [post 15](../15-tools-and-mcp/index.md) develops. The cost: layer 02 belongs to the stable prefix, and a catalogue that changes per turn changes the prefix a prompt cache reuses ([post 05](../05-economics-of-context/index.md)), so a design keeps a fixed core of tools in the prefix or selects among a few fixed groups.

**Memory recall.** The corpus is the memory store, one row per item. The query is built from the intent of the turn ("what does this user usually want when they ask this?") rather than its surface text. Re-ranking mixes relevance with recency and confidence: a memory scored 0.9 for relevance from two years ago may rank below one scored 0.7 from yesterday (illustrative scores). Packing respects layer 03's small budget, 5 to 10 percent of the input in post 04's illustrative defaults.

**Few-shot example selection.** The corpus is the bank of labelled examples, with the label class in the metadata. Retrieval is dense within a filter ("only examples of class C"). The series' starting rule is two or three examples: each extra one costs tokens on every call, and whether it still helps is measured. Examples picked per turn are per-turn content, so they travel with the retrieved material in layer 04, after the cached prefix; a fixed set that never changes can live in layer 01 and cache. Good selection re-ranks for diversity as well as relevance, so the model sees varied cases rather than three near copies. The usual mechanism is maximal marginal relevance (MMR; Carbonell and Goldstein, 1998): each candidate's relevance is penalised by its similarity to the examples already picked.

---

## 7. Tuning the system

The dials, in the order this series turns them. The values are the series' illustrative starting defaults, not measurements; each is confirmed on the system's own evaluation set.

1. **Reranker on or off.** It attacks precision directly and is the cheapest large change. On for production search; optional for low-stakes lookups.
2. **k, the packed count.** Start at 5; down to 3 for short factual answers, up to 10 for synthesis across sources. Beyond that, the series prefers better re-ranking to more chunks.
3. **Top-N, the candidate set.** Start at 50; raise to 100 if recall@N is poor on rare queries, lower to 20 if re-ranking latency is tight.
4. **Hybrid weighting.** RRF works without tuning; a weighted fusion can edge it out when there are offline labels to fit it on.
5. **Chunk size.** Start at 400 to 600 tokens for prose and 200 to 300 for code, with 10 to 20 percent overlap, and tune by how often an answer's supporting fact sits entirely inside one chunk. Chunking strategies are [post 11](../11-rag-in-depth/index.md)'s subject.
6. **Embedding model.** Switch only with an offline benchmark on the system's own queries; a public leaderboard ranks general-purpose models, not a particular corpus.
7. **Query rewriting or HyDE.** Rewriting wherever there are follow-up turns; HyDE where questions and documents use different vocabularies.

The reranker and k come first because they act on precision directly; the embedding model comes late because changing it means re-embedding the corpus.

---

## 8. Measuring whether it works

Two retrieval metrics come before any of the dials, one per half of the pipeline. With $R$ the set of items relevant to a query:

- **Recall@N** $= |R \cap \mathrm{top}N| / |R|$, the share of the relevant items that reach the candidate set, averaged over a curated set of queries. It measures candidate generation and caps everything after it: an item missing from the top-N cannot be re-ranked or packed.
- **Precision@k** $= |R \cap \mathrm{top}k| / k$, the share of the packed items that are relevant. It measures re-ranking and the choice of k; post 06 names a falling precision@k as the signal of distraction.

A third metric watches the answer. **Citation accuracy** asks whether the chunk the model cited contains the fact it asserted: a person labels a weekly sample of production answers (50 is an illustrative size). It catches packing and citation bugs that neither retrieval metric sees. End-to-end correctness on a held-out set closes the loop ([post 20](../20-evaluation/index.md)).

The snippet `snippets/select_pipeline.py` builds the pipeline over a toy corpus with the standard library and measures both retrieval metrics. Run from the series root:

```text
uv run python posts/09-select-strategies/snippets/select_pipeline.py
```

The corpus is 36 one-sentence help-centre articles for a made-up invoicing application, with six questions and three relevant articles each. Two parts are stand-ins, not models: the "dense" retriever maps words to hand-written concept groups (so "terminate" matches "cancel") and knows nothing of identifiers such as `E-4012`; the re-rank step scores the query and one candidate together by the share of the query's concepts and identifiers the candidate covers. Each list is cut at its top 6, fused into a top-6, and the top 3 are packed. The run begins:

```text
corpus: 36 articles; 6 questions, 3 relevant articles each
each list top-6, fused by RRF (k = 60) into top-N = 6; packed top-k = 3

configuration       recall@6   precision@3
BM25 only               0.56          0.44
dense only              0.94          0.56
hybrid (RRF)            1.00          0.67
hybrid + re-rank        1.00          0.78
```

![A dot chart measured on the toy corpus, recall@6 and precision@3 per configuration: BM25 only 0.56 and 0.44; dense only 0.94 and 0.56; hybrid (RRF) 1.00 and 0.67; hybrid plus re-rank 1.00 and 0.78.](diagrams/03-which-lever-moves.svg)

*On the toy corpus, fusion raises recall@6 to its ceiling and the reranker then moves precision@3 alone.*

The figure reads the table one lever at a time. BM25 alone finds none of the articles for the reimbursement question, whose words the corpus never uses; the dense stand-in, blind to identifiers, loses one of the three `E-4012` articles from its top 6; fusing the two lists finds all 18 relevant articles. Switching the reranker on leaves recall@6 at 1.00, as it must, and lifts precision@3 from 0.67 to 0.78. The run also shows the first lever: a follow-up asked after a turn about adding a team member finds nothing until rewritten:

```text
q4 asked     'And how do I take one away?': recall@6 0.00, precision@3 0.00
q4 rewritten "How do I remove a team member's access?": recall@6 1.00, precision@3 0.67
```

The corpus was written to show the mechanism, so the numbers say which lever moves which metric, not how much a real system gains. Changing one setting at a time (`N_EACH`, `TOP_N`, `TOP_K`, or a configuration) and rerunning is the post's exercise in small: record which number moved before believing a lever works.

---

## 9. What can go wrong?

- **Re-ranking a candidate set that never held the answer.** A cross-encoder is added to fix wrong answers. Precision@k rises, but complaints about missing information continue: the relevant chunk never reached the top-N, and no reranker promotes what it never sees.
- **Tuning on one metric.** Top-N and k are raised together to fix recall. Recall@N improves and the answers get worse: precision@k fell, and the extra chunks distract the model.
- **A follow-up turn sent to the index as typed.** "What about the second one?" is embedded verbatim, retrieval returns whatever is closest to "second", and the model answers fluently from the wrong documents.
- **Per-turn tool selection that breaks the cache.** Tool schemas are selected per query to stop a tool-storm. The storm stops and the input bill rises, because layer 02 now differs on every call.
- **Truncating to fit.** The packed chunks exceed layer 04's budget and the request builder cuts the best chunk at the limit; the answer cites a sentence that ends half way.

---

## Common pitfalls

1. **Embedding the user message verbatim.** A rewriting step is one small model call, and it is what makes follow-up turns retrievable.
2. **Skipping re-ranking.** Candidate generation is built for recall; without a reranker, the top-k is whatever the retriever happened to rank first.
3. **Reading the RRF constant as top-k.** The $k$ of $1/(k + r)$ is a damping constant (60 in the RRF paper); it has nothing to do with how many items are packed.
4. **Packing in score order without a reason.** The bookend layout puts the two best chunks where models use information most reliably; whichever layout ships, the choice is measured.
5. **Treating tool selection as a separate problem.** It is the same pipeline as RAG over a different corpus, with one extra constraint: the prompt cache.

---

## Further reading

- Karpukhin, V. *et al.*, *"Dense Passage Retrieval for Open-Domain Question Answering"* (EMNLP 2020).
- Robertson, S. and Zaragoza, H., *"The Probabilistic Relevance Framework: BM25 and Beyond"* (2009).
- Cormack, G. V., Clarke, C. L. A. and Büttcher, S., *"Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"* (SIGIR 2009): the RRF formula and $k = 60$.
- Gao, L. *et al.*, *"Precise Zero-Shot Dense Retrieval without Relevance Labels"* (arXiv 2022, ACL 2023): HyDE.
- Anthropic, *"Introducing Contextual Retrieval"* (September 2024): contextual embeddings, contextual BM25 and re-ranking, and the failure rates of sections 3 and 4.
- Liu, N. F. *et al.*, *"Lost in the Middle: How Language Models Use Long Contexts"* (arXiv 2023, TACL 2024): the position finding behind the bookend layout.
- Carbonell, J. and Goldstein, J., *"The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries"* (SIGIR 1998): maximal marginal relevance.
- Cohere, *"Rerank"*; Voyage AI, *"Rerankers"*; BAAI, *"bge-reranker-v2"* model cards: the rerankers of section 4.

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 10 - Data ingestion and document pipelines](../10-data-ingestion-pipelines/index.md):** the offline half that decides which text and metadata the select pipeline can ever find.
- **[Post 11 - RAG in depth](../11-rag-in-depth/index.md):** the document-corpus instance end to end, with a companion that runs BM25 and reciprocal rank fusion.
