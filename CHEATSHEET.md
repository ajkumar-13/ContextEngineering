# Context engineering cheatsheet

One page: the six layers, the four operations, the five failure modes, and the defaults the posts recommend. Print it, pin it. Terms are defined in the [glossary](GLOSSARY.md) and the fixed vocabulary in the [notation guide](notation_guide.md). Every number on this page is either cited (the source is named beside it, and the full entry is in [REFERENCES.md](REFERENCES.md)) or is a default the posts recommend and label as such.

---

## The six layers, in the order they are sent

| # | Layer | What it carries | Lifetime |
|---|---|---|---|
| 01 | **System prompt** | Five blocks: identity, rules, format, knowledge, tool-use guidance (when to reach for which tool) | stable prefix |
| 02 | **Tools and MCP descriptions** | The schema of every callable tool; its description is prompt text | stable prefix |
| 03 | **Memory and state** | Recalled episodic, semantic, and procedural memory; task state | per-turn injection |
| 04 | **Retrieved chunks** | Evidence selected for this turn, packed bookend-style with citations | per-turn injection |
| 05 | **Conversation history** | Earlier turns of this session; older turns get summarised | growing tail |
| 06 | **User instruction** | The current request: last in, never compressed | trigger |

The system prompt's tools block holds only the guidance on when to use each tool; the schemas themselves are layer 02 ([post 14](posts/14-system-prompt-as-software/index.md), [post 15](posts/15-tools-and-mcp/index.md)). Layers 01 and 02 come first so that they cache.

---

## WSCI: the four operations on context

| Operation | Direction | Scope | Typical move |
|---|---|---|---|
| **Write** | out of the window | spans several windows | park information in memory, a scratchpad, `AGENTS.md`, or an index |
| **Select** | into the window | one window | RAG, tool selection, memory recall, few-shot picking |
| **Compress** | out of the window | one window | windowing, summarisation, tool-result clearing, priority pruning |
| **Isolate** | into the window | spans several windows | a sub-agent with its own window, each running its own select |

---

## The five failure modes

| Mode | Symptom | Fixes (first fix first) | Operation |
|---|---|---|---|
| Distraction | The model latches on to irrelevant material | Lower top-k, add a reranker, scope the index | Select |
| Confusion | The right information is present, the wrong choice is made | Explicit, motivated, exemplified rules; push rules into code | Select (of rules) |
| Conflict | Contradictory information in the window | Provenance and recency stamp plus a precedence rule; dedupe the candidates | Select, compress |
| Lost-in-the-middle | Long context, the middle is ignored | Bookend packing; summarise old history; split into sub-agents | Compress, isolate |
| Tool-storm | Repeated, redundant, or useless tool calls | Trim the catalogue, add a stop budget, cap result size | Select, isolate |

A bug report that fits none of the five is a model problem, not a context problem ([post 06](posts/06-context-failure-modes/index.md)). Poisoning is a security term ([post 23](posts/23-security/index.md)).

---

## The select pipeline and RAG

**Offline:** source, parse (born-digital extraction, layout-aware parsing, or OCR), clean, enrich (provenance at ingest), chunk, index (dense and BM25). Illustrative starting chunk for prose: 400 to 600 tokens, sentence-aware, 10 to 20 percent overlap (not a measurement). Contextual retrieval adds a short generated header to each chunk before indexing (Anthropic, 2024).

**Online:** query (rewrite, HyDE, decompose), candidates (dense top-30 plus BM25 top-30, fused by reciprocal rank fusion into a top-50 candidate set), rerank (a cross-encoder keeps the top-5), pack (bookends, citations, dedupe), generate. These are the series' recommended starting defaults, not measurements ([post 09](posts/09-select-strategies/index.md)).

**Measure:** recall@N on the candidate set, precision@k on the packed set. **Ragas:** faithfulness, answer relevancy, context precision, context recall.

---

## The system prompt in five blocks

```
# Identity     who the model is
# Rules        one concept per rule, each motivated by a real failure
# Format       output shape; examples beat instructions
# Knowledge    small, stable facts needed on almost every call
# Tool-use     when to reach for which tool (the schemas are layer 02)
```

Six rules for rules: one concept per rule; motivated by a real failure; positive over negative; specific over vague; examples beat instructions; reviewed like code.

---

## Tool design

**Iron triangle:** catalogue size, per-tool description quality, runtime selection. A design gets any two of a large catalogue, rich descriptions and no selection step; keeping both of the first two means paying for runtime selection.

**One tool description has six parts:** a `verb_object` name; a one-line summary; when to use it; when not to use it; parameters with types and descriptions; one worked example.

