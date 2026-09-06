# 05 · The economics of context — pricing, caching, and latency

> **TL;DR.** Every architectural decision in context engineering is also an economic one, and prompt caching is the single biggest cost lever a production system has. [Post 04](../04-tokens-windows-budgets/index.md) introduced tokens, budgets, and a preview of caching; this post is the deep treatment. It walks the per-million-token price ladder, explains the input–output asymmetry, dissects prompt caching down to the byte, models the latency of one agent turn, and works a full per-layer example so the arithmetic that decides whether a demo can ship is written out once.
>
> **After reading this you will be able to:**
> - Price any prompt at any tier and predict how caching changes the bill.
> - Design a stable-prefix layout that maximises cache hits instead of silently invalidating them.
> - Set cost guardrails (budgets, model routing, cache-hit monitoring) before the first bill arrives.

![Two request bars pricing the same 10,500-token input: a cache miss bills the whole prompt at full input price plus a 1.25x write premium on the stable prefix, while a cache hit re-reads that frozen system-and-tools prefix at about a tenth of the price and pays full rate only for the small volatile suffix.](diagrams/00-hero-economics-of-context.svg)
*A cache hit re-reads the frozen prefix at about a tenth of the price; only the volatile suffix pays full rate.*

---

## 1. The same demo, unshippable at scale

A prototype that works in a notebook says almost nothing about whether it can ship. The gap between the two is rarely quality. It is arithmetic.

Consider the customer-support agent sized in [Post 04](../04-tokens-windows-budgets/index.md): about 10,500 input tokens and 400 output tokens per call. On a mid tier at roughly $3 / 1M input and $15 / 1M output, one call costs a few cents. In a demo, at a handful of calls a day, that rounds to free. In production, at ten thousand conversations a day, four turns each, several model calls per turn, the same agent bills thousands of dollars a day before any infrastructure. The demo and the deployment run identical code. Only the multiplier changed.

This is the recurring shape of context economics. The unit cost is trivial; the volume is not. A design that ignores the unit cost is fine until it meets the volume, at which point the choice is to re-engineer the context or to lose money on every request. The purpose of this post is to make the unit cost legible early, so the re-engineering happens on a whiteboard rather than in an incident review. Three levers dominate: which tier you route to, how you order the context so it caches, and how long each generation runs.

---

## 2. Cost per million tokens

Providers price in dollars per million tokens, quoted separately for input (the prompt you send) and output (the tokens the model generates). The absolute numbers move constantly; the *ratios* between them are what you design against.

The representative early-2026 rates below use this series' running models (Anthropic, "Pricing", 2026):

| Tier | Running model | $ / 1M input | $ / 1M output |
|---|---|---|---|
| Frontier | Claude Opus 4.x | ~$5 | ~$25 |
| Mid | Claude Sonnet 4.5 | ~$3 | ~$15 |
| Cheap | Claude Haiku 4.5 | ~$1 | ~$5 |

Two spreads matter more than any single cell. Vertically, the frontier tier costs about five times the cheap tier for the same token, which is what makes model routing (section 7) worth the engineering. Horizontally, output costs about five times input at every tier, which is the asymmetry section 3 unpacks.

Model names and prices in this post are current as of early 2026; providers change both often, so check the provider's pricing page before you commit a number to a budget. Everything downstream in this post is arithmetic on these three rows, so a stale table quietly invalidates every dollar figure that follows. Treat the numbers as orders of magnitude and re-derive when you deploy.

---

## 3. Input versus output asymmetry

Notice the horizontal spread again: output tokens cost roughly five times input tokens at every tier (Anthropic, "Pricing", 2026). This is not a pricing quirk; it reflects how the two halves of a call actually run on the hardware.

Ingesting the prompt is *prefill*: the model processes every input token in a single parallel pass, filling its attention cache in one shot. Generating the answer is *decode*: each output token requires a full forward pass through the model, and each pass depends on the one before it, so output cannot be parallelised the way input can (Pope et al., 2022). Output tokens are simply more expensive to produce, and the price reflects it.

![Prefill runs in one parallel pass while decode runs one forward pass per token; two priced calls show six times the input costing about the same as a seventh of the output](diagrams/01-input-output-asymmetry.svg)

*The mechanism on the left, the consequence on the right: the bill follows the answer, not the prompt.*

