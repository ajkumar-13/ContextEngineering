# 12 · Compress strategies

> **TL;DR.** *Compress* is the operation that shrinks what is already in the context window. Six techniques cover almost every production system: **windowing**, **summarisation**, **tool-result clearing**, **priority pruning**, **semantic chunking**, and **prompt-level token compression** (LLMLingua-style). Each has a sweet spot, a token-reduction range, and what this post calls an **information retention ratio (IRR)** (a teaching construct, not a standard metric): the fraction of key facts that survive. A good compression policy mixes two or three of them under a clear trigger and is measured every release.
>
> **After reading this you will be able to:**
> - Pick the right compression technique for a given layer and failure mode.
> - Set sensible auto-compaction triggers and tell `/compact` apart from `/clear`.
> - Measure information retention so the next "summary" change does not silently regress quality.

![Timeline of context-window usage climbing to the compaction trigger, where /compact swaps the older history for a much smaller summary, dropping usage and freeing window space, with an information retention ratio of about 85 per cent annotated.](diagrams/00-hero-compress-strategies.svg)
*Compaction buys back window space at the price of fidelity; the goal is to lose only what will not be needed.*

---

## 1. Why compression is the day-to-day discipline

Most long-running agents reach a moment, around 80 % of the context window, where the next decision is *cheap and lossy* (truncate something) or *expensive and lossless* (issue a smaller, denser representation of what is already there). The first option is what frameworks default to; the second is what well-engineered systems do.

The framing this post uses comes directly from production agent debuggers (Anthropic's auto-compaction in Claude Code, Cursor's history compression, the LangGraph compress nodes). All of them implement a variant of the six techniques below.

A useful rule of thumb (illustrative, not a measured constant): a well-tuned compression pass typically reaches **70–90 % token reduction** while keeping most of the facts that matter. Beyond that, retention drops sharply, the familiar compression-versus-quality knee documented for prompt compressors such as LLMLingua (Jiang et al., 2023): the last slice of compression tends to cost a disproportionate share of the facts. The per-technique reduction and IRR figures throughout this post are illustrative planning ranges from production practice, not benchmark results; measure your own with the replay set in §8.

---

## 2. Technique 1: windowing

**Operation.** Drop everything older than the last *N* turns or *M* tokens.

**When it works.** When the task is genuinely local: short tool-use loops, recent-context-only assistants, latency-sensitive UIs.

**When it breaks.** Anything with cross-turn dependencies. The classic failure: the user said "remember Alice is the project lead" twelve turns ago; window of 8 turns drops it; the agent now refers to the project lead as "the user" because that is the most recent salient noun.

**Token reduction.** 50–90 %, depending on window size.
**IRR.** 100 % within the window, 0 % outside it. Bimodal, which is why pure windowing fails alone.

**Tuning.** Two refinements that lift IRR without ballooning cost:

- **Pin the system prompt and the first turn.** They almost always carry rules and goals that need to outlive the window.
- **Pin "important" turns** explicitly: turns the user marked, turns the agent flagged as containing decisions, turns where a tool wrote to long-term memory.

Windowing is the cheapest technique on this list and the most often used as a default. It is rarely the right *only* technique.

---

## 3. Technique 2: summarisation

**Operation.** Replace a span of older context with an LLM-generated (large-language-model-generated) summary of that span.

**When it works.** Long conversations where the *gist* of the past matters but the *exact phrasing* does not. Project meetings, multi-turn research, customer-support sessions.

**When it breaks.** Anywhere the exact wording matters: code, legal text, tool outputs that will be re-cited. A summary of a stack trace is useless; the agent needed the line numbers.

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

The prompt explicitly enumerates what to keep, in priority order, and explicitly bans filler. The output is half the size of an unstructured summary, with higher retention.

Three variants are worth naming. **Rolling summarisation** keeps a single running summary and folds each new batch of turns into it. **Hierarchical summarisation** builds a tree: summarise turns 1–20, then later compress that summary together with turns 21–40; it stays coherent across thousands of turns but multiplies cost, so reserve it for genuinely long sessions. **Structured summarisation** produces one digest per topic rather than one chronological digest (that is semantic chunking, §6).

The rolling variant is the one most systems ship first. A minimal, runnable implementation with the direct Anthropic SDK:

```python
from anthropic import Anthropic

client = Anthropic()
MODEL = "claude-sonnet-4-5"  # names/prices current as of early 2026; check the provider's page

def fold(summary: str, new_turns: list[str], target_tokens: int = 300) -> str:
    """Fold new turns into a running summary, preserving decisions and facts."""
    prior = f"Existing summary:\n{summary}\n\n" if summary else ""
    convo = "\n".join(new_turns)
    prompt = (
        f"{prior}New turns to fold in:\n{convo}\n\n"
        "Rewrite the summary for the agent that will continue this conversation. "
        "Preserve, in order: decisions and their reasoning; open questions; "
        "user-stated facts and preferences; tool conclusions (not verbatim output). "
        f"No politeness or filler. Bullet points, <= {target_tokens} tokens."
    )
    msg = client.messages.create(
        model=MODEL, max_tokens=target_tokens + 100,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text

# Usage: fold each batch of turns into the running summary as the budget fills.
running = ""
for batch in batches_of_turns:          # your turn buffer, chunked
    running = fold(running, batch)
```
---

## 4. Technique 3: tool-result clearing

**Operation.** After a tool call, extract the bits the agent needed and drop the verbatim body.

**When it works.** Almost always. This is the most under-used technique in the field.

A web-search tool returns 8 KB of result snippets. The agent reads them, decides which two URLs to fetch, and proceeds. The 8 KB stays in context for the rest of the session, paid for on every subsequent call, contributing only distraction. Replacing the body with `[search results: 2 URLs selected, see fetch outputs]` reclaims the 8 KB at zero quality cost, and if the agent ever needs the original results, it can re-issue the call (deterministic and cheap).

**Token reduction.** 70–95 % of tool-result tokens, often the largest single line item in a long agent run.
**IRR.** Effectively 100 %, because the result is *re-callable* on demand.

**The principle.** Tool calls with deterministic, cheap-to-re-issue results are *safe to clear*. Tool calls with expensive, non-deterministic, or stateful results (a payment, a write, an API call that costs $1) are not; those should be summarised, not cleared.

In practice this technique alone can push the auto-compaction trigger a long way further into the session (a large fraction, though the exact figure is workload-specific and worth measuring, not a fixed constant). Implement it before reaching for windowing or summarisation.

---

## 5. Technique 4: priority pruning

**Operation.** Assign every layer (or every chunk within a layer) a priority class. When over budget, trim from the lowest class first.

**When it works.** Multi-layer prompts (most production systems) where the layers have clearly different importance. The system prompt is more important than tool results; the latest user turn is more important than the third-most-recent retrieved chunk.

**Token reduction.** 20–60 %, depending on how aggressive the trimming is.
**IRR.** 90–100 % on the high-priority classes; 0 % on the trimmed ones (which is the point).

**A practical four-class scheme** that works as a default for most agents:

| Class | Contents | Trim policy |
|---|---|---|
| **P0** | System prompt, identity, hard rules | Never trim |
| **P1** | Last 3 user turns, current goal | Never trim until budget is impossible to meet |
| **P2** | Older history, retrieved RAG chunks (retrieval-augmented generation) beyond the top-3 (the *k* highest-scoring retrieved chunks) | Trim first |
| **P3** | Stale tool results, expired memory entries | Trim eagerly; clear by default |

Implementation is mechanical: tag every entry with its class as it lands in the budget; sort by class then by recency; pop from the bottom until the budget fits.

Priority pruning composes well with the other techniques. Most production systems use it as the *default* trim mechanism and reach for summarisation only when even P2 trimming cannot rescue the budget.

---

## 6. Technique 5: semantic chunking

**Operation.** Group context by topic, summarise each topic independently, recombine.

**When it works.** Sessions that have moved across multiple distinct sub-topics. A coding session that touched authentication, then billing, then a UI bug benefits from three small topic-summaries more than one long chronological summary.

**When it breaks.** Sessions that are tightly intertwined; sessions that are short enough that simpler techniques suffice.

**Token reduction.** 80–95 %.
**IRR.** 85–95 %, typically the highest of the lossy techniques, because the topical structure preserves more relationship information.

**Cost.** Highest on this list. Topic detection adds a clustering pass; per-topic summarisation multiplies LLM cost by the number of topics. Reserve for long-lived sessions where the cost amortises over many future turns.

A simple-but-effective implementation: every *N* turns, embed each turn, run a small clustering algorithm (density- and hierarchy-based methods such as HDBSCAN or agglomerative clustering, or even k-means with a sensible number of clusters *k*), summarise each cluster with the prompt template from §3, replace the original turns with the summaries. This is the *structured* variant of summarisation: instead of one chronological digest, you produce one digest per detected topic.

