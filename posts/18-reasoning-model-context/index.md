# 18 - Context for reasoning models

> **TL;DR.** A reasoning model spends thinking tokens before, and between, the tokens of its answer; they are billed as output, they occupy the window, and on some models they stay in the history. This post budgets thinking as its own line at three effort levels, shows how adaptive thinking is steered with an effort level instead of a fixed token budget, and keeps the text of a reasoning trace out of the application's layers, the cached prefix and long-term memory.
>
> **Prerequisites:** [Post 04](../04-tokens-windows-budgets/index.md).
> **Safe to skip?** Skip it if every token budget already has a thinking line, and what a changed effort level or a copied trace does to the cache is already familiar.
>
> **After reading, you will be able to:**
>
> - Budget thinking tokens as a separate output line, priced at the output rate, and size the output cap and the window to hold them.
> - Choose an effort level per task instead of one global setting, knowing that changing it inside a cached conversation restarts the cache.
> - Keep the text of reasoning traces out of the application's own layers, the cached prefix and long-term memory, while passing thinking blocks back unchanged.
> - Budget an interleaved tool-use loop as one thinking segment per step, and keep its trail of tool calls and results at full fidelity.
> - Decide when thinking can replace a hand-built reasoning step and when low effort, retrieval or a tool call is the better choice.

![Three dashed bars for one hard turn on Claude Opus 4.6 at low, medium and high effort: the same 10,500 input tokens by layer, then 1,000, 4,000 or 16,000 thinking tokens and a 1,500-token answer, costing 0.09430, 0.16930 and 0.46930 dollars.](diagrams/01-thinking-in-the-budget.svg)

*The input does not change with the effort level; the thinking line does, and at high effort it outweighs the whole prompt.*

---

## 1. The question: is a million-token reader a million-token reasoner?

Claude Opus 4.6, this series' frontier model as of early 2026, has a context window of 1,000,000 tokens (Anthropic, "Context windows", consulted October 2026, as [post 04](../04-tokens-windows-budgets/index.md) cites it). It is tempting to read that number as a capacity for work. The window says how much one call may hold, not what the model can derive from it.

The evidence the series already cites points the same way. Liu et al. ("Lost in the Middle", 2023) measured accuracy falling when the relevant document sat in the middle of inputs of about 3,000 tokens. RULER (Hsieh et al., 2024) added tracing, aggregation and question answering to the plain needle test and found that almost all the models it evaluated, despite nearly perfect needle scores, drop sharply as the context grows ([post 03](../03-how-llms-read-context/index.md)); in its main table, 16 of the 17 long-context models reach its threshold only at a length shorter than the window they claim ([post 06](../06-context-failure-modes/index.md)). Finding a fact and combining facts are different tasks, and the window size measures neither. Holding text is a storage question; combining it is a computation question.

Computation has a unit. Each output token is one forward pass through the model ([post 05](../05-economics-of-context/index.md)), so, on one common account, a model that answers at once has only the passes of its answer in which to work. Wei et al. ("Chain-of-Thought Prompting Elicits Reasoning in Large Language Models", 2022) showed that prompting large models with a few worked examples whose answers spell out intermediate steps improved their arithmetic, commonsense and symbolic reasoning. A reasoning model is trained to write such steps itself, as tokens, before it answers.

If thinking is tokens, how does it change the budget, the cache and the hygiene of a prompt, and how is it steered? That is this post's question. [Post 25](../25-long-context-vs-rag/index.md) makes the storage case against loading everything; this post makes the computation case.

---

## 2. What a reasoning model does

A **reasoning model** generates intermediate tokens, its **thinking tokens**, before, and sometimes between, the tokens of its visible answer. DeepSeek-AI's R1 report (2025) is an open account of how one is trained: its first model, R1-Zero, was trained by large-scale reinforcement learning with no supervised fine-tuning as a preliminary step, and reasoning behaviours such as self-reflection and verification emerged during that training. Field names in this post come from Anthropic's application programming interface (API) documentation pages "Thinking", "Extended thinking", "Effort" and "Steering thinking", all consulted in October 2026.

On that API, thinking arrives as `thinking` content blocks ahead of the answer's `text` blocks. Three properties of those blocks matter.

**What comes back is not the raw chain of thought.** The "Thinking" page states that the text of a thinking block is a summary of Claude's reasoning, written by a different model, and that no `display` setting returns the raw chain of thought. `display: "summarized"` (the default on Claude Opus 4.6) returns the summary; `display: "omitted"` returns an empty `thinking` field. Either way the block carries a `signature`, an encrypted copy of the full reasoning that the API reads when the block is passed back. The returned text is a by-product, not a transcript.

