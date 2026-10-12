# 04 - Tokens, windows, and budgets

> **TL;DR.** A token is the unit a large language model (LLM) reads, bills and runs out of room in, and how many tokens a piece of content takes depends on its shape (prose, code or JavaScript Object Notation, JSON) and on its language. Three numbers then govern every design decision in this series: the context window (the most tokens one call may hold), the budget (how many tokens, dollars and seconds a call may spend) and the triangle of latency, cost and quality, of which a design can favour two at the expense of the third. This post defines all three and sizes a customer-support agent on an envelope: about 10,500 input and 400 output tokens per call (illustrative counts), priced and timed before a line of the application is written.
>
> **Prerequisites:** [Post 03](../03-how-llms-read-context/index.md).
> **Safe to skip?** Skip it if a call's tokens, dollars and seconds can already be estimated from its layers without running it, and each layer of an agent already has an enforced token budget.
>
> **After reading, you will be able to:**
>
> - Explain why the same content costs more tokens as code, JSON or non-English text than as English prose, and estimate tokens from a word count.
> - Check that a prompt plus its output reserve fits the context window, treating the window as a ceiling rather than a target.
> - Estimate the cost and latency of a call from its input and output tokens, with and without a cached prefix.
> - Set a per-layer token budget for an agent and identify the layer that breaks it.
> - Decide between a smaller model on a longer prompt and a larger model on a shorter one for a given task.

![A long bar for the 200,000-token context window of Claude Sonnet 4.5 with a thin slice at its left end, zoomed into a strip of one call: 01 System prompt 3,000, 02 Tools and MCP descriptions 1,600, 03 Memory and state 1,200, 04 Retrieved chunks 2,500, 05 Conversation history 2,000, 06 User instruction 200, then 400 output tokens, 10,900 in all, with layers 01 and 02 bracketed as the 4,600-token stable prefix.](diagrams/01-window-and-budget.svg)

*The window is the ceiling and the budget is the much smaller share one call spends; the six layers divide that share.*

---

## 1. The question: what is a token, and what does one call spend?

Before a context can be designed, three quantities need numbers: how much a call may hold, how much it should spend, and what it costs in money and time. All three are counted in tokens, so the unit comes first.

A token is the unit a provider's tokeniser produces when it splits the input string. OpenAI's tokenisers, and many others, are **byte-pair encoding** (BPE) variants: a deterministic, reversible scheme that learns a vocabulary of sub-word units from a training corpus (Sennrich et al., 2016). Post 03 shows the mechanism. Common words become one token; rare words, names and unusual strings split into several, and whitespace is part of the token. OpenAI's `cl100k_base` encoding has a vocabulary of 100,277 tokens and its `o200k_base` encoding 200,019, as `snippets/count_tokens.py` prints with the `tiktoken` library.

OpenAI's "Tokenizer" page gives the usual rule of thumb: for common English text, one token is roughly three quarters of a word, so 100 tokens are about 75 words. The snippet's English paragraph of 69 words is 87 tokens under both encodings, 0.79 words per token, close to the rule. The rule is good enough for a budget and too rough for a bill, because the ratio depends on what the text is.

The snippet makes this visible by writing one support ticket three ways: as a paragraph of prose, as a Python dictionary and as indented JSON. The facts are identical; the token counts are not.

```text
the same ticket, three shapes (characters, then tokens per encoding):
  prose    356 chars    87 (1.00x prose)    87 (1.00x prose)
  python   425 chars   148 (1.70x prose)   148 (1.70x prose)
  json     517 chars   183 (2.10x prose)   183 (2.10x prose)
```

![Two bar charts of measured token counts. Left, one support ticket written three ways: prose 87 tokens, a Python dictionary 148, 1.70 times the prose, and indented JSON 183, 2.10 times, the same under cl100k_base and o200k_base. Right, one customer message: English 14 tokens under both encodings, Hindi 61 under cl100k_base and 22 under o200k_base.](diagrams/02-same-content-tokens.svg)

*Punctuation, quotes, indentation and keys are tokens too, and a script the vocabulary saw less often splits into more pieces.*

The figure adds the second effect: the same customer message, 57 characters in English and 57 in Hindi, is 14 tokens in English under both encodings, but 61 tokens in Hindi under `cl100k_base` and 22 under the newer `o200k_base`. Three consequences follow for budgeting.

