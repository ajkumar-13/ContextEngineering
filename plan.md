# Context Engineering

Standard: 2.2.0 · Plan version: 1.0.0 · Status: draft · Date: 2026-10-03

Context Engineering is a thirty-post, framework-agnostic series on engineering the whole input a large language model sees on every call: the system prompt, the tool and MCP descriptions, memory, retrieved context, conversation history, and the user instruction. It names the six layers, explains how the model reads them and what they cost, gives the four operations that act on them (write, select, compress, isolate), goes deep on each layer, covers the production disciplines (evaluation, structured output, observability, security, privacy, the long-context-versus-RAG decision), and ends with the agentic workflow and three runnable builds. A reader who finishes can diagnose a misbehaving LLM application by layer and failure mode, size and price a context budget, design a retrieval, memory, and tool stack for a given workload, and ship a RAG chatbot, an MCP server, and an email-reply agent with an eval gate in front of them.

# 1. Purpose and authority

This plan owns the curriculum of the series: who it is for, what each post teaches, in what order, with what dependencies, and what is deliberately left to sibling series. It is the prose form of the lock; `series.yaml` is the machine form (ids, parts, order, prerequisites), and the two must agree.

Everything else is owned by the family standard at `series-standard/STANDARD.md`, pinned by `series.yaml: standard`: directory layout, identifiers, the sidecar schema, the body template, question banks, diagrams, tooling, and the publishing workflow. This plan points at those rules and never restates them. `validate.py` runs its plan stage against this file and `series.yaml` together, so the ids, titles, parts, levels, and dependencies written here cannot drift from the manifest or the sidecars without an error.

The thirty posts under `posts/` are canonical for everything they say; where this plan and a shipped post differ, Section 9 records the divergence and the direction of the fix.

# 2. Audience, entry, and exit levels

## Reader profiles

- The builder: an engineer shipping an LLM-backed feature who needs patterns that hold up in production. Every post addresses this reader first.
- The product or strategy reader: someone who needs accurate mental models of layers, costs, and failure modes without writing the code. Parts I and IV are written to be read without running anything.
- The self-learner: someone who wants a structured path from "what is a context window" to a deployable agent. The linear order is for this reader.

## Entry requirement

No post of another family series is required. The series assumes working Python, the ability to call one provider SDK (Anthropic, OpenAI, or Gemini), and the vocabulary of a first RAG tutorial (embedding, vector store, chunk). It does not assume transformer internals; ctx-003 gives the one-post account of tokens, attention, positions, and the KV-cache that the rest of the series needs, and leaves the derivations to the transformer series. The three builds in Part V assume a shell, `git`, and the ability to set an API key in `.env`.

## Exit levels

- After ctx-006 (end of Part I, beginner to intermediate): the reader can name the six layers in a raw API request, estimate the tokens, latency, and dollars of a prompt without running it, lay out a prefix so it caches, and map a production bug report to one of the five failure modes.
- After ctx-013 (end of Part II, intermediate): the reader can classify any technique as write, select, compress, or isolate; choose a write destination and its metadata; tune the four levers of a retrieval pipeline; stand up an ingestion pipeline with provenance; pick a compression policy and measure its information retention; and decide when a task should be split across sub-agents.
- After ctx-019 (end of Part III, intermediate to advanced): the reader can write a five-block system prompt under version control and CI, design a tool catalogue and decide when MCP is the integration, route data to episodic, semantic, or procedural memory, pick GraphRAG, late interaction, SQL retrieval, or long-context loading by corpus shape, budget thinking tokens, and account for image tokens.
- After ctx-025 (end of Part IV, intermediate to advanced): the reader can wire a four-layer eval pyramid with a CI gate, constrain and validate model output, instrument traces and the four dashboard numbers, apply the four architectural defences against prompt injection, govern PII across prompts, memory, and the trace store, and decide between long context, RAG, and a hybrid with the four-question test.
- After ctx-030 (end of Part V, advanced): the reader has run the agentic workflow locally and remotely and has three working builds whose every function traces to an earlier post.

## Gates

`series.yaml` declares no formal gates (`gates: []`). The de facto gates are the companions: a reader should not pass ctx-011 without running `code/11-rag-from-scratch`, ctx-020 without the eval harness in `code/20-eval-ragas` producing a pass or fail, and Part V without each build's tests passing locally.

# 3. Pedagogical rules

- One question per post. Each post states one central question in its TL;DR and answers it; the "After reading this you will be able to" list is the contract the body must meet.
- Examples before formalism. A concrete call, trace, or cost table comes first; the general rule or framework is named afterwards.
- Framework-agnostic. Examples are plain Python against the official provider SDKs and the MCP reference SDK; a framework appears only when it changes the shape of the code, and no framework is the protagonist. Vendor features (Claude Code commands, Cursor rules) are named as instances of a vendor-neutral pattern.
- Every number is labelled. Prices, token counts, and percentages are either cited to a provider page or paper with a date, or marked "illustrative" in the sentence that uses them. The series never presents an unmeasured figure as a benchmark.
- Every non-obvious claim is cited inline and expanded in `REFERENCES.md`; every acronym is defined on first use in every post because readers do not read linearly.
- The six layers and the four operations are the fixed vocabulary. Later posts explain a technique by naming the layer it touches and the operation it performs; a technique that fits neither is a reason to revisit the framework, not to invent a new term.
- Neutral, textbook voice: third person, short sentences, no marketing. Every post carries a TL;DR, a hero figure, numbered sections, Common pitfalls, Further reading, and What to read next.
- Code companions are offline-testable. Each directory under `code/` has a `pyproject.toml`, tests that run without a network or an API key, and a `.env.example`; the three Part V builds are complete applications with the same discipline.

# 4. Curriculum lock

30 posts in 5 parts. Post numbers are permanent; a post inserted later takes the next ordinal from `series.yaml` and the directories after it renumber (STANDARD.md Section 2.2).

| Part | Title | Posts | Ids |
|---|---|---|---|
| I | Part I - Foundations | 01-06 | ctx-001 to ctx-006 |
| II | Part II - The WSCI operating system | 07-13 | ctx-007 to ctx-013 |
| III | Part III - Layers in depth | 14-19 | ctx-014 to ctx-019 |
| IV | Part IV - Production-grade practice | 20-25 | ctx-020 to ctx-025 |
| V | Part V - Workflow and builds | 26-30 | ctx-026 to ctx-030 |

Retired ids: none.

# 5. Per-post specifications

Each spec is a drafting brief and the prose form of the lock; the heading id, title, part, level, scope, and dependencies must equal `series.yaml` and the sidecar (STANDARD.md Section 18.3). All thirty posts are drafted, so every title below is the sidecar title with its number removed, and every brief is written from the shipped post.

## Part I - Foundations

### ctx-001 - Why context engineering — and why now

- **Meta:** Part I; beginner; core; proof none; code none.
- **Central question:** Why did the work move from engineering a prompt to engineering the whole window the model reads, and what is genuinely new about it?
- **Promise:** The reader can state in one sentence what separates context engineering from prompt engineering, recognise the five recurring jobs of a context engineer, and decide whether a given problem is a prompt problem, a context problem, or a model problem.
- **Coverage:** the three eras (prompt, RAG, agent); tools, retrieval, and memory as the three changes that broke the old name; who coined the term and when; what is new and what is not; the five jobs; when a problem is not a context problem; what the series will and will not cover.
- **Dependencies:** requires none; supports ctx-002.
- **Visuals:** hero `01-timeline.svg` (2022 to 2026, the surface grows from a message to a window); `02-prompt-subset.svg` (the prompt as a slice of the context); `03-five-jobs.svg` (the five jobs as an icon grid).
- **Lab/gate:** Take one LLM feature the reader has shipped or used and write down, for one call, which of the six layers were present and which of the five jobs were done by hand.
- **Anchors:** Karpathy (2025) on the term; Anthropic Engineering, "Effective context engineering for AI agents" (2025); IBM Think, "What is context engineering?" (2025); Martin, "Context Engineering for Agents" (2025); Horthy, "12-Factor Agents".

### ctx-002 - The Six Layers of Context

