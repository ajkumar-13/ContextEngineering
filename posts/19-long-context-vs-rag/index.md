# 19 · Long context vs. RAG — a decision framework

> **TL;DR.** Frontier models now ship with context windows of 200 k, 1 M, even 10 M tokens. The question every team eventually asks: *"do we still need RAG?"* The honest answer is **yes, almost always — but the boundary has moved**. This post is the decision framework: when long context wins, when RAG wins, when the right answer is a hybrid, and what the recent benchmarks (RULER, BABILong, LongBench, MRCR, NIAH) actually tell us about how well long-context models *use* the room they have.
>
> **Reading time:** ~12 minutes.
>
> **After reading this you will be able to:**
> - Match a workload to long context, RAG, or a hybrid using a four-question test.
> - Read the current long-context benchmarks without being misled by the marketing version.
> - Estimate the cost-and-latency penalty of long context vs. retrieval.

---

## 1. The temptation

A 1-million-token context window can hold roughly the entire user manual for a complex product, an entire codebase of moderate size, a hundred customer-support transcripts, or a year of meeting notes. The pitch is irresistible: stop building retrieval pipelines, just paste the corpus in. *"Long context killed RAG"* — a recurring thread on technical Twitter throughout 2024 and 2025.

The pitch is wrong in detail and right in spirit. **It killed *trivial* RAG.** Specifically, the use case where someone built a vector store to retrieve from a 50-page document — that case is now better served by loading the document. But *real* RAG corpora are bigger, more dynamic, and structurally different from "a 50-page document"; they are not going anywhere.

The job of this post is to draw the boundary precisely.

---

## 2. The four-question test

Apply these in order.

**Question 1 — Does the corpus fit in one context window, with budget left for the conversation?**

If the corpus is a single 30-page contract and the model has a 200 k window, the answer is yes. Load the whole document; skip retrieval; cache the prefix. If the corpus is a 200 GB collection of customer documents, the answer is no, and the question is closed: you are doing retrieval.

The threshold worth keeping in mind: even a 1 M-token model has practical room for ~700 k tokens of corpus before quality and cost get unpleasant. Most production corpora are larger.

**Question 2 — Is the corpus stable enough to cache?**

