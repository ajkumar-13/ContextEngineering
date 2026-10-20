# 25 - Long context vs. RAG: a decision framework

> **TL;DR.** Frontier context windows reach 1,000,000 tokens, which makes it tempting to load a whole corpus and drop retrieval-augmented generation (RAG). Four questions, asked in order, decide each workload: does the corpus fit with room to spare, is it stable enough to cache, does each query need most of it, and can the model use it at that length? The benchmarks say that finding one fact in a long input is easy and combining facts across it is not, and the arithmetic says an uncached load costs many times a retrieval call. A workload that holds both whole-corpus and local queries is answered with a router that picks per query.
>
> **Prerequisites:** [Post 11](../11-rag-in-depth/index.md), [Post 17](../17-advanced-retrieval/index.md).
> **Safe to skip?** Skip it if a workload can already be placed on long context, RAG or a router from its corpus and queries, with the benchmarks read for what they measure and the cost and latency of each option worked out.
>
> **After reading, you will be able to:**
>
> - Match a workload to long context, RAG or a hybrid by answering the four questions of the test in order.
> - Read a long-context benchmark for what it measures, and tell a needle-in-a-haystack score from evidence of reasoning at length.
> - Estimate the cost and the time to first token of a long-context load against a retrieval call, with and without a cache hit.
> - Design a per-query router between long-context loading and RAG, and say what each route is evaluated on.

![Four questions in a chain: fits with room to spare, stable enough to cache, each query needs most of it, the model can use it at that length. A no, or a small slice at question 3, leads to RAG (incrementally indexed after question 2, over a curated subset after question 4), a mix of queries to a per-query router, four yes answers to loading the corpus once and caching it.](diagrams/00-hero-long-context-vs-rag.svg)

*Any answer that leaves the spine sends the workload, or that kind of query, to retrieval; only four yes answers justify loading everything.*

---

## 1. The question: does a million-token window replace retrieval?

The windows grew. As [post 04](../04-tokens-windows-budgets/index.md) tabulates them, Claude Haiku 4.5 and Claude Sonnet 4.5 hold 200,000 tokens and Claude Opus 4.6 holds 1,000,000 (Anthropic, "Context windows", consulted October 2026), and Google's Gemini "Long context" page (updated 22 June 2026) says that many Gemini models "come with large context windows of 1 million or more tokens". Models and sizes are as of early 2026 and change. By [post 04](../04-tokens-windows-budgets/index.md)'s rule of three-quarters of a word per token, 1,000,000 tokens are about 750,000 words of English.

The pitch follows: stop building retrieval pipelines and paste the corpus in. It is right for small corpora. [Post 11](../11-rag-in-depth/index.md), section 8, quotes Anthropic's contextual-retrieval page drawing the line at a knowledge base "smaller than 200,000 tokens (about 500 pages of material)": below it, the whole corpus goes into the prompt and is cached. A vector store built to search one 50-page document is now the harder way to do an easy thing. Many real RAG corpora are bigger, change more often, and are queried a slice at a time; there the boundary has to be drawn precisely.

This post asks when a million-token window replaces retrieval, when retrieval still wins, and how well models use the room they have. The figure at the top of the post is the answer in one picture.

---

## 2. The four-question test

The questions are asked in order; each can settle the case before the next.

**Question 1. Does the corpus fit in one window, with room to spare for everything else?** A 30-page contract on a 200,000-token model fits: load the document, skip retrieval, cache the prefix. A 200 GB collection of customer documents (an illustrative size) does not, and the question is closed: retrieval it is. Room to spare matters because the window holds the whole call ([post 04](../04-tokens-windows-budgets/index.md)): besides the corpus, layer 01, the system prompt; layer 02, tools and MCP (Model Context Protocol) descriptions; layer 05, conversation history; and the output. As an illustrative rule, a 30% reserve for those leaves 700,000 tokens of corpus in a 1,000,000-token window; the right reserve depends on the prompt and the answers, and section 3 gives the deeper reason not to fill the window.

