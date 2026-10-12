# 05 - The economics of context: pricing, caching, and latency

> **TL;DR.** A large language model (LLM) application that works in a notebook can still be unshippable, because its cost per call is multiplied by production volume. This post prices a call from its input and output tokens, explains why output costs more than input and why a long prompt delays the first token, takes prompt caching apart down to the write premium and the read discount, and works one agent turn at three tiers with and without caching. The arithmetic is done by a short script, so every dollar figure in the post can be rerun.
>
> **Prerequisites:** [Post 04](../04-tokens-windows-budgets/index.md).
> **Safe to skip?** Skip it if a call can already be priced at any tier with and without a cache hit, and the reason a timestamp in the system prompt raises the bill is already familiar.
>
> **After reading, you will be able to:**
>
> - Price a call at any tier from its input and output tokens, and predict how prompt caching changes the bill.
> - Explain why output tokens cost more than input tokens and why a long prompt delays the first token, in terms of prefill and decode.
> - Design a stable-prefix layout that maximises cache hits, and name the changes that silently invalidate it.
> - Decide whether caching a prefix pays for its write premium, from how often the prefix is reused within the cache lifetime.
> - Set cost guardrails before launch: per-call budgets, model routing, a capped output length and cache-hit monitoring.

![Three horizontal bars price one agent turn on Claude Sonnet 4.5, 10,500 input tokens and 400 output tokens. With no caching the call costs 0.03750 dollars; the first call, which writes the 4,600-token prefix of layers 01 and 02 to the cache, costs 0.04095; a later call that reads the prefix costs 0.02508. Only the prefix segment changes between the bars.](diagrams/01-cache-miss-and-hit.svg)

*The same call, priced three ways. The cache changes only what the prefix costs, and that is enough to take a third off every later call.*

---

## 1. The question: why can a working demo not ship?

A prototype that works in a notebook says little about whether it can ship. The gap between the two is often not quality. It is arithmetic.

Consider the customer-support agent sized in [post 04](../04-tokens-windows-budgets/index.md): with illustrative token counts, about 10,500 input tokens and 400 output tokens per call. At the mid-tier rates of section 2 (3 dollars per million input tokens and 15 per million output tokens), one call costs $10{,}500 \times 3 / 10^6 + 400 \times 15 / 10^6 = 0.0315 + 0.006 = 0.0375$ dollars, under four cents. In a demo, at a handful of calls a day, that rounds to free. In production, at an illustrative 10,000 conversations a day, four turns each and five model calls per turn, it is 200,000 calls and $200{,}000 \times 0.0375 = 7{,}500$ dollars a day before any infrastructure. The demo and the deployment run identical code. Only the multiplier changed.

The unit cost is trivial and the volume is not. The question of this post is which properties of a call decide its cost and its latency, so that the re-engineering happens on a whiteboard rather than in an incident review. Three levers dominate: which tier a call is routed to, how the context is ordered so that it caches, and how long each generation runs. The figure at the top of the post is the second lever in one picture: the same call, priced without caching, on the call that writes the cache, and on every call that reads it.

---

## 2. Cost per million tokens

Providers price in dollars per million tokens, quoted separately for input (the prompt sent) and output (the tokens the model generates). The absolute numbers move often; the ratios between them are what a design is built against.

The table below gives the rates of this series' three running models as of early 2026, from Anthropic's "Pricing" page as consulted on 12 October 2026. All three are still listed there, Claude Sonnet 4.5 marked as deprecated, alongside newer models at other rates.

| Tier (early 2026) | Running model | Input, dollars per million tokens | Output, dollars per million tokens |
|---|---|---|---|
| Frontier | Claude Opus 4.6 | 5 | 25 |
| Mid | Claude Sonnet 4.5 | 3 | 15 |
| Cheap | Claude Haiku 4.5 | 1 | 5 |

Two spreads matter more than any single cell. Down the table, the frontier tier costs five times the cheap tier for the same token (5 against 1 dollar for input, 25 against 5 for output), which is what makes model routing (section 7) worth the engineering. Across the table, output costs five times input in every row, which is the asymmetry section 3 unpacks.

