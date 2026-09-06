# 07 · Write, select, compress, isolate

> **TL;DR.** Once you can name the six layers of context ([Post 02](../02-six-layers-of-context/index.md)) and the five ways context fails ([Post 06](../06-context-failure-modes/index.md)), the next thing you need is a vocabulary for what you can *do about it*. The **WSCI framework**: Write, Select, Compress, Isolate — is the smallest set of primitive operations that covers every context-engineering technique in this series. The remaining posts of Part II spend one chapter on each. This post is the map.
>
> **After reading this you will be able to:**
> - Name the four operations and the question each one answers.
> - Pick the right operation for any of the five failure modes.
> - Read the rest of the series knowing where each technique fits.

![The WSCI framework](diagrams/01-wsci-quadrants.svg)

*The four WSCI operations arranged by direction (information in or out) and scope (one context window or several).*

---

## 1. Why a framework

The honest reason: without one, every conversation about an LLM bug becomes a list of techniques with no shared structure. RAG (retrieval-augmented generation), summarisation, sub-agents, prompt caching, semantic memory: these are all useful, but they are answers, not questions. WSCI, the series' shorthand for **W**rite / **S**elect / **C**ompress / **I**solate, gives you the questions.

The framework is two axes, four quadrants, four primitive verbs.

- **Direction**: does the operation move information *into* the live context or *out of* it?
- **Scope**: does the operation act on a *single* context window or *span several* windows?

| | **In** (add to context) | **Out** (remove from context) |
|---|---|---|
| **Single window** | **Select**: pull the right facts in for *this* turn | **Compress**: shrink what is already inside |
| **Spans several windows** | **Isolate**: split the work into separate contexts, each running its own Select | **Write**: move information out to a store so it can be retrieved later |

Read the quadrants as a 2×2 on those two axes: Select and Compress work within one window (one adds, one removes); Isolate and Write reach beyond a single window (one splits the work, one parks information elsewhere). Each verb owns exactly one cell.

The framing is Lance Martin's, "Context Engineering for Agents" (LangChain blog, 2025); Anthropic and IBM later described the same four operations in their own vocabulary (see Further reading). It is small enough to memorise and complete enough to classify almost any technique.

---

## 2. Write: move information out for later

**The question it answers:** what should be kept around even though it cannot be afforded on every call to this prompt?

Write is the operation that puts information *somewhere other than the live context window*. The destination is some kind of persistent store: a file, a database row, a vector index, a memory store, an `AGENTS.md`, a scratchpad, a ticket. The defining property is that the information is no longer being paid for on every API call but it is still recoverable later.

Concretely, "write" covers:

- **Persistent memory**: episodic facts, semantic preferences, procedural rules ([Post 16](../16-memory-systems/index.md)).
- **Scratchpads**: a sub-agent's intermediate work, dropped to disk between iterations.
- **Repository documentation**: `AGENTS.md`, `CLAUDE.md`, `skill.md` files that load conditionally.
- **Audit logs**: full conversation transcripts kept for debugging and evals, *not* in the prompt.
- **Embeddings**: the offline write side of RAG: documents are chunked, embedded, and indexed *before* they are needed.

Write is the cheapest of the four operations to perform and the one that pays the largest long-term dividends. The cost is a small extra hop (one API call to summarise, one database insert) at the moment of writing; the benefit is one fewer thing competing for context space on every subsequent call.

The most common Write mistake is to write everything indiscriminately. A memory store with no provenance, no decay, and no schema becomes a memory-poisoning factory, the adversarial failure covered in [Post 23](../23-security/index.md). Write is also the only operation with a meaningful security surface: anything written becomes data the agent will trust on the next read. Post 23 is dedicated to this side of the trade-off.

[Post 08](../08-write-strategies/index.md) is the deep dive.

---

## 3. Select: pull the right information in for *this* turn

**The question it answers:** of everything that could be included, what does the model actually need *right now*?

Select is the operation that decides what enters the per-turn payload. The classic instance is **retrieval-augmented generation (RAG)**: a corpus of millions of tokens lives offline, a query at inference time fetches the handful of chunks most relevant to the current turn, and only those chunks land in the prompt. But RAG is one species of Select; there are others.

- **Tool selection**: the agent has a hundred tools but only the schemas of the few relevant to this turn are exposed. The dynamic version of this is the central insight of the Model Context Protocol (MCP) ecosystem ([Post 15](../15-tools-and-mcp/index.md)).
- **Memory retrieval**: pulling a few episodic facts from a vector store of years of session history.
- **Few-shot example selection**: choosing the two or three most similar prior examples to seed in-context learning, instead of a static set.
- **Conversation-history selection**: including the last *k* turns plus a topic-relevant turn from earlier in the session.

Two design tensions sit at the heart of every Select: **recall vs. precision** (does the pipeline get the right chunk? does it get *only* the right chunk?) and **breadth vs. depth** (a wide range of plausible matches, or a small number of high-confidence ones?). The post on RAG ([Post 11](../11-rag-in-depth/index.md)) and the post on advanced retrieval ([Post 17](../17-advanced-retrieval/index.md)) take both apart in detail.