**Question 2. Is the corpus stable enough to cache?** Long context is affordable only with prompt caching, and a cache hit needs a prefix identical up to the cache breakpoint ([post 05](../05-economics-of-context/index.md), section 4). A corpus that changes daily, or a customer's evolving project state, misses the cache after every change and pays the write premium again; section 7 shows how far that moves the bill. RAG absorbs change through incremental indexing: a new document is chunked and indexed, and nothing else is recomputed. Freshness and provenance pull the same way: a retrieved chunk carries its source and date into layer 04, retrieved chunks.

**Question 3. Does each query need most of the corpus, or a small slice?** Summarising one document needs the whole document; a factoid lookup in a knowledge base needs one paragraph. The first suits long context; the second suits RAG on both cost and latency. A useful exercise is to label a sample of the real query log as global (needs most of the corpus) or local (needs a slice). If global queries are rare, RAG with an occasional whole-document load beats loading everything on every call; if both kinds are common, the answer is a router (section 6).

**Question 4. Can the model actually use the long context for this task?** A window is a capacity, not a guarantee of use. Section 3 shows what the benchmarks say in general; the answer for one application comes from its own evaluation ([post 20](../20-evaluation/index.md)): the same ten or so real questions run once with the whole document loaded and once through the [post 11](../11-rag-in-depth/index.md) pipeline, with accuracy, latency and cost recorded for each. A model that finds single facts at that length but fails questions that combine them has answered no for the second kind.

---

## 3. What the long-context benchmarks show

Each of five benchmarks adds something to the plain task, and what it adds is what it measures.

**Needle in a haystack (NIAH).** The test hides one sentence, the needle, in a long document and asks the model to retrieve it; Greg Kamradt's open harness popularised it in 2023 ([post 03](../03-how-llms-read-context/index.md), section 8). Model reports have since claimed near-perfect needle recall at great lengths: the Gemini 1.5 report (Gemini Team, 2024) states "near-perfect retrieval (>99%) up to at least 10M tokens". Google's own "Long context" page adds the caveat: the tests "consider the most basic setup, where you have a single needle you are looking for", and with several needles "the model does not perform with the same accuracy". A needle score shows recall of one planted fact; it is the result behind the claim that long context just works.

**RULER (Hsieh et al., NVIDIA, 2024).** RULER extends the needle test with multiple needles, keys and values, and adds multi-hop tracing and aggregation tasks: 13 tasks in all, run on 17 models at lengths from 4K to 128K tokens. Its abstract reports: "Despite achieving nearly perfect accuracy in the vanilla NIAH test, almost all models exhibit large performance drops as the context length increases." It adds that while all the models claim context sizes of 32K tokens or more, "only half of them can maintain satisfactory performance at the length of 32K". RULER defines a model's effective length as the longest tested length at which its 13-task average stays above 85.6%, the score of Llama 2 7B at 4K; [post 06](../06-context-failure-modes/index.md) draws the claimed window against the effective length for eight of the models. The figure below draws the scores themselves.

![A line chart cited from RULER Table 3: the 13-task average score against context length from 4K to 128K tokens for five models, with the 85.6% threshold drawn and the region below it shaded. Gemini-1.5-Pro, claiming 1M, falls from 96.7 to 94.4 and stays above the threshold. GPT-4, claiming 128K, falls from 96.6 to 81.2, below it after 64K. GradientAI/Llama3 (70B), claiming 1M, falls from 95.1 to 72.1, below it after 16K. Llama3.1 (70B), claiming 128K, falls from 96.5 to 66.6, below it after 64K. Qwen2 (72B), claiming 128K, falls from 96.9 to 53.7, below it after 32K.](diagrams/01-ruler-scores-by-length.svg)

*Every model starts above 95%; what separates them is how soon the line crosses the threshold, and four of the five cross it inside the window they claim.*

**BABILong (Kuratov et al., NeurIPS 2024).** BABILong scatters the facts of 20 reasoning tasks (fact chaining, induction, deduction, counting, lists and sets) through long natural text. Its authors report that "popular LLMs effectively utilize only 10-20% of the context and their performance declines sharply with increased reasoning complexity" (LLM: large language model). It also warns about the other side: the RAG methods it tested "achieve a modest 60% accuracy on single-fact question answering, independent of context length". Retrieval does not degrade with length, but it is not a free win either.

