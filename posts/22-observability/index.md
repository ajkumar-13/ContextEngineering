# 22 · Observability, tracing, and cost

> **TL;DR.** Observability is what turns an LLM system from a black box into a debuggable one. The minimum stack is **traces** (every call, every prompt, every token, every cost), **spans** (the structure inside an agent run), and **dashboards** (cost, latency, quality, error rate). As of early 2026 the mature tools include LangSmith, Langfuse, Phoenix, Helicone, and Braintrust; there is no strict ranking, so choose on operational fit. This post is a practitioner's guide: what to instrument, how to read the traces, and the four numbers every dashboard needs.
>
> **After reading this you will be able to:**
> - Wire trace and span instrumentation into an existing LLM application.
> - Read a trace and identify the four most common bug shapes.
> - Set up a dashboard that surfaces cost, quality, latency, and error trends.

![Trace tree for one agent turn on the left, fanning from a root span into context-assembly, retrieval, model-call, tool-call, and sub-agent spans with their latency, tokens, and cost; on the right, four headline dashboard cards showing cost per session, p95 latency, quality, and error rate.](diagrams/00-hero-observability.svg)
*One agent turn is a tree of spans; four headline numbers turn the tree into a dashboard.*

---

## 1. Why observability matters for LLM systems

Conventional observability (logs, metrics, traces in the OpenTelemetry sense) was built for systems where the cost of a single request is small and predictable, and the quality of a response is binary. LLM systems break both assumptions: a single request can cost ten cents or ten dollars depending on what got into the prompt, and "quality" is a soft, multi-dimensional judgement.

This means LLM observability has to record *more* per call than a normal observability stack, including artefacts that classical systems never bothered with: the full prompt, the full response, the model version, the tool calls, the reasoning trace, the token counts, and the dollar cost. Without these, debugging is anecdote and capacity planning is guessing.

The good news: the field has converged on a small standard set of structured records, the **trace**, that captures all of this and that all the major tools speak.

---

## 2. The trace and the span

A **trace** is the record of one user-facing interaction (a single chat turn, an agent run, a workflow execution). Inside a trace are **spans**: nested records of every operation: the system-prompt assembly, each retrieval call, each LLM call, each tool execution, each sub-agent invocation.

A typical trace for one agent turn (the retrieval span here runs **RAG**, retrieval-augmented generation, the pipeline from [Post 11](../11-rag-in-depth/index.md)). The numbers below are illustrative, not real pricing:

```
trace: customer-support / session-A1B2 / turn-7         5.2 s   $0.043
├─ span: assemble_context                              0.05 s
│   ├─ span: load_memory                               0.30 s   $0.001  (256 tok in / 80 tok out)
│   └─ span: select_tools                              0.20 s   $0.000  (cached)
├─ span: retrieve_rag                                  0.40 s
│   ├─ span: query_rewrite                             0.20 s   $0.001
│   ├─ span: hybrid_search                             0.10 s
│   └─ span: rerank                                    0.10 s   $0.002
├─ span: llm_call (mid-tier model)                     3.80 s   $0.038  (12 400 tok in / 380 tok out)
└─ span: tool_call (issue_refund)                      0.20 s
    └─ span: db_query                                  0.10 s
```

*A trace tree for one agent turn: nested spans, each with its own latency, token, and cost figures (illustrative).*

Every span carries: name, parent, start/end timestamps, a typed payload (the prompt for an LLM span; the query for a search span; the args for a tool span), and the metrics specific to its kind (tokens, cost, latency, error). The whole tree is queryable, drillable, and shareable as a single URL, which is exactly the affordance that makes "show me the trace" a productive bug-report channel.

---

## 3. What to instrument

A reliable starter set:

- **One trace per user-facing interaction.** Tagged with `user_id`, `session_id`, `release_version`.
- **One span per LLM call.** Captures `model`, `prompt`, `response`, `input_tokens`, `output_tokens`, `cost`, `latency_ms`, `cached_tokens`. Do not redact the prompt unless there is a hard regulatory reason; the prompt is the artefact most worth keeping.
- **One span per retrieval.** Captures the query, the retrieved chunks (with their ids and scores), the reranker scores, the final pack.
- **One span per tool call.** Captures the tool name, the args, the result, the exit code, the latency.
- **One span per sub-agent invocation.** With its own nested trace inside.
- **One span per memory read/write.** With the kind, the cell ids, the source.

The pattern: every operation that *might* be the cause of a bug is its own span. When the trace is right, the next-week debugging session is a 5-minute lookup, not a 5-hour reconstruction.

Wiring this in is a few lines. The minimal shape, using an OTel-style tracer around one Anthropic call, is:

```python
from opentelemetry import trace
from anthropic import Anthropic

tracer = trace.get_tracer("support-agent")
client = Anthropic()

def answer(turn, session_id):
    with tracer.start_as_current_span("turn") as t:      # one trace per interaction
        t.set_attribute("session_id", session_id)
        with tracer.start_as_current_span("llm_call") as s:  # one span per LLM call
            resp = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=512,
                messages=[{"role": "user", "content": turn}],
            )
            u = resp.usage
            s.set_attribute("input_tokens", u.input_tokens)
            s.set_attribute("output_tokens", u.output_tokens)
            s.set_attribute("cached_tokens", getattr(u, "cache_read_input_tokens", 0))
        return resp
```