Select is the operation that most rewards engineering effort. Going from "embed and top-*k*" (take the *k* nearest chunks by embedding similarity) to "hybrid search + rerank" can cut retrieval failures sharply on the same data with no model change: Anthropic report ~35% fewer failures from contextual embeddings alone, ~49% when combined with contextual BM25 (a keyword-ranking algorithm), and ~67% once a reranker is added (Anthropic, "Introducing Contextual Retrieval", 2024). [Post 09](../09-select-strategies/index.md) is the deep dive.

---

## 4. Compress: shrink what is already inside

**The question it answers:** this information cannot be dropped, but it cannot be afforded verbatim either, so what is the smallest representation that still works?

Compress acts on tokens that are *already* in the context. It does not change *what* is in the prompt; it changes *how much* of it. Five techniques cover essentially every production system:

1. **Windowing**: keep the last *N* turns; drop the rest. Cheap, lossy in a known way.
2. **Summarisation**: replace a span of context with an LLM-generated summary. Costs an extra call; preserves semantics.
3. **Tool-result clearing**: drop the body of a tool response after extracting the bits the agent needed. Safe (deterministic; re-callable) and underused.
4. **Priority pruning**: assign each layer a priority class (P0 system prompt, P1 recent, P2 older history, P3 stale tool results) and trim from the lowest first. Rule-based and cheap.
5. **Semantic chunking**: group context by topic, summarise each topic independently. Highest quality, highest cost.

A useful metric to define for yourself is the **information retention ratio** (IRR): the fraction of key facts that survive a compression pass. The goal is a high IRR at a large token reduction; the exact target is a policy choice, and [Post 12](../12-compress-strategies/index.md) puts numbers on it per technique. More aggressive compression is always possible but tends to lose nuance ("what was decided" without "why").

Almost every long-running agent reaches a point where compression is no longer optional. Auto-compaction in Claude Code, which fires at a high-water mark near the top of the window (Anthropic, Claude Code documentation, 2025), and similar triggers in other agent frameworks are attempts to make this automatic, but the policy still has to be designed, because the framework cannot know which part of the context is safe to summarise and which is load-bearing.

---

## 5. Isolate: split the work into separate contexts

**The question it answers:** can this task be done in pieces, each with its own clean context, instead of one monster prompt?

Isolate is the operation that gives up on a single context window and uses several. The two most common instances:

- **Sub-agents.** A research task is decomposed into "find sources", "read each source", "synthesise". Each sub-task runs in its own context window, with its own scoped tools and its own scoped memory. The orchestrator sees only the *result* of each sub-task, not the full transcript ([Post 13](../13-isolate-strategies/index.md)).
- **Sandboxing.** Tool execution happens in a process whose stdout is not all funnelled back into the model's context. Only the structured result returns; the noisy `npm install` log stays out.

Isolate is the most powerful operation on this list and the most often misused. Done right, an isolated sub-agent cannot suffer distraction or conflict from the parent's context, because that context is not in its window. Done wrong, sub-agents multiply the token bill by *N* while introducing coordination bugs the single-agent version did not have.

The single rule worth memorising: **isolate when the sub-task has a clean input contract and a clean output contract.** "Find me the three most relevant papers and return their titles and DOIs" is a perfect sub-agent. "Help me think through the problem" is a terrible one: there is no clean output that the orchestrator can integrate.

---

## 6. Mapping the six layers onto WSCI

![Each context layer paired with the WSCI operation that primarily manages it](diagrams/02-layers-to-wsci.svg)

*Operations own layers. No layer needs all four, and the pairings chain: memory is Written before it is Selected.*

The four operations describe *what* to do with context; the six layers of [Post 02](../02-six-layers-of-context/index.md) describe *where* the context lives. They compose. Each layer is managed primarily by one operation, with a secondary operation for the cases the first cannot reach.

| Layer (Post 02) | Primary operation | How it shows up |
|---|---|---|
| 01 System prompt | **Write** | Authored once into `CLAUDE.md` / `AGENTS.md`, loaded every call; Compress it only when it has grown bloated. |
| 02 Tools / MCP | **Select** | Expose only the schemas relevant to this turn; Isolate scopes a tool set to a sub-agent. |
| 03 Memory & state | **Write**, then **Select** | Facts are written to a store between sessions, then a few are selected back in per turn. |
| 04 RAG / retrieved chunks | **Select** | The offline Write side (chunk, embed, index) feeds the per-turn Select side (retrieve, rerank). |
| 05 Conversation history | **Compress** | The layer that grows without bound; windowing and summarisation keep it in budget. |
| 06 User instruction | (none) | The trigger, not something to manage; it is the input every other operation serves. |

