# 25 · Long context vs. RAG — a decision framework

> **TL;DR.** Frontier models now ship with context windows of 200 k, 1 M, and beyond (Gemini 2.5 reaches roughly 2 M). The question every team eventually asks: *"do we still need RAG?"* (RAG: retrieval-augmented generation — fetch relevant chunks and paste them into the prompt.) The honest answer is **yes, almost always, but the boundary has moved**. This post is the decision framework: when long context wins, when RAG wins, when the right answer is a hybrid, and what the recent benchmarks (RULER, BABILong, LongBench, MRCR, NIAH) actually tell us about how well long-context models *use* the room they have.
>
> **After reading this you will be able to:**
> - Match a workload to long context, RAG, or a hybrid using a four-question test.
> - Read the current long-context benchmarks without being misled by the marketing version.
> - Estimate the cost-and-latency penalty of long context vs. retrieval.

![Decision tree of four questions routing a query to long context, RAG, or per-query routing.](diagrams/00-hero-long-context-vs-rag.svg)
*Four questions decide it; most production systems route per query rather than pick once.*

---

## 1. The temptation

By early 2026 the frontier windows are, roughly: Gemini 2.5 up to ~2 M tokens (Google, "Long context," Gemini API docs, 2024–25); Claude Opus 4.x and Sonnet 4.5 at 1 M; the smaller and cheaper tiers (Claude Haiku 4.5, most open-weight models) at 200 k. (Names and figures are current as of early 2026; providers change both often.) A 1-million-token context window can hold roughly the entire user manual for a complex product, an entire codebase of moderate size, a hundred customer-support transcripts, or a year of meeting notes. The pitch is irresistible: stop building retrieval pipelines, just paste the corpus in. *"Long context killed RAG"* became a recurring refrain in the technical community across 2024 and 2025 (offered here as colour, not a sourced claim).

The pitch is wrong in detail and right in spirit. **It killed *trivial* RAG.** Specifically, the use case where someone built a vector store to retrieve from a 50-page document; that case is now better served by loading the document. But *real* RAG corpora are bigger, more dynamic, and structurally different from "a 50-page document"; they are not going anywhere.

The job of this post is to draw the boundary precisely.

---

## 2. The four-question test

Apply these in order.

**Question 1. Does the corpus fit in one context window, with budget left for the conversation?**

If the corpus is a single 30-page contract and the model has a 200 k window, the answer is yes. Load the whole document; skip retrieval; cache the prefix. If the corpus is a 200 GB collection of customer documents, the answer is no, and the question is closed: retrieval it is.

The threshold worth keeping in mind: even a 1 M-token model has practical room for a corpus rather smaller than the raw window. As a rule of thumb, reserve roughly 30% of the window for the conversation, the system prompt, tool schemas, and the output, leaving ~700 k tokens of corpus in a 1 M window before quality and cost get unpleasant. (The 30% haircut is illustrative; the exact reserve depends on your prompt and how much the model must generate, and the benchmark degradation in §3 is the deeper reason not to fill the window to the brim.) Most production corpora are larger.

**Question 2. Is the corpus stable enough to cache?**