A managed tool (Langfuse, LangSmith, Phoenix, Braintrust) replaces the manual `set_attribute` calls with an SDK wrapper or a proxy, but the structure is identical: a span per call, carrying tokens, cost, and cache stats.

---

## 4. The four numbers every dashboard needs

Out of the dozens of metrics the trace store can compute, four are non-negotiable on the headline dashboard.

**1. Cost per session (median, p95).** The leading indicator for context bloat, sub-agent loops, and retrieval-over-fetch. A sharp week-over-week jump in p95 cost (say, 30 % as a hypothetical) almost always means a recent change is putting more into context than intended.

**2. Latency p95.** The user-experienced metric. Average is a lie; tail is what matters. A jump in p95 with stable median often means a small fraction of sessions hit a slow path that needs a fix (uncached prefix, slow tool, sub-agent retry storm).

**3. Quality (offline LLM-judge or thumbs).** The end-to-end eval score from [Post 20](../20-evaluation/index.md), computed nightly on a sample of real traffic, plus the explicit-feedback rate. Without quality on the dashboard, cost and latency optimisations can silently degrade the product.

**4. Error rate, by kind.** Tool errors, schema-validation errors, refusal rate, timeout rate, retry rate. Each kind tells a different story; combined into one number they are useless.

Four dashboards (or one dashboard with four panels). Every team change reviews them before declaring success.

---

## 5. Reading a trace: four common bug shapes

A short field guide to what bugs look like in a trace.

**Shape 1: context bloat.** The LLM span shows 80 000 input tokens. Drill into the prompt. The conversation history span shows 60 000 tokens because tool results were never cleared ([Post 12](../12-compress-strategies/index.md), §4) and a 40-turn session accumulated. The fix is in the compression policy, not the model.

**Shape 2: retrieval miss.** The retrieval span shows the right chunks were returned with high scores, but the LLM span's response cites a wrong fact. Drill into the prompt. The chunks were packed in the middle of the context, where attention is weakest ([Post 03](../03-how-llms-read-context/index.md), §4). The fix is bookend layout ([Post 09](../09-select-strategies/index.md), §5).

**Shape 3: tool storm.** The trace shows 15 tool calls in one turn, all to the same `search_*` tool with slightly different queries. Drill into the prompt. The tool descriptions are similar; the model is confused ([Post 06](../06-context-failure-modes/index.md), §3) and is brute-forcing. The fix is tool selection or tool-name disambiguation ([Post 15](../15-tools-and-mcp/index.md), §4).

**Shape 4: silent regression.** The dashboard shows cost dropped a week ago, say 20 % as a hypothetical. Champagne. Then quality dropped the same week. Drill into traces from before and after. A "cleanup" PR removed an instruction the model had been silently relying on. The fix is reverting the prompt and adding a fixture so it cannot happen again. This is exactly the case that **replays** catch, which the next section treats in full.

The pattern: most LLM bugs are *visible in the trace* once the right things are instrumented. The cost of *not* instrumenting is paying engineering time to reconstruct what was already happening.

---

## 6. Replays and regression detection

Traces are not only a forensic record; they are a **fixture library**. Because a trace stores the full input to every call, any past interaction can be re-run against a new prompt, a new model, or a new retrieval config, and the outputs compared. This is the online counterpart to the offline eval set in [Post 20](../20-evaluation/index.md): the eval set is curated in advance, whereas a replay corpus is harvested from production traffic and grows for free.

A practical replay loop:

- **Capture.** Sample real traces (say, a few hundred spanning the common intents) and freeze their inputs. Interesting failures, once triaged, become permanent fixtures so the same bug cannot recur silently.
- **Re-run.** On every prompt or model change, replay the frozen inputs through the new configuration. Deterministic sub-steps (parsing, routing, tool selection) can be checked exactly; generative steps go through the LLM-judge or a rubric from [Post 20](../20-evaluation/index.md).
- **Diff.** Compare new outputs to the recorded baseline. A drop on any fixture blocks the change, the same gate CI already applies to code.

Replays are what turn Shape 4 (silent regression) from a next-quarter surprise into a pull-request check. When a "cleanup" PR removes an instruction the model was quietly relying on, the replay diff lights up before the change ships, not after quality has already sagged in production. The discipline is cheap: the traces already exist; the only new work is freezing a representative sample and wiring the diff into the change-review gate.

---

## 7. Cost engineering

Observability is also where cost engineering lives. Three knobs the trace store will surface immediately.

**Prompt caching utilisation.** Cached prefix tokens are billed at a large discount, but the mechanics differ by provider (see [Post 04](../04-tokens-windows-budgets/index.md), §5): Anthropic cache **reads** bill at roughly 10 % of the base input price, while cache **writes** cost *more* than a normal input token (1.25× for the 5-minute tier, 2× for the 1-hour tier), so caching only pays off when the same prefix is reused many times (Anthropic, "Prompt caching"). OpenAI caching is automatic and discounts cached input by a smaller amount (around 50 %); Gemini offers both implicit and explicit context caching. The trace records `cached_tokens` per call. A well-behaved assistant with a stable system prompt and tool catalogue should cache the large majority of its input tokens on conversational turns; when the cached fraction is low, look at why the prefix is invalidating, usually moving system content (date strings, dynamic counters) sitting at the top.