- **Meta:** Part I; beginner; core; proof none; code optional.
- **Central question:** What does the model literally receive on one call, and why is it useful to see that flat token sequence as six layers with different lifetimes and costs?
- **Promise:** The reader can name the six layers and the job of each, identify every layer in a raw Anthropic, OpenAI, or Gemini request, and predict which layer is responsible for a given category of failure.
- **Coverage:** the single flat sequence the model receives; purpose, lifetime, cost shape, and failure mode of a layer; system prompt, tool and MCP descriptions, memory and state, retrieved chunks, conversation history, user instruction; the layers in a real API call; why order matters (priority and a lost-in-the-middle preview); a pragmatic mental model.
- **Dependencies:** requires ctx-001; supports ctx-003, ctx-006, ctx-007, ctx-014.
- **Visuals:** hero `00-hero-six-layers.svg` (the stack bracketed by lifetime: stable prefix, per-turn injection, growing tail, trigger, with effective attention bars); `01-api-xray.svg` (one assembled request with each layer marked); `02-symptom-to-layer.svg` (symptom to responsible layer).
- **Lab/gate:** Print one assembled request from a real application and label every span with its layer; the labels must cover every token.
- **Anchors:** Anthropic Engineering, "Effective context engineering for AI agents" (2025); Anthropic, "Prompt caching" documentation; Anthropic, "Introducing Contextual Retrieval" (2024); Liu et al., "Lost in the Middle" (2023).

### ctx-003 - How LLMs Actually Read Context

- **Meta:** Part I; intermediate; core; proof none; code included.
- **Central question:** Which properties of tokenisation, attention, positions, and the KV-cache explain why ordering, position, and prefix stability change what a prompt costs and what the model recalls?
- **Promise:** The reader can explain in one sentence each what tokens, attention, positions, and the KV-cache are, predict where in a long prompt a model will under-attend and design around it, and reason about which parts of a prompt are cacheable.
- **Coverage:** byte-pair tokenisation and a `tiktoken` check; self-attention in one paragraph; positional encodings and RoPE; the lost-in-the-middle U-curve as measured; attention sinks; the KV-cache and why prefix caching exists; needle-in-a-haystack and what it does and does not measure; a placement heuristic.
- **Dependencies:** requires ctx-002; supports ctx-004, ctx-019, ctx-025.
- **Visuals:** hero `03-lost-in-the-middle.svg` (recall against position, high at both ends); `01-kv-cache-reuse.svg` (the cached prefix reused across turns); `02-attention-bias-bar.svg` (attention mass by position).
- **Lab/gate:** Run the `tiktoken` snippet on three strings and a page of code, then move one fact from the end to the middle of a 20k-token prompt and record whether the model still finds it.
- **Anchors:** Liu et al., "Lost in the Middle" (2023); Xiao et al., "Efficient Streaming Language Models with Attention Sinks" (2023); Su et al., "RoFormer" (2021); Anthropic Engineering, "Prompt caching with Claude" (2024); OpenAI, "Tokenizer" and `tiktoken`.

### ctx-004 - Tokens, Windows, and Budgets

- **Meta:** Part I; beginner; core; proof none; code optional.
- **Central question:** What are the three numbers (window, budget, and the latency, cost, quality triangle) that govern every context design decision, and how are they estimated on an envelope?
- **Promise:** The reader can estimate the token cost and latency of any prompt without running it, decide between a smaller model on a longer prompt and a larger model on a shorter one, and set a defensible token budget for each layer of an agent.
- **Coverage:** what a token is and why code and JSON tokenise worse than prose; the context window as a ceiling; the three budgets; the triangle; sizing an agent on an envelope, with what prompt caching does and does not do; per-layer budgets; a one-page model-picking decision.
- **Dependencies:** requires ctx-003; supports ctx-005, ctx-012, ctx-018, ctx-019, ctx-025.
- **Visuals:** hero `00-hero-token-window-budget.svg` (token as unit, window as ceiling, budget as the share spent); `01-budget-triangle.svg` (latency, cost, quality); `02-per-layer-budget.svg` (a budget split across the six layers).
- **Lab/gate:** Size the post's customer-support agent on paper (about 10,500 input and 400 output tokens per call), then check the estimate against a real tokeniser and a provider price page.
- **Anchors:** OpenAI, "Tokenizer"; Anthropic, "Token counting" and "Prompt caching" documentation; Google, "Long context" (Gemini API documentation); Yao (Manus), "Context Engineering for AI Agents" (2025); Sennrich et al., "Neural Machine Translation of Rare Words with Subword Units" (2016).

### ctx-005 - The Economics of Context — Pricing, Caching, and Latency

- **Meta:** Part I; intermediate; core; proof none; code optional.
- **Central question:** How do per-token pricing, the input-output asymmetry, prompt caching, and the latency of an agent turn decide whether a working demo can ship?
- **Promise:** The reader can price any prompt at any tier and predict how caching changes the bill, design a stable-prefix layout that maximises cache hits instead of silently invalidating them, and set cost guardrails (budgets, model routing, cache-hit monitoring) before the first bill arrives.
- **Coverage:** the same demo, unshippable at scale; cost per million tokens by tier; input against output asymmetry and the prefill-decode split; prompt caching in depth (breakpoints, render order, write premium, read discount, invalidation); the latency budget of an agent turn; a worked example with and without caching; cost guardrails to ship.
- **Dependencies:** requires ctx-004; supports ctx-006, ctx-022, ctx-025.
- **Visuals:** hero `00-hero-economics-of-context.svg` (the same 10,500-token input as a cache miss and a cache hit); `01-input-output-asymmetry.svg` (prefill against decode); `02-latency-budget.svg` (the waterfall of one agent turn).
- **Lab/gate:** Reproduce the worked example: price one agent turn at three tiers with and without caching, and show which layer ordering turns the cache hit rate from near zero to near one.
- **Anchors:** Anthropic, "Pricing" (2026) and "Prompt caching" documentation; Pope et al., "Efficiently Scaling Transformer Inference" (2022); OpenAI and Gemini prompt- and context-caching documentation; Yao (Manus), "Context Engineering for AI Agents" (2025).

### ctx-006 - Five Context Failure Modes

- **Meta:** Part I; intermediate; core; proof none; code none.
- **Central question:** When an LLM application starts producing bad answers, which of five mechanical failures of the context is responsible, and what is the cheapest fix for each?
- **Promise:** The reader can name the five failure modes and the symptom each produces, diagnose a production bug report by mapping it to one or two of them, and apply the first-fix for each without a model upgrade or a framework switch.
- **Coverage:** why a taxonomy; distraction, confusion, conflict, lost-in-the-middle, tool-storm, each as symptom, mechanism by layer, first-fix, and last resort; a diagnostic checklist; why poisoning is deferred to security.
- **Dependencies:** requires ctx-002; recommends ctx-005; supports ctx-007, ctx-020, ctx-023.
- **Visuals:** hero `01-failure-modes-grid.svg` (five modes mapped to originating layer and fixing operation); `02-diagnostic-walk.svg` (symptom to mode to fix); `03-detection-signals.svg` (the trace signals that reveal each mode).
- **Lab/gate:** Take three real bug reports from any LLM application, classify each with the checklist, and name the first-fix; the series' own rule is that a report that fits none of the five is a model problem, not a context problem.
- **Anchors:** Breunig, "How Long Contexts Fail" (2025); Liu et al., "Lost in the Middle" (2023); Hsieh et al., "RULER" (2024); Hong et al., "Context Rot" (Chroma, 2025); Anthropic Engineering, "Effective context engineering for AI agents" (2025).

## Part II - The WSCI operating system

### ctx-007 - Write, Select, Compress, Isolate