---

## 7. Technique 6: prompt-level token compression (LLMLingua, RECOMP)

The five techniques above all operate at the granularity of turns, tool results, or topics. A different family compresses at the granularity of *tokens*: it deletes or rewrites individual words a downstream model can afford to lose, leaving the prompt readable enough for the model but shorter on the wire.

**LLMLingua** (Jiang et al., 2023) uses a small language model to score each token's *perplexity* (roughly, how surprising or informative it is) and drops the low-information tokens: articles, redundant phrasing, boilerplate. The authors report up to ~20x prompt compression with little task-performance loss on their benchmarks. **LLMLingua-2** (Pan et al., 2024) reframes the same idea as a supervised token-classification task (keep or drop) trained on a distillation dataset, which makes it faster and more faithful than the original perplexity heuristic. Because the compressed prompt is no longer fluent English, this is a machine-to-machine technique: fine for a retrieval context or a long reasoning trace, wrong for anything a human will read back.

**RECOMP** (Xu et al., 2023) is the RAG-specific cousin. Instead of pruning tokens uniformly, it trains two compressors that run *before* the answer model sees the retrieved documents: an *extractive* one that selects the most useful sentences, and an *abstractive* one that summarises multiple documents into a short synthesis. The point is the same as tool-result clearing (§4): shrink the retrieved payload before it costs tokens on every subsequent turn, without throwing away the facts the answer depends on.

**When it works.** Fixed, verbose context you feed a model many times: long RAG contexts, few-shot exemplar blocks, static instruction preambles. The compressor pays for itself when the same block is re-sent across many calls.

**When it breaks.** Anything a human reads, anything re-cited verbatim, and short prompts where the extra compressor call costs more than it saves. Token-level pruning also interacts badly with prompt caching: if you rewrite the prefix on every call you lose the cache-read discount ([Post 03](../03-how-llms-read-context/index.md), §6), so compress the *stable* part once and cache it, rather than re-compressing each turn.

**Token reduction.** Reported figures reach several-fold to ~20x on the source benchmarks (Jiang et al., 2023); treat those as an upper bound and measure on your own traffic. This is the only technique here that needs a separate model in the loop, so budget for its latency and cost.

---

## 8. Two Claude Code commands: `/compact` vs `/clear`

If you use Claude Code, two of its slash commands map directly onto the techniques above, and conflating them is a common mistake.

- **`/compact`** is *summarisation* (§3) applied to the whole conversation: it replaces the running history with an LLM-generated summary and keeps going. You reach for it, or let auto-compaction reach for it, when the gist of the session must survive but the token bill has grown too large. Auto-compaction is the same operation fired automatically as the budget fills (Anthropic, 2024–25).
- **`/clear`** is a *full reset*: it drops the conversation entirely and starts fresh. It is the degenerate case of *windowing* (§2) with a window of zero. Use it at a genuine task boundary, when nothing from the previous exchange needs to carry forward.

Note that Claude Code's `/clear` (reset the whole conversation) is not the same as this post's **tool-result clearing** (§4), which surgically drops one verbose tool body while leaving the rest of the conversation intact. Same verb, very different blast radius. The rule of thumb: `/compact` when you want to keep the thread but shrink it; `/clear` when the thread is done; tool-result clearing continuously, in the background, regardless of either.

---

## 9. The two triggers: 80 % and 95 %

A compression *policy* is two thresholds and a reaction at each. The two numbers below are illustrative defaults (a useful starting point, not a measured law); tune them to your own token-usage variance.

- **At 80 % of the budget (*soft trigger*).** Run the cheap operations: tool-result clearing, P3 priority pruning. If this brings the prompt under 60 %, stop. This is the routine maintenance pass; it should happen frequently enough that the user never notices.
- **At 95 % of the budget (*hard trigger*).** Run summarisation or semantic chunking on the older portion of the conversation. The agent surfaces a brief notice ("Compressing earlier conversation to free space"). The compressed turns are kept verbatim in a separate log for debugging.

The thresholds are not magic. 80 % is far enough below the limit to give the next few turns headroom; 95 % is close enough that waiting risks overflow. Move both downward when token-usage variance is high (long tool outputs, deep RAG); upward when it is low.