**Per-call model selection.** The trace shows which model handled each call. Most production stacks use a small model for routing, query rewriting, and summarisation; a larger model for the main reasoning step. If a small-model span is using the large model, that is a cost bug.

**Sub-agent overuse.** A trace with three nested sub-agent spans for a task that fits in one window is a cost bug. Set a guard: a metric that flags sessions whose sub-agent count exceeds a threshold; review the traces; either justify or refactor.

A pattern that pays back: **a per-feature cost budget** wired to the trace store. The "support agent" feature has a budget of $0.10 per session; sessions above that are flagged for review; week-over-week trends are reported. This turns cost from a quarterly accounting surprise into a daily engineering signal.

---

## 8. Privacy and PII

Tracing every prompt and response means storing user data, often including **PII** (personally identifiable information: names, emails, payment details). The disciplines that have to be in place:

- **Retention policy.** Traces older than *N* days are deleted. *N* is set by the regulatory environment (GDPR, HIPAA), not by what is convenient.
- **PII redaction.** Optional layer that masks emails, phone numbers, payment data on the way into the store. Useful for compliance; also degrades debugging value, so apply selectively.
- **Access control.** Trace stores carry a lot of customer data. Production traces should not be readable by anyone who would not be allowed to read the underlying transcripts.
- **User opt-out.** Where the terms of service require it, allow users to opt out of trace recording (and confirm the choice in the trace itself).

These are unsexy and unavoidable. Most production teams set them up once and then never think about them; teams that ship without them learn the hard way.

---

## 9. The tools

A short, opinionated assessment as of early 2026. There is no strict ordering here; the sensible criterion is operational fit, not a maturity leaderboard.

- **LangSmith.** Mature and full-featured, with more friction to self-host. First-party LangChain integration but works with any framework. Strong eval integration. Pricing is per trace.
- **Langfuse.** Open-source first; self-hostable; strong dashboards; per-trace pricing on the cloud version. The right default for teams that want control.
- **Phoenix (Arize).** Open-source; **OpenTelemetry** (OTel, the vendor-neutral tracing standard) native; best for teams that already speak OTel. Strong on retrieval evaluation.
- **Braintrust.** Eval-first: tight loop between logged production traces, curated eval datasets, and prompt experiments, so a change can be scored against real traffic before it ships. Good fit for teams whose main pain is regression detection rather than raw tracing.
- **Helicone.** Proxy-based (sits between the application and the model API); zero-code-change setup; good for cost dashboards; less rich on agent-trace structure.
- **Roll your own with OpenTelemetry.** A minimal DIY stack wires OTel spans around each LLM, retrieval, and tool call, exports them to any OTel-compatible backend (Jaeger, Grafana Tempo, a cloud trace store), and adds token and cost attributes by hand. The emerging **GenAI semantic conventions** (OpenTelemetry, in development) standardise the attribute names, so a roll-your-own stack stays portable. Useful when LLM observability is one shape among many in an existing OTel deployment; more engineering than buying, and you own the dashboards.

The choice is mostly operational. The lesson is *pick one and instrument*; the differences between them are smaller than the difference between any of them and nothing.

---

## Common pitfalls

- **No tracing at all.** Every debug is a reconstruction.
- **Average instead of p95.** Tails dominate user experience.
- **Cost dashboard without quality dashboard.** Optimisations silently regress.
- **Trace records the response but not the prompt.** Half the artefact is missing.
- **No retention policy.** Compliance violation waiting.
- **Single-judge eval driving the dashboard.** Trust collapses on the first miscalibrated week.
- **No per-feature budget.** Cost surprises everyone at the end of the month.

---

## Further reading

- LangSmith docs, *"Tracing and evaluation"* (2024–26).
- Langfuse docs, *"Open source LLM observability"* (2025–26).
- Arize, *"Phoenix and OpenTelemetry for LLMs"* (2024–26).
- Braintrust docs, *"Evals, logging, and prompt experiments"* (2025–26): the eval-first observability workflow used in §9.
- Helicone docs, *"Proxy-based LLM observability"* (2025–26).
- OpenTelemetry, *"Generative AI semantic conventions"* (in development, 2026): the emerging standard for span attribute names, referenced in §9.
- Anthropic, *"Prompt caching"* (documentation, 2024–25): source of the cache-read (~10 % of input) and cache-write (1.25×/2×) figures in §7; see also [Post 04](../04-tokens-windows-budgets/index.md), §5.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 20 — Evaluation](../20-evaluation/index.md)**: the offline counterpart to the online dashboards.
- **[Post 23 — Security and prompt injection](../23-security/index.md)**: what to monitor for adversarial inputs.
- **[Post 25 — Long context vs RAG](../25-long-context-vs-rag/index.md)**: cost engineering applied to architecture.
