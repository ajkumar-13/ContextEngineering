# 22 - Observability, tracing, and cost

> **TL;DR.** A large language model (LLM) application can be debugged, costed and regression-tested only from what it recorded about each call. This post defines the trace, the span and the trace store, lists what every span must carry, reads four recurring bug shapes off a trace, builds the four headline dashboard numbers, and replays captured traces to stop a regression before it ships. Three short standard-library scripts produce every trace, dashboard and replay number it quotes.
>
> **Prerequisites:** [Post 05](../05-economics-of-context/index.md), [Post 20](../20-evaluation/index.md).
> **Safe to skip?** Skip it if every model, retrieval and tool call already lands in a trace store with its prompt, tokens, cost and latency, and no prompt change ships without a replay.
>
> **After reading, you will be able to:**
>
> - Wire trace and span instrumentation into an LLM application so that every model, retrieval and tool call is recorded with its prompt, tokens, cost and latency.
> - Read a trace and identify the four common bug shapes: context bloat, buried evidence, tool-storm and silent regression.
> - Set up a dashboard that surfaces cost, quality, latency and error trends, reading the 95th percentile rather than the mean.
> - Replay captured traces against a changed prompt or model and block the change when the diff shows a regression.
> - Compute a call's cost and cache-hit rate from its usage fields, and trace a falling hit rate to the change that broke the prefix.

![One agent turn as eleven spans on a time axis, with dashed illustrative bars: the turn takes 4,500 ms and 0.02558 dollars, the query rewrite 350 ms and 0.00050 dollars, the model call 3,800 ms and 0.02508 dollars. Beside it, four dashboard cards over every trace: cost per session at the median and p95, latency at p95, quality, and errors by kind.](diagrams/01-turn-as-span-tree.svg)

*One turn is a tree of timed, priced spans; the dashboard is the same fields aggregated over every trace.*

---

## 1. The question: what must be recorded about every call?

Classical observability (logs, metrics and traces in the OpenTelemetry sense) grew up around requests of small, steady cost whose failures show in a status code. An LLM call breaks both assumptions.

Its cost depends on what the assembler put in the window. On Claude Opus 4.6, this series' frontier model as of early 2026, at 5 dollars per million input tokens and 25 per million output tokens (Anthropic, "Pricing", as [post 05](../05-economics-of-context/index.md) quotes it), a 2,000-token prompt with a 300-token answer costs $2{,}000 \times 5 / 10^6 + 300 \times 25 / 10^6 = 0.0175$ dollars, and a 900,000-token prompt with a 2,000-token answer on the same endpoint costs $900{,}000 \times 5 / 10^6 + 2{,}000 \times 25 / 10^6 = 4.55$ dollars (illustrative sizes). It can fail with a fluent, well-formed, wrong answer that returns status 200.

So the record of a call has to hold what classical tracing never kept: the full prompt as sent, the full response, the model, the tool calls and their results, the token counts split by cache status, the cost and the latency. This post asks what that record looks like, where it lives and how to read it.

---

## 2. The trace, the span and the trace store

A **trace** is the record of one user-facing interaction: a chat turn, an agent run, a workflow execution. Inside it are **spans**, timed records of each operation, nested by parent: assembling the context, each retrieval, each model call, each tool call, each sub-agent. Every span carries a name, a parent, start and end times, a payload (a prompt, a query, tool arguments) and the metrics of its kind.

The **trace store** is the store of captured traces, each a copy of the full prompt and response of every model call in it, with the spans around them. Everything later in this post reads from it: the dashboard aggregates it, a bug report is answered by opening one trace in it, and a replay re-runs inputs frozen from it. Because it copies every prompt, it also copies whatever personal data entered the window (section 8).

`snippets/trace_store.py` holds a small tracer and simulates one turn of a support agent with a fake clock and illustrative token counts: it retrieves through RAG (retrieval-augmented generation, [post 11](../11-rag-in-depth/index.md)), calls the model, and issues a refund through a tool. It prints the turn as the trace store holds it:

```text
trace store: 1 trace, 11 spans
turn                      4500 ms  $0.02558
  assemble_context          40 ms
    load_memory             30 ms
    select_tools            10 ms
  retrieve                 560 ms
    query_rewrite          350 ms  $0.00050  claude-haiku-4-5: in 300 (cache read 0) out 40
    hybrid_search           90 ms
    rerank                 120 ms
  llm_call                3800 ms  $0.02508  claude-sonnet-4-5: in 10500 (cache read 4600) out 400
  tool_call issue_refund   100 ms
    db_query                60 ms
```