**LongBench (Bai et al., ACL 2024).** LongBench is 21 datasets in six task categories (question answering over one or several documents, summarisation, few-shot learning, synthetic tasks and code completion) in English and Chinese. Of its findings across eight models, one bears directly on this post: "context compression technique such as retrieval brings improvement for model with weak ability on long contexts, but the performance still lags behind models that have strong long context understanding capability". Retrieval narrows the gap for a weak long-context model without closing it.

**MRCR (Multi-Round Co-reference Resolution).** MRCR was introduced in the Gemini 1.5 report and is one of the three tasks of Michelangelo (Vodrahalli et al., Google DeepMind, 2024). The model must reproduce one answer from a long conversation ("the first poem about penguins") among adversarially similar ones. Michelangelo's Figure 1 caption reads: "All models experience significant fall off in performance before 32K." The paper also reports that after that initial drop the Gemini models' performance does not decrease from 128K to 1M tokens, while GPT and Claude models of 2024 have a more negative slope at 128K.

The benchmarks beyond the needle agree. **Finding one stated fact at length works well; combining, tracing and disambiguating facts degrades well before the window is full.** A million-token reader is not a million-token reasoner. Long context suits "find this in this pile"; RAG over a curated subset suits reasoning, because the subset is short enough for the model to use well. The numbers are for the 2024 models the papers tested; what carries over is the method, measuring at the real length on the real task.

---

## 4. When long context wins

Loading beats retrieving in these cases:

- **Single-document workflows.** Reviewing a contract, summarising a paper, debugging one repository. The whole document fits, every query is global or local within it, and the cached prefix spreads the cost across the session.
- **Many worked examples.** A specialised classification may benefit from a few hundred in-context examples (an illustrative count); loading and caching them beats retrieving a different subset per query, which also breaks the cache.
- **Long working sessions.** A coding session that has touched many files keeps them loaded rather than reconstructing them by retrieval each turn.
- **Low volume, high stakes.** On Claude Opus 4.6 a full 1,000,000-token load costs 5 dollars of input, uncached, at 5 dollars per million input tokens as of early 2026. Anthropic's "Pricing" page (consulted October 2026) bills the model's whole window at standard pricing: "A 900k-token request is billed at the same per-token rate as a 9k-token request." For a legal review asked a handful of times, the cost of a wrong answer dwarfs that bill.

In each case seeing everything together is worth the bill, provided material asked about more than once is cached.

---

## 5. When RAG wins

Retrieval beats loading in these cases:

- **Large or unbounded corpora.** Anything past question 1's room to spare, where large knowledge bases sit.
- **Frequently changing corpora.** Each change invalidates the cached prefix and the long-context economics with it.
- **High volume, low value per query.** At an illustrative million queries a day, every per-query saving is multiplied by a million.
- **Precision.** RAG with reranking hands the model a short, focused layer 04; a whole corpus surrounds the answer with material that can pull it off course, the distraction failure mode of [post 06](../06-context-failure-modes/index.md).
- **Multi-tenant or per-user data.** Loading one user's data is fine; loading every user's is not. The corpus differs by tenant, and retrieval with a mandatory tenant filter keeps each prompt to its owner's data ([post 24](../24-privacy-and-governance/index.md) covers the governance side).

RAG remains the default for knowledge systems and any corpus the model cannot comfortably hold or cache.

---

## 6. Hybrid: routing per query

A system whose query log holds both kinds needs neither option alone. When question 3 finds both global and local queries, a router picks the technique per query, as [post 17](../17-advanced-retrieval/index.md), section 7, builds it: rules where the query kinds are crisp, a small model call with a rubric where they are not, and RAG as the fall-through. A reference setup for an assistant over documents and a database:

```text
query
  whole-document task       ->  long-context load, document cached at the front of layer 04
  local lookup              ->  RAG, top-5 chunks after reranking
  multi-document synthesis  ->  RAG, top-15 chunks after reranking
  count over records        ->  text-to-SQL
```

The top-k sizes are illustrative. Text-to-SQL is [post 17](../17-advanced-retrieval/index.md)'s route that turns a question into SQL (Structured Query Language) over a known schema.