1. **Code and structured data cost more per fact than prose.** In this measurement the Python form took 1.70 times the tokens of the prose and the JSON 2.10 times. By the same ratio (illustrative arithmetic), a record that fills 20,000 tokens as prose would need about 42,000 as indented JSON, which changes whether it fits a budget at all.
2. **Non-English text costs more, and by an amount that depends on the tokeniser.** A bilingual support agent priced on its English traffic underestimates the cost of its Hindi conversations, and the size of the error changes when the provider changes the vocabulary.
3. **Counting words is not counting tokens.** The counts above are OpenAI's encodings; Claude and Gemini use their own tokenisers, which `tiktoken` does not reproduce. A number quoted to anyone with a budget comes from the provider's own counter: `tiktoken` for OpenAI models (OpenAI, "Tokenizer"), Anthropic's token-counting endpoint for Claude (Anthropic, "Token counting"), and Google's token-counting method for Gemini.

---

## 2. The context window

The **context window** is the maximum number of tokens one call may hold, the input *and* the output it generates. Anthropic's "Context windows" page (consulted October 2026) says so directly: everything in the request counts, the system prompt, every message, the tool definitions, and the output generated for the turn as well.

What happens at the limit depends on which side overflows. On Anthropic's application programming interface (API), as that page describes it, an input that alone exceeds the window is rejected with an error ("prompt is too long") on every model. When the input fits but the input plus `max_tokens` does not, Claude 4.5 and newer models accept the request and stop generating when the window is full, with the stop reason `model_context_window_exceeded`; earlier models reject the request instead. Either way the window is a hard limit, and the failure on newer models is a truncated answer rather than an error.

Window sizes, as the providers' pages give them:

| Model | Window (tokens) | Source, date consulted |
|---|---|---|
| Claude Haiku 4.5 | 200,000 | Anthropic, "Context windows", October 2026 |
| Claude Sonnet 4.5 | 200,000 | Anthropic, "Context windows", October 2026 |
| Claude Opus 4.6 | 1,000,000 | Anthropic, "Context windows", October 2026 |
| Many Gemini models | 1,000,000 or more | Google, "Long context", page updated June 2026 |

These were current models in early 2026 (Anthropic now marks Claude Sonnet 4.5 deprecated), and windows change with new releases, so a real design reads the provider's page on the day. By the three-quarters rule, 200,000 tokens are about 150,000 words of English prose. The hero figure puts one call of the support agent of section 5 against the 200,000-token window: 10,900 tokens, a thin slice at the left of the bar.

Two warnings follow.

First, **the window is a ceiling, not a target.** Quality degrades well before the ceiling, for the reasons post 03 covers: attention spreads over more tokens, and information in the middle of a long input is used less reliably (Liu et al., "Lost in the Middle", 2023). Anthropic's page names the effect too: as the token count grows, accuracy and recall degrade. This series' working rule of thumb, an illustrative heuristic and not a measured threshold, is to plan for a fraction of the advertised window and to test before relying on the rest.

Second, **the input and the output share the window.** A call to a 200,000-token model that reserves 20,000 tokens for the answer through `max_tokens` leaves 180,000 for the input (illustrative numbers). An agent whose input creeps up to the window without that reserve gets its answers cut short.

---

## 3. The three budgets

Every call is constrained by three budgets at once. Engineering for one while ignoring the other two is a way for a feature to fail in production.

**The token budget** is the number of *input* tokens a design chooses to spend per call. It is bounded above by the context window and, more often, by cost and latency. As a starting point (illustrative rules of thumb, not measurements): 8,000 to 16,000 input tokens for an interactive assistant, 50,000 to 100,000 for a background agent that works for an hour, and up to 200,000 for batch document analysis on a model whose window allows it.

**The cost budget** is what the tokens cost in dollars. Prices are quoted per million tokens, separately for input and output. The table gives Anthropic's published rates in dollars per million tokens as of early 2026 (Anthropic, "Pricing"), still listed for these models when consulted in October 2026; prices change, so a design checks the page before committing a number:

| Tier | Model | Input | Output | Cache read |
|---|---|---|---|---|
| Frontier | Claude Opus 4.6 | 5.00 | 25.00 | 0.50 |
| Mid | Claude Sonnet 4.5 | 3.00 | 15.00 | 0.30 |
| Cheap | Claude Haiku 4.5 | 1.00 | 5.00 | 0.10 |