The figure at the top draws this tree on a time axis: the model call is 3,800 of the 4,500 milliseconds and 0.02508 of the 0.02558 dollars. It is post 05's agent turn at its early-2026 rates: 10,500 input tokens on Claude Sonnet 4.5, of which 4,600, layers 01 and 02, are read from the cache.

---

## 3. What to instrument

A starter set that covers the bugs of section 5:

- **One trace per user-facing interaction**, tagged with the session, the user and the release.
- **One span per model call**, with the model, the full prompt, the full response, input tokens split into fresh, cache-read and cache-write, output tokens, cost and latency.
- **One span per retrieval**, with the query, the top-N candidates with ids and scores, and the top-k that was packed.
- **One span per tool call**, with the name, the arguments, the result (or its size), the status and the latency.
- **One span per sub-agent and per memory read or write**, with its subtree or row ids.

The rule behind the list: every operation that could cause a bug gets its own span.

**Token fields need care.** Anthropic's usage block reports `input_tokens`, `cache_read_input_tokens` and `cache_creation_input_tokens`, and its "Prompt caching" page (consulted October 2026) defines `input_tokens` as the tokens after the last cache breakpoint: the total input is the sum of the three. The OpenTelemetry semantic conventions for generative AI (GenAI), kept in the `semantic-conventions-genai` repository and marked Development (consulted October 2026), name the attributes `gen_ai.usage.input_tokens`, `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens` and `gen_ai.usage.output_tokens`, and their Anthropic page says the cache fields must be added to Anthropic's `input_tokens` to compute `gen_ai.usage.input_tokens`. The snippet's `record_usage` does exactly that, and prices the call at post 05's multipliers:

```python
def record_usage(span, model, usage):
    """Copy a provider usage block onto an LLM span, and price the call.

    usage holds Anthropic's fields. Its input_tokens counts only the tokens after the
    last cache breakpoint, so the total input is the sum of three fields.
    """
    fresh = usage["input_tokens"]
    read = usage.get("cache_read_input_tokens", 0)
    write = usage.get("cache_creation_input_tokens", 0)
    out = usage["output_tokens"]
    rate = RATES[model]
    a = span["attrs"]
    a["gen_ai.request.model"] = model
    a["gen_ai.usage.input_tokens"] = fresh + read + write
    a["gen_ai.usage.cache_read.input_tokens"] = read
    a["gen_ai.usage.cache_write.input_tokens"] = write
    a["gen_ai.usage.output_tokens"] = out
    a["cost_usd"] = (
        fresh * rate["input"]
        + write * rate["input"] * CACHE_WRITE_5M
        + read * rate["input"] * CACHE_READ
        + out * rate["output"]
    ) / 1e6
```

The same file holds `traced_anthropic_call`, which wraps one live Messages API (application programming interface) call in a span; it needs the Anthropic software development kit (SDK) and a key, and the offline run never calls it.

**Content capture is opt-in.** The GenAI conventions list the prompt and the response (`gen_ai.input.messages`, `gen_ai.output.messages`, and `gen_ai.system_instructions` for the system prompt) as opt-in attributes, so instrumentation that follows them records tokens and timings but not the text unless told to. For debugging, the text is the artefact most worth keeping: without the prompt, none of the bug shapes of section 5 can be confirmed. Switching capture on is a decision taken together with the controls of section 8.

---

## 4. The four numbers every dashboard needs

Four numbers belong on the headline dashboard.

**1. Cost per session, median and 95th percentile (p95).** The p95 is the value that 95% of sessions stay at or below. It is the early warning for context bloat, sub-agent loops and over-fetching retrieval; a jump after a deploy (30% week over week, as an illustrative threshold) points first at a change that puts more into the window than intended.

**2. Latency, p95.** A slow session is that user's whole experience of the product, and the mean hides it.

**3. Quality.** The end-to-end evaluation score of [post 20](../20-evaluation/index.md), computed on a sample of real traffic, beside the rate of explicit user feedback. Without it on the same screen, a cost optimisation can degrade the product unseen.

