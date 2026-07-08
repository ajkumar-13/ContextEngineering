# Cheatsheet — Context Engineering on one page

---

## The six layers (in order)

| # | Layer | One-liner |
|---|-------|-----------|
| 1 | **System prompt** | Identity · Rules · Format · Knowledge · Tools |
| 2 | **Tools** | Typed schemas; descriptions are part of the prompt |
| 3 | **Memory** | Episodic · Semantic · Procedural — each with its own store |
| 4 | **Retrieved chunks** | RAG / search / KG output, packed bookend-style |
| 5 | **Conversation history** | Recent turns; older turns get summarised |
| 6 | **User instruction** | Last in; pinned; never compressed |

---

## WSCI — the four operations on context

| Op | Direction | Scope | Typical move |
|----|-----------|-------|---------------|
| **W**rite | out of context | persistent | save to memory / scratchpad / index |
| **S**elect | into context | per call | RAG, tool selection, memory recall |
| **C**ompress | within context | per call | windowing, summarise, prune, clear tool results |
| **I**solate | across context | per task | sub-agent with its own context window |

---

## Five context-failure modes

| Mode | Symptom | First fix |
|------|---------|-----------|
| Distraction | Model latches on to a stray phrase | tighten Select; cut noise |
| Confusion | Right info present, wrong choice made | clearer rules; examples |
| Conflict | Contradictory info in context | resolve in retrieval / dedupe |
| Lost-in-middle | Long context, middle ignored | bookend packing |
| Tool-storm | Repeated useless tool calls | catalog trimming; better descriptions |

---

## RAG pipeline (offline | online)

**Offline:** ingest (parse / OCR / table-extract; attach provenance at ingest) → chunk (400–600 tok, sentence-aware, overlap 50–100) → contextual header (1 LLM call/chunk) → embed → index (dense + BM25).

**Online:** query rewrite → hybrid search top-50 → RRF merge → cross-encoder rerank top-5 → bookend pack → generate with citations.

**Eval (Ragas):** faithfulness · answer relevancy · context precision · context recall.

---

## System-prompt five blocks

```
# Identity     — who the model is
# Rules        — one-concept-per-rule, motivated by failure
# Format       — output shape; examples beat instructions
# Knowledge    — facts the model needs once
# Tools        — what's available + when to use each
```

Six rules for rules: *one concept per rule · motivated by real failure · positive over negative · specific over vague · examples beat instructions · reviewed like code.*

---

## Tool design — iron triangle

Catalog size · description quality · runtime selection cost — **pick two**.

Each tool description has six elements:

1. What it does · 2. When to use it · 3. When NOT to use it · 4. Parameter schema with descriptions · 5. Structured return shape · 6. Failure modes.

---

## Memory taxonomy

| Kind | What | Schema | Retrieval | Decay |
|------|------|--------|-----------|-------|
| Episodic | Past events | `{when, what, who, summary}` | similarity | recency |
| Semantic | Facts / prefs | `{kind, content, conf, source}` | exact + similarity | confirm-or-decay |
| Procedural | How-to | `skill.md`, hook scripts | name lookup | versioned |

---

## Compression triggers

- Soft @ **80 %** of budget — windowing, tool-result clearing, P3 drop.
- Hard @ **95 %** of budget — summarise older turns to ~200-tok brief.
- Measure with **IRR** (information retention ratio) on a replay set.

---

## Cost & caching

- **Input vs output asymmetry** — output tokens cost ~5x input; keep generations tight.
- **Cache read ≈ 10 %** of the base input price; **cache write = 1.25x** (5-min TTL) or **2x** (1-hour TTL) input.
- **TTL tiers:** 5-minute (default) and 1-hour.
- **Freeze the prefix** — stable system prompt and tools first, volatile / user content last, so the cached prefix stays intact.
- **Watch the cache-hit rate** — a dip means the prefix is churning; find what moved.

**Reasoning models:** thinking tokens count against the budget — keep reasoning traces out of downstream context and out of the cached prefix.

---

## Eval pyramid

```
        online (production traffic + approval rate)
      end-to-end (50–500 fixtures, regression-gated)
   component (retriever, reranker, judge — each in isolation)
unit (chunker, prompt assembly, send-gate — pure functions)
```

LLM-judge biases to watch: **position · length · self-preference · rubric drift.**

**Guardrails:** validate output against a schema · retry-on-invalid · moderate / redact before returning.

---

## Observability — four headline numbers

1. Cost per session
2. p95 latency
3. Quality (approval rate or eval score)
4. Error rate, by kind

---

## Security — four architectural defences

1. The **model is not the permission system** — enforce in code.
2. **Constrain blast radius** — least-privileged credentials, sandboxed tools.
3. **Filter at trust boundaries** — validate args, structure tool returns.
4. **Never silently merge attacker text** into trusted context.

---

## Long context vs RAG — the four-question test

1. Does the answer require *all* of the document?
2. Is the document available at query time?
3. Is the cost of full-context inference acceptable?
4. Does the model do better with the whole or the relevant part?

If yes-yes-yes-whole → long context. If no anywhere → RAG. Most production systems route per-query.

---

## Workflow checklist

- [ ] Project has an `AGENTS.md` (five blocks).
- [ ] Skills directory for repeated tasks.
- [ ] Hooks for dangerous commands and post-edit checks.
- [ ] Auto-compaction enabled; manual `/compact` known to the team.
- [ ] Sub-agent budgets capped.
- [ ] Eval suite gates the deploy.
- [ ] Trace store on every call.
- [ ] Send-gate (or equivalent) on every outbound action.