Two readings fall out of this table. First, no layer needs all four operations, which is why the framework stays small. Second, the operations chain across layers: memory is Written before it is Selected, and RAG's index is Written offline before it is Selected online. Keeping the pairing straight (which operation owns which layer) is the fastest way to locate the right lever when a specific layer misbehaves.

---

## 7. WSCI vs. the five failure modes

![The five failure modes of Post 06, each with a first-line WSCI operation and a fallback](diagrams/03-wsci-vs-failures.svg)

*Every first-fix in the failure catalogue is one of these four operations, with a second-line operation behind it.*

The reason WSCI is worth memorising is that the four operations map cleanly onto the five failure modes catalogued in [Post 06](../06-context-failure-modes/index.md). Those five are **distraction, confusion, conflict, lost-in-the-middle, and tool-storm**; each has a first-line operation and a fallback.

| Failure (Post 06 §) | First-line operation | Second line |
|---|---|---|
| Distraction (§2) | **Select** (lower *k*, rerank so the noise never enters) | Compress (shrink a distracting history) |
| Confusion (§3) | **Select** (fewer, more distinct tools) + **Write** (one canonical rule) | Isolate (one sub-agent per tool family) |
| Conflict (§4) | **Compress** (de-duplicate) + **Write** (a canonical rule with provenance) | Select (resolve the winner before the model sees it) |
| Lost-in-the-middle (§5) | **Compress** (shrink so the answer sits near an end) | Isolate (split so no single window runs that long) |
| Tool-storm (§6) | **Select** (trim the tool catalogue to this turn) | Isolate (a deterministic router pre-selects tools) |

Read it the other way and a pattern emerges: in many over-stuffed production prompts, the first thing to reach for is Compress, because most such prompts are too long, in part because the cost of *not* compressing was invisible during development. Compress also makes Select cheaper (smaller prompts leave room for more retrieval) and makes Isolate possible (clean summaries are clean inputs for sub-agents). Hence the order in which Part II covers them: Write first (the foundation), Select second (the input pipeline), Compress third (the day-to-day discipline), Isolate fourth (the structural lever).

---

## 8. A worked walk-through

A concrete example to anchor the four operations. Imagine a customer-support agent that has been running for three months.

- **At setup**, you **Write** the company's product knowledge into a vector index, write a `CLAUDE.md` with tone and policy rules, and write per-customer profiles into a key-value store.
- **On every turn**, you **Select**: the top-5 RAG chunks for this question, the customer's profile, the schemas of the four tools relevant to this intent, the last three turns of the session.
- **Every twenty turns** the conversation history threatens to break the budget, so you **Compress**: a sub-agent summarises turns 1–17 into a roughly 200-token brief; turns 18–20 stay verbatim.
- **When the customer says "build me a refund report",** the orchestrator **Isolates**: a sub-agent with database tools and no other context generates the report, returns a 1 KB result, and disappears. The main agent's context grows by one short message, not by a full report-generation transcript.

Every modern agent does some version of these four moves; the engineering is in the policies that decide *when*. The next four posts cover those policies.

---

## Common pitfalls

- **Reaching for Select when the bug is Compress.** Adding more retrieval to a system that is already over-stuffed makes things worse.
- **Treating Isolate as the default.** Sub-agents are powerful but not free. A single-agent design that fits comfortably in a 32 k prompt usually beats a three-agent design that fits in 12 k each.
- **Writing without a schema.** A memory store with no fields, timestamps, or provenance is a poisoning incident waiting to happen.
- **Compressing and then never measuring IRR.** A "summary" that drops the one fact the next turn needed is not a summary; it is a regression.
- **Conflating Select and Compress.** They feel similar (both shrink the prompt) but they are different operations: Select chooses what to *include*; Compress shrinks what is *already there*.

---

## Further reading

- Martin, L., *"Context Engineering for Agents"* (LangChain blog, 2025): the write/select/compress/isolate operations this post abbreviates as WSCI.
- Anthropic Engineering, *"Effective context engineering for AI agents"* (2025): the same four operations, described in a different vocabulary.
- IBM Think, *"What is context engineering?"* (2025): an independent re-derivation, useful for triangulation.
- Anthropic, *"Introducing Contextual Retrieval"* (2024): source of the ~35% / ~49% / ~67% retrieval-failure reductions cited in §3.
- Anthropic, *"Claude Code"* documentation (2025): the auto-compaction behaviour cited in §4.
- Karpathy, A., *"On the term 'context engineering'"* (2025): the thread that named the field.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 08 — Write strategies](../08-write-strategies/index.md)**: memory stores, scratchpads, AGENTS.md.
- **[Post 09 — Select strategies](../09-select-strategies/index.md)**: retrieval, tool selection, few-shot selection.
- **[Post 12 — Compress strategies](../12-compress-strategies/index.md)**: the five techniques, with numbers.
- **[Post 13 — Isolate strategies](../13-isolate-strategies/index.md)**: sub-agents, sandboxing, when to split.
- Back to **[Post 06 — Five context failure modes](../06-context-failure-modes/index.md)**: the five modes the §7 table maps onto.