**It is billed as output, in full.** Thinking tokens are billed as output tokens even when their text is not returned, and they count toward `max_tokens`. The bill is for the full thinking, not the summary; the response reports it in `usage.output_tokens_details.thinking_tokens`, part of `output_tokens`.

**On some models, earlier thinking stays in the window.** When earlier assistant turns are passed back, Claude Opus 4.5 and later Opus models and Claude Sonnet 4.6 and later Sonnet models, among others, keep all prior turns' thinking in context, counted against the window and billed as input; earlier models, and Haiku models through Claude Haiku 4.5, keep only the last turn's. On a keep-all model such as Claude Opus 4.6, old thinking becomes part of layer 05, conversation history.

---

## 3. Adaptive thinking and the effort dial

The first form of the API asked for a fixed budget, `thinking: {"type": "enabled", "budget_tokens": N}`, with N at least 1,024 and below `max_tokens`, a target rather than a strict cap. The "Extended thinking" page now marks it deprecated on the Claude 4.6 models (requests still succeed) and states that Claude 4.7 and later models reject it with a 400 error.

Its replacement is **adaptive thinking**, `thinking: {"type": "adaptive"}`: in the "Steering thinking" page's words, "the model evaluates each request and determines whether to think and how much", so a simple question may get no thinking block at all. On Claude Opus 4.6 thinking is off until a request sets it. Adaptive thinking is steered with **effort**, `output_config.effort`, which sits outside the `thinking` object:

```json
{
  "model": "claude-opus-4-6",
  "max_tokens": 32000,
  "thinking": {"type": "adaptive"},
  "output_config": {"effort": "medium"},
  "messages": [{"role": "user", "content": "Plan the schema migration."}]
}
```

The "Effort" page lists five levels, `low`, `medium`, `high`, `xhigh` and `max`, and not every model accepts all five: Claude Opus 4.6 accepts `low`, `medium`, `high` and `max`, with `high` the default. At `low` the model minimises thinking and skips it for simple tasks; at `max` it thinks most readily, with no constraint on length ("Steering thinking"). Effort shapes every output token, so lower effort also means fewer and terser tool calls. It is a tendency, not a limit; in the "Thinking" page's words: "Effort is soft guidance. `max_tokens` is a strict limit."

One rule turns "effort per task" into a design constraint. The thinking configuration and the effort level are rendered into the prompt, so changing either between requests invalidates cache breakpoints: message-level breakpoints always miss, and tool and system-prompt breakpoints can miss too, depending on the model ("Thinking", section "Thinking and prompt caching"). Some newer models accept a per-message effort change that keeps the cache (in beta); Claude Opus 4.6 does not. On it, effort per task means one level per workflow or conversation, or a separate call at another level, not a new level on each turn of a cached conversation. `snippets/thinking_budget.py` prices the worst case on the turn of section 4: at medium effort the input costs 0.03180 dollars with the prefix read from the cache and 0.05825 dollars if the 4,600-token prefix is written again.

---

## 4. Thinking tokens against the six-layer budget

Thinking spends from the two accounts of [post 04](../04-tokens-windows-budgets/index.md), the window and the bill.

**The window.** Thinking of the current turn counts toward `max_tokens` and occupies the window for that turn; thinking of earlier turns follows the preservation rule of section 2 ("Thinking"). Post 04's output reserve, set through `max_tokens`, now has to hold the thinking as well as the answer; the same page lists 128K tokens as the largest `max_tokens` Claude Opus 4.6 accepts.

**The bill.** Thinking is billed at the output rate: for Claude Opus 4.6, 25 dollars per million output tokens against 5 per million input tokens (Anthropic, "Pricing", as of early 2026, as [post 05](../05-economics-of-context/index.md) quotes it), so one thinking token costs what five prompt tokens cost.

`snippets/thinking_budget.py` adds a thinking line to one hard turn of post 04's agent: the same six layers, 10,500 input tokens with the 4,600-token prefix read from the cache, a 1,500-token answer, and thinking at three effort levels. Every token count is illustrative: Anthropic's pages give no thinking counts per level, and a real request reports its own. Run as `uv run python posts/18-reasoning-model-context/snippets/thinking_budget.py` from the series root, it prints:

```text
one hard turn on Claude Opus 4.6, illustrative token counts
input: layers 01-06 = 10500 tokens (prefix 01-02: 4600, read from the cache)

effort  thinking  answer  output  thinking share  input $  output $  total $
low         1000    1500    2500          40.0%  0.03180   0.06250  0.09430
medium      4000    1500    5500          72.7%  0.03180   0.13750  0.16930
high       16000    1500   17500          91.4%  0.03180   0.43750  0.46930

high against low effort: 4.98 times the cost of the turn
high effort, thinking against the whole input: 16000 against 10500 tokens

a top-level effort change between requests restarts the cache (worst case, prefix written again):
  medium effort, input with the prefix read: 0.03180; written again: 0.05825

input tokens of turn 5 at high effort, earlier turns kept in the history
  thinking blocks kept: 80500; omitted: 16500; difference 64000
  at the full input price: 0.40250 against 0.08250
```

The figure at the top of the post draws the three rows. The input does not move; the thinking line does. At medium effort, $4{,}000 \times 25 / 10^6 = 0.1$ dollars of thinking already costs more than three times the cached input; at high effort the 16,000 thinking tokens outnumber the 10,500 of the prompt, make up 91.4% of the output, and take the turn to 4.98 times its low-effort cost. None of it is visible in the answer.

The last lines are the keep-all rule in numbers: if every earlier turn stays in the history with its thinking, the fifth turn at high effort sends 80,500 input tokens instead of 16,500, and 64,000 of them are old thinking. Thinking therefore enters the budget twice, as an output line on the turn that generates it and, on a keep-all model, as a growing share of layer 05 afterwards.

Two rules follow. **Effort is a per-task decision.** Leaving every call at high or max is the reasoning-era version of loading every document into every prompt: it works, and the thinking line is paid on turns that needed none. Greetings, lookups and format conversions go to low effort or to calls with thinking off. **The budget has a thinking line**, sized per effort level from measured usage, inside the output reserve.

---

## 5. Keep the trace's text out of the application's layers