The operational consequence surprises teams: **a short prompt with a long answer can cost more than a long prompt with a short one.** Take a 2,000-token input that yields a 1,500-token generation against a 12,000-token input that yields a 200-token generation, at the mid-tier rates above. The first costs about `2000/1e6 x $3 + 1500/1e6 x $15 ≈ $0.029`; the second about `12000/1e6 x $3 + 200/1e6 x $15 ≈ $0.039`. Six times the input, yet a comparable bill, because the short-prompt call generated seven times as much text (figures illustrative, at the section 2 rates).

Long generations therefore dominate cost in exactly the workloads that produce them: verbose chain-of-thought, agents that narrate every step, code assistants that regenerate a whole file to change one line. The cheapest optimisation in the book is often a lower `max_tokens` and a system-prompt instruction to be terse, because it attacks the five-times-priced side of the ledger. Trimming the prompt saves input dollars; trimming the answer saves output dollars, and output dollars are worth five of the other kind.

---

## 4. Prompt caching in depth

Prompt caching is the single highest-leverage cost lever in production context engineering, and it is worth understanding to the byte. The mechanism reuses the model's internal attention state, the **KV-cache** (the cached key and value tensors from [Post 03](../03-how-llms-read-context/index.md)), for a run of tokens the model has already processed, so a repeat call skips re-computing them (Anthropic, "Prompt caching", 2024–25).

**A cache breakpoint is a prefix match.** The provider stores the processed state for a *contiguous prefix* of your request, measured from the very first byte. On the next call it compares your new request against what it has stored and reuses the state up to the first byte that differs. Everything from that byte onward is a miss and must be re-processed. This is the property that governs every caching decision: **any change, however small, invalidates the cache from the point of change to the end.** Insert one space into the system prompt and the tool schemas that follow it, previously cached, are all recomputed.

**Render order is tools, then system, then messages.** In the Anthropic request shape, the tool definitions serialise first, the system prompt next, and the conversation messages last (Anthropic, "Prompt caching", 2024–25). Because the cache is a prefix from the front, the frontmost blocks are the ones worth caching: they precede everything else, so keeping them byte-stable protects the largest cached span. The volatile content (the latest user turn, freshly retrieved chunks) belongs at the back, after the breakpoint, where it can change every call without disturbing what came before.

**What caches and what does not.** Static, repeated content caches well: tool schemas, a frozen system prompt, long few-shot exemplars, a large document you will ask several questions about. Per-request content does not benefit, because it is different every time by definition: the user's message, this turn's retrieval results, a timestamp injected into the prompt. Injecting a current-time string near the front of an otherwise stable prompt is a classic self-inflicted wound, since it changes the first bytes on every call and moves the breakpoint to position zero.

**There is a minimum cacheable prefix.** Prefixes below roughly 1k to 4k tokens, model-dependent, are not cached at all (Anthropic, "Prompt caching", 2024–25). Tiny prompts see no benefit; caching pays off only once the stable prefix is large enough to clear the floor and is reused enough to amortise its write cost.

**Two TTL tiers govern how long a cached prefix survives.** The default time-to-live is five minutes; a one-hour tier is also available (Anthropic, "Prompt caching", 2024–25). Each cache read refreshes the clock, so under steady traffic a prefix that is hit every few seconds stays warm indefinitely. The one-hour tier is for prefixes reused on a slower cadence, where a five-minute window would expire between hits.

**The write premium is the catch.** Populating the cache costs *more* than a normal input token: **1.25x the input price for the five-minute tier, 2x for the one-hour tier.** A subsequent cache *read* costs about **0.1x, roughly ten per cent of, the base input price** (Anthropic, "Prompt caching", 2024–25). So the first call that establishes a prefix pays a premium; every call that reuses it pays a tenth. Caching wins precisely when a prefix is reused many times, which is the normal case for any agent with a stable system prompt under sustained load.

The architectural consequence is one word: **discipline.** Freeze the system prompt. Do not reorder tools between deploys. Put every volatile byte last. The rule to internalise is that **editing the system prompt on every deploy re-writes the entire cache**, so each release pays the write premium again and the first wave of post-deploy traffic runs at full input price until the prefix re-warms. Vendors differ in the details (OpenAI caching is automatic and discounts cached input by around fifty per cent rather than the Anthropic ~10%, and Gemini offers both implicit and explicit caching), but the lesson is identical everywhere: **order the context stable-to-volatile so the expensive, unchanging bytes sit in front.**

