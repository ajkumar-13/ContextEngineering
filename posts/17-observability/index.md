# 17 · Observability, tracing, and cost

> **TL;DR.** Observability is what turns an LLM system from a black box into a debuggable one. The minimum stack is **traces** (every call, every prompt, every token, every cost), **spans** (the structure inside an agent run), and **dashboards** (cost, latency, quality, error rate). The tools that work in 2025 are LangSmith, Langfuse, Phoenix, and Helicone, in roughly that order of maturity. This post is a practitioner's guide: what to instrument, how to read the traces, and the four numbers every dashboard needs.
>
> **Reading time:** ~11 minutes.
>
> **After reading this you will be able to:**
> - Wire trace and span instrumentation into an existing LLM application.
> - Read a trace and identify the four most common bug shapes.
> - Set up a dashboard that surfaces cost, quality, latency, and error trends.

---

## 1. Why observability matters for LLM systems

Conventional observability (logs, metrics, traces in the OpenTelemetry sense) was built for systems where the cost of a single request is small and predictable, and the quality of a response is binary. LLM systems break both assumptions: a single request can cost ten cents or ten dollars depending on what got into the prompt, and "quality" is a soft, multi-dimensional judgement.

This means LLM observability has to record *more* per call than a normal observability stack, including artefacts that classical systems never bothered with: the full prompt, the full response, the model version, the tool calls, the reasoning trace, the token counts, and the dollar cost. Without these, debugging is anecdote and capacity planning is guessing.

The good news: the field has converged on a small standard set of structured records — the **trace** — that captures all of this and that all the major tools speak.

---

## 2. The trace and the span

A **trace** is the record of one user-facing interaction (a single chat turn, an agent run, a workflow execution). Inside a trace are **spans** — nested records of every operation: the system-prompt assembly, each retrieval call, each LLM call, each tool execution, each sub-agent invocation.

A typical trace for one agent turn:

```
trace: customer-support / session-A1B2 / turn-7         5.2 s   $0.043
├─ span: assemble_context                              0.05 s
│   ├─ span: load_memory                               0.30 s   $0.001  (256 tok in / 80 tok out)
│   └─ span: select_tools                              0.20 s   $0.000  (cached)
├─ span: retrieve_rag                                  0.40 s
│   ├─ span: query_rewrite                             0.20 s   $0.001
│   ├─ span: hybrid_search                             0.10 s
│   └─ span: rerank                                    0.10 s   $0.002
├─ span: llm_call (claude-sonnet-4)                    3.80 s   $0.038  (12 400 tok in / 380 tok out)
└─ span: tool_call (issue_refund)                      0.20 s
    └─ span: db_query                                  0.10 s
```

Every span carries: name, parent, start/end timestamps, a typed payload (the prompt for an LLM span; the query for a search span; the args for a tool span), and the metrics specific to its kind (tokens, cost, latency, error). The whole tree is queryable, drillable, and shareable as a single URL — which is exactly the affordance that makes "show me the trace" a productive bug-report channel.

---

## 3. What to instrument

A reliable starter set:

- **One trace per user-facing interaction.** Tagged with `user_id`, `session_id`, `release_version`.
- **One span per LLM call.** Captures `model`, `prompt`, `response`, `input_tokens`, `output_tokens`, `cost`, `latency_ms`, `cached_tokens`. Do not redact the prompt unless you have a hard regulatory reason; the prompt is the artefact you most need.
- **One span per retrieval.** Captures the query, the retrieved chunks (with their ids and scores), the reranker scores, the final pack.
- **One span per tool call.** Captures the tool name, the args, the result, the exit code, the latency.
- **One span per sub-agent invocation.** With its own nested trace inside.
- **One span per memory read/write.** With the kind, the cell ids, the source.

The pattern: every operation that *might* be the cause of a bug is its own span. When the trace is right, the next-week debugging session is a 5-minute lookup, not a 5-hour reconstruction.

---

## 4. The four numbers every dashboard needs

Out of the dozens of metrics the trace store can compute, four are non-negotiable on the headline dashboard.

**1. Cost per session (median, p95).** The leading indicator for context bloat, sub-agent loops, and retrieval-over-fetch. A 30 % week-over-week jump in p95 cost almost always means a recent change is putting more into context than intended.

**2. Latency p95.** The user-experienced metric. Average is a lie; tail is what matters. A jump in p95 with stable median often means a small fraction of sessions hit a slow path that needs a fix (uncached prefix, slow tool, sub-agent retry storm).

**3. Quality (offline LLM-judge or thumbs).** The end-to-end eval score from Post 16, computed nightly on a sample of real traffic, plus the explicit-feedback rate. Without quality on the dashboard, cost and latency optimisations can silently degrade the product.

**4. Error rate, by kind.** Tool errors, schema-validation errors, refusal rate, timeout rate, retry rate. Each kind tells a different story; combined into one number they are useless.