Each route has its own cost and quality metric, and the router is evaluated like any component: a labelled set of real queries, routing accuracy on it, and every misroute read ([post 20](../20-evaluation/index.md)). A misroute costs more than a weaker answer: a count sent to vector search returns a confident number from whichever rows were retrieved.

A second hybrid pattern recurs: **retrieve, then read long**. Retrieve a generous set (top-30, illustrative) and pack all of it into one long-context call: retrieval keeps the corpus out of the window, and the model sees every candidate together. It costs more than a top-5 call, and whether it pays is measured on a golden set of multi-source questions.

---

## 7. Cost and latency arithmetic

The workload of the worked comparison is illustrative: 1,000 queries a day over a 200,000-token corpus, a 100-token question and a 500-token answer on every route, a 5,000-token RAG call with an illustrative 0.001 dollars of embedding and reranking per query, and 10 cache writes a day, one after each quiet spell longer than the five-minute cache lifetime. The rates are cited: Claude Opus 4.6 at 5 dollars per million input tokens and 25 per million output, as of early 2026, with a five-minute cache write at 1.25 times and a cache read at 0.1 times the base input price, the rate for most models (Anthropic, "Pricing" and "Prompt caching", consulted October 2026; [post 05](../05-economics-of-context/index.md)).

Per query, the uncached corpus costs $200{,}000 \times 5 / 10^6 = 1.00$ dollar, a cache write $1.25$ dollars and a cache read $0.10$; the question and answer add $100 \times 5 / 10^6 + 500 \times 25 / 10^6 = 0.013$ dollars. A RAG call costs $5{,}000 \times 5 / 10^6 + 0.0125 + 0.001 = 0.0385$ dollars. Run from the series root as `uv run python posts/25-long-context-vs-rag/snippets/cost_latency.py`, the snippet does the arithmetic for the day:

```text
per day, 1,000 queries, 10 cache writes a day
  A  long context, uncached    1013.00
  A  long context, cached       124.50   (paid in full 25.50, read from cache 99.00)
  C  hybrid, 10% long            57.45   (long 22.80: in full 13.80, cache 9.00; RAG 34.65)
  B  RAG                         38.50
  against RAG: uncached 26.3 times, cached 3.2 times, hybrid 1.5 times
```

The figure below draws the four days to one scale.

![Four dashed horizontal bars of dollars per day at illustrative sizes on Claude Opus 4.6. Long context uncached runs past a broken axis to 1,013.00. Long context cached is 124.50: 25.50 paid in full and 99.00 read from the cache. The hybrid, 10% long, is 57.45: 13.80 in full, 9.00 from the cache and 34.65 of RAG calls. RAG alone is 38.50. A note gives the prefill before the first token, uncached: 80.04 seconds for the corpus, 2.00 for a RAG call.](diagrams/02-cost-per-day.svg)

*Caching cuts the long-context day from 1,013.00 dollars to 124.50; retrieval cuts it to 38.50 by keeping the corpus out of the call.*

At these sizes, long context without caching costs about 26 times as much as RAG and with caching about 3 times; the hybrid stays within 1.5 times of RAG while sending the whole-document tenth of the traffic to long context. The ratios move with the corpus, the RAG call and the cache writes, each a variable in the snippet; a route that serves a tenth of the traffic sees longer quiet spells, so 10 writes a day flatters the hybrid.

Latency follows the same tokens. At [post 04](../04-tokens-windows-budgets/index.md)'s illustrative frontier-class rates of 0.4 milliseconds per prefill token and 32 per decode token, the snippet prints 80.04 seconds of prefill before the first token for the uncached corpus against 2.00 seconds for the RAG call, and 16.00 seconds of decode for the answer on either route. The linear model understates the long call, because attention work grows faster than the token count ([post 03](../03-how-llms-read-context/index.md)). A cache hit skips the cached prefix's prefill, so the first token comes sooner; Anthropic's documentation gives no figure, and neither does this post ([post 05](../05-economics-of-context/index.md), section 5).

---

## 8. The forecast

What follows is the author's expectation, not a measured trend.