Everything downstream in this post is arithmetic on these three rows, so the rates are re-read from the provider's pricing page before any of these numbers goes into a budget.

---

## 3. Input against output: prefill and decode

The horizontal spread is not a quirk of one table. It matches how the two halves of a call run on the hardware, as Pope et al. ("Efficiently Scaling Transformer Inference", 2022) describe them.

Ingesting the prompt is **prefill**: the model processes all input tokens together, in parallel, and stores the key and value tensors of every position in its key-value (KV) cache ([post 03](../03-how-llms-read-context/index.md)). Generating the answer is **decode**: each output token needs its own forward pass through the model, and each pass depends on the token produced by the one before, so output cannot be parallelised the way input can. Per token, decode keeps the hardware far less busy than prefill. Providers do not publish their cost structure, so this is an explanation of the price ratio, not a statement from the price page, but it is the explanation the ratio is consistent with.

The operational consequence is easy to miss: **a short prompt with a long answer can cost more than a long prompt with a short one.** Take two illustrative calls at the Claude Sonnet 4.5 rates. A 2,000-token prompt that produces a 2,500-token answer costs $2{,}000 \times 3 / 10^6 + 2{,}500 \times 15 / 10^6 = 0.006 + 0.0375 = 0.0435$ dollars. A 12,000-token prompt that produces a 200-token answer costs $12{,}000 \times 3 / 10^6 + 200 \times 15 / 10^6 = 0.036 + 0.003 = 0.039$ dollars. The first call sends a sixth of the input and still costs more, because its 2,500 output tokens cost as much as 12,500 input tokens would. The figure draws both calls twice, once in tokens and once in dollars.

![Two calls on Claude Sonnet 4.5 drawn in tokens and in dollars. The short prompt sends 2,000 input tokens and gets 2,500 output tokens, costing 0.00600 plus 0.03750, 0.04350 dollars. The long prompt sends 12,000 input tokens and gets 200, costing 0.03600 plus 0.00300, 0.03900 dollars.](diagrams/02-output-asymmetry.svg)

*In tokens the long prompt dominates; in dollars the long answer does.*

Long generations therefore dominate cost in exactly the workloads that produce them: verbose chain-of-thought, agents that narrate every step, code assistants that regenerate a whole file to change one line. One of the cheapest optimisations is often a lower `max_tokens` and a system-prompt instruction to be terse, because it attacks the side of the ledger priced at five times the other. Trimming the prompt saves input dollars; trimming the answer saves output dollars, and at these rates each output token saved is worth five input tokens saved.

---

## 4. Prompt caching in depth

For any application that resends a stable prefix, prompt caching is a large lever on the input bill, and it rewards understanding it exactly. The provider stores the processed state of a prompt prefix (in effect, the KV cache of those positions) and reuses it when a later request starts with the same prefix, so the repeat call skips recomputing it. The rules below are Anthropic's, from its "Prompt caching" documentation as consulted on 12 October 2026; other providers differ in the details named at the end of the section.

**A hit needs an identical prefix up to a breakpoint.** A request marks the end of a cacheable prefix with a cache breakpoint (a `cache_control` marker on a content block; up to four per request). The documentation states that cache hits require 100% identical prompt segments, including all text and images, up to and including the block marked with cache control. When the prefix at a breakpoint has no stored entry, the system walks back one block at a time, checking at most 20 positions including the breakpoint itself, for an earlier position where a previous request wrote an entry. So a change anywhere in a cached prefix makes that entry unusable, and only an entry that ends before the change, written there by an earlier request, can still be read. Everything after the reused part is computed again and billed as new input.

**The prefix runs tools, then system, then messages.** Anthropic builds the cached prefix in the order `tools`, `system`, `messages`, and a change at one level invalidates that level and every level after it. In this series' layer numbers, the tool definitions (layer 02) come first, the system prompt (layer 01) second, and layers 03 to 06 follow in the message list. Editing the system prompt therefore leaves a cached tool list reusable, provided a breakpoint marks the end of the tools; changing a single tool definition invalidates everything after it. [Post 02](../02-six-layers-of-context/index.md) draws the same rule in the layer order: the reusable prefix ends at the first entry that differs from the previous call.