Two ratios in the table matter more than any single price. First, the **input and output asymmetry**: at each of these tiers an output token costs five times an input token, so a short prompt with a long answer can cost more than a long prompt with a short one. Second, the **tier gap**: the frontier model's input costs five times the cheap model's, and a cache read (section 5) costs a tenth of the base input price for these three models (Anthropic, "Prompt caching", consulted October 2026), a further ten-to-one gap within a tier.

**The latency budget** is how long the user, or the service upstream, will wait. A call's time splits into two terms (Pope et al., 2022): *prefill*, which reads the whole prompt in one parallel pass, and *decode*, which generates the answer one token at a time. With $N_{\text{in}}$ input tokens, $N_{\text{out}}$ output tokens and per-token times $t_{\text{prefill}}$ and $t_{\text{decode}}$,

$T \approx N_{\text{in}} \, t_{\text{prefill}} + N_{\text{out}} \, t_{\text{decode}}$.

Per token, prefill is far cheaper than decode, because the prompt's tokens are processed together while each output token waits for the one before it. The rates below are illustrative, chosen to show the shape and not measured on any provider; `snippets/envelope.py` applies them to the support agent's call of 10,500 input and 400 output tokens:

```text
latency of one call (10500 in, 400 out), illustrative rates:
  class      prefill ms/tok  decode ms/tok  prefill s  decode s  total s
  cheap                0.1            8.0       1.05      3.20     4.25
  mid                  0.2           16.0       2.10      6.40     8.50
  frontier             0.4           32.0       4.20     12.80    17.00
  prefill and decode take equal time when the prompt is 80 times the output
```

![Three horizontal bars for one call of 10,500 input and 400 output tokens at illustrative rates, each split into prefill and decode: cheap 1.05 plus 3.20 seconds, 4.25 in all; mid 2.10 plus 6.40, 8.50; frontier 4.20 plus 12.80, 17.00. Dashed outlines mark the rates as illustrative.](diagrams/03-latency-split.svg)

*At these rates a prompt 26 times longer than the answer still spends most of the call's time on the answer.*

The figure shows the consequence: although the prompt is 26 times longer than the answer, decode takes three times as long as prefill in every class. Under these rates, the prompt dominates only once it is more than 80 times the output. Shrinking the *prompt* helps latency on long inputs; shrinking the *output* helps on everything else. Streaming hides decode time, because the first tokens appear while the rest are generated, but it cannot hide prefill: the first token waits for the whole prompt to be read, which is why a long-context agent is slow to start even with streaming on. Real rates vary by provider, model, load and hardware, so a latency quoted to anyone is measured on the real workload.

---

## 4. The triangle

The three budgets pull against each other, and a design can favour any two at the expense of the third.

- **Cheap and fast** means accepting lower quality: a cheap-tier model on a small prompt. It suits high-volume classification, intent detection and simple extraction.
- **Cheap and high-quality** means accepting slow: a frontier model with prompt caching, batch processing or off-peak runs. It suits nightly analytics jobs.
- **Fast and high-quality** means accepting expensive: a frontier model on a focused prompt, with cache hits and reserved capacity. It suits the user-facing critical path of a paid product.

No configuration is cheap, fast and high-quality at once. A product that seems to be deserves a check: it may be compared with an older generation of models, or measured in a configuration other than the one in production.

The practical rule is to choose the corner per workflow, not per company. A coding agent's "explain this stack trace" call belongs in the fast and high-quality corner; its "summarise the last 200 turns" maintenance call belongs in the cheap and high-quality corner. Different models, different prompts, same product.

---

## 5. Sizing an agent on an envelope

The arithmetic below is a back-of-envelope sizing, written out once. It uses the mid-tier rates of section 3, Claude Sonnet 4.5 at 3 dollars per million input tokens and 15 dollars per million output tokens (Anthropic, "Pricing", as of early 2026).

Consider a customer-support agent with the per-call shape below. Two acronyms appear in it: **MCP** (Model Context Protocol, the open protocol through which an application connects a model to tool servers; [post 15](../15-tools-and-mcp/index.md)) and **RAG** (retrieval-augmented generation, which retrieves the top-k most relevant chunks from a store for this turn; [post 11](../11-rag-in-depth/index.md)). The token counts are illustrative:

| Layer | What it holds | Tokens per call (illustrative) |
|---|---|---|
| 01 System prompt | identity, format and rules | 3,000 |
| 02 Tools and MCP descriptions | the schemas of 8 tools | 1,600 |
| 03 Memory and state | the user's profile and 5 earlier tickets, summarised | 1,200 |
| 04 Retrieved chunks | the top-5 chunks from RAG, 500 tokens each | 2,500 |
| 05 Conversation history | the session so far, compressed | 2,000 |
| 06 User instruction | the customer's message | 200 |
| **Input total** | | **10,500** |
| Output | a typical reply | 400 |