```text
  request layout, front (cached) → back (fresh)
  ┌───────────────────────────────────────────────┐
  │  TOOLS      schemas, frozen        ┐          │
  │  SYSTEM     prompt, frozen         ├ stable   │ ← cache this prefix
  │  EXEMPLARS  few-shot, frozen       ┘  (cached)│
  ├─────────── cache breakpoint ───────────────── │
  │  HISTORY    older turns            ┐          │
  │  RETRIEVAL  this turn's chunks     ├ volatile │ ← recomputed each call
  │  USER       latest message         ┘          │
  └───────────────────────────────────────────────┘
  one changed byte above the breakpoint invalidates
  everything below it, back to full input price
```
*Cache the frozen prefix at the front; keep everything that changes per request behind the breakpoint.*

---

## 5. The latency budget of an agent turn

Caching cuts latency, not only cost, and to see why you split the wall-clock time of a turn into the same two phases the price reflects. Total time is prefill plus per-token decode (Pope et al., 2022):

$$
T_{\text{total}} = T_{\text{prefill}} + N_{\text{out}} \cdot T_{\text{decode}}
$$

*Prefill* scales with input length: the model must process every prompt token before it can emit the first output token, so a long context means a long wait to **time-to-first-token** (TTFT), the moment the user sees anything happen. *Decode* scales with output length: each generated token adds one forward pass, roughly constant per token at a given model size.

Streaming hides decode time by showing tokens as they arrive, but it cannot hide prefill, which happens before the first token exists. This is why a long-context agent feels sluggish to first token even with streaming on: the user is waiting through prefill of tens of thousands of tokens.

![Three turn timelines on one scale: a cold long-context turn, the same turn warm, and a cold short-context turn](diagrams/02-latency-budget.svg)

*Decode is the same length in all three. Prefill is what a cache read deletes, and prefill is what the user waits through.*

Here is the connection to section 4. A cache read skips prefill for the cached prefix, because the model reloads stored attention state instead of recomputing it. On a request whose 40k-token prefix is cached and whose 500-token tail is fresh, the model prefills only the 500 new tokens, so time-to-first-token collapses toward the small-prompt case. Caching therefore buys the same architectural move twice: cheaper *and* faster on every hit. In an interactive product, where TTFT is what users perceive as "responsiveness", the latency win often justifies the caching work on its own, with the cost saving as a bonus.

---

## 6. A worked example, with and without caching

Take one turn of the section-1 agent and price it both ways. The per-layer breakdown (token counts illustrative, in the spirit of the [Post 04](../04-tokens-windows-budgets/index.md) envelope):

| Layer | Tokens | Position | Stable? |
|---|---|---|---|
| Tool / MCP schemas (8 tools) | 1,600 | front | yes |
| System prompt + rules | 3,000 | front | yes |
| Memory (profile + summarised tickets) | 1,200 | middle | mostly |
| Conversation history (compressed) | 2,000 | middle | no |
| Retrieval (top-5 chunks) | 2,500 | back | no |
| User message | 200 | back | no |
| **Input total** | **10,500** | | |
| Output (typical reply) | 400 | | |

Two acronyms appear here: **MCP** (Model Context Protocol, the open standard for exposing tools to a model; [Post 15](../15-tools-and-mcp/index.md)) and RAG (retrieval-augmented generation; [Post 11](../11-rag-in-depth/index.md)).

**Without caching**, at the mid-tier $3 / 1M input and $15 / 1M output:

$$
\frac{10{,}500}{10^6}\times\$3 + \frac{400}{10^6}\times\$15 \approx \$0.0315 + \$0.006 = \$0.0375
$$

**With caching**, freeze the front. The tool schemas and system prompt (1,600 + 3,000 = 4,600 tokens) are byte-identical every call, so they sit before the breakpoint and read from cache at ~10% of input price, that is $0.30 / 1M. The remaining 5,900 input tokens are volatile and bill at the full $3 / 1M. Output is unchanged:

$$
\frac{4{,}600}{10^6}\times\$0.30 + \frac{5{,}900}{10^6}\times\$3 + \frac{400}{10^6}\times\$15 \approx \$0.00138 + \$0.0177 + \$0.006 = \$0.0251
$$

The cached call costs about $0.0251 against $0.0375, roughly a third less per turn, from ordering the context and freezing the prefix. Scale it: at 10,000 conversations a day, four turns each, five calls per turn (200,000 calls), the uncached bill is about $7,500 a day and the cached bill about $5,020, a difference near $2,480 a day, or roughly $74,000 a month, for an afternoon of layout work (all figures illustrative, at the section 2 rates and these token counts). Note what the write premium does *not* do here: the 4,600-token prefix is written once per five-minute window and read by every call in it, so under sustained traffic the amortised write cost rounds away. Route the simpler turns to the cheap tier on top of this and the multiplier compounds, which is the subject of section 7.