**What caches and what does not.** Static, repeated content caches well: tool definitions, a frozen system prompt, long few-shot examples, a large document that several questions are asked about. Per-request content does not: the user's message, this turn's retrieved chunks, a timestamp. A current-time string near the front of an otherwise stable prompt changes the prefix on every call. Ji ("Context Engineering for AI Agents: Lessons from Building Manus", July 2025) gives the same warning about timestamps in the system prompt and recommends keeping the context append-only, with deterministic serialisation, so that nothing earlier in it changes silently.

**There is a minimum cacheable length.** Shorter prefixes are not cached even when marked, and the documentation states that such requests are processed without caching and that no error is returned. The minimum depends on the model: 1,024 tokens for Claude Sonnet 4.5 and 4,096 tokens for Claude Opus 4.6 and Claude Haiku 4.5, with values from 512 to 4,096 tokens across the models the page lists.

**Two lifetimes.** A cache entry lives five minutes by default; a one-hour lifetime is also available. The documentation states that the cache is refreshed at no additional cost each time the cached content is used, so under steady traffic a prefix that is read every few seconds stays warm. The one-hour lifetime is for prefixes reused on a slower cadence, where five minutes would expire between hits.

**The write premium and the read discount.** Writing a prefix to the cache costs more than sending it as normal input: 1.25 times the base input price for the five-minute lifetime and 2 times for the one-hour lifetime. Reading it costs 0.1 times the base input price on most models, and the multiplier is no longer one number across models: the page lists 0.05 times for Claude Opus 5.5 and Claude Sonnet 5.5, 0.025 times for Claude Fable 5.1 and Claude Mythos 5.1, and the standard 0.1 times for all other models, which include this series' three running models. At 0.1 times, Anthropic's "Pricing" page notes, caching pays off after one cache read for the five-minute lifetime and after two for the one-hour lifetime. The figure below draws that break-even for the 4,600-token prefix of the section 6 agent.

![A line chart of the cumulative cost of a 4,600-token prefix over five calls on Claude Sonnet 4.5. Without caching it rises to 0.06900 dollars. A five-minute cache costs more on call 1 and less from call 2, ending at 0.02277. A one-hour cache costs more on calls 1 and 2 and less from call 3, ending at 0.03312. A cache that expires between calls ends highest, at 0.08625.](diagrams/03-write-premium-break-even.svg)

*Call 1 always pays more with caching than without; from then on each read costs a tenth of a full send. The only way to lose is to keep writing a prefix that is never read.*

The line labelled "expires between calls" is the real trap. If calls arrive further apart than the cache lifetime, every call writes the prefix again and none reads it, so caching costs 1.25 times as much as not caching. A prefix that is reused at all within its lifetime repays the five-minute premium on its first read.

The architectural consequence is one word: **discipline.** Freeze the system prompt, fix the order of the tool list, and put every volatile byte last.

Other providers apply the same principle with different mechanics. OpenAI's "Prompt caching" guide (consulted 12 October 2026) describes caching as enabled by default for supported models, with cached input tokens discounted by up to 95%, depending on the model. Google's Gemini application programming interface (API) documentation ("Context caching", consulted 12 October 2026) describes implicit caching, enabled by default for Gemini 2.5 and newer models, and explicit caching, in which the application creates and manages cache objects. The lesson is the same everywhere: **order the context from stable to volatile, so that the expensive, unchanging tokens sit in front.**

---

## 5. The latency of an agent turn

Caching cuts latency as well as cost. To see why, the wall-clock time of a turn is split into the same two phases that explain the price (Pope et al., 2022):

$T_{\text{total}} = T_{\text{prefill}} + N_{\text{out}} \cdot T_{\text{decode}}$

Here $N_{\text{out}}$ is the number of output tokens and $T_{\text{decode}}$ the time of one decode step. Prefill grows with the number of input tokens the model must compute: every prompt token is processed before the first output token can be produced, so a long context means a long wait for the **time to first token** (TTFT), the moment the user sees anything happen. Decode grows with the output length: each generated token adds one forward pass, at a roughly constant time per token for a given model and context length.