Four dashboards (or one dashboard with four panels). Every team change reviews them before declaring success.

---

## 5. Reading a trace — four common bug shapes

A short field guide to what bugs look like in a trace.

**Shape 1 — context bloat.** The LLM span shows 80 000 input tokens. Drill into the prompt. The conversation history span shows 60 000 tokens because tool results were never cleared (Post 10, §4) and a 40-turn session accumulated. The fix is in the compression policy, not the model.

**Shape 2 — retrieval miss.** The retrieval span shows the right chunks were returned with high scores, but the LLM span's response cites a wrong fact. Drill into the prompt. The chunks were packed in the middle of the context, where attention is weakest (Post 03, §3). The fix is bookend layout (Post 08, §5).

**Shape 3 — tool storm.** The trace shows 15 tool calls in one turn, all to the same `search_*` tool with slightly different queries. Drill into the prompt. The tool descriptions are similar; the model is confused (Post 05, §4) and is brute-forcing. The fix is tool selection or tool-name disambiguation (Post 13, §3).

**Shape 4 — silent regression.** The dashboard shows cost dropped 20 % a week ago. Champagne. Then quality dropped 10 % the same week. Drill into traces from before and after. A "cleanup" PR removed an instruction the model had been silently relying on. The fix is reverting the prompt and adding a fixture so it cannot happen again.

The pattern: most LLM bugs are *visible in the trace* once the right things are instrumented. The cost of *not* instrumenting is paying engineering time to reconstruct what was already happening.

---

## 6. Cost engineering

Observability is also where cost engineering lives. Three knobs the trace store will surface immediately.

**Prompt caching utilisation.** Anthropic, OpenAI, and Google all charge ~10 % of normal input price for cached prefix tokens. The trace records `cached_tokens` per call. A healthy assistant with stable system prompt and stable tool catalog should see >80 % of input tokens cached on conversational turns. Below that, look at why the prefix is invalidating — usually it is moving system content (date strings, dynamic counters) at the top.

**Per-call model selection.** The trace shows which model handled each call. Most production stacks use a small model for routing, query rewriting, and summarisation; a larger model for the main reasoning step. If a small-model span is using the large model, that is a cost bug.

**Sub-agent overuse.** A trace with three nested sub-agent spans for a task that fits in one window is a cost bug. Set a guard: a metric that flags sessions whose sub-agent count exceeds a threshold; review the traces; either justify or refactor.

A pattern that pays back: **a per-feature cost budget** wired to the trace store. The "support agent" feature has a budget of $0.10 per session; sessions above that are flagged for review; week-over-week trends are reported. This turns cost from a quarterly accounting surprise into a daily engineering signal.

---

## 7. Privacy and PII

Tracing every prompt and response means storing user data, often including personal information. The disciplines that have to be in place:

- **Retention policy.** Traces older than *N* days are deleted. *N* is set by the regulatory environment (GDPR, HIPAA), not by what is convenient.
- **PII redaction.** Optional layer that masks emails, phone numbers, payment data on the way into the store. Useful for compliance; also degrades debugging value, so apply selectively.
- **Access control.** Trace stores carry a lot of customer data. Production traces should not be readable by anyone who would not be allowed to read the underlying transcripts.
- **User opt-out.** If your terms of service require it, allow users to opt out of trace recording (and confirm in the trace itself).

These are unsexy and unavoidable. Most production teams set them up once and then never think about them; teams that ship without them learn the hard way.

---

## 8. The tools

A short, opinionated assessment as of late 2025.

- **LangSmith.** The most mature, highest-friction-to-self-host. First-party LangChain integration but works with any framework. Strong eval integration. Pricing is per trace.
- **Langfuse.** Open-source first; self-hostable; strong dashboards; per-trace pricing on the cloud version. The right default for teams that want control.
- **Phoenix (Arize).** Open-source; OpenTelemetry-native; best for teams that already speak OTEL. Strong on retrieval evaluation.
- **Helicone.** Proxy-based (sits between your app and the model API); zero-code-change setup; good for cost dashboards; less rich on agent-trace structure.
- **Roll your own with OpenTelemetry.** Possible; useful when LLM observability is one shape among many; more engineering than buying.

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

- LangSmith docs, *"Tracing and evaluation"* (2024–25).
- Langfuse docs, *"Open source LLM observability"* (2025).
- Arize, *"Phoenix and OpenTelemetry for LLMs"* (2024).
- Helicone docs, *"Proxy-based LLM observability"* (2025).
- OpenTelemetry, *"Generative AI semantic conventions"* (in development, 2025) — the emerging standard.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 16 — Evaluation](../16-evaluation/index.md)** — the offline counterpart to the online dashboards.
- **[Post 18 — Security and prompt injection](../18-security/index.md)** — what to monitor for adversarial inputs.
- **[Post 19 — Long context vs RAG](../19-long-context-vs-rag/index.md)** — cost engineering applied to architecture.