---

## Memory

| Kind | Holds | Key fields | Retrieval | Ageing |
|---|---|---|---|---|
| Episodic | past events | post 08's nine fields (`content` is the event) | reference recall when the turn refers to the past | confidence decays on read without confirmation |
| Semantic | facts and preferences | the same nine fields | top-k background facts on each turn | decays on read; ask below the cutoff; never overwrite in place |
| Procedural | rules learned for one user, account or project | the nine fields plus `trigger` (`subject` is the scope, `content` the rule) | trigger matching, not similarity | no decay; removed by a person; written after confirmation |

---

## Compression triggers

- Soft trigger at **80 percent** of the budget: tool-result clearing, drop the lowest priority band; stop if the prompt falls under 60 percent.
- Hard trigger at **95 percent**: summarise or semantically chunk the older part of the conversation; keep the original turns in a separate log.
- Check every summary policy with the information retention ratio on a replay set (a teaching construct, not a standard metric).

The thresholds are the series' illustrative defaults, to be tuned per workload; Claude Code's documentation states no default percentage ([post 12](posts/12-compress-strategies/index.md)).

---

## Cost and caching

Figures from Anthropic's "Pricing" and "Prompt caching" pages: rates as of early 2026, cache multipliers as consulted on 12 October 2026; they go stale ([post 05](posts/05-economics-of-context/index.md)).

- **Input against output:** output tokens cost about five times input tokens at every tier. Keep generations tight.
- **Cache read:** 0.1 times the base input price for most models, including the series' three running models; some newer models list 0.05 or 0.025 times (Anthropic, "Pricing", consulted 12 October 2026). **Cache write:** 1.25 times the base input price for the five-minute lifetime, 2 times for the one-hour lifetime; one read repays the first, two the second.
- **Freeze the prefix:** layers 01 and 02 first and byte-identical; every volatile byte last.
- **Watch the cache-hit rate:** a drop means the prefix is churning; find what moved.

**Reasoning models:** thinking tokens are billed as output and count against the budget; pass thinking blocks back unchanged, but keep the trace text out of the layers the application writes, the cached prefix and memory; changing the effort level restarts the cache ([post 18](posts/18-reasoning-model-context/index.md)).

---

## Evaluation pyramid

```
            4. online       production traffic and its signals
         3. end-to-end      the full pipeline on gold tasks, regression-gated
      2. component          retriever, reranker, prompt block, each alone
   1. unit                  deterministic functions: chunker, prompt assembly, send gate
```

LLM-as-judge biases to watch: position, verbosity (length), self-preference, rubric drift.

**Output guardrails:** validate against a schema, retry on failure with a cap, moderate or redact, then return.

---

## Observability: the four headline numbers

1. Cost per session (median and p95).
2. Latency, p95.
3. Quality: the end-to-end eval score or explicit feedback.
4. Error rate, by kind.

Cache-hit rate = cache-read input tokens over total input; on Anthropic the total is `input_tokens` + `cache_read_input_tokens` + `cache_creation_input_tokens`.

---

## Security: the four architectural defences

1. The model is not the permission system: enforce permissions in code.
2. Constrain tool blast radius: least-privileged credentials, sandboxed tools.
3. Filter at trust boundaries: tag external text as data, validate model output before it is used.
4. Never silently merge attacker text into trusted context.

**Privacy:** detect and redact at the trust boundary; placeholders into the trace store, values only when the task needs them; a lifecycle rule on every store; erasure fans out to memory, documents, chunks, traces and the provider; filter by tenant before ranking ([post 24](posts/24-privacy-and-governance/index.md)).

---

## Long context or RAG: the four-question test

1. Does the corpus fit in one window, with budget left for the conversation?
2. Is the corpus stable enough to cache?
3. Does each query need most of the corpus, or a small slice?
4. Can the model actually use the long context for this task?

Apply them in order. A no to question 1 settles it for retrieval; the other three weigh caching, the shape of the queries, and what the long-context benchmarks show. A workload with both whole-corpus and local queries routes per query ([post 25](posts/25-long-context-vs-rag/index.md)).

---

## Workflow checklist

- [ ] The project has an `AGENTS.md` in the five-block form.
- [ ] Skills for repeated tasks.
- [ ] Hooks for dangerous commands and post-edit checks.
- [ ] Auto-compaction on; the team knows `/compact` from `/clear`.
- [ ] Sub-agent budgets capped.
- [ ] An eval suite gates the deploy.
- [ ] A trace on every call.
- [ ] A send gate, or its equivalent, on every outbound action.