- **Meta:** Part II; beginner; core; proof none; code none.
- **Central question:** What is the smallest set of operations that covers every context-engineering technique, and how do the six layers and the five failure modes map onto it?
- **Promise:** The reader can name the four operations and the question each answers, pick the right operation for any of the five failure modes, and read the rest of the series knowing where each technique fits.
- **Coverage:** the two axes (information in or out; one window or several) and the four quadrants; write, select, compress, isolate defined with their canonical techniques; the six layers mapped onto WSCI; WSCI against the five failure modes; a worked walk-through of one agent session.
- **Dependencies:** requires ctx-002, ctx-006; supports ctx-008, ctx-009, ctx-012, ctx-013.
- **Visuals:** hero `01-wsci-quadrants.svg` (the two-by-two by direction and scope); `02-layers-to-wsci.svg` (each layer to the operations that act on it); `03-wsci-vs-failures.svg` (each failure mode to its fixing operation).
- **Lab/gate:** Trace one real agent session and annotate every event as W, S, C, or I; every event must land in exactly one cell.
- **Anchors:** Martin, "Context Engineering for Agents" (LangChain, 2025); Anthropic Engineering, "Effective context engineering for AI agents" (2025); IBM Think, "What is context engineering?" (2025); Anthropic, "Introducing Contextual Retrieval" (2024).

### ctx-008 - Write Strategies

- **Meta:** Part II; intermediate; core; proof none; code optional.
- **Central question:** When information might be needed later but not now, where should it be written, and what must be written alongside it so the store stays useful?
- **Promise:** The reader can choose the right write destination for a given piece of information, specify the metadata fields every memory or scratchpad row needs, and avoid the three classes of bug that turn a memory store into a liability.
- **Coverage:** why writing is a governance problem; memory stores (episodic, semantic, procedural rows and their schema); scratchpads and plan files; repository documentation (`AGENTS.md`, `CLAUDE.md`, `skill.md`) as a write destination; embedding indexes as the offline write side of RAG; the what-to-write-where cheat sheet.
- **Dependencies:** requires ctx-007; supports ctx-014, ctx-016.
- **Visuals:** hero `00-hero-write-strategies.svg` (four destinations and their lifetimes); `01-memory-write-schema.svg` (the three kinds and the nine-field row); `02-what-to-write-where.svg` (the decision table).
- **Lab/gate:** Write the memory schema for one agent with all nine metadata fields, then show one write per destination (memory row, scratchpad entry, `AGENTS.md` rule, index chunk) with its provenance filled in.
- **Anchors:** LangChain, "Memory for Agents" (2024); Anthropic Engineering, "Building Effective AI Agents" (2024); Anthropic, "Introducing Contextual Retrieval" (2024); agents.md project, "AGENTS.md" (2025); Park et al., "Generative Agents" (2023).

### ctx-009 - Select Strategies

- **Meta:** Part II; intermediate; core; proof none; code optional.
- **Central question:** Why are RAG, tool selection, memory recall, and few-shot picking one operation, and which of its four levers fixes a given selection failure?
- **Promise:** The reader can recognise that RAG, tool selection, memory recall, and few-shot picking are instances of the same operation, reason about each in terms of recall, precision, latency, and cost on one template, and pick the lever (query, candidates, re-rank, pack) most likely to fix a given failure.
- **Coverage:** why select generalises; query construction (rewriting, HyDE, decomposition); candidate generation (dense, sparse, hybrid, reciprocal rank fusion, top-N); re-ranking with cross-encoders (top-k); packing (bookends, citations, dedup); the same pipeline over four corpora; the tuning order; measuring recall@N and precision@k.
- **Dependencies:** requires ctx-007; supports ctx-010, ctx-011, ctx-015, ctx-016, ctx-028.
- **Visuals:** hero `00-hero-select-pipeline.svg` (query, candidates, re-rank, pack, from user turn to packed prompt); `01-four-corpora.svg` (documents, tools, memory rows, examples through the same boxes); `02-tuning-order.svg` (which lever to turn first).
- **Lab/gate:** Build the four-stage pipeline over a toy corpus, measure recall@50 and precision@5, then change one lever at a time and record which one moved each number.
- **Anchors:** Karpukhin et al., "Dense Passage Retrieval" (2020); Robertson and Zaragoza, "BM25 and Beyond" (2009); Cormack et al., "Reciprocal Rank Fusion" (2009); Gao et al., "HyDE" (2022); Anthropic Engineering, "Contextual Retrieval" (2024).

### ctx-010 - Data Ingestion and Document Pipelines

- **Meta:** Part II; intermediate; core; proof none; code optional.
- **Central question:** How does the parsing, cleaning, and enrichment of raw files decide which tokens can ever be retrieved, and how is a corpus that changes daily kept from rotting?
- **Promise:** The reader can choose the right parsing strategy (born-digital extraction, layout-aware parsing, or OCR) for a source type, preserve tables, structure, and provenance through the pipeline, and stand up incremental re-indexing.
- **Coverage:** garbage in; the six-stage pipeline (source, parse, clean, enrich, chunk, index); three PDF strategies for three situations; tables and structure as the hardest case; HTML and boilerplate removal; layout-aware tools as a class (Docling, Unstructured, LlamaParse); metadata and provenance at ingest; incremental re-indexing and change detection.
- **Dependencies:** requires ctx-009; supports ctx-011, ctx-019.
- **Visuals:** hero `00-hero-data-ingestion-pipelines.svg` (raw sources through parse and OCR to clean, enrich, chunk, index, with quality set upstream); `01-pdf-decision.svg` (born-digital, layout-aware, OCR); `02-table-flattening.svg` (what a flattened table loses).
- **Lab/gate:** Parse one table-heavy PDF three ways, read the extracted text before embedding anything, and show which strategy keeps the cell the answer lives in; then re-run ingestion after a one-page edit and confirm only that page re-indexes.
- **Anchors:** Smith, "An Overview of the Tesseract OCR Engine" (2007); Barbaresi, "Trafilatura" (2021); Docling, Unstructured, and LlamaParse documentation; Smock et al., "PubTables-1M" (2022); Anthropic, "Introducing Contextual Retrieval" (2024).

### ctx-011 - RAG in Depth

- **Meta:** Part II; intermediate; core; proof none; code included.
- **Central question:** Which offline and online engineering choices account for most of the gap between a demo RAG system and a production one?
- **Promise:** The reader can walk through every stage of a production RAG pipeline and name what fails where, apply the three techniques that consistently lift quality (contextual retrieval, hybrid search with reciprocal rank fusion, cross-encoder re-ranking), and wire the minimum eval harness that shows whether a change helped.
- **Coverage:** the offline and online halves; chunking (size, splitter family, overlap); embedding model choice and the index; the four online levers recapped; what the generation prompt should look like; the evaluation harness; where production RAG goes wrong; when not to use RAG. Companion `code/11-rag-from-scratch` (chunk, BM25, RRF).
- **Dependencies:** requires ctx-009, ctx-010; supports ctx-017, ctx-020, ctx-025, ctx-028.
- **Visuals:** hero `04-rag-pipeline.svg` (offline half sets the ceiling, online half approaches it); `01-chunking-choices.svg` (splitter, size, overlap); `02-contextual-retrieval.svg` (chunk headers before and after).
- **Lab/gate:** Run `code/11-rag-from-scratch` tests offline, then add contextual chunk headers and hybrid fusion to the toy corpus and show the recall change on a ten-question golden set.
- **Anchors:** Anthropic, "Introducing Contextual Retrieval" (2024); Cormack et al., "Reciprocal Rank Fusion" (2009); Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (2020); Muennighoff et al., "MTEB" (2022); Cohere, Voyage AI, and BAAI reranker documentation.

### ctx-012 - Compress Strategies

- **Meta:** Part II; intermediate; core; proof none; code optional.
- **Central question:** Which techniques shrink what is already in the window, what does each cost in retained information, and when should compression be triggered or avoided?
- **Promise:** The reader can pick the right compression technique for a given layer and failure mode, set auto-compaction triggers and tell `/compact` apart from `/clear`, and measure information retention so a summary change does not silently regress quality.
- **Coverage:** windowing, summarisation (rolling, hierarchical, structured), tool-result clearing, priority pruning, semantic chunking, prompt-level token compression (LLMLingua, RECOMP); the two Claude Code commands; the 80 and 95 percent triggers; the information retention ratio as a teaching construct; picking among the six; when compression is the wrong answer and isolate is the right one.
- **Dependencies:** requires ctx-007; recommends ctx-004; supports ctx-013, ctx-030.
- **Visuals:** hero `00-hero-compress-strategies.svg` (window usage climbing to the trigger and dropping after compaction); `01-six-techniques.svg` (reduction range and retention per technique); `02-priority-and-triggers.svg` (what is pruned first, and at which thresholds).
- **Lab/gate:** Build a replay set of ten long conversations with a list of key facts each, run a rolling-summary policy over them, and report the information retention ratio and token reduction per conversation.
- **Anchors:** Anthropic, "Claude Code" documentation (auto-compaction); Martin, "Context Engineering for Agents" (2025); Jiang et al., "LLMLingua" (2023); Pan et al., "LLMLingua-2" (2024); Xu et al., "RECOMP" (2023).

