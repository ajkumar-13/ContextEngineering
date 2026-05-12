# 10 · Compress strategies

> **TL;DR.** *Compress* is the operation that shrinks what is already in the context window. Five techniques cover almost every production system: **windowing**, **summarisation**, **tool-result clearing**, **priority pruning**, and **semantic chunking**. Each has a sweet spot, a token-reduction range, and an **information retention ratio (IRR)** — the fraction of key facts that survive. A good compression policy mixes two or three of them under a clear trigger and is measured every release.
>
> **Reading time:** ~12 minutes.
>
> **After reading this you will be able to:**
> - Pick the right compression technique for a given layer and failure mode.
> - Set sensible auto-compaction triggers (the 80 % / 95 % rule).
> - Measure information retention so the next "summary" change does not silently regress quality.

---

## 1. Why compression is the day-to-day discipline

Most long-running agents reach a moment, around 80 % of the context window, where the next decision is *cheap and lossy* (truncate something) or *expensive and lossless* (issue a smaller, denser representation of what is already there). The first option is what frameworks default to; the second is what well-engineered systems do.

The framing this post uses comes directly from production agent debuggers (Anthropic's auto-compaction in Claude Code, Cursor's history compression, the LangGraph compress nodes). All of them implement a variant of the five techniques below.

A useful number to keep in mind: a well-tuned compression pass typically achieves **70–90 % token reduction** at **80–95 % IRR**. Beyond that, IRR drops sharply — the last 5 % of compression eats the first 20 % of facts.

---

## 2. Technique 1 — windowing

**Operation.** Drop everything older than the last *N* turns or *M* tokens.

**When it works.** When the task is genuinely local — short tool-use loops, recent-context-only assistants, latency-sensitive UIs.

**When it breaks.** Anything with cross-turn dependencies. The classic failure: the user said "remember Alice is the project lead" twelve turns ago; window of 8 turns drops it; the agent now refers to the project lead as "the user" because that is the most recent salient noun.

**Token reduction.** 50–90 %, depending on window size.
**IRR.** 100 % within the window, 0 % outside it. Bimodal, which is why pure windowing fails alone.

**Tuning.** Two refinements that lift IRR without ballooning cost:

- **Pin the system prompt and the first turn.** They almost always carry rules and goals that need to outlive the window.
- **Pin "important" turns** explicitly — turns the user marked, turns the agent flagged as containing decisions, turns where a tool wrote to long-term memory.

Windowing is the cheapest technique on this list and the most often used as a default. It is rarely the right *only* technique.

---

## 3. Technique 2 — summarisation

**Operation.** Replace a span of older context with an LLM-generated summary of that span.

**When it works.** Long conversations where the *gist* of the past matters but the *exact phrasing* does not. Project meetings, multi-turn research, customer-support sessions.

**When it breaks.** Anywhere the exact wording matters — code, legal text, tool outputs that will be re-cited. A summary of a stack trace is useless; the agent needed the line numbers.

**Token reduction.** 80–95 %.
**IRR.** 70–95 % with a careful prompt; 40–60 % with a careless one.

**The summarisation prompt matters as much as the model.** A skeleton that consistently outperforms "summarise this conversation":

```
Summarise the conversation below for the agent that will continue it.
Preserve, in this order:
1. Decisions made, with the reasoning given.
2. Open questions and unresolved items.
3. User-stated facts and preferences.
4. Tool calls and their key results (only the conclusion, not the verbatim output).
Do NOT include politeness, recap, or filler.
Output as bullet points, ≤ {target_tokens}.
```

The prompt explicitly enumerates what to keep, in priority order, and explicitly bans filler. The output is half the size of an unstructured summary, with higher IRR.

**Hierarchical summarisation** — summarise turns 1–20, then later compress the summary itself with turns 21–40 — works well for very long sessions but multiplies cost; reserve it for sessions that genuinely need to stay coherent across thousands of turns.

---

## 4. Technique 3 — tool-result clearing

**Operation.** After a tool call, extract the bits the agent needed and drop the verbatim body.

**When it works.** Almost always. This is the most under-used technique in the field.

A web-search tool returns 8 KB of result snippets. The agent reads them, decides which two URLs to fetch, and proceeds. The 8 KB stays in context for the rest of the session, paid for on every subsequent call, contributing only distraction. Replacing the body with `[search results: 2 URLs selected, see fetch outputs]` reclaims the 8 KB at zero quality cost — and if the agent ever needs the original results, it can re-issue the call (deterministic and cheap).

**Token reduction.** 70–95 % of tool-result tokens, often the largest single line item in a long agent run.
**IRR.** Effectively 100 %, because the result is *re-callable* on demand.

**The principle.** Tool calls with deterministic, cheap-to-re-issue results are *safe to clear*. Tool calls with expensive, non-deterministic, or stateful results (a payment, a write, an API call that costs $1) are not — those should be summarised, not cleared.

This technique alone often delays the auto-compaction trigger by 30–50 % of the session length. Implement it before reaching for windowing or summarisation.

---

## 5. Technique 4 — priority pruning

**Operation.** Assign every layer (or every chunk within a layer) a priority class. When over budget, trim from the lowest class first.

**When it works.** Multi-layer prompts (most production systems) where the layers have clearly different importance. The system prompt is more important than tool results; the latest user turn is more important than the third-most-recent retrieved chunk.