![Four bars price the next call's input on Claude Opus 4.6 when 2,000 tokens of thinking text are copied: nowhere, 0.03180 dollars; into layer 06 or layer 03, 0.04180; into layer 01, 0.06155, with only 1,600 tokens read from the cache and 5,000 written again.](diagrams/02-where-the-trace-lands.svg)

*Copied anywhere, the trace costs tokens; copied into the stable prefix, it also turns the cache read into a write.*

Two things go by the name of a reasoning trace. The **thinking blocks** belong to the provider's protocol: within a tool-use turn they must be passed back complete and unmodified, and a modified block is rejected with a 400 error; outside tool use the "Thinking" page allows earlier turns' thinking to be omitted, and recommends passing everything back. The **text** of the trace, the summary in a block's `thinking` field, is something the application can copy into layers it writes itself. That copy is what this section rules out. A raw trace is a working note, full of hypotheses tried and abandoned; its job ends with this turn's answer. Three places it must not go.

**Not into the stable prefix.** Anthropic builds the cached prefix in the order tools, system, messages, and a hit needs the prompt identical up to a cache breakpoint ("Prompt caching", consulted October 2026; [post 05](../05-economics-of-context/index.md)). `snippets/trace_cache.py` prices the next call on Claude Opus 4.6 when 2,000 tokens of thinking text (an illustrative size) are copied into one layer, with breakpoints after the tools and after the system prompt:

```text
next call's input, Claude Opus 4.6, 2000 tokens of turn 1 thinking text, illustrative sizes
where the thinking text goes          read 0.1x  written 1.25x  full price  input $
copied nowhere                             4600              0        5900  0.03180
appended to layer 06                       4600              0        7900  0.04180
saved to memory, back in layer 03          4600              0        7900  0.04180
spliced into layer 01                      1600           5000        5900  0.06155
```

The figure above draws the four rows. Spliced into layer 01, the system prompt, the trace leaves only the 1,600 tool tokens readable, and the 5,000 tokens of the new system prompt are written again at 1.25 times the base price: 0.06155 dollars against 0.03180, nearly double, and on every turn, because the trace is new every turn. Feeding the trace into the next request breaks the cached prefix exactly when it lands in front of a breakpoint.

**Not into the next turn's other layers.** Appended to layer 06, the user instruction, the text leaves the cache intact but adds 2,000 full-price tokens to every call. The quality cost is worse: a trace carries rejected branches beside the accepted one, and out of context a rejected branch reads like a conclusion, so the next turn holds two statements that disagree, the conflict of [post 06](../06-context-failure-modes/index.md). What carries forward is the answer, with any decision or fact it produced.

**Not into long-term memory.** Saved to the memory store and read back into layer 03, memory and state, the trace costs the same tokens as in layer 06, and keeps costing them in later sessions. It is the second bug class of [post 08](../08-write-strategies/index.md), the wrong content: a transient value written into a long-lived store and read back as if it were still true. [Post 16](../16-memory-systems/index.md) routes what deserves to outlive a session into episodic, semantic or procedural memory; a deliberation is none of those. The outcome is written (the decision, the preference, the corrected rule), never the deliberation.

On a keep-all model the thinking blocks themselves still accumulate in layer 05. Reclaiming that space is the compress operation of [post 12](../12-compress-strategies/index.md), at a price the API states: the "Context editing" page (consulted October 2026) offers a `clear_thinking_20251015` strategy, in beta under the header `context-management-2025-06-27`, that keeps the thinking of the last N assistant turns and clears the rest, and the cache is invalidated at the point where clearing occurs. A trace needed for debugging goes to the trace store of observability ([post 22](../22-observability/index.md)), never back into the window.

---

## 6. Interleaved thinking and tool calls

![One tool-use turn on Claude Opus 4.6, illustrative counts: thinking 1,200, tool call, result 800, thinking 900, tool call, result 600, thinking 700, answer. Three requests of 10,500, 12,600 and 14,200 input tokens read 4,600, 10,500 and 12,600 of them from the cache.](diagrams/03-interleaved-tool-turn.svg)

*Each request repeats the one before it unchanged, thinking blocks included, so each reads the last from the cache; three thinking segments are paid as output.*

**Interleaved thinking** lets the model think between tool calls within one assistant turn: reason about a tool result before deciding what to do next, and chain calls with reasoning in between ("Thinking"). With adaptive thinking it is automatic, with no beta header. Claude Opus 4.6 interleaves only in adaptive mode, and Claude Haiku 4.5 does not support it; some older models interleave in manual mode with the `interleaved-thinking-2025-05-14` beta header ("Extended thinking"). Consecutive tool calls do not require interleaving; what it changes is where the thinking sits.

The "Thinking" page defines the unit that matters for budgeting: a tool-use loop is one assistant turn. Each request returns a thinking block and a tool call, the application sends the tool result, and the next request repeats everything before it, thinking blocks unmodified. Thinking blocks cannot carry `cache_control` themselves, but they are cached with the request content when the tool results go back, and they count as input tokens when read from the cache ("Prompt caching"). The second part of `snippets/trace_cache.py` follows one such turn, with a cache breakpoint on the last block of each request:

```text
one tool-use turn, three requests, thinking blocks passed back unchanged
request  input tokens  read from cache    new
      1         10500             4600   5900
      2         12600            10500   2100
      3         14200            12600   1600
input over the turn: 37300 tokens; cached 0.07385, uncached 0.18650
output over the turn: 3400 tokens, of which thinking 2800 in 3 segments (82.4%); 0.08500
```

The figure above draws the turn. First, **a loop has as many thinking segments as steps**: 2,800 of the turn's 3,400 output tokens are thinking, in three segments, and since each request in the loop has its own `max_tokens` ("Steering thinking"), the cap bounds a request, not the turn. Post 04's per-turn budget multiplies the thinking per step by the expected number of steps. Second, **blocks passed back unchanged keep the loop cheap**: each request reads the one before it from the cache, so the turn's 37,300 input tokens cost 0.07385 dollars cached against 0.18650 uncached, at the snippet's sizes. The "Thinking" page adds that thinking-heavy tasks often outlast the default five-minute cache lifetime, and suggests the one-hour lifetime.

A useful default: keep the trail of tool calls and tool results, the record of what the agent did and saw, at full fidelity, and treat the thinking between them as working memory, passed back unchanged within the turn and a candidate for clearing later, at the cache price of section 5.

---

## 7. When reasoning replaces scaffolding, and when not to reach for it

**Where it replaces scaffolding.** A capable reasoning model can absorb steps that older pipelines ran as separate prompts: splitting a many-part question into sub-queries (the decomposition of [post 09](../09-select-strategies/index.md)), multi-hop planning, self-critique, a pass that checks arithmetic. Anthropic's "Building effective agents" (December 2024) gives the general rule: "we recommend finding the simplest solution possible, and only increasing complexity when needed". The trade is real, though: logic moves from code that can be tested into a trace that is summarised at best, so steps that need determinism, tool access or an audit trail stay hand-built.

**Where not to reach for it.**

- **Simple, deterministic tasks.** A format conversion, a classification into known classes, a lookup. There is nothing to derive, and thinking costs output dollars and time; low effort, or thinking off (the default on Claude Opus 4.6 until `thinking` is set), is the right setting.
- **Latency-sensitive paths.** Anything a user waits on pays the thinking as delay; higher effort belongs to background work. `display: "omitted"` brings the first text token sooner when streaming ("Thinking"), which lowers latency, not cost.
- **Missing information, not missing reasoning.** If the answer needs a fact the model does not have, more thinking will not supply it. The fix is select: retrieval-augmented generation (RAG, [post 11](../11-rag-in-depth/index.md)) or a tool call, not a higher effort level.

A system that thinks hard on every turn is not a smart system; it is an untuned one.

---

## 8. Make it run

Both snippets run from the series root with the standard library only and no network call:

```text
uv run python posts/18-reasoning-model-context/snippets/thinking_budget.py
uv run python posts/18-reasoning-model-context/snippets/trace_cache.py
```

Their token counts are illustrative, so they show the shape of the trade, not a measurement. The measurement is a short live run: one hard task at `low`, `medium` and `high` effort, recording `usage.output_tokens_details.thinking_tokens`, the wall-clock time and correctness at each level; then a second turn sent once with the first turn's thinking text spliced into the system prompt and once without, comparing `cache_read_input_tokens` and `cache_creation_input_tokens`.

---

## 9. What can go wrong?

- **`max_tokens` sized for the answer.** Adaptive thinking is switched on and the old cap kept. Hard requests return `stop_reason: "max_tokens"` with a truncated answer, because the thinking spent the cap; "Steering thinking" gives the two remedies, a higher cap or a lower effort level.
- **Effort changed on every turn of a cached conversation.** A router sets `low` for easy turns and `high` for hard ones within one conversation on Claude Opus 4.6. After each change the next response reports `cache_creation_input_tokens` where a read was expected: message-level breakpoints always miss, and, depending on the model, the tool and system-prompt breakpoints too.
- **Thinking blocks filtered or edited before they go back.** Code that keeps only blocks of type `thinking` silently drops `redacted_thinking` blocks, and code that trims a block's text gets a 400 error for a modified thinking block.
- **Thinking text in the system prompt.** Every response reports a cache write for the system prompt and a read for the tools alone, and the input cost of each call nearly doubles (section 5).
- **A long session on a keep-all model.** Input climbs by each turn's thinking, and the window fills turns earlier than a per-layer budget without a line for old thinking predicted.

---

## Common pitfalls

1. **Budgeting for the answer, not the thinking.** Thinking is billed as output and counts toward `max_tokens`; a budget without a thinking line undercounts the bill and truncates hard answers.
2. **One effort level for every call.** Easy calls pay for thinking they do not need; on models without per-message effort, the level is held constant within a cached conversation.
3. **Copying trace text into the application's layers.** In layer 01 it breaks the cached prefix; elsewhere it adds full-price tokens and rejected branches that read like conclusions.
4. **Writing traces to long-term memory.** The outcome is persisted, never the deliberation.
5. **Treating the summarised trace as the model's logic.** It is a summary written by another model; no control flow depends on parsing it.
6. **Reaching for thinking to fix missing information.** Retrieval or a tool call supplies a fact; more reasoning does not.

---

## Further reading

- Anthropic, *"Thinking"*, *"Extended thinking"*, *"Effort"* and *"Steering thinking"* documentation (consulted October 2026): thinking blocks, display and billing, preservation by model, the deprecated `budget_tokens`, effort levels per model, interleaved thinking.
- Anthropic, *"Prompt caching"* and *"Context editing"* documentation (consulted October 2026): how thinking blocks are cached, what invalidates the cache, and thinking-block clearing.
- Anthropic Engineering, *"Building effective agents"* (December 2024): the simplest solution first.
- Wei, J. *et al.*, *"Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"* (2022): intermediate steps improve reasoning in large models.
- DeepSeek-AI, *"DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning"* (2025): reasoning trained with large-scale reinforcement learning.
- Hsieh, C.-P. *et al.*, *"RULER"* (2024), and Liu, N. F. *et al.*, *"Lost in the Middle"* (2023): the evidence of section 1.

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 19 - Multimodal context: images, PDF pages, and audio](../19-multimodal-context/index.md):** images and audio spend the same window and budget that thinking does.
- **[Post 17 - Advanced retrieval](../17-advanced-retrieval/index.md):** the techniques to reach for when the answer lacks information rather than reasoning.