### ctx-013 - Isolate Strategies

- **Meta:** Part II; intermediate; core; proof none; code optional.
- **Central question:** When should a task give up on one context window and use several, and what contracts make sub-agents and sandboxes safe to deploy?
- **Promise:** The reader can decide when a task should be isolated and when it should not, specify the input and output contracts a sub-agent needs, and pick among sequential, fan-out and fan-in, and supervisor topologies.
- **Coverage:** why isolation matters and the workflow-versus-agent distinction; the sub-agent pattern; when to isolate; the three topologies; designing the contract; sandboxing to keep tool noise out of the context; memory across isolated agents; the cost arithmetic; the "Don't Build Multi-Agents" steelman; anti-patterns.
- **Dependencies:** requires ctx-007; recommends ctx-012; supports ctx-015, ctx-026, ctx-030.
- **Visuals:** hero `06-subagent-isolation.svg` (parent delegating to children with clean contexts, only the structured result returning); `01-three-topologies.svg` (sequential, fan-out and fan-in, supervisor); `02-isolate-or-not.svg` (the decision rule).
- **Lab/gate:** Write an orchestrator and one worker without a framework, with a typed input and output contract, and show that the parent's context after the call contains the result and none of the worker's intermediate tokens.
- **Anchors:** Anthropic Engineering, "Building Effective AI Agents" (2024) and "How we built our multi-agent research system" (2025); Cognition, "Don't Build Multi-Agents" (2025); LangGraph multi-agent documentation; Wu et al., "AutoGen" (2023).

## Part III - Layers in depth

### ctx-014 - The System Prompt as Software

- **Meta:** Part III; intermediate; core; proof none; code optional.
- **Central question:** What does it mean to treat the system prompt as the executable specification of an agent, versioned, reviewed, tested, and monitored like code?
- **Promise:** The reader can decompose any system prompt into five named blocks, apply six rules that keep a prompt from accumulating contradictions, and wire the minimum CI harness that lets a team change prompts safely.
- **Coverage:** the five blocks (identity, rules, format, knowledge, tools); the six rules; versioning and `AGENTS.md`; caching and the prompt's cost; testing as the harness without which prompts rot; production monitoring; the payoff.
- **Dependencies:** requires ctx-002; recommends ctx-008; supports ctx-015, ctx-026, ctx-028, ctx-030.
- **Visuals:** hero `00-hero-system-prompt-as-software.svg` (five stacked cards with fluid boundaries); `01-six-rules.svg` (the six rules); `02-prompt-cache-order.svg` (the block order that keeps the prefix stable).
- **Lab/gate:** Rewrite one existing system prompt into the five blocks, put it under version control with a ten-case regression set, and show the CI gate failing on a deliberately contradictory rule.
- **Anchors:** Anthropic Engineering, "Crafting effective system prompts"; OpenAI, "Model Spec" (2024, revised 2025); agents.md project, "AGENTS.md" (2025); DAIR.ai, "Prompt Engineering Guide" (2024); Anthropic, "Prompt caching" documentation.

### ctx-015 - Tools and MCP

- **Meta:** Part III; intermediate; core; proof none; code included.
- **Central question:** How does a tool catalogue trade off size, description quality, and runtime selection inside the prompt, and where does the Model Context Protocol fit?
- **Promise:** The reader can design tool descriptions the model will use correctly, manage a large catalogue without polluting the prompt, decide when MCP is the right integration and when bespoke glue still wins, and choose between a tool call and a structured `response_format` for a task.
- **Coverage:** tools as schema text in the prompt; the iron triangle; designing a single tool; the catalogue problem and runtime selection; MCP as host, client, server with tools, resources, and prompts; permissions and confirmations; sandboxing; the selection pipeline in production; structured output when the answer is the payload. Companions `code/15-tool-schemas` (token budget, schema validation) and `code/15-mcp-quickstart` (a sixty-line server).
- **Dependencies:** requires ctx-009, ctx-014; recommends ctx-013, mcp-001; supports ctx-016, ctx-021, ctx-023, ctx-029.
- **Visuals:** hero `05-mcp-triangle.svg` (host, client, servers exposing tools, resources, prompts); `01-iron-triangle.svg` (catalogue size, description quality, runtime selection); `02-tool-description.svg` (a tool description annotated line by line).
- **Lab/gate:** Run the `code/15-tool-schemas` budget calculator on a fifty-tool catalogue, cut it to five with a selection step, and start the `code/15-mcp-quickstart` server in one MCP host.
- **Anchors:** Anthropic, "Introducing the Model Context Protocol" (2024); modelcontextprotocol.io specification; Anthropic Engineering, "Equipping agents for the real world with Agent Skills" (2025); Anthropic, "Code execution with MCP" (2025); OpenAI, "Function calling" documentation.

### ctx-016 - Memory Systems

- **Meta:** Part III; intermediate; core; proof none; code included.
- **Central question:** Why does an agent that remembers need three different memories (episodic, semantic, procedural), and how are they written, retrieved, decayed, and kept from poisoning each other?
- **Promise:** The reader can distinguish episodic, semantic, and procedural memory and route data to the right one, specify the minimum metadata each memory cell needs, and avoid the four classes of bug that turn a memory store into a liability.
- **Coverage:** statelessness and short-term against long-term memory; why three kinds; each kind's schema, write trigger, retrieval, and decay; the retrieval orchestrator; a minimal memory layer in code; the four bugs; what Mem0, Letta, and Zep do; how to choose; memory in the prompt; when not to use a memory store.
- **Dependencies:** requires ctx-008; recommends ctx-009, ctx-015; supports ctx-017, ctx-023, ctx-024, ctx-030.
- **Visuals:** hero `08-memory-taxonomy.svg` (the three kinds with write trigger, retrieval, decay); `01-three-kinds-compared.svg` (the same conversation stored three ways); `02-retrieval-orchestrator.svg` (one query fanned to three stores and merged).
- **Lab/gate:** Run the post's minimal memory layer, write ten facts of mixed kind, and show that a preference, an event, and a rule are each retrieved by the right path and that a stale event decays while the rule does not.
- **Anchors:** Tulving, "Episodic and semantic memory" (1972); Park et al., "Generative Agents" (2023); Packer et al., "MemGPT" (2023); Rasmussen et al., "Zep" (2025); Mem0 and Letta documentation.

### ctx-017 - Advanced Retrieval

- **Meta:** Part III; advanced; core; proof none; code optional.
- **Central question:** Which corpus shapes defeat hybrid RAG, and which of GraphRAG, late interaction, SQL retrieval, or long-context routing serves each at what cost?
- **Promise:** The reader can recognise the corpus shapes that defeat vanilla RAG, pick the right advanced technique for each shape, and estimate the engineering and inference overhead before committing.
- **Coverage:** the four ceilings (multi-hop, long single documents, structured data, rare exact terms); GraphRAG; late-interaction retrieval with ColBERT and MaxSim; structured and text-to-SQL retrieval; long-context routing; the router; what not to do; the shape of a production retrieval stack.
- **Dependencies:** requires ctx-011; recommends ctx-016; supports ctx-018, ctx-025.
- **Visuals:** hero `00-hero-advanced-retrieval.svg` (a router dispatching by question shape); `01-four-ceilings.svg` (four question shapes, why each fails, the technique each needs); `02-technique-costs.svg` (build and query cost per technique).
- **Lab/gate:** Write twelve questions, three per ceiling, run them through hybrid RAG and record which fail; then route each failing shape to its technique and show the fix on at least one question per shape.
- **Anchors:** Edge et al., "From Local to Global: A Graph RAG Approach" (2024); Khattab and Zaharia, "ColBERT" (2020); Santhanam et al., "ColBERTv2" (2022); Pourreza and Rafiei, "DIN-SQL" (2023); Gemini API, "Long context" documentation.