**Token reduction.** 20–60 %, depending on how aggressive the trimming is.
**IRR.** 90–100 % on the high-priority classes; 0 % on the trimmed ones (which is the point).

**A practical four-class scheme** — works as a default for most agents:

| Class | Contents | Trim policy |
|---|---|---|
| **P0** | System prompt, identity, hard rules | Never trim |
| **P1** | Last 3 user turns, current goal | Never trim until budget is impossible to meet |
| **P2** | Older history, retrieved RAG chunks beyond top-3 | Trim first |
| **P3** | Stale tool results, expired memory entries | Trim eagerly; clear by default |

Implementation is mechanical: tag every entry with its class as it lands in the budget; sort by class then by recency; pop from the bottom until the budget fits.

Priority pruning composes well with the other techniques. Most production systems use it as the *default* trim mechanism and reach for summarisation only when even P2 trimming cannot rescue the budget.

---

## 6. Technique 5 — semantic chunking

**Operation.** Group context by topic, summarise each topic independently, recombine.

**When it works.** Sessions that have moved across multiple distinct sub-topics. A coding session that touched authentication, then billing, then a UI bug benefits from three small topic-summaries more than one long chronological summary.

**When it breaks.** Sessions that are tightly intertwined; sessions that are short enough that simpler techniques suffice.

**Token reduction.** 80–95 %.
**IRR.** 85–95 % — typically the highest of the lossy techniques, because the topical structure preserves more relationship information.

**Cost.** Highest on this list. Topic detection adds a clustering pass; per-topic summarisation multiplies LLM cost by the number of topics. Reserve for long-lived sessions where the cost amortises over many future turns.

A simple-but-effective implementation: every *N* turns, embed each turn, run a small clustering algorithm (HDBSCAN, agglomerative, or even k-means with a sensible k), summarise each cluster with the prompt template from §3, replace the original turns with the summaries.

---

## 7. The two triggers — 80 % and 95 %

A compression *policy* is two thresholds and a reaction at each.

- **At 80 % of the budget — *soft trigger*.** Run the cheap operations: tool-result clearing, P3 priority pruning. If this brings the prompt under 60 %, stop. This is the routine maintenance pass; it should happen frequently enough that the user never notices.
- **At 95 % of the budget — *hard trigger*.** Run summarisation or semantic chunking on the older portion of the conversation. The agent surfaces a brief notice ("Compressing earlier conversation to free space"). The compressed turns are kept verbatim in a separate log for debugging.

The thresholds are not magic. 80 % is far enough below the limit to give the next few turns headroom; 95 % is close enough that you cannot afford to wait. Adjust both downward if your token-usage variance is high (long tool outputs, deep RAG); upward if it is low.

**Anti-pattern: compress on every turn.** The token cost of running summarisation eight times an hour usually exceeds the savings. Compress on triggers, not on schedule.

---

## 8. Measuring information retention

A summary that drops the fact the next turn needed is not a summary; it is a regression. The way to detect this before it ships:

- **A small replay set.** 20–50 conversations from production, with the next-turn ground-truth answer recorded.
- **The metric.** Run the conversation through the new compression policy; ask the model to answer the next turn; score whether the answer matches the ground truth. The IRR-equivalent is the fraction that match.
- **The gate.** A new compression prompt that drops IRR by more than the noise floor blocks merge.

This is the same gate as the RAG eval ([Post 09](../09-rag-in-depth/index.md), §6) and the same overall pattern as system-level eval ([Post 16](../16-evaluation/index.md)). A team that ships compression without this gate is shipping silent regressions.

---

## 9. Picking among the five

A short decision sketch.

- **Default — priority pruning + tool-result clearing.** Cheap, predictable, composable. Most systems should ship with these two on from day one.
- **Add summarisation** when the conversation length itself is the bottleneck and the gist suffices.
- **Add semantic chunking** when the conversation has multiple long-running threads and a single chronological summary loses the structure.
- **Use windowing only** when the task is genuinely local; otherwise use it *with* pinned-turn refinements (§2).

The ordering matters: clearing and pruning give you headroom that lets the more expensive techniques stay infrequent.

---

## Common pitfalls

- **Skipping tool-result clearing.** The largest single line item in long agent runs.
- **Summarising when clearing would do.** Never compress a deterministic re-callable result; clear it.
- **No replay set.** Without it the next "improvement" silently regresses.
- **Compressing on every turn.** The cost is a hidden second LLM bill.
- **Treating windowing as a complete strategy.** It loses anything outside the window, no matter how important.
- **Compressing P0 / P1.** A "smarter" summariser will eventually try to summarise the system prompt. Pin it.

---

## Further reading

- Anthropic, *"Claude Code: auto-compact and the conversation budget"* (2024 docs) — production reference implementation.
- LangChain Blog, *"Context engineering for agents"* (2025) — the windowing / summarisation / pruning taxonomy.
- Bai, Y. *et al.*, *"LongBench: A Bilingual, Multitask Benchmark for Long Context Understanding"* (2024) — measures compression quality.
- Liu, N. *et al.*, *"Lost in the middle: How language models use long contexts"* (2023) — the empirical motivation for compression even when the window allows.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 11 — Isolate strategies](../11-isolate-strategies/index.md)** — the structural alternative to compression.
- **[Post 04 — Tokens, windows, budgets](../04-tokens-windows-budgets/index.md)** — the budget the compression policy serves.
- **[Post 16 — Evaluation](../16-evaluation/index.md)** — the harness that catches IRR regressions.