Streaming hides decode time by showing tokens as they arrive, but it cannot hide prefill, which happens before the first token exists. This is why a long-context agent feels slow to start even with streaming on: the user waits through the prefill of the whole prompt.

A cache hit removes the cached prefix from prefill. The model reuses the stored state for those positions instead of recomputing them, so on the section 6 turn, prefill computes 5,900 tokens instead of 10,500 while decode is unchanged. Anthropic's documentation says that time to first token generally improves for long documents and gives no figure; the size of the gain depends on the provider, the model and the load, and this post claims no timing. The figure draws the mechanism, not a measurement.

![Two rows show one agent turn. On a cache miss, prefill computes 10,500 input tokens before the first token, then decode runs 400 passes, one per output token. On a cache hit, 4,600 prefix tokens are read from the cache, prefill computes 5,900 tokens, the first token comes sooner, and decode is the same 400 passes. Prefill boxes are to scale in tokens, not seconds.](diagrams/04-turn-latency.svg)

*A hit shortens the part of the turn the user waits through before anything appears; the decode that follows is unchanged.*

Caching therefore buys the same move twice: cheaper and sooner on every hit.

---

## 6. A worked example, with and without caching

Take one turn of the section 1 agent and price it both ways. The per-layer breakdown uses post 04's illustrative token counts, in this series' layer order:

| Layer | Tokens | Changes between calls? |
|---|---|---|
| 01 System prompt | 3,000 | no |
| 02 Tools and MCP descriptions (eight tools) | 1,600 | no |
| 03 Memory and state | 1,200 | yes |
| 04 Retrieved chunks (top five) | 2,500 | yes |
| 05 Conversation history (compressed) | 2,000 | yes |
| 06 User instruction | 200 | yes |
| **Input total** | **10,500** | |
| Output (a typical reply) | 400 | |

Layer 02 holds the tool schemas, including any exposed through the Model Context Protocol (MCP, [post 15](../15-tools-and-mcp/index.md)); layer 04 is filled by retrieval-augmented generation (RAG, [post 11](../11-rag-in-depth/index.md)). Layers 01 and 02, 4,600 tokens, are the same on every call and form the cacheable prefix; 4,600 tokens clears the minimum cacheable length of all three running models. The other 5,900 tokens change on every call and pay the full input price.

The arithmetic lives in `snippets/cost_model.py`. Its core is one function, which splits a call into the prefix, the rest of the input and the output, and applies the cache multiplier to the prefix only:

```python
def call_cost(rate, prefix, rest, output, prefix_mode="none"):
    """Dollar cost of one call, split into its parts.

    rate: {"input": $/M, "output": $/M}; prefix: tokens of the cacheable prefix;
    rest: input tokens after it; prefix_mode: "none" (no caching), "write" (a
    five-minute cache write) or "read" (a cache hit).
    """
    factor = {"none": 1.0, "write": CACHE_WRITE_5M, "read": CACHE_READ}[prefix_mode]
    parts = {
        "prefix": prefix * rate["input"] * factor / 1e6,
        "rest": rest * rate["input"] / 1e6,
        "output": output * rate["output"] / 1e6,
    }
    parts["total"] = sum(parts.values())
    return parts
```

Running `uv run python posts/05-economics-of-context/snippets/cost_model.py` from the series root needs nothing beyond the standard library and makes no network call. It prints:

```text
input per call: 10500 tokens (prefix 01-02: 4600, layers 03-06: 5900); output: 400

cost of one call, dollars
model               no caching  cache write  cache read  saving
Claude Opus 4.6        0.06250      0.06825     0.04180   33.1%
Claude Sonnet 4.5      0.03750      0.04095     0.02508   33.1%
Claude Haiku 4.5       0.01250      0.01365     0.00836   33.1%

Sonnet 4.5, none : prefix 0.01380 + layers 03-06 0.01770 + output 0.00600 = 0.03750
Sonnet 4.5, write: prefix 0.01725 + layers 03-06 0.01770 + output 0.00600 = 0.04095
Sonnet 4.5, read : prefix 0.00138 + layers 03-06 0.01770 + output 0.00600 = 0.02508
cache-hit rate of a warm call: 4600 / 10500 = 43.8%

Sonnet 4.5, 200000 calls a day: no caching 7500.00, cached 5016.02, difference 2483.98

Sonnet 4.5, cumulative prefix cost over calls 1 to 5, dollars
  no caching 0.01380  0.02760  0.04140  0.05520  0.06900
  5-minute   0.01725  0.01863  0.02001  0.02139  0.02277
  1-hour     0.02760  0.02898  0.03036  0.03174  0.03312
  lapsed     0.01725  0.03450  0.05175  0.06900  0.08625

Sonnet 4.5, 2000 in + 2500 out: 0.00600 + 0.03750 = 0.04350
Sonnet 4.5, 12000 in + 200 out: 0.03600 + 0.00300 = 0.03900
```

On Claude Sonnet 4.5, the uncached call costs $0.0138 + 0.0177 + 0.006 = 0.0375$ dollars. On a cache hit the 4,600 prefix tokens are read at 0.1 times 3 dollars, 0.30 dollars per million, so the call costs $4{,}600 \times 0.30 / 10^6 + 5{,}900 \times 3 / 10^6 + 400 \times 15 / 10^6 = 0.00138 + 0.0177 + 0.006 = 0.02508$ dollars, 33.1% less, from ordering the context and freezing the prefix. The one call that writes the prefix costs 0.04095 dollars, more than no caching, which is the hero figure's middle bar. The saving is the same 33.1% at all three tiers, because the three rows of section 2 share the same ratio of output to input price: routing changes the size of the bill, and caching takes the same share off it.

Scale it. At the section 1 volume of 200,000 calls a day, the uncached bill is 7,500 dollars a day. With caching, the prefix is written once and then, refreshed by every read, stays warm all day, so one write and 199,999 reads cost 5,016.02 dollars, a difference of 2,483.98 dollars a day, or about 74,500 dollars over a 30-day month (all illustrative: these token counts, this volume, the section 2 rates). The write premium rounds away under sustained traffic; it matters only when traffic is too sparse to keep the prefix warm, the expiring case of section 4.

The cache-hit rate of a warm call, the share of its input tokens read from the cache, is 4,600 out of 10,500, or 43.8%, and that is the ceiling for this layout, because layers 03 to 06 change on every call. A layout that wrote the time of the call into the system prompt, with one breakpoint after it, would score 0% on every call.

---

## 7. Cost guardrails to ship

Caching lowers the unit cost; guardrails keep the total from surprising anyone. Four are worth building before launch, not after the first invoice.

**Per-call and per-workflow budgets.** Each workflow gets an explicit token ceiling per layer (the allocation of [post 04](../04-tokens-windows-budgets/index.md)) and a dollar ceiling per call, enforced in code. The layers that grow on their own, retrieval and history in particular, take the other layers' share as soon as nobody is watching. A hard cap turns silent overspend into a loud, catchable error.

**Cheaper models for sub-tasks.** Not every call needs the frontier tier. Short, well-defined steps (classification, intent detection, extraction, summarising old history) can go to the cheap tier, which costs a fifth as much per token (section 2), keeping the frontier tier for the reasoning that needs it. Two patterns recur: a **cascade** (try the cheap model, escalate only when a check flags the answer) and **plan and execute** (a frontier model writes the plan once, cheaper models run the steps). Both cut the average cost per task; whether quality holds is a question for an evaluation suite ([post 20](../20-evaluation/index.md)), not an assumption.

**Cache-hit monitoring.** A cache that cannot be observed cannot be trusted. Anthropic reports `cache_read_input_tokens`, `cache_creation_input_tokens` and `input_tokens` (the tokens after the last breakpoint) in the usage block of every response, and OpenAI reports `cached_tokens` among the input-token details. The **cache-hit rate**, cached input tokens over total input tokens, deserves a place beside latency and error rate; Ji (2025) calls the KV cache hit rate the single most important metric for a production-stage agent. A hit rate that drops after a deploy is the fingerprint of a prefix change: someone edited the system prompt, reordered the tools, or slipped a timestamp in front of the breakpoint, and every request now pays the full input price. Wiring these signals into traces and dashboards is the subject of [post 22](../22-observability/index.md); applying all of it to a real system is the RAG build of [post 28](../28-build-rag-chatbot/index.md).