### ctx-018 - Context for Reasoning Models

- **Meta:** Part III; intermediate; core; proof none; code optional.
- **Central question:** How do thinking tokens change the budget, the cache, and the hygiene of a prompt, and how is adaptive thinking steered with an effort dial instead of a fixed budget?
- **Promise:** The reader can budget thinking tokens as a distinct, controllable cost line, set the effort dial per task instead of leaving extended thinking on or off globally, and keep raw reasoning traces out of downstream prompts, the cached prefix, and memory.
- **Coverage:** a million-token reader is not a million-token reasoner; what a reasoning model does; adaptive thinking and the effort dial; thinking tokens against the six-layer budget; trace hygiene; interleaved thinking and tool calls; when reasoning replaces scaffolding and when not to reach for it.
- **Dependencies:** requires ctx-004; recommends ctx-017; supports ctx-019.
- **Visuals:** hero `00-hero-reasoning-model-context.svg` (one turn as prompt, adaptive thinking, answer, with the effort dial and the dropped trace); `01-trace-hygiene.svg` (where a trace must not go); `02-interleaved-thinking.svg` (thinking between tool calls on a timeline).
- **Lab/gate:** Run one hard task at three effort levels, record thinking tokens, latency, and correctness per level, and demonstrate that feeding the raw trace into the next turn breaks the cached prefix.
- **Anchors:** Anthropic, "Extended thinking" documentation; Anthropic Engineering, "Building effective agents" (2024); Wei et al., "Chain-of-Thought Prompting" (2022); DeepSeek-AI, "DeepSeek-R1" (2025); Anthropic, "Prompt caching" documentation.

### ctx-019 - Multimodal Context — Images, PDF Pages, and Audio

- **Meta:** Part III; intermediate; core; proof none; code optional.
- **Central question:** How do images, rendered pages, screenshots, and audio occupy the same window and budget as text, and when should a document be sent as pixels rather than extracted text?
- **Promise:** The reader can estimate how many tokens an image adds from its resolution and tiling, decide per document whether to send pixels or extracted text, and choose between visual retrieval and OCR-then-text RAG for a page-image corpus.
- **Coverage:** how images consume the window through tiling; PDF as images against OCR; ColPali against OCR-then-text RAG; screenshots for computer-use agents; audio and transcription; multimodal caching and token accounting.
- **Dependencies:** requires ctx-003, ctx-004; recommends ctx-010, ctx-018; supports none.
- **Visuals:** hero `00-hero-multimodal-context.svg` (a page tiled into image tokens inside the stack, with the pixels and OCR routes meeting at retrieval); `01-visual-vs-ocr-retrieval.svg` (the two retrieval routes side by side); `02-image-cache-boundary.svg` (where an image breaks the cached prefix).
- **Lab/gate:** Send the same page at three resolutions and record the token count each time, then answer five questions about a scanned table once from pixels and once from OCR text and compare.
- **Anchors:** Faysse et al., "ColPali" (2024); OpenAI, "Vision" and "Computer use" guides; Anthropic, "Vision", "Computer use", and "Prompt caching" documentation; Khattab and Zaharia, "ColBERT" (2020).

## Part IV - Production-grade practice

### ctx-020 - Evaluation

- **Meta:** Part IV; intermediate; core; proof none; code included.
- **Central question:** What eval pyramid, metric families, and CI gate turn changing an LLM system into improving it?
- **Promise:** The reader can pick the right metric for each layer of an LLM system, wire a regression gate that blocks bad pull requests, and avoid the four common LLM-as-judge failure modes.
- **Coverage:** why eval is the first discipline; the four-layer pyramid (unit, component, end-to-end, online); the three metric families (deterministic, programmatic judge, human); the minimum harness with promptfoo, Ragas, and a custom gate; the retrieval metrics (faithfulness, answer relevance, context precision, context recall); the four judge failure modes; online evaluation; what changes once eval exists. Companion `code/20-eval-ragas` (golden set, gate, judge).
- **Dependencies:** requires ctx-011; recommends ctx-006; supports ctx-021, ctx-022, ctx-028, ctx-030.
- **Visuals:** hero `00-hero-evaluation.svg` (the pyramid with frequency and cost axes); `01-metric-families.svg` (deterministic, judge, human, by layer); `02-judge-failure-modes.svg` (position, verbosity, self-preference, and inconsistency).
- **Lab/gate:** Run `code/20-eval-ragas` against the ctx-011 pipeline on a twenty-item golden set, then introduce a regression and show the gate failing in CI.
- **Anchors:** Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (2023); Es et al., "Ragas" (2023); Liu et al., "G-Eval" (2023); Saad-Falcon et al., "ARES" (2023); promptfoo, DeepEval, and LangSmith documentation.

### ctx-021 - Structured Output and Guardrails

- **Meta:** Part IV; intermediate; core; proof none; code optional.
- **Central question:** Which mechanisms make model output typed and valid, which loop recovers from the failures that remain, and where does a runtime guardrail layer sit relative to offline evaluation?
- **Promise:** The reader can choose the right output mechanism (`response_format`, tool call, or constrained decoding) for a task, wire a validate-and-retry loop that turns a malformed response into a valid one, and assemble an output-side guardrail layer (schema, moderation, PII filtering, refusal handling).
- **Coverage:** a fluent answer that will not parse is an incident; the ladder of guarantees (JSON Schema and `response_format`, tool-call arguments, Pydantic, Instructor, Outlines, grammar-constrained decoding); `response_format` against `tool_choice`; the failures that remain and the retry loop; output guardrails as a defence layer; measure against enforce.
- **Dependencies:** requires ctx-015, ctx-020; supports none.
- **Visuals:** hero `00-hero-structured-output-guardrails.svg` (validate, retry on failure, moderate, return); `01-guarantee-ladder.svg` (four rungs and what each leaves to you); `02-payload-or-action.svg` (is the answer the payload or an action).
- **Lab/gate:** Implement one extraction task three ways (prompt instruction, `response_format`, constrained decoding), run a hundred inputs through each, and report parse-failure rate before and after a capped retry loop.
- **Anchors:** OpenAI, "Structured Outputs" documentation; Anthropic, "Tool use" documentation; Outlines (Willard and Louf, 2023, and project documentation); Instructor and Pydantic documentation; Guardrails AI and NVIDIA NeMo Guardrails documentation.

### ctx-022 - Observability, Tracing, and Cost

- **Meta:** Part IV; intermediate; core; proof none; code optional.
- **Central question:** What must be recorded about every LLM call so an agent run can be debugged, costed, and regression-tested from its traces?
- **Promise:** The reader can wire trace and span instrumentation into an existing LLM application, read a trace and identify the four most common bug shapes, and set up a dashboard that surfaces cost, quality, latency, and error trends.
- **Coverage:** why LLM observability records more than classical tracing; the trace and the span; what to instrument; the four dashboard numbers; the four bug shapes in a trace; replays and regression detection; cost engineering and cache-hit monitoring; privacy and PII in traces; the tools (LangSmith, Langfuse, Phoenix, Helicone, Braintrust, OpenTelemetry GenAI conventions).
- **Dependencies:** requires ctx-005, ctx-020; supports ctx-023, ctx-024, ctx-030.
- **Visuals:** hero `00-hero-observability.svg` (one turn as a span tree beside four dashboard cards); `01-bug-shapes.svg` (the four shapes as they look in a trace); `02-replay-loop.svg` (capture, replay, diff).
- **Lab/gate:** Instrument the ctx-011 pipeline with OpenTelemetry spans into Langfuse or Phoenix, find the cost and latency of each span for ten turns, and replay one captured trace after a prompt change.
- **Anchors:** LangSmith, Langfuse, Arize Phoenix, Braintrust, and Helicone documentation; OpenTelemetry GenAI semantic conventions.

### ctx-023 - Security and Guardrails