Long context is only affordable with prompt caching ([Post 14](../14-system-prompt-as-software/index.md), §5). Caching requires the prefix not to change. If the corpus updates daily (a customer's evolving project state), the cache will miss often; the cost calculation flips. RAG with incremental indexing handles this naturally.

**Question 3. Does each query need most of the corpus, or just a small slice?**

A summarisation query of a single document needs the whole document. A factoid lookup against a knowledge base needs one paragraph. The first wins with long context; the second wins with RAG, every time, on cost and latency.

A pattern that helps: bucket your real query log into "global" vs. "local" queries; if global is rare, RAG with occasional whole-document loads beats always-long-context.

**Question 4. Can the model actually use the long context for this task?**

This is the question the marketing diagrams never answer. Long-context models advertise a window; they do not all *use* it equally. Section §3 covers what the benchmarks say.

---

## 3. What long-context benchmarks really show

![Five long-context benchmarks with what each adds to the task, what it finds, and whether performance degrades](diagrams/01-benchmark-gap.svg)

*Read down the last column: the one benchmark that barely degrades is the one the marketing is built on.*

A short tour of the empirical situation as of early 2026.

**Needle-in-a-haystack (NIAH).** The best-marketed test: hide a single random fact (the "needle") inside a long context, ask the model to retrieve it. Modern frontier models (Claude Opus 4.x and Sonnet 4.5, Gemini 2.5, and current frontier GPT models) score in the high nineties on standard single-needle NIAH well past 100 k tokens, and stay strong toward the top of their advertised windows. Those specific percentages are illustrative of the pattern rather than pinned to one vendor's leaderboard; the point is that this benchmark is behind the "long context just works" pitch.

**RULER (Hsieh et al., 2024).** Adds variations to NIAH: multi-needle (find multiple facts), multi-key (correct fact lookup with distractors), multi-value (one key, multiple values, return all), variable tracking (resolve a chain of references). RULER reports "effective context length" well short of the advertised window: models that saturate single-needle NIAH fall off substantially on these harder subtasks as length grows, and the gap widens the further you push toward the window edge (Hsieh et al., 2024). The "I can find one needle" capability does not generalise to "I can do retrieval-equivalent tasks at length"; the exact per-model figures live in the RULER paper's tables.

**BABILong (Kuratov et al., 2024).** Adds reasoning steps over the long context. Performance degrades sharply with reasoning depth: for example, models that handle one-hop questions comfortably struggle with three-hop questions at the same length. The paper's headline is that most models use a small fraction of their nominal window effectively once reasoning is required (Kuratov et al., 2024).

**LongBench (Bai et al., 2024).** Diverse real-world tasks (QA, summarisation, code completion, few-shot learning) at varied lengths. The robust qualitative finding: tasks where the answer is a small extract from a known location degrade gracefully, while tasks requiring synthesis across the document degrade sharply as length grows (Bai et al., 2024). (Treat any specific crossover length as illustrative; it moves with model and task.)

**MRCR (Multi-Round Co-reference Resolution).** Multi-turn conversations where reference resolution depends on long history, part of the Michelangelo suite (Vodrahalli et al., 2024). Accuracy on these co-reference tasks drops markedly as the relevant history moves deeper into the window, even for models that handle the same task trivially at short lengths (Vodrahalli et al., 2024). The precise accuracy-vs-length curve is in the Michelangelo paper; the shape, not the exact numbers, is what matters here.

The honest summary: **the *retrieval* part of long-context use works well; the *synthesis and reasoning* part degrades faster than the window size suggests.** A 1 M-token model is not a 1 M-token reasoner.

This is the empirical foundation of the decision framework. Long context is great when the task is "find this thing in this big pile". RAG is still the right answer when the task involves complex reasoning over a curated subset, because the *curated subset* is what the model can actually reason over well.

---

## 4. When long context wins

![Where long context wins and where RAG wins, as two lists read against each other](diagrams/02-when-each-wins.svg)

*Neither column is a default for the other's cases, and the left one holds only while the prefix stays cacheable.*

Concrete cases where loading the corpus beats retrieving from it.

- **Single-document workflows.** Reviewing a contract, summarising a paper, debugging a single repository. The whole document fits, every query is "global" or "local within this document", and the prefix cache amortises cost across the session.
- **Few-shot learning with many examples.** Some tasks (specialised classification, structured extraction in a niche domain) benefit from 50–200 in-context examples. Loading them all and caching beats retrieving subsets per query.
- **Conversational coherence over long sessions.** A coding session that has touched many files; loading the relevant files into context beats reconstructing them via retrieval each turn.
- **Low-volume, high-stakes queries.** A legal review where a single query might cost $5; the human cost of a wrong answer dwarfs the model bill.

In each case, *the value of having the model see everything together exceeds the cost of having it pay for everything.* The cost only becomes acceptable with caching; without it, even these cases lose.

---

## 5. When RAG wins

Concrete cases where retrieval beats long context.

- **Large or unbounded corpora.** Anything bigger than the practical-use threshold of a long-context model. Most production knowledge bases.
- **Frequently-updating corpora.** Cache invalidation kills the long-context economics.
- **High query volume, low query value.** A consumer search assistant runs millions of queries; even small per-query savings dominate.
- **Strong precision requirements.** RAG with reranking gives the model a small, focused context; long context dilutes attention with surrounding material.
- **Multi-tenant or per-user data.** A corpus that differs by user; loading the *user's* data is fine; loading *every* user's data is not.

The pattern: RAG remains the right default for production knowledge systems, search-style assistants, and any workload where the corpus exceeds what the model can comfortably hold or cache.

---

## 6. Hybrid: the production reality

The interesting answer is rarely either-or. A serious production system has a router ([Post 17](../17-advanced-retrieval/index.md), §6) that picks per query.

A reference setup for an enterprise agent over both unstructured documents and structured data:

```
user query
  ├─ small ad-hoc lookup  →  RAG (top-5 chunks, reranked)
  ├─ whole-document task  →  long-context load (with prefix cache)
  ├─ multi-document syn.  →  RAG (top-15 chunks, reranked, larger pack)
  └─ structured query     →  text-to-SQL
```

*A query router for a hybrid stack. The top-k pack sizes (top-5 / top-15 / top-30) are illustrative defaults, not tuned recommendations; the right value depends on your reranker and query mix. ("top-k" is the number of retrieved chunks kept after ranking.)*

Each route has its own cost profile and its own quality metric. The router is itself a small classifier ([Post 17](../17-advanced-retrieval/index.md), §6) tuned and evaluated against a labelled query set. The end-to-end answer-quality lift from getting the routing right is often larger than any single component improvement, because the *wrong* technique on the *wrong* query is the difference between a useful answer and a wasted call.

A second hybrid pattern that recurs: **RAG to a long-context call**. Retrieve the top-30 candidates (oversampled), pack them into a long-context model, let the model synthesise. This combines retrieval's precision (you avoid loading the whole corpus) with long context's synthesis ability (the model sees every candidate together). Slower and more expensive than top-5 with a small model, but substantially higher quality on questions that span multiple sources.

---

## 7. Cost arithmetic

A worked comparison for an illustrative knowledge-assistant workload (1 000 queries / day, 200 k corpus). The per-token rates below are Claude Opus 4.x-tier list prices as of early 2026, roughly $5 / 1 M input tokens (Anthropic, "Pricing," 2026); providers change these often, so check the current page. Cache reads run at about 10% of the base input rate for Anthropic (Anthropic, "Prompt caching," 2024).

**Option A: Long context always.** Each query loads the 200 k corpus plus the user turn. Without caching: 200 k input at ~$5 / 1 M ≈ $1 / query → ~$1 000 / day. With caching, the cached prefix reads at ~10% of input (~$0.10 / query) plus a small uncached suffix (~$0.01) → ~$110 / day.

**Option B: RAG.** Retrieval costs: ~$0.001 / query (embedding plus rerank). The LLM call sees ~5 k input tokens and ~500 output → ~$0.02 / query → ~$20 / day.

**Option C: Hybrid (10% long, 90% RAG).** ~$11 (the long-context tenth) plus ~$18 (the RAG nine-tenths) → ~$29 / day.

The exact figures move with model and provider, but the *ratios* are roughly stable: long-context-with-caching is on the order of 5× the cost of well-engineered RAG, and long-context-without-caching is on the order of 50× (illustrative, derived from the per-token rates above). Hybrid stays close to RAG's cost while picking up long context's quality on the cases that need it.

The cost-quality Pareto frontier almost always lives at hybrid; pure long-context is paying for capability you do not use on most queries.

---

## 8. The forecast

A few directions worth tracking.

- **Larger contexts will keep coming.** From 200 k to 1 M and beyond (Gemini 2.5 already reaches ~2 M), and vendors are demonstrating research prototypes past that. The reasoning quality at the back of the window will keep improving, but slower than the size grows.
- **Caching will keep getting better.** Per-call effective costs of long context will keep dropping. The long-context-vs-RAG line will move further toward long context for medium corpora.
- **RAG quality will keep improving.** Better embedders, better rerankers, better routers. The retrieval line is also moving.
- **Hybrid wins for the foreseeable future.** Neither extreme is the right architecture for production workloads at scale.

The architectural lesson: **build a router, not a religion**. Teams that bet on "long context will replace retrieval" or "retrieval will always win" both lose. Teams that build the router get to ride the curve.

---

## Common pitfalls

- **Loading the full corpus on every query.** Without caching, the bill is unaffordable.
- **Trusting NIAH as evidence the model can reason at length.** It cannot.
- **Choosing long context because retrieval was hard.** Fix the retrieval; long context is the more expensive bandage.
- **Choosing RAG when the corpus fits and is stable.** Loading is simpler and often better.
- **No router.** The wrong technique runs on the wrong query half the time.
- **No per-route eval.** Improvements regress silently across the boundary.

---

## Further reading

- Hsieh, C.-P. *et al.*, *"RULER: What's the Real Context Size of Your Long-Context Language Models?"* (NVIDIA, 2024): the effective-context-length figures behind §3.
- Kuratov, Y. *et al.*, *"In Search of Needles in a 11M Haystack: Recurrent Memory Finds What LLMs Miss"* (2024): BABILong.
- Bai, Y. *et al.*, *"LongBench: A Bilingual, Multitask Benchmark for Long Context Understanding"* (2024).
- Vodrahalli, K. *et al.*, *"Michelangelo: Long Context Evaluations Beyond Haystacks"* (Google DeepMind, 2024): the MRCR co-reference variants cited in §3.
- Google, *"Long context"* (Gemini API documentation, 2024–25): the ~2 M-token Gemini window.
- Gemini Team, *"Gemini 1.5: Unlocking multimodal understanding across millions of tokens of context"* (2024): the foundational long-context report (the current running example is Gemini 2.5).
- Anthropic, *"Pricing"* (Anthropic, 2026): the per-token rates used in the §7 cost arithmetic; check the live page, prices change often.
- Anthropic, *"Prompt caching"* (Anthropic documentation, 2024–25): the ~10%-of-input cache-read rate used in §7.
- Anthropic, *"Long context prompting for Claude 2.1"* (2023): early discussion still relevant.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 26 — The modern agentic workflow](../26-modern-agentic-workflow/index.md)**: context engineering inside Claude Code, Cursor, Aider.
- **[Post 11 — RAG in depth](../11-rag-in-depth/index.md)**: the retrieval side of the trade-off.
- **[Post 17 — Advanced retrieval](../17-advanced-retrieval/index.md)**: the router that picks the right technique.