One uncached call costs 10,500 times 3 dollars divided by 1,000,000, which is 0.0315 dollars of input, plus 400 times 15 dollars divided by 1,000,000, which is 0.006 dollars of output: 0.0375 dollars, under four cents. Now suppose 10,000 conversations a day, 4 turns per conversation and 5 model calls per turn for sub-agents and tool replies (an illustrative workload). That is 200,000 calls a day, and 200,000 times 0.0375 dollars is 7,500 dollars a day, or 225,000 dollars over 30 days, before any infrastructure. This is the calculation that turns "just call the API" into an engineering project.

**Turn on prefix caching.** The first 4,600 tokens, layers 01 and 02, are identical on every call. A cached prefix has a short lifetime, five minutes by default on Anthropic's API and refreshed at no cost each time it is read (Anthropic, "Prompt caching", consulted October 2026), so under steady traffic the prefix stays warm and nearly every call reads it from the cache. A read costs 0.1 times the base input price, 0.30 dollars per million tokens on Sonnet 4.5. One call then costs 4,600 times 0.30 dollars plus 5,900 times 3 dollars, both divided by 1,000,000, plus the same 0.006 dollars of output: 0.00138 plus 0.0177 plus 0.006, which is 0.02508 dollars. The day's bill falls from 7,500 dollars to 5,016 dollars, a saving of 33.1 percent from one architectural choice: a stable prefix, placed first. The occasional write of the prefix costs 1.25 times the base input price, rare enough at this traffic to round away; [post 05](../05-economics-of-context/index.md) prices it in full.

**Route the simple turns.** Suppose 60 percent of calls are short, questions of the frequently-asked kind (an illustrative share) and go to Claude Haiku 4.5 at 1 dollar and 5 dollars per million tokens, with the same cached prefix. Such a call costs 0.00836 dollars, the blended cost per call is 0.01505 dollars, and the day costs about 3,010 dollars: 2.49 times cheaper than the uncached baseline. Whether quality holds on the routed turns is a question for an evaluation set ([post 20](../20-evaluation/index.md)), not an assumption.

The whole envelope fits in a short function. This excerpt of `snippets/envelope.py` takes a per-layer token breakdown and the rates and returns the cost of one call:

```python
def call_cost(layers, price_in, price_out, out_tokens,
              cached_prefix=0, cache_read=0.10):
    """Cost of one LLM call in dollars.
    layers: {name: input_tokens}; price_* in $ per 1M tokens;
    cached_prefix: leading tokens billed at cache_read x price_in."""
    total_in = sum(layers.values())
    billable_in = total_in - cached_prefix
    return (cached_prefix / 1e6 * price_in * cache_read
            + billable_in / 1e6 * price_in
            + out_tokens / 1e6 * price_out)
```

Run from the series root, the snippet prints every figure of this section:

```text
calls per day: 200000
                         per call    per day   per 30 days
  uncached, Sonnet 4.5     0.03750    7500.00    225000.00
  cached prefix            0.02508    5016.00    150480.00
  cached, Haiku 4.5        0.00836    1672.00     50160.00
  routed 60% to Haiku      0.01505    3009.60     90288.00

caching saves 33.1% of the uncached bill
caching plus routing is 2.49 times cheaper than the uncached bill
```

### What prompt caching does and does not do

Prompt caching, also called prefix caching, stores the model's computed attention state for a prefix, the **key-value (KV) cache** that post 03 introduces, so a later call that starts with the identical prefix skips recomputing it. Yichao Ji's account of building the Manus agent ("Context Engineering for AI Agents: Lessons from Building Manus", July 2025) calls the KV cache hit rate the single most important metric for a production agent, and gives a timestamp at the start of the system prompt as a common way to destroy it. Three properties decide whether caching helps, as Anthropic's "Prompt caching" page describes them (consulted October 2026):