- **Meta:** Part IV; advanced; core; proof none; code optional.
- **Central question:** Given that any text reaching the window is executable, what are the three classes of prompt injection and the four architectural defences that reduce the risk?
- **Promise:** The reader can recognise the three classes of prompt-injection attack, apply the four architectural defences that reduce risk, and avoid the comfortable but ineffective mitigation of asking the model nicely.
- **Coverage:** the reframing; direct injection, indirect injection, and memory poisoning with the data-exfiltration pattern and a catalogue of incidents; the four defences (isolate authority, constrain tool blast radius, filter at trust boundaries, never silently merge attacker text) with the same agent vulnerable and patched; defences that feel like they help; the Dual LLM pattern; the MCP-specific risk; detection and response; a threat-model template; the OWASP Top 10.
- **Dependencies:** requires ctx-015, ctx-016; recommends ctx-006, ctx-022; supports ctx-024, ctx-026, ctx-029, ctx-030.
- **Visuals:** hero `00-hero-security.svg` (untrusted content through four layered defences before any consequential action); `01-exfiltration-chain.svg` (the injection-to-exfiltration chain); `02-three-classes.svg` (blast radius per class).
- **Lab/gate:** Run the deliberately vulnerable agent against a seeded document and show the exfiltration, then apply the four defences and show the same input failing to act.
- **Anchors:** OWASP, "Top 10 for LLM Applications" (2025); Greshake et al., "Not what you've signed up for" (2023); Willison, "Prompt injection" essays (2022 to 2025) and "The Dual LLM pattern" (2023); NIST, "AI 600-1 Generative AI Profile" (2024).

### ctx-024 - Privacy, PII, and Data Governance

- **Meta:** Part IV; intermediate; core; proof none; code optional.
- **Central question:** Where does regulated data enter the context and its copies, and where must detection, redaction, retention, consent, and tenant isolation be placed to govern it without gutting answer quality?
- **Promise:** The reader can trace where PII enters the context pipeline and the trace store, place detection, redaction, retention, and residency controls at the right boundary, and enforce memory consent, deletion, and multi-tenant isolation across a RAG and memory stack.
- **Coverage:** the trace store as a copy of every prompt; where regulated data enters; detection and redaction at the trust boundary (Presidio, NER); retention and residency of logged prompts and zero-retention terms; memory governance, consent, and the right to be forgotten; tenant isolation in multi-tenant RAG and memory; a governance checklist. Framed explicitly as engineering obligations, not legal advice.
- **Dependencies:** requires ctx-022, ctx-023; recommends ctx-016; supports ctx-025.
- **Visuals:** hero `00-hero-privacy-and-governance.svg` (inputs converging on a detect-and-redact gate, then fanning to the window and the trace store); `01-detect-and-redact.svg` (the gate in detail); `02-retention-tiers.svg` (retention and deletion by store).
- **Lab/gate:** Draw the data-flow diagram for one agent, insert a redaction gate before the model and the logger, run twenty prompts containing synthetic PII, and verify none reaches the trace store; then delete one user's memory rows and show the deletion propagates to the index.
- **Anchors:** NIST, "AI 600-1" (2024); OWASP, "Top 10 for LLM Applications" (2025), LLM02; EU GDPR Articles 5 and 17 at a high level; Microsoft, "Presidio"; Anthropic and OpenAI data-usage and retention documentation.

### ctx-025 - Long Context vs. RAG — A Decision Framework

- **Meta:** Part IV; intermediate; core; proof none; code optional.
- **Central question:** When does a million-token window replace retrieval, when does retrieval still win, and what do the long-context benchmarks say about how well models use the room they have?
- **Promise:** The reader can match a workload to long context, RAG, or a hybrid using a four-question test, read the current long-context benchmarks without being misled by the marketing version, and estimate the cost and latency penalty of long context against retrieval.
- **Coverage:** the temptation; the four-question test (fits with room to spare, stable enough to cache, needs provenance or freshness, per-tenant data); what RULER, BABILong, LongBench, MRCR, and NIAH show; when long context wins; when RAG wins; hybrid routing as the production reality; cost arithmetic; the forecast.
- **Dependencies:** requires ctx-011, ctx-017; recommends ctx-003, ctx-004, ctx-005, ctx-024; supports ctx-026.
- **Visuals:** hero `00-hero-long-context-vs-rag.svg` (four questions routing to long context, RAG, or per-query routing); `01-benchmark-gap.svg` (advertised against effective context length); `02-when-each-wins.svg` (the two columns).
- **Lab/gate:** Take one real corpus, answer the four questions in writing, then run the same ten questions under whole-document loading and under the ctx-011 pipeline and record accuracy, latency, and cost for each.
- **Anchors:** Hsieh et al., "RULER" (2024); Kuratov et al., "BABILong" (2024); Bai et al., "LongBench" (2024); Vodrahalli et al., "Michelangelo" and MRCR (2024); Google, "Long context" (Gemini API documentation); Anthropic, "Pricing" (2026).

## Part V - Workflow and builds

### ctx-026 - The Modern Agentic Workflow

- **Meta:** Part V; intermediate; core; proof none; code optional.
- **Central question:** What operating model did the editor and terminal coding agents converge on, and how do `AGENTS.md`, skills, hooks, and sub-agents make a session productive?
- **Promise:** The reader can describe the agent loop common to Claude Code, Cursor, Aider, and their peers, configure a project with the `AGENTS.md`, skills, and hooks that make the agent useful, and avoid the four workflow anti-patterns that multiply a session's cost.
- **Coverage:** what changed since autocomplete; the agent loop; `AGENTS.md` and `CLAUDE.md` in the five-block form; skills; sub-agents and the orchestrator pattern; hooks; the four anti-patterns; the session as the unit of work. Vendor-neutral throughout.
- **Dependencies:** requires ctx-013, ctx-014; recommends ctx-023, ctx-025; supports ctx-027, ctx-028.
- **Visuals:** hero `00-hero-modern-agentic-workflow.svg` (the repo as a small operating system feeding the loop); `01-hook-points.svg` (where hooks fire in the loop); `02-orchestrator-handshake.svg` (parent to sub-agent and back).
- **Lab/gate:** Set up one repository with an `AGENTS.md`, one skill, and one hook, run a bounded task through the agent, and read the resulting session transcript as a sequence of write, select, compress, and isolate events.
- **Anchors:** Anthropic, "Claude Code" documentation; Cursor, "Rules and Composer" documentation; Aider documentation; agents.md project, "AGENTS.md" (2025); Anthropic Engineering, "Agent Skills" (2025); Cognition, "Don't Build Multi-Agents" (2025).

### ctx-027 - Remote Agentic Workflow

- **Meta:** Part V; intermediate; core; proof none; code optional.
- **Central question:** When is it worth moving the agent process to a remote server, and what stack keeps a long-running session alive, reachable, and safe from any device?
- **Promise:** The reader can decide when remote agentic work is worth the setup, configure a remote-agent stack (a cloud VM, tmux, SSH, VS Code Remote), and add the ergonomic layers (chat-bridge notifications, web access) that make it usable from anywhere.
- **Coverage:** why remote; the four-box architecture; the minimum setup; persistence and handoff; notifications and asynchronous oversight; the cost model; security on a remote agent (scoped credentials, security groups, no keys on the laptop); the mobile workflow.
- **Dependencies:** requires ctx-026; supports ctx-028.
- **Visuals:** hero `00-hero-remote-agentic-workflow.svg` (laptop over SSH to a VM running a tmux session, with a chat bridge and a security boundary); `01-persistence-and-handoff.svg` (one session, three clients); `02-remote-controls.svg` (the credential and network controls).
- **Lab/gate:** Stand up the minimum setup on one small VM, start a thirty-minute agent task in tmux, close the laptop, and resume the session from a second device with the task still running.
- **Anchors:** AWS EC2 pricing and "EC2 Instance Connect" documentation; Hetzner cloud pricing; VS Code, "Remote development over SSH"; Anthropic, "Pricing" and "Prompt caching" documentation; tmux manual.

### ctx-028 - Build #1 — RAG Chatbot from Scratch