---

## 7. Cost guardrails to ship

Caching lowers the unit cost; guardrails keep the total from surprising anyone. Four are worth building before launch, not after the first invoice.

**Per-call and per-workflow budgets.** Give every workflow an explicit token ceiling per layer (the allocation table in [Post 04](../04-tokens-windows-budgets/index.md)) and a dollar ceiling per call, enforced in code. The layer that grows fastest, almost always retrieval or history, will eat everyone else's share the moment nobody is watching. A hard cap turns silent overspend into a loud, catchable error.

**Cheaper models for sub-tasks.** Not every call needs the frontier tier. Route short, well-defined steps (classification, intent detection, extraction, summarising old history) to the cheap tier, which costs about a fifth as much (section 2), and reserve the frontier tier for the reasoning that actually needs it. Two patterns recur: **cascade** (try the cheap model, escalate only when an eval flags the answer) and **plan-and-execute** (a frontier model writes the plan once, cheap models run the steps). Both cut average cost per task without touching tail quality.

**Cache-hit monitoring.** A cache you cannot observe is a cache you cannot trust. Providers report cache-read and cache-write token counts on every response; track the **cache-hit rate** (cached input tokens over total input tokens) as a first-class metric. A hit rate that drops after a deploy is the fingerprint of a prefix change: someone edited the system prompt, reordered tools, or slipped a timestamp in front of the breakpoint, and every request is now paying full input price. Alerting on that number catches a whole class of regressions before they show up on the bill. Wiring these signals into traces and dashboards is the subject of [Post 22](../22-observability/index.md); applying all of it to a real system is the RAG build in [Post 28](../28-build-rag-chatbot/index.md).

**Set `max_tokens` deliberately.** Because output is the five-times-priced side (section 3), an unbounded generation is an unbounded bill. Cap it per workflow and treat a truncation as a signal to redesign the task, not to raise the ceiling.

---

## Common pitfalls

- **Injecting a timestamp or session ID near the front of the prompt.** It changes the first bytes on every call, moving the cache breakpoint to position zero and reducing the hit rate to nothing. Volatile values go behind the breakpoint, always.
- **Editing the system prompt on every deploy.** Each edit re-writes the whole cache at the write premium, and the first post-deploy traffic runs at full input price. Freeze the prompt; batch changes; expect a cold window after each release.
- **Reordering tool definitions between builds.** The tool block is part of the cached prefix. Re-sorting it (an innocent refactor, an alphabetised map) invalidates everything after it. Pin the order.
- **Optimising input tokens while ignoring output.** Output costs about five times input. A verbose agent that regenerates whole files is bleeding from the expensive side; a lower `max_tokens` often beats any prompt trim.
- **Assuming caching is free money.** The write premium (1.25x or 2x input) means a prefix reused only a handful of times can cost *more* than not caching. Caching pays off with reuse, not by default.
- **Pricing the demo, not the deployment.** A few cents per call rounds to free until the daily volume multiplies it into a real line item. Do the volume arithmetic before shipping, not after.
- **Trusting last quarter's price table.** Providers change rates often; a stale table silently invalidates every downstream cost figure. Re-derive against the current pricing page.

---

## Further reading

- Anthropic, *"Pricing"* (2026): per-token input and output rates for the three tiers used throughout sections 2, 3, and 6. Prices change often; treat as orders of magnitude.
- Anthropic, *"Prompt caching"* (documentation, 2024–25): the cache-breakpoint prefix model, render order, the ~10% cache-read discount, the 1.25x / 2x write premiums, the 5-minute and 1-hour TTL tiers, and the minimum cacheable prefix in section 4.
- Pope, R. *et al.*, *"Efficiently Scaling Transformer Inference"* (2022): the prefill/decode split behind the input–output asymmetry in section 3 and the latency model in section 5.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 06 — Five context failure modes](../06-context-failure-modes/index.md)**: what breaks when a budget is wrong, and the five symptoms to look for.
- **[Post 04 — Tokens, windows, and budgets](../04-tokens-windows-budgets/index.md)** (back): the token, window, and budget definitions this post prices out.
- **[Post 22 — Observability](../22-observability/index.md)**: instrumenting cache-hit rate and per-turn cost so the guardrails in section 7 have data.