**4. Error rate, by kind.** Tool errors, schema-validation failures, refusals, timeouts, retries. Each kind has its own cause; summed into one number they hide each other.

`snippets/dashboard.py` computes three of the four on two weeks of synthetic, illustrative traffic: 1,000 sessions a week, of which 2% in week A and 8% in week B take a slow path (an uncached prefix and a retry, 7 seconds extra). Its p95 is the nearest-rank percentile. It prints:

```text
1000 synthetic sessions per week; slow-path share: week A 2%, week B 8%

                            week A    week B
latency mean, s               4.63      5.03
latency median, s             4.55      4.59
latency p95, s                5.58     11.18
cost per session median      0.100     0.102
cost per session p95         0.169     0.184
errors per 1000 sessions, by kind:
  tool_error                     9        15
  schema_invalid                 4         6
  refusal                        4         3
  timeout                        5        19
```

The figure below draws the latency and cost rows. The median moved by 0.04 seconds and the mean by 0.40, while the p95 doubled, from 5.58 to 11.18 seconds: a dashboard of means shows a 9% drift where the p95 shows a broken path. Timeouts rose with it, from 5 to 19; the other error kinds, drawn at the same rates in both weeks, moved only by chance, which is why each kind is read against its own history.

![A dot plot for two weeks of 1,000 synthetic sessions each, week A against week B. Latency: mean 4.63 and 5.03 seconds, median 4.55 and 4.59, p95 5.58 and 11.18. Cost per session: median 0.100 and 0.102 dollars, p95 0.169 and 0.184.](diagrams/02-mean-hides-tail.svg)

*Raising the slow-path share from 2% to 8% barely moves the median; the p95 doubles.*

---

## 5. Reading a trace: four bug shapes

Four shapes recur in the author's experience; each is invisible in the answer and plain in a trace that captured the prompt. The figure lays them side by side.

![A four-row table of shape, trace, prompt and fix. Context bloat: 05 Conversation history keeps old tool results; compress. Buried evidence: the best chunk sits mid 04 Retrieved chunks; select, bookend packing. Tool-storm: 02 Tools and MCP descriptions overlap; select and isolate. Silent regression: 01 System prompt lost a line; replay gate.](diagrams/03-bug-shapes.svg)

*None of the four is fixed in the model; every fix lives in the window or in the gate in front of it.*

**Shape 1: context bloat.** The model span shows input tokens climbing turn after turn, to 80,000 by turn 40 of a long session, and the prompt shows layer 05, conversation history, holding 60,000 tokens of tool results that were read once and never cleared (illustrative sizes). The fix is compress, here tool-result clearing ([post 12](../12-compress-strategies/index.md), section 4), not a bigger model.

**Shape 2: buried evidence.** The retrieval span shows the right chunk in the top-k with a high score, yet the answer states a wrong fact. The prompt shows that chunk packed in the middle of layer 04, retrieved chunks, where models use information least reliably ([post 03](../03-how-llms-read-context/index.md), section 5): lost-in-the-middle. The first fix is bookend packing, the packing lever of select ([post 09](../09-select-strategies/index.md), section 5).

**Shape 3: tool-storm.** The trace shows fifteen calls in one turn to the same `search_*` tool with slightly different arguments. The prompt shows layer 02, tools and MCP (Model Context Protocol) descriptions, with tools whose descriptions overlap, and a system prompt with no stop rule. This is tool-storm ([post 06](../06-context-failure-modes/index.md), section 6), whose first fixes are select and isolate: trim the catalogue to the tools the turn needs ([post 15](../15-tools-and-mcp/index.md), section 4), say in each description when not to call it, add a budget rule, cap the result size. Post 06's alert signals, tool calls and tokens per turn, are span counts.

**Shape 4: silent regression.** The dashboard shows cost per session down a week ago (20%, as an illustrative figure), and quality down the same week. Traces grouped by release show why: a "cleanup" change removed a line from layer 01, the system prompt, that the model had relied on. The fix is to restore the line and add a fixture so that the same change cannot ship again unseen, which is what replays do.

---

## 6. Replays and regression detection

A trace store is also a fixture library: each trace holds the full input to every call, so a past interaction can be run again against a new prompt, model or retrieval configuration. This is the production-fed counterpart of the curated evaluation set of [post 20](../20-evaluation/index.md), written in advance.

The loop has three steps, drawn in the figure below:

- **Capture.** Freeze the inputs of sampled traces that span the common intents. A triaged failure becomes a permanent fixture.
- **Re-run.** On every prompt or model change, replay the frozen inputs through the new configuration. Deterministic steps (parsing, routing, tool selection) are checked exactly; generative steps go through the rubric or LLM judge of post 20.
- **Diff.** Compare with the recorded baseline. A failing fixture blocks the change, as continuous integration (CI) blocks code that fails its tests.

![Five boxes joined left to right: the trace store, capture with 8 fixtures frozen, a re-run on prompt v13, a diff with routes 8 of 8 and rubric 5 of 8, and a gate that blocks v13. Below, eight fixture cells with their routes: fx-02, fx-05 and fx-07, the refund questions, fail; the other five pass.](diagrams/04-replay-loop.svg)

*The traces already exist; freezing a sample and wiring the diff into the review gate is the whole of the new work.*

`snippets/replay.py` runs shape 4 offline. Eight frozen fixtures are replayed against the baseline system prompt, v12, and a "cleanup" release, v13, that dropped the line telling the agent to state the refund window. A deterministic stand-in replaces the model, so the run needs no key; it states the window only when the prompt asks for it, the dependence a real model can have on an instruction nobody remembers writing. It prints:

```text
fixtures frozen from the trace store: 8
prompt v12 (baseline): routes match 8/8, rubric passes 8/8
prompt v13 (cleanup): routes match 8/8, rubric passes 5/8; failing fx-02, fx-05, fx-07
gate: block v13
```

Every route matches; the three refund questions fail the rubric, and the gate blocks the release before it ships.

---

## 7. Cost engineering and cache-hit monitoring

The trace store holds the cost of every call beside its cause. Three knobs show up in it first.

**Prompt-cache use.** The rule is post 05's, from Anthropic's "Prompt caching" page (consulted October 2026): a cache read costs 0.1 times the base input price for most models (the page lists lower multipliers for some newer models), and a cache write costs 1.25 times the base input price for a five-minute entry and 2 times for a one-hour entry, so a prefix pays only when it is read again within its lifetime ([post 05](../05-economics-of-context/index.md), section 4). OpenAI's "Prompt caching" guide (consulted October 2026) says caching is enabled by default for supported models, discounts cached input by up to 95%, and reports the count in the Responses API's `usage.input_tokens_details.cached_tokens`; Gemini offers implicit and explicit caching, as post 05 describes.

The number to watch is the **cache-hit rate**, cache-read input tokens over total input tokens. On the turn of section 2 it is $4{,}600 / 10{,}500 = 43.8\%$, the ceiling for that layout, because layers 03 to 06 change on every call. The denominator matters: the snippet also prints the rate over Anthropic's `input_tokens` alone, $4{,}600 / 5{,}900 = 78.0\%$, which looks healthy and is wrong, because that field excludes the cached tokens. A hit rate that drops after a deploy is the fingerprint of a prefix change (a timestamp in the system prompt, a reordered tool list, a non-deterministic serialisation): the first trace after the deploy shows a cache write where a read was expected, and diffing its prompt against the last good one finds the change.

**Per-call model selection.** The trace names the model of every call. Routing, query rewriting and summarising old history can go to the cheap tier, a fifth of the frontier tier's price per token (post 05, section 2); the rewrite of section 2 costs 0.00050 dollars on Claude Haiku 4.5. A small-model task running on the frontier model is a cost bug the trace makes visible.

**Sub-agent overuse.** Three nested sub-agent spans for a task that fits in one window are a cost bug too ([post 13](../13-isolate-strategies/index.md)); flag sessions above a sub-agent threshold and review their traces.

A pattern that pays back is **a per-feature cost budget** read from the trace store: the support agent gets, say, 0.10 dollars per session (an illustrative budget), sessions above it are flagged, and the weekly trend is reported. Cost becomes a daily signal instead of a surprise on the monthly invoice.

---

## 8. Privacy and PII in traces

Tracing every prompt and response stores user data, often including **PII** (personally identifiable information: names, email addresses, payment details). Four controls belong in place before content capture is switched on:

- **Retention.** Traces older than a set number of days are deleted; the number is set by the regulatory and contractual environment, not by convenience.
- **Selective redaction.** Masking emails, phone numbers and payment data on the way in removes personal data from the record, and debugging value with it, so it is applied to the fields a rule names, not to the whole prompt.
- **Access control.** The trace store is readable only by people allowed to read the underlying transcripts.
- **Opt-out.** Where the terms of service require it, users can opt out of recording, and the trace records the choice.

The full treatment is [post 24](../24-privacy-and-governance/index.md).

---

## 9. The tools

From each tool's documentation as consulted in October 2026; there is no strict ranking, and the criterion is operational fit.

- **LangSmith** (LangChain). Observability, evaluation and prompt engineering for many frameworks and providers; cloud, hybrid or self-hosted.
- **Langfuse.** Open source and self-hostable, with tracing based on OpenTelemetry, prompt management, evaluation and datasets.
- **Phoenix** (Arize). Built on OpenTelemetry; runs locally, in a container or in the cloud; tracing, LLM-based evaluation, datasets and experiments. Its repository calls it open source and licenses it under the Elastic License 2.0.
- **Braintrust.** Observability centred on evaluation: logs feed datasets with human feedback, and changes are tested in experiments before they ship.
- **Helicone.** Open source under Apache 2.0; its AI gateway logs every request's cost and latency once an OpenAI-compatible client points at the gateway's base URL, and groups an agent's requests into sessions. The lightest set-up, with less structure inside an agent run.
- **OpenTelemetry directly.** The vendor-neutral standard: spans around each call, the GenAI attributes of section 3, any OpenTelemetry backend. The conventions are marked Development, so the instrumentation pins the version it follows.


---

## 10. Make it run

All three scripts run from the series root with the standard library only and make no network call:

```text
uv run python posts/22-observability/snippets/trace_store.py
uv run python posts/22-observability/snippets/dashboard.py
uv run python posts/22-observability/snippets/replay.py
```

Their token counts, timings and traffic are illustrative: they show each mechanism, not a measurement. The measurement is a short live exercise: instrument the RAG pipeline of [post 11](../11-rag-in-depth/index.md) with OpenTelemetry spans exported to Langfuse or Phoenix, read the cost and latency of each span over ten turns, then change the prompt and replay one captured trace against it.

---

## 11. What can go wrong?

- **The hit rate is computed over the wrong field.** Dividing cache reads by Anthropic's `input_tokens` reports 78.0% on a layout whose real rate is 43.8%, and a cost model built on that field undercounts every cached call's input.
- **Content capture was never switched on.** The first serious bug report finds traces with tokens and timings but no prompt: the shape is visible, the cause is not.
- **Traces carry no release tag.** A silent regression shows on the dashboard, but traces cannot be split into before and after, so the change behind it is found by guesswork.
- **A replay compares generative output byte for byte.** Every fixture differs on every run, the gate is switched off within a week, and the next regression ships. Exact comparison is for deterministic steps; generative steps get a rubric or a judge.

---

## Common pitfalls

1. **Tracing the response but not the prompt.** No bug shape can be confirmed without the window that produced it.
2. **Reading the mean instead of the p95.** The tail is what users experience, and the mean barely moves when it breaks.
3. **A cost dashboard with no quality panel.** A cost cut that removed an instruction passes unseen until users complain.
4. **No per-feature budget.** Cost surprises everyone at the end of the month instead of flagging the session the same day.
5. **Content capture with no retention policy.** The trace store becomes the largest copy of user data, kept indefinitely.

---

## Further reading

- OpenTelemetry, *"Semantic conventions for generative AI systems"*, `semantic-conventions-genai` repository (status Development, consulted October 2026): the span attributes, the opt-in content attributes, and how Anthropic's cache fields map to `gen_ai.usage.input_tokens`.
- Anthropic, *"Prompt caching"* documentation (consulted October 2026): the usage fields and the cache multipliers of sections 3 and 7.
- OpenAI, *"Prompt caching"* guide (consulted October 2026): default caching, the cached-input discount and the `cached_tokens` field.
- LangSmith, Langfuse, Arize Phoenix, Braintrust and Helicone documentation (all consulted October 2026): the tools of section 9.

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 23 - Security and prompt injection](../23-security/index.md):** the attacks a trace must make visible, and the audit trail a response to them depends on.
- **[Post 24 - Privacy, PII, and data governance](../24-privacy-and-governance/index.md):** governs the trace store this post defines, the second copy of every prompt.