- **Meta:** Part V; advanced; core; proof none; code required.
- **Central question:** How do the principles of Parts I to IV compose into one runnable RAG chatbot of about 250 lines where every function traces back to an earlier post?
- **Promise:** The reader can assemble an end-to-end RAG pipeline (ingest, retrieve, prompt, generate, evaluate), recognise the connection between every code block and an earlier post, and take the build as a starter and harden it for real traffic.
- **Coverage:** goals and scope; architecture and layout; ingestion with contextual chunk headers; hybrid retrieval with reciprocal rank fusion and a cross-encoder reranker; bookend prompt assembly with citations and the five-block system prompt; the chat loop; the four Ragas metrics as an eval gate; deployment; what the build leaves out; the lesson. Companion `code/28-rag-chatbot`.
- **Dependencies:** requires ctx-009, ctx-011, ctx-014, ctx-020; recommends ctx-026, ctx-027; supports ctx-029, ctx-030.
- **Visuals:** hero `00-hero-build-rag-chatbot.svg` (offline indexing lane, online query lane, eval gate on deploy); `01-module-map.svg` (each module to the post it implements); `02-packed-prompt.svg` (the bookended prompt with citation tags).
- **Lab/gate:** Run `code/28-rag-chatbot` tests offline, index the sample corpus, answer the golden set, and show the eval gate passing; then swap the reranker off and show it failing.
- **Anchors:** Anthropic, "Introducing Contextual Retrieval" (2024); LangChain, "RAG from scratch" (2024); Cohere, "Rerank" documentation; Voyage AI model cards; Es et al., "Ragas" (2023).

### ctx-029 - Build #2 — MCP Server from Scratch

- **Meta:** Part V; advanced; core; proof none; code required.
- **Central question:** What does a production-shaped MCP server with tools, a resource, a prompt, typed validation, and a permission boundary look like end to end, and how is it wired into a host?
- **Promise:** The reader can write a production-shaped MCP server end to end, apply the iron triangle of tool design and the four security defences inside it, and connect the server to a host and verify it from a real model session.
- **Coverage:** goals and scope (three tools, one resource, one prompt); the minimum of the wire shape and the stdio-against-HTTP transport choice; layout; the server with FastMCP; the server's `AGENTS.md`; connecting to a host and the description-iteration test loop; the security checklist; tests; what the build leaves out; publishing and distribution; the lesson. Companion `code/29-mcp-server-full`.
- **Dependencies:** requires ctx-015, ctx-023; recommends ctx-028, mcp-005; supports ctx-030.
- **Visuals:** hero `00-hero-build-mcp-server.svg` (host and client on one side, a server exposing tools, resources, prompts over a transport); `01-transport-choice.svg` (stdio against streamable HTTP); `02-permission-boundary.svg` (model proposes, server checks in code, host confirms).
- **Lab/gate:** Run `code/29-mcp-server-full` tests, connect the server to one MCP host, trigger `issue_refund` above the threshold from a live session, and show the confirmation gate firing.
- **Anchors:** Model Context Protocol specification (current revision); Anthropic, "Introducing the Model Context Protocol" (2024); MCP Python SDK; FastMCP, "Running Your Server"; agents.md project, "AGENTS.md" (2025).

### ctx-030 - Capstone — Email Reply Agent