Long context is only affordable with prompt caching ([Post 12](../12-system-prompt-as-software/index.md), §5). Caching requires the prefix not to change. If the corpus updates daily (a customer's evolving project state), the cache will miss often; the cost calculation flips. RAG with incremental indexing handles this naturally.

**Question 3 — Does each query need most of the corpus, or just a small slice?**

A summarisation query of a single document needs the whole document. A factoid lookup against a knowledge base needs one paragraph. The first wins with long context; the second wins with RAG, every time, on cost and latency.

A pattern that helps: bucket your real query log into "global" vs. "local" queries; if global is rare, RAG with occasional whole-document loads beats always-long-context.

**Question 4 — Can the model actually use the long context for this task?**

This is the question the marketing diagrams never answer. Long-context models advertise a window; they do not all *use* it equally. Section §3 covers what the benchmarks say.

---

## 3. What long-context benchmarks really show

A short tour of the empirical situation as of late 2025.

**Needle-in-a-haystack (NIAH).** The best-marketed test: hide a single random fact inside a long context, ask the model to retrieve it. Modern frontier models (Claude 3.5+, GPT-4o, Gemini 1.5+) score 95–100 % on standard NIAH up to 200 k tokens, and 90 %+ at 1 M. This is the benchmark behind the "long context just works" pitch.

**RULER (Hsieh et al., 2024).** Adds variations to NIAH: multi-needle (find multiple facts), multi-key (correct fact lookup with distractors), multi-value (one key, multiple values, return all), variable tracking (resolve a chain of references). On these, frontier models that scored 99 % on NIAH score 60–80 % at 128 k and 40–70 % at 1 M. The "I can find one needle" capability does not generalise to "I can do retrieval-equivalent tasks at length".

**BABILong.** Adds reasoning steps over the long context. Performance degrades sharply with reasoning depth — models that handle one-hop questions at 64 k struggle with three-hop at the same length.

**LongBench.** Diverse real-world tasks (QA, summarisation, code completion, few-shot learning) at varied lengths. Roughly: tasks where the answer is a small extract from a known location degrade gracefully; tasks requiring synthesis across the document degrade sharply past 32 k–64 k.

**MRCR (Multi-Round Co-reference Resolution).** Multi-turn conversations where reference resolution depends on long history. Frontier models drop to 60 % accuracy at 128 k for tasks they handle at 99 % at 8 k.

The honest summary: **the *retrieval* part of long-context use works well; the *synthesis and reasoning* part degrades faster than the window size suggests.** A 1 M-token model is not a 1 M-token reasoner.

This is the empirical foundation of the decision framework. Long context is great when the task is "find this thing in this big pile". RAG is still the right answer when the task involves complex reasoning over a curated subset, because the *curated subset* is what the model can actually reason over well.

---

## 4. When long context wins

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

## 6. Hybrid — the production reality

The interesting answer is rarely either-or. A serious production system has a router (Post 15, §6) that picks per query.

A reference setup for an enterprise agent over both unstructured documents and structured data:

```
user query
  ├─ small ad-hoc lookup  →  RAG (top-5 chunks, reranked)
  ├─ whole-document task  →  long-context load (with prefix cache)
  ├─ multi-document syn.  →  RAG (top-15 chunks, reranked, larger pack)
  └─ structured query     →  text-to-SQL
```

Each route has its own cost profile and its own quality metric. The router is itself a small classifier (Post 15, §6) tuned and evaluated against a labelled query set. The end-to-end answer-quality lift from getting the routing right is often larger than any single component improvement, because the *wrong* technique on the *wrong* query is the difference between a useful answer and a wasted call.

A second hybrid pattern that recurs: **RAG to a long-context call**. Retrieve the top-30 candidates (oversampled), pack them into a long-context model, let the model synthesise. This combines retrieval's precision (you do not load the whole corpus) with long context's synthesis ability (the model gets to see them all together). Slower and more expensive than top-5 + small-model; substantially higher quality on questions that span multiple sources.

---

## 7. Cost arithmetic

A worked comparison for an illustrative knowledge-assistant workload (1 000 queries / day, 200 k corpus, frontier-model pricing as of 2025).

**Option A — Long context always.** Each query loads the 200 k corpus + the user turn. Without caching: ~$1 / query → $1 000 / day. With caching: ~$0.10 / query (cached prefix) + ~$0.01 (uncached suffix) → $110 / day.

**Option B — RAG.** Retrieval costs: ~$0.001 / query (embedding + rerank). LLM call: ~5 k input tokens, ~500 output → ~$0.02 / query → $20 / day.

**Option C — Hybrid (10 % long, 90 % RAG).** $11 + $18 → $29 / day.

The numbers move with model and provider, but the *ratios* are roughly stable: long-context-with-caching is ~5× the cost of well-engineered RAG; long-context-without-caching is ~50×. Hybrid is close to RAG's cost while picking up long context's quality on the cases that need it.

The cost-quality Pareto frontier almost always lives at hybrid; pure long-context is paying for capability you do not use on most queries.

---

## 8. The forecast

A few directions worth tracking.

- **Larger contexts will keep coming.** 10 M today, more tomorrow. The reasoning quality at the back of the window will keep improving but slower than the size grows.
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

- Hsieh, C.-P. *et al.*, *"RULER: What's the Real Context Size of Your Long-Context Language Models?"* (NVIDIA, 2024).
- Kuratov, Y. *et al.*, *"In Search of Needles in a 11M Haystack: Recurrent Memory Finds What LLMs Miss"* (2024) — BABILong.
- Bai, Y. *et al.*, *"LongBench: A Bilingual, Multitask Benchmark for Long Context Understanding"* (2024).
- Vodrahalli, K. *et al.*, *"Michelangelo: Long Context Evaluations Beyond Haystacks"* (2024) — MRCR variants.
- Gemini Team, *"Gemini 1.5: Unlocking multimodal understanding across millions of tokens of context"* (2024).
- Anthropic, *"Long context prompting for Claude 2.1"* (2023) — early discussion still relevant.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 20 — The modern agentic workflow](../20-modern-agentic-workflow/index.md)** — context engineering inside Claude Code, Cursor, Aider.
- **[Post 09 — RAG in depth](../09-rag-in-depth/index.md)** — the retrieval side of the trade-off.
- **[Post 15 — Advanced retrieval](../15-advanced-retrieval/index.md)** — the router that picks the right technique.