- **It caches only an identical prefix.** One changed token ends the reusable prefix at that point. Volatile content (the user turn, freshly retrieved chunks) goes last and stable content (the system prompt, the tool schemas) first, or nothing caches.
- **It has a minimum length.** A prefix shorter than the model's minimum is not cached at all: 1,024 tokens for Claude Sonnet 4.5, and 4,096 for Claude Haiku 4.5 and Claude Opus 4.6. The support agent's 4,600-token prefix clears both.
- **It expires, and writing it costs extra.** The default lifetime is five minutes, refreshed by every read, with a one-hour option. A write costs 1.25 times the base input price for the five-minute lifetime and 2 times for the one hour, so caching pays only when a prefix is read many times after it is written.

The cache is marked in the request with `cache_control`, either once at the top level, where the API places the breakpoint itself, or on individual blocks. Other providers cache too, with their own minimum lengths and discounts, and post 05 compares them. The architectural lesson is the same everywhere: **order the context from stable to volatile, so the expensive, unchanging tokens sit in front.**

---

## 6. Setting per-layer budgets

The arithmetic above holds only if each layer has a budget that the code enforces. A useful starting allocation, treating the input token budget as 100 percent (illustrative defaults, the series' own starting points rather than measured optima):

| Layer | Default share | Why |
|---|---|---|
| 01 System prompt | 5 to 15 percent | it is sent on every call and competes with the evidence for the model's attention |
| 02 Tools and MCP descriptions | 5 to 15 percent | above this, select tools per call rather than sending the whole catalogue ([post 15](../15-tools-and-mcp/index.md)) |
| 03 Memory and state | 5 to 10 percent | recall a few relevant facts; a memory layer that grows without bound crowds the rest |
| 04 Retrieved chunks | 20 to 40 percent | the largest variable lever; tune top-k to the budget, not the other way round |
| 05 Conversation history | 10 to 30 percent | summarise on a schedule ([post 12](../12-compress-strategies/index.md)), not at the limit |
| 06 User instruction | 1 to 5 percent | the smallest layer, although it is the reason for the call |
| Output reserve | 10 to 20 percent of the *window* | set by `max_tokens`; the model is not trusted to be brief |

The percentages are starting points, not laws. What matters is *having* a number per layer and checking it on every call. `snippets/envelope.py` checks the support agent of section 5 against these defaults:

```text
layer                            tokens  share  default
  01 System prompt                 3000  28.6%  5-15%  outside
  02 Tools and MCP descriptions    1600  15.2%  5-15%  outside
  03 Memory and state              1200  11.4%  5-10%  outside
  04 Retrieved chunks              2500  23.8%  20-40%
  05 Conversation history          2000  19.0%  10-30%
  06 User instruction               200   1.9%  1-5%
  input total                     10500
  output                            400
```

![For each of the six layers, a dashed band shows its default share of the input budget and a mark shows the support agent's share: 01 System prompt 28.6 percent against 5 to 15, 02 Tools and MCP descriptions 15.2 against 5 to 15, and 03 Memory and state 11.4 against 5 to 10 are outside their bands; 04 at 23.8, 05 at 19.0 and 06 at 1.9 percent are inside.](diagrams/04-layer-shares.svg)

*A per-layer budget turns "the prompt feels long" into a named layer and a number.*

The agent breaks three of the defaults, as the figure shows. Its system prompt is 28.6 percent of the input, nearly twice the top of its band. Because layers 01 and 02 sit in the cached prefix, the overrun costs little money, but it still takes window and attention from the evidence in layer 04. Without explicit numbers per layer, the layer that grows fastest, often the retrieved chunks or the history, silently takes the other layers' share.

---

## 7. Picking a model: a one-page decision

Model choice is the other half of the triangle. The five questions below are a heuristic for the common cases, walked in order; the first that gives a clear answer decides.

1. **Does the task need strong reasoning?** Multi-step planning, code synthesis, hard mathematics, an unfamiliar domain: the frontier tier.
2. **Is the task a short, well-defined extraction or classification?** The cheap tier; check on an evaluation set that the difference is too small to matter.
3. **Is the input long but the task simple?** Summarising a long report: a cheap-tier model whose window holds the input.
4. **Is the input short but the task hard?** Planning a refactor: the frontier tier with a small prompt, where the money pays for reasoning, not reading.
5. **Is the task user-facing and time-critical?** The mid tier with streaming, plus a per-call latency budget that falls back to a cheaper model on timeout.

Questions 3 and 4 settle the choice between a smaller model on a longer prompt and a larger model on a shorter one: the smaller model when the difficulty lies in the volume of input, the larger when it lies in the reasoning. Two patterns recur often enough to have names. **Cascade**: try the cheap model first and escalate to the frontier model only when a check ([post 20](../20-evaluation/index.md)) flags the cheap answer. **Plan and execute**: a frontier model writes the plan once and cheaper models carry out the steps. Both lower the average cost per task while keeping the frontier model for the cases that need it.

---

## 8. Make it run: the two snippets

Both snippets run from the series root in the root environment, which provides `tiktoken` with its encodings cached; neither makes a network call.

```text
uv run python posts/04-tokens-windows-budgets/snippets/count_tokens.py
uv run python posts/04-tokens-windows-budgets/snippets/envelope.py
```

`count_tokens.py` prints the counts of section 1; `envelope.py` prints the latencies of section 3, the costs of section 5 and the layer shares of section 6. Changing the layer counts, rates or traffic in `envelope.py` sizes any other agent. The estimate is then checked twice: the real prompt is counted with the provider's own token counter, and the rates are read from the provider's price page, with its date.

---

## 9. What can go wrong?

- **Estimating from words when the prompt is code or JSON.** A budget built on three quarters of a word per token is applied to a prompt full of tool results in JSON. The `usage` block of each response reports about twice the estimated input tokens, and the bill and the window fill twice as fast as planned.
- **No output reserve.** The input grows to fill the window and `max_tokens` is left at whatever fits. Answers stop mid-sentence, with a stop reason of `max_tokens`, or `model_context_window_exceeded` on newer Claude models, and nothing in the input looks wrong.
- **Pricing only the input.** A forecast multiplies input tokens by the input rate and forgets that output costs five times as much per token at the tiers of section 3. A feature that writes long answers comes in well over its estimate.
- **A cached prefix below the minimum.** A 3,000-token prefix is marked for caching on Claude Haiku 4.5, whose minimum is 4,096. The response reports zero `cache_read_input_tokens` on every call, and the expected saving never appears.
- **No cap on the growing layers.** History and retrieved chunks are appended without a per-layer limit. The cost per call climbs turn after turn, the first token arrives later and later, and finally the provider rejects the request because the prompt is too long.

---

## Common pitfalls

1. **Sizing the prompt at the window ceiling.** A larger window is permission, not advice; every token in it is paid for and read, and quality falls well before the limit.
2. **Treating tool schemas as free.** Eight tools took 1,600 tokens per call in the support agent's illustrative envelope; each one is worth auditing against how often it is used.
3. **Optimising the wrong corner of the triangle.** A user-facing call tuned only for cost, or a nightly batch job tuned for latency, pays for the wrong thing.
4. **Quoting a price without its model and date.** A per-million-token rate copied from an old note, or from another tier, makes the whole envelope wrong without anyone noticing.
5. **One model for every call.** Routing simple turns to a cheaper tier, checked by an evaluation, cut section 5's illustrative cached bill by a further 40 percent.

---

## Further reading

- OpenAI, *"Tokenizer"* and the `tiktoken` library: the three-quarters-of-a-word rule and the encodings counted in section 1.
- Anthropic, *"Token counting"* documentation: counting Claude's tokens before sending a request.
- Anthropic, *"Context windows"* documentation (consulted October 2026): what counts toward the window, the overflow behaviour and the window sizes of section 2.
- Google, *"Long context"* (Gemini API documentation, updated June 2026): Gemini's windows of a million tokens or more.
- Anthropic, *"Pricing"* (rates as of early 2026) and *"Prompt caching"* documentation (consulted October 2026): the prices of section 3, and the cache-read price, write premiums, lifetimes and minimum lengths of section 5.
- Ji, Y. (Manus), *"Context Engineering for AI Agents: Lessons from Building Manus"* (July 2025): the KV cache hit rate as the metric that matters, and the stable prefix that keeps it high.
- Sennrich, R. *et al.*, *"Neural Machine Translation of Rare Words with Subword Units"* (2016): the paper that adapted byte-pair encoding to sub-word units for neural machine translation.
- Pope, R. *et al.*, *"Efficiently Scaling Transformer Inference"* (2022): the prefill and decode phases behind the latency model of section 3.
- Liu, N. F. *et al.*, *"Lost in the Middle: How Language Models Use Long Contexts"* (2023): why quality falls before the window is full.

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 05 - The economics of context: pricing, caching, and latency](../05-economics-of-context/index.md):** prices the same agent in full, with cache writes, latency and cost guardrails.
- **[Post 12 - Compress strategies](../12-compress-strategies/index.md):** what to do when the history or the retrieved chunks break their per-layer budget.