- **Meta:** Part V; advanced; core; proof none; code required.
- **Central question:** How do all six layers, all four operations, and the production disciplines compose into one deployable email-reply agent with a send gate?
- **Promise:** The reader can see how every earlier post applies in a single working system, adapt the architecture to their own production agent, and present the result as a credible portfolio piece.
- **Coverage:** the problem; architecture at a glance; the five-block system prompt; episodic, semantic, and procedural memory of recipients and style; RAG over prior replies; compression of long threads; the triager sub-agent; the send gate; observability and eval with held-out replies; deployment (Gmail API and OAuth, FastAPI on Railway, Next.js on Vercel); the lesson; where to go next; closing. Companion `code/30-email-reply-agent`.
- **Dependencies:** requires ctx-014, ctx-016, ctx-020, ctx-022, ctx-023, ctx-028, ctx-029; recommends ctx-012, ctx-013; supports none.
- **Visuals:** hero `00-hero-capstone-email-reply-agent.svg` (Gmail to triager and drafter drawing on RAG and memory, through a send gate and human review); `01-every-lever.svg` (every post's lever placed in the architecture); `02-send-gate.svg` (the gate in detail).
- **Lab/gate:** Run `code/30-email-reply-agent` tests offline, deploy against a test mailbox, draft replies to ten held-out threads, and show the eval harness scores and the send gate blocking an unreviewed send.
- **Anchors:** Google, "Gmail API" and "OAuth 2.0 for Web Server Applications" documentation; Anthropic, "Models overview" and "Pricing"; Vercel and Railway documentation; the twenty-three earlier posts the sections trace to.

# 6. Series-specific contracts

## Notation and vocabulary

- The six layers are numbered 01 to 06 in the fixed order system prompt, tools and MCP descriptions, memory and state, retrieved chunks, conversation history, user instruction; a post that names a layer uses the number and the name.
- WSCI is the series' abbreviation for write, select, compress, isolate, always in that order; a technique is placed in exactly one quadrant.
- The five failure modes are distraction, confusion, conflict, lost-in-the-middle, and tool-storm; poisoning is a security term and lives in ctx-023.
- Retrieval numbers: top-N is the candidate-set size, top-k the packed count; recall@N and precision@k are the two metrics.
- Math is confined to `$...$` inline where a formula appears (reciprocal rank fusion, MaxSim); the series carries no derivations.

## Claim standards

- Every price, token count, window size, and percentage is either cited to a dated provider page or paper or marked "illustrative" in the sentence that uses it. The information retention ratio of ctx-012 is labelled a teaching construct, not a standard metric.
- Model names and prices are stated as "as of early 2026" and are expected to go stale; the posts say so where they quote them.

## Datasets and registries

- No dataset registry. The companions ship their own small sample corpora and golden sets under `code/<companion>/data/`; there are no external datasets to register.

## Compute

- Every companion has an offline-testable core that runs on a laptop without a network or an API key. Live runs call a hosted model (the `api-small` tier in the family vocabulary) and are documented in each companion's README. `series.yaml` leaves `vocab` empty because the sidecars do not yet carry `compute`; when they do, the only tier in use is `api-small`.

## Library and companions

- `series.yaml: library` is null. There is no single library; seven independent companions live under `code/`: `11-rag-from-scratch`, `15-tool-schemas`, `15-mcp-quickstart`, `20-eval-ragas`, `28-rag-chatbot`, `29-mcp-server-full`, `30-email-reply-agent`. Each has `pyproject.toml`, `tests/`, a README, and (where a key is needed) `.env.example`.
- Inline snippets in posts live under `posts/NN-slug/snippets/` when they are more than a few lines.

## Interactives

- None. The series has no `interactives/` directories and the plan does not add any.

## Series-specific checks

- The repository has `tools/lint-posts.ps1` (frontmatter, dead links, alt text) and `tools/render-diagrams.ps1`; the family validator supersedes the frontmatter and link checks once the sidecars migrate. `templates/`, `tools/`, and `assets/` are listed in `.gitignore` and are workspace-only; the family tooling under `series-standard/tools` is the committed path.

# 7. Sibling handoffs and deliberate omissions

## Assumed from siblings

- Nothing is required from another series. ctx-003 summarises transformer mechanics (tokens, attention, RoPE, the KV-cache) at the depth the series needs and points the reader who wants the derivations to the transformer series.

## Handoffs to locked siblings

- mcp (What The Hell is MCP?): ctx-015 gives the host, client, server picture and the place of MCP in tool design, and recommends mcp-001 for the protocol's own account of the problem it solves; ctx-029 builds a server with FastMCP and recommends mcp-005 for the from-first-principles server. Everything deeper (the wire protocol, transports, elicitation, tasks, clients and hosts, authorization, publishing) belongs to mcp-003 to mcp-012 and mcp-019 to mcp-022, and this series does not restate it.

## Handoffs to siblings that are not yet locked (prose only)

- harness-engineering: the agent loop, hooks, permissions and sandboxes, verification loops, multi-agent orchestration, and the economics of harnesses. ctx-013 and ctx-026 introduce sub-agents, hooks, and the loop as context-engineering concerns and stop where the harness becomes the subject. Once harness-engineering is locked, ctx-026 should recommend its opening post and ctx-013 its orchestration posts.
- vector-db: approximate nearest-neighbour indexes, quantisation, and the internals of a vector store. ctx-009 and ctx-011 treat the vector database as a black box with a recall and latency profile.
- evaluation-engineering (planned): eval methodology beyond the one-post harness of ctx-020.
- ai-security (planned): red-teaming, jailbreak taxonomies, and defences beyond the four architectural ones in ctx-023.

## Deliberate omissions

- Fine-tuning, distillation, and training of any kind: the series engineers the input to a fixed model.
- Transformer internals and attention derivations beyond the single-paragraph accounts in ctx-003.
- A survey of frameworks (LangChain, LlamaIndex, LangGraph, DSPy): named where a pattern originates, never taught.
- Legal advice: ctx-024 frames privacy regimes as engineering obligations and says so.
- Mailing list, translations, and the website: handled outside the series.

# 8. Projects

None. `series.yaml: projects` is empty and `next_project_ordinal` is 1. The three builds (ctx-028, ctx-029, ctx-030) are posts with companions, not projects under `projects/`; promoting the capstone to a project (`ctx-p01`, kind service, after_post ctx-030) is a candidate for a later plan version once the companion is deployed and has an evaluation record.

# 9. Risks and decisions

## Risk register

- Pre-standard sidecars. Every `frontmatter.yaml` is a fenced, pre-2.0 document with `description`, `author`, `last_modified`, `category`, `series`, `chapter`, `keywords`, `toc`, `draft`, `canonical_url`, `hero_alt`, `prev`, `next`, and no `summary`, `updated`, `status`, `level`, `prerequisites`, `code`, or `outcomes`. Mitigation: this plan is the record of level, scope, code, and dependencies for every post; the migration commit copies them into the sidecars from Section 5.
- Dated prices and model names. Six posts quote early-2026 prices and windows. Mitigation: every figure is dated in the sentence; a yearly pass re-checks them.
- Companion drift. Seven companions pin provider SDKs and the MCP SDK, which iterate quickly. Mitigation: offline tests in CI, and each README names the SDK version it was last run against.
- Workspace folders are gitignored. `templates/`, `tools/`, and `assets/` are in `.gitignore`, so the hero diagrams that posts reference must live under `posts/NN-slug/diagrams/` (they do) and the series-level poster under `poster/`.

## Decisions locked

- Five parts with the titles of the pre-lock plan in sentence case: Part I - Foundations, Part II - The WSCI operating system, Part III - Layers in depth, Part IV - Production-grade practice, Part V - Workflow and builds. The sidecars' `chapter` strings (which disagreed within Parts III, IV, and V) are not used.
- ctx-025 sits in Part IV. Its sidecar said part 5 with a Part V chapter string ("End-to-End Applications"); the pre-lock plan and the README place the long-context decision in production practice, and the post has no build. The sidecar `part` was set to Part IV.
- Levels: beginner for ctx-001, ctx-002, ctx-004, ctx-007; advanced for ctx-017, ctx-023, ctx-028, ctx-029, ctx-030; intermediate otherwise. `levels_used` is `[beginner, intermediate, advanced]`.
- Scope is `core` for every post; proof is `none` for every post; code is `required` for the three builds, `included` where a companion or a complete in-post implementation exists, `optional` where snippets are illustrative, `none` for ctx-001, ctx-006, and ctx-007.
- Prerequisites were derived from each post's own cross-references (TL;DR, body, What to read next): a post the body depends on to be understood is `requires`; a post it points to for depth is `recommends`.
- Cross-series references are limited to the locked mcp series (mcp-001, mcp-005), both as `recommends`; harness-engineering is handled in prose until locked.
- `series.yaml: status` is `complete`: all thirty locked posts are drafted and no post is planned.
- No projects; the builds stay posts.

## Recorded divergences

- Titles: every sidecar title uses a middle-dot separator (`NN · Title`), twenty-eight are in title case, and ctx-001, ctx-005, ctx-019, ctx-025, ctx-028, ctx-029, and ctx-030 contain em-dashes; ctx-028 and ctx-029 contain `#`. Section 5 keeps them verbatim as the standard requires. The migration commit rewrites each to `NN - Sentence case title` and the body H1 to match.
- ctx-023: the sidecar title is "Security and Guardrails"; the body H1 and the README say "Security and prompt injection". The body title is the better one; the migration commit aligns the sidecar to it.
- Slugs: the sidecar `slug` differs from the directory name for ctx-010 (`10-data-ingestion-document-pipelines`), ctx-018 (`18-context-for-reasoning-models`), ctx-021 (`21-structured-output-and-guardrails`), ctx-022 (`22-observability-tracing-and-cost`), ctx-023 (`23-security-and-guardrails`), ctx-024 (`24-privacy-pii-data-governance`), ctx-028 (`28-build-rag-chatbot-from-scratch`), and ctx-029 (`29-build-mcp-server-from-scratch`). The directory names are canonical; the migration commit sets `slug` to the directory name.
- `prev` and `next` pointers in eleven sidecars name directories that do not exist (`05-context-lifecycle`, `14-system-prompts`, `18-context-evaluation`, `20-building-reliable-agents`, `19-memory-in-production`, `21-deployment-patterns`, `24-deployment-and-operations`, `24-inference-optimization`, `25-long-context-models`, `27-modern-agentic-workflow`, `29-multimodal-agent`). The keys are outside the schema and are dropped at migration; the website derives order from `series.yaml`.
- ctx-006 against the pre-lock plan: the plan's taxonomy was Breunig's (rot, poisoning, distraction, confusion, clash); the post renames clash to conflict, moves poisoning to ctx-023, and adds lost-in-the-middle and tool-storm. The post is canonical.
- ctx-009, ctx-011, ctx-017 against the pre-lock plan: the plan split select into "RAG done right" and "advanced RAG (HyDE, Self-RAG, CRAG, GraphRAG)"; the posts split it into the generalised select operation, the RAG pipeline with query-side patterns, and corpus-shape techniques (GraphRAG, ColBERT, SQL, long-context routing). Self-RAG and CRAG are named, not taught.
- ctx-015 and ctx-021 against the pre-lock plan: the plan had separate posts for tools and function calling, MCP end to end, and structured output; the posts merge tools and MCP into ctx-015 and give structured output and guardrails their own post, ctx-021.
- Companion code against the pre-lock plan: the plan promised code for ctx-006 (failure-mode notebooks), ctx-008 (a `task.md` runner), ctx-012 (a rolling-summary memory), ctx-013 (an orchestrator-worker example), and ctx-025 (a two-regime benchmark harness); none shipped as companions, and the posts carry inline snippets instead. Section 5 records those posts as `code optional`.
- The pre-lock plan's own numbering was inconsistent (two posts numbered 04 and 05 with the same thesis; Section 5 headings numbered 06 to 24 against a table numbered 01 to 30). The directory numbers are canonical and the plan is archived as `audits/plan-pre-lock.md`.
- ctx-017 carries `date: 2026-05-20`, earlier than ctx-016's 2026-05-24; dates are publication dates and are left alone.

# 10. Roadmap

All 30 posts are drafted; none is planned. Next, in order:

1. Lock commit: `Lock the curriculum`, tag `lock-1.0.0`. It adds `series.yaml`, this `plan.md`, `audits/plan-pre-lock.md`, the `id:` and `part:` sidecar edits, and removes `PLAN.md`.
2. Sidecar migration (`series-standard/tools/migrate_2_1_0.py` and a hand pass): unfence each sidecar, map `description` to `summary`, `last_modified` to `updated`, add `status: drafted`, `level`, `prerequisites`, `recommended`, `code`, and `outcomes` from Section 5 and each post's "After reading this you will be able to" list, rewrite titles to `NN - Sentence case`, set `slug` to the directory name, drop the keys outside the schema, and fix the ctx-023 title.
3. Body migration: bring every post onto the family body template (prerequisites line with a "Safe to skip?" test, sidecar outcomes verbatim, two "What to read next" bullets) and extract any assessment into `questions.json` banks.
4. Validate with `validate.py` without `--lock` until the layout, sidecar, and body stages pass; then set `status` per post and move the series to `maintained`.
5. Re-check dated prices, windows, and model names once a year; re-pin companion SDK versions after each check.
6. Once harness-engineering is locked, add its ids to ctx-013 and ctx-026 as `recommends` and bump the plan version.