**Set `max_tokens` deliberately.** Output is the side priced at five times input (section 3), so an unbounded generation is an unbounded bill. A per-workflow cap, with a truncation treated as a signal to redesign the task rather than to raise the ceiling, keeps it bounded.

---

## 8. What can go wrong?

- **A per-call value sits in the prefix.** A timestamp, a request id or the user's name is formatted into the system prompt. With caching on and one breakpoint after the system prompt, every response reports `cache_creation_input_tokens` for the whole prefix and `cache_read_input_tokens` of 0, so every call pays the write premium and none reads it: on the section 6 turn, 0.04095 dollars a call instead of 0.03750 without caching. Moving the value into layer 03, 04 or 06 restores the reads.
- **The prefix is below the minimum.** A 900-token system prompt marked for caching on Claude Haiku 4.5 is never cached. No error is returned; the usage block simply reports zero cache-write and zero cache-read tokens, and the expected saving never appears.
- **Traffic is sparser than the cache lifetime.** A batch job that calls every ten minutes, with the default five-minute lifetime, writes the prefix on every call and never reads it, paying 1.25 times the uncached price for the prefix. The one-hour lifetime, or no caching, is cheaper for that cadence.
- **The serialisation is not deterministic.** The tool list is built from an unordered collection, or JavaScript Object Notation (JSON) keys come out in a different order from one process to the next. The prompt means the same thing, but the bytes differ, so the cache misses after a deploy or between two servers. Sorting the tools and fixing the key order makes the prefix byte-stable.

---

## Common pitfalls

1. **Editing the system prompt on every deploy.** Each edit rewrites the cached prefix and pays the write premium again; batching prompt changes into deliberate releases keeps the prefix warm.
2. **Optimising input tokens while ignoring output.** At these rates one output token costs as much as five input tokens, so the answer length is the first thing to check.
3. **Assuming caching always saves money.** One read repays a five-minute write and two repay a one-hour write, but a prefix that expires before it is read costs 1.25 or 2 times as much as not caching.
4. **Quoting one cache-read discount for every model.** The read multiplier is 0.1 for most Anthropic models but lower for some newer ones, and other providers use other rates; the current page decides.
5. **Pricing the demo, not the deployment.** A few cents per call becomes thousands of dollars a day at production volume; the volume arithmetic is done before shipping.
6. **Trusting last quarter's price table.** Rates and models change, and every downstream cost figure inherits a stale table; the provider's pricing page is re-read before a number goes into a budget.

---

## Further reading

- Anthropic, *"Pricing"* (consulted 12 October 2026): the per-token rates of the three running models in section 2 and the cache-write and cache-read prices.
- Anthropic, *"Prompt caching"* documentation (consulted 12 October 2026): the identical-prefix rule, breakpoints and lookback, the tools, system, messages order, the minimum cacheable lengths, the two lifetimes, the write and read multipliers and their per-model exceptions, and the usage fields.
- Pope, R. *et al.*, *"Efficiently Scaling Transformer Inference"* (2022): prefill and decode, behind the asymmetry of section 3 and the latency model of section 5.
- Ji, Y. (Manus), *"Context Engineering for AI Agents: Lessons from Building Manus"* (July 2025): the cache-hit rate as the agent metric to watch, and the case against timestamps in the prefix.
- OpenAI, *"Prompt caching"* guide, and Google, *"Context caching"* (Gemini API documentation), both consulted 12 October 2026: the other providers' caching in section 4.

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 06 - Five context failure modes](../06-context-failure-modes/index.md):** what breaks in the answers when a context is laid out or budgeted badly, and the first fix for each failure.
- **[Post 22 - Observability, tracing, and cost](../22-observability/index.md):** instruments the per-call cost and the cache-hit rate so that the guardrails of section 7 have data.