- **Windows will keep growing.** The Gemini 1.5 report already tested recall up to 10 million tokens in research. Reasoning quality deep in the window is likely to improve more slowly than the size.
- **Caching will keep getting cheaper.** Anthropic's price list already shows lower read multipliers on some newer models ([post 05](../05-economics-of-context/index.md)), and every such cut moves the line toward long context for medium corpora.
- **Retrieval will keep improving too.** Better embedders, rerankers and routers move the other line.
- **Hybrids will stay the production answer.** Neither extreme is the right architecture for most workloads at scale.

The lesson: **build a router, not a religion**. A system built on "long context will replace retrieval" or "retrieval will always win" is rebuilt when prices move; a system with a router changes a rule.

---

## 9. What can go wrong?

- **Loading the full corpus on every call, uncached.** The demo works; the first month's bill is about 26 times the RAG design's at section 7's sizes.
- **A timestamp ahead of the corpus.** A date or the question sits before the document, the prefix differs on every call, and every call pays the cache write instead of the read.
- **Trusting a needle score.** A model that scores near 100% on single-needle retrieval is assumed to reason over the whole window; questions that combine two clauses come back wrong or incomplete.
- **Choosing long context because retrieval was hard.** A poorly tuned pipeline is replaced by the expensive option; the retrieval problem was a chunker or a missing reranker ([post 11](../11-rag-in-depth/index.md)).
- **One corpus for every tenant.** All customers' documents are loaded into one cached prefix to save writes, and one customer's answer quotes another's contract.

---

## Common pitfalls

1. **No caching for a long-context design.** Without a stable cached prefix the long-context option is the most expensive one on the table.
2. **Reading NIAH as evidence of reasoning at length.** A needle test measures recall of one fact; RULER, BABILong and MRCR show combining facts degrading much earlier.
3. **Choosing RAG when the corpus fits and is stable.** Loading is simpler and often better below the 200,000-token line.
4. **No router when both kinds of query are common.** Whole-document questions get five fragments, and lookups pay for the whole corpus.
5. **No evaluation per route.** A change to one route regresses quality on the queries routed across the boundary, and nothing notices.

---

## Further reading

- Hsieh, C.-P. *et al.*, *["RULER: What's the Real Context Size of Your Long-Context Language Models?"](https://arxiv.org/abs/2404.06654)* (NVIDIA, 2024): effective context length, Table 3.
- Kuratov, Y. *et al.*, *["BABILong: Testing the Limits of LLMs with Long Context Reasoning-in-a-Haystack"](https://arxiv.org/abs/2406.10149)* (NeurIPS 2024 Datasets and Benchmarks), the successor to *["In Search of Needles in a 11M Haystack"](https://arxiv.org/abs/2402.10790)* (2024).
- Bai, Y. *et al.*, *["LongBench: A Bilingual, Multitask Benchmark for Long Context Understanding"](https://arxiv.org/abs/2308.14508)* (ACL 2024).
- Vodrahalli, K. *et al.*, *["Michelangelo: Long Context Evaluations Beyond Haystacks via Latent Structure Queries"](https://arxiv.org/abs/2409.12640)* (Google DeepMind, 2024): MRCR and its sibling tasks.
- Gemini Team, Google, *["Gemini 1.5: Unlocking multimodal understanding across millions of tokens of context"](https://arxiv.org/abs/2403.05530)* (2024): the needle results to 10 million tokens, and the origin of MRCR.
- Google, *["Long context"](https://ai.google.dev/gemini-api/docs/long-context)* (Gemini API documentation, updated 22 June 2026, consulted October 2026).
- Anthropic, *["Pricing"](https://platform.claude.com/docs/en/about-claude/pricing)* and *["Prompt caching"](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)* (Claude API documentation, consulted October 2026): the rates and multipliers of section 7.
- Anthropic, *["Long context prompting for Claude 2.1"](https://claude.com/blog/claude-2-1-prompting)* (December 2023): one sentence added to the start of the answer raised a needle-in-a-haystack score from 27% to 98%.

---

## What to read next

- **[Post 26 - The modern agentic workflow](../26-modern-agentic-workflow/index.md):** where coding agents make this post's decision turn by turn inside one session.
- **[Post 20 - Evaluation](../20-evaluation/index.md):** the golden set and the gate that answer question 4 and keep each route of the router honest.