**Anti-pattern: compress on every turn.** The token cost of running summarisation eight times an hour usually exceeds the savings. Compress on triggers, not on schedule.

---

## 10. Measuring information retention

A summary that drops the fact the next turn needed is not a summary; it is a regression. The way to detect this before it ships:

- **A small replay set.** 20–50 conversations from production, with the next-turn ground-truth answer recorded.
- **The metric.** Run the conversation through the new compression policy; ask the model to answer the next turn; score whether the answer matches the ground truth. The IRR-equivalent is the fraction that match.
- **The gate.** A new compression prompt that drops IRR by more than the noise floor blocks merge.

If you want a public benchmark to calibrate against rather than only your own replay set, long-context task suites such as LongBench (Bai et al., 2024) measure how much task quality a given compression pass costs across many tasks; use them to sanity-check a technique before trusting it on your own traffic.

This is the same gate as the RAG eval ([Post 11](../11-rag-in-depth/index.md), §6) and the same overall pattern as system-level eval ([Post 20](../20-evaluation/index.md)). A team that ships compression without this gate is shipping silent regressions.

---

## 11. Picking among the six

A short decision sketch.

- **Default: priority pruning + tool-result clearing.** Cheap, predictable, composable. Most systems should ship with these two on from day one.
- **Add summarisation** when the conversation length itself is the bottleneck and the gist suffices.
- **Add semantic chunking** when the conversation has multiple long-running threads and a single chronological summary loses the structure.
- **Add prompt-level compression (§7)** only for large, fixed context you re-send many times, and only when it can coexist with caching.
- **Use windowing only** when the task is genuinely local; otherwise use it *with* pinned-turn refinements (§2).

The ordering matters: clearing and pruning give you headroom that lets the more expensive techniques stay infrequent.

---

## 12. When compression is the wrong answer

Compression is lossy by construction, so the honest limit of this whole post is: sometimes the right move is not to shrink the context but to *not put it there in the first place*. That is the **Isolate** operation ([Post 13](../13-isolate-strategies/index.md)), and it is the correct answer whenever compression would force you to throw away something you cannot afford to lose.

Reach for Isolate instead of Compress when:

- **The material is exact and irreplaceable.** Code, legal text, financial figures, verbatim tool outputs that will be re-cited. Any lossy pass corrupts them; hand the work to a sub-agent whose isolated context holds the full text, and return only the conclusion.
- **The context is really several unrelated jobs.** If a session keeps three loosely-related threads alive at once, compressing the combined history fights the confusion failure mode (Post 06) instead of curing it. Splitting the threads into separate isolated contexts removes the tokens entirely rather than summarising them.
- **You need auditability.** A summariser that silently drops a fact leaves no trace; a sub-agent boundary makes the hand-off explicit and inspectable.

Compression and isolation are complementary, not rivals: compress *within* a context to keep it under budget, isolate *across* contexts so no single window has to hold everything. When a compression policy starts fighting its own IRR, that is the signal to isolate rather than compress harder.

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

- Anthropic, *"Claude Code"* documentation (auto-compact and the conversation budget) (2024–25): production reference implementation for `/compact` and auto-compaction.
- Martin, L., *"Context Engineering for Agents"* (LangChain blog, 2025): the windowing / summarisation / pruning taxonomy this post follows.
- Jiang, H. *et al.*, *"LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models"* (2023): perplexity-based prompt-token compression, with the compression-versus-quality curves referenced in §1 and §7.
- Pan, Z. *et al.*, *"LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression"* (2024): the supervised token-classification successor.
- Xu, F. *et al.*, *"RECOMP: Improving Retrieval-Augmented LMs with Compression and Selective Augmentation"* (2023): extractive and abstractive compression of retrieved documents.
- Bai, Y. *et al.*, *"LongBench: A Bilingual, Multitask Benchmark for Long Context Understanding"* (2024): a benchmark for measuring how much task quality a compression pass costs (§10).
- Liu, N. *et al.*, *"Lost in the Middle: How Language Models Use Long Contexts"* (TACL 2024; arXiv 2023): the empirical motivation for compression even when the window allows.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 13 — Isolate strategies](../13-isolate-strategies/index.md)**: the structural alternative to compression.
- **[Post 04 — Tokens, windows, budgets](../04-tokens-windows-budgets/index.md)**: the budget the compression policy serves.
- **[Post 20 — Evaluation](../20-evaluation/index.md)**: the harness that catches IRR regressions.
