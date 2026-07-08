# Context Engineering — Free Blog Series

A complete, free, practitioner-grade series on **Context Engineering for LLMs and AI Agents**, expanded to cover everything the field has produced through early 2026.

This document is the **single source of truth** for the series:

- The repository layout
- The 30-post series outline (with thesis, sections, diagrams, code, and references for each post)
- The diagram system, writing style, and review checklist
- The list of reference assets (glossary, cheatsheet, reference-architecture poster)

When in doubt, edit this file *first*, then update the posts.

---

## 1. Goals & Audience

**Goal.** Produce the most complete free resource on context engineering, beautiful enough to be the default link people share when someone asks "how do I learn this?"

**Audience.** Three personas, all served by the same posts at different depths:

1. **Builders** — engineers shipping LLM-powered features who need patterns that work in production.
2. **Product / strategy** — PMs and founders who need accurate mental models without the math.
3. **Students / self-learners** — people who want a structured, free curriculum.

**Pedagogical principles.**
- Every post answers one question.
- Every post has at least one diagram and one runnable code snippet (or a link to one).
- Every claim that is non-obvious is cited.
- No marketing voice. Neutral, textbook tone.
- Examples come before formalism.
- **Framework-agnostic.** Examples are written in plain Python and direct provider SDKs first; a framework is shown only when it materially changes the shape of the code. No single framework is the protagonist of the series.

---

## 2. Repository Layout

```
context-engineering-series/
├── README.md                          # Series overview + table of contents
├── PLAN.md                            # This file (the master plan)
├── GLOSSARY.md                        # One-page glossary, alphabetised
├── CHEATSHEET.md                      # One-page printable PDF source
├── REFERENCES.md                      # Master bibliography (papers, blogs, talks)
├── CONTRIBUTING.md                    # Style guide, diagram standards, PR rules
├── LICENSE                            # CC-BY 4.0 for prose, MIT for code
│
├── assets/
│   ├── diagrams/
│   │   ├── src/                       # Editable sources (.excalidraw, .drawio, .svg, .mmd)
│   │   ├── exports/                   # Rendered SVG/PNG used by posts
│   │   └── style/                     # Shared palette, typography tokens, icon set
│   ├── images/                        # Screenshots, photos
│   ├── animations/                    # Lottie JSON / animated SVG / GIFs
│   └── poster/                        # Reference-architecture single-page SVG
│
├── posts/
│   ├── 01-why-context-engineering/
│   │   ├── index.md
│   │   ├── frontmatter.yaml           # slug, date, tags, hero, reading_time
│   │   ├── diagrams/                  # Post-specific diagram sources
│   │   └── snippets/                  # Inline code shown in the post
│   ├── 02-six-layers-of-context/
│   │   └── ...
│   ...
│   └── 24-capstone-email-reply-agent/
│
├── code/                              # Runnable companions; smaller ones have an offline-testable core
│   ├── 11-rag-from-scratch/           # Post 11 — chunk / BM25 / RRF
│   │   ├── README.md
│   │   ├── pyproject.toml
│   │   ├── .env.example
│   │   ├── src/
│   │   └── tests/
│   ├── 15-tool-schemas/              # Post 15 — token budget + schema validation
│   ├── 15-mcp-quickstart/           # Post 15 / 29 — ~60-line MCP server
│   ├── 20-eval-ragas/               # Post 20 — golden set / gate / judge
│   ├── 28-rag-chatbot/              # Post 28 — full build
│   ├── 29-mcp-server-full/          # Post 29 — full build
│   └── 30-email-reply-agent/        # Post 30 — capstone
│
├── templates/
│   ├── post-template.md               # Required headings, frontmatter shape
│   ├── diagram-style-guide.md         # Palette, stroke widths, fonts, examples
│   ├── code-readme-template.md
│   └── citation-style.md
│
└── tools/
    ├── render-diagrams.ps1            # Batch: .excalidraw/.mmd/.drawio -> SVG/PNG
    ├── lint-posts.ps1                 # Frontmatter, dead links, image alt-text
    ├── word-count.ps1                 # Per-post stats
    └── build-cheatsheet.ps1           # CHEATSHEET.md -> PDF
```

**Naming rule:** `posts/NN-kebab-case-slug/`. `NN` is a stable two-digit number. The slug never changes after publishing (URL stability).

---

## 3. The Series at a Glance

30 posts in 5 parts + 3 reference assets. Reading order is linear, but each part is also a useful standalone unit.

| #   | Part                       | Title (working)                                                                  |
| --- | -------------------------- | -------------------------------------------------------------------------------- |
| 01  | I — Foundations            | From Prompt Engineering to Context Engineering                                   |
| 02  | I                          | The Six Layers of an LLM's Context                                               |
| 03  | I                          | How LLMs Read Context — Tokens, Windows, Attention, Lost-in-the-Middle           |
| 04  | I                          | Tokens, Windows, and Budgets                                                     |
| 05  | I                          | The Economics of Context — Pricing, Prompt Caching, Latency                      |
| 06  | I                          | Five Context Failure Modes — Rot, Poisoning, Distraction, Confusion, Clash       |
| 07  | II — WSCI Operating System | The WSCI Framework — Write / Select / Compress / Isolate                         |
| 08  | II                         | WRITE Strategies — Scratchpads, `task.md`, Persistent Files, Plan Files          |
| 09  | II                         | SELECT Strategies — RAG Done Right                                               |
| 10  | II                         | Data Ingestion & Document Pipelines                                              |
| 11  | II                         | RAG in Depth — HyDE, Self-RAG, CRAG, GraphRAG, ColBERT/ColPali                   |
| 12  | II                         | COMPRESS Strategies — `/compact`, Summarisation, LLMLingua, Information Loss     |
| 13  | II                         | ISOLATE Strategies — Sub-agents, Parallelism, "Don't Build Multi-Agents"        |
| 14  | III — Layers in Depth      | System Prompt as Software — `CLAUDE.md` / `AGENTS.md` Anatomy                    |
| 15  | III                        | Tools and MCP — Function Calling, Model Context Protocol End-to-End              |
| 16  | III                        | Memory Systems — Episodic/Semantic/Procedural, Mem0/Letta/Zep                    |
| 17  | III                        | Advanced Retrieval                                                               |
| 18  | III                        | Context for Reasoning Models — Thinking Budgets and Traces                       |
| 19  | III                        | Multimodal Context — Images, PDF Pages, ColPali                                  |
| 20  | IV — Production            | Evaluation — Ragas, promptfoo, DeepEval, LLM-as-judge Pitfalls                   |
| 21  | IV                         | Structured Output & Guardrails — Constrained Decoding                            |
| 22  | IV                         | Observability, Tracing, and Cost — LangSmith, Langfuse, Phoenix, Helicone        |
| 23  | IV                         | Security — Prompt Injection, Indirect Injection via Tools / MCP                  |
| 24  | IV                         | Privacy, PII, and Governance — Retention and Tenant Isolation                    |
| 25  | IV                         | Long Context vs RAG — A Decision Framework (RULER, LongBench, BABILong, MRCR)    |
| 26  | V — Workflow & Builds      | The Modern Agentic Workflow — Claude Code, Skills, Sub-agents, Hooks             |
| 27  | V                          | Remote Agentic Workflow — EC2, VS Code SSH, tmux, OpenClaude, Telegram           |
| 28  | V                          | Build #1 — RAG Chatbot from Scratch                                              |
| 29  | V                          | Build #2 — MCP Server from Scratch                                               |
| 30  | V                          | Capstone — Email Reply Agent (Gmail API, Vercel, Railway, Evals)                 |

Reference assets shipped alongside:
- `GLOSSARY.md` — every term used in any post, alphabetised, one-line definitions.
- `CHEATSHEET.md` — single page: 6 layers, WSCI, failure modes, decision tree.
- `assets/poster/reference-architecture.svg` — single SVG showing every concept on one canvas; designed to print at A2.

---

## 4. Diagram System

Goal: posts should look like a small, beautifully designed book — not a Notion dump.

**Toolchain.**
- **Custom SVG** (hand-edited) for the canonical hero diagrams and any chart that benefits from precise control (e.g. lost-in-the-middle U-curve, token-cost charts).
- **Excalidraw** for hand-feel conceptual diagrams when the looser style helps comprehension.
- **Mermaid** for sequence diagrams and decision trees that benefit from being source-controllable as text.
- **draw.io** only when neither of the above fits.
- **Animated SVG / Lottie** for one or two key moments (e.g. context window filling and being compacted).

**Style tokens** (defined once in `assets/diagrams/style/tokens.json` and `tokens.css`):
- Palette: 1 primary, 1 accent, 3 neutrals, 1 alert. Colour-blind safe.
- Stroke: 1.5 px primary, 1 px secondary.
- Type: Inter for labels, JetBrains Mono for code.
- All diagrams sized for max 960 px display width with 2× retina export.
- Every diagram has dark-mode and light-mode variants.

**Required per diagram:**
- A short caption.
- An `alt` description for accessibility.
- The editable source committed alongside the export.

A canonical set of "hero" diagrams that recur across posts (drawn once, reused):
1. The Context Window Stack (6 layers) — used in 02, 06, 12, 15.
2. WSCI Quadrants — used in 06, 07, 08, 10, 11.
3. Lost-in-the-Middle U-curve — used in 02, 03, 19.
4. RAG Pipeline — used in 08, 09, 22.
5. MCP Triangle (Host / Client / Server) — used in 14, 23.
6. Sub-agent Isolation — used in 11, 20.
7. Prompt-cache token flow — used in 04, 17.
8. Memory taxonomy tree — used in 15.
9. Reference Architecture poster — used as a recurring "you are here" mini-map at the top of every post.

---

## 5. Per-Post Specs

Each spec below is the brief a writer (human or agent) needs to draft the post. Format:

> **Thesis** — one sentence the post must prove.
> **Sections** — H2 outline.
> **Diagrams** — what to draw.
> **Code** — what to ship in `code/NN-…/` if any.
> **References** — must-cite sources.

### Part I — Foundations

#### 01. From Prompt Engineering to Context Engineering
- **Thesis.** "Prompt engineering" was the right name for 2022–2023, but the work is now about engineering the *entire* set of tokens an LLM sees per call — a discipline with its own primitives.
- **Sections.** A short history (2022 prompt era → 2024 RAG era → 2025 agent era) · Definitions from Karpathy, Anthropic, IBM, Lance Martin, 12-Factor Agents · Why "context" subsumes "prompt" · The five jobs of a context engineer · What this series will and won't cover.
- **Diagrams.** (a) Timeline of the field 2022→2026. (b) Venn: Prompt ⊂ Context. (c) The five jobs as a small icon grid.
- **Code.** None.
- **References.** Karpathy tweet on context engineering; Anthropic "Effective context engineering" (2025); IBM Think article; Lance Martin "Context Engineering for Agents"; Dex Horthy "12-Factor Agents".

#### 02. The Six Layers of an LLM's Context
- **Thesis.** Every LLM call is a stack of six well-defined layers; engineering the call means engineering each layer and the order they appear in.
- **Sections.** What an LLM literally receives · Layer 1 System prompt · Layer 2 Tools/MCP descriptions · Layer 3 Memory/state · Layer 4 RAG/retrieved context · Layer 5 Conversation history · Layer 6 User instruction · Why order matters (priority + lost-in-the-middle preview) · A pragmatic mental model.
- **Diagrams.** (a) Hero — Context Window Stack with priority arrows and a "U-curve" overlay. (b) A small "X-ray" of a real Claude API call.
- **Code.** Tiny script that prints a real assembled context for one user query.
- **References.** Anthropic API docs; OpenAI API docs; Liu et al. 2023 "Lost in the Middle".

#### 03. How LLMs Read Context — Tokens, Windows, Attention, Lost-in-the-Middle
- **Thesis.** A context window is not a bucket — it's a sequence the model attends to non-uniformly, and that non-uniformity dictates how you should pack it.
- **Sections.** Tokenisation (BPE in 2 minutes, why "strawberry" has 3 R's matters) · The shape of a context window · Attention in plain English · Lost-in-the-middle (Liu et al.) · Needle-in-a-haystack (Greg Kamradt) · Why "200k context" ≠ "200k useful context" · Practical rules of thumb (keep effective context 50k–100k, put the question last).
- **Diagrams.** (a) BPE animation for one word. (b) Lost-in-the-Middle U-curve, redrawn cleanly with citation. (c) NIAH heatmap, simplified.
- **Code.** `tiktoken` snippet showing tokens for the same sentence across families.
- **References.** Liu et al. 2023; Kamradt NIAH; Anthropic NIAH replies; Chroma "Context Rot".

#### 04. The Economics of Context — Tokens, Pricing, Prompt Caching, Latency
- **Thesis.** Every architectural decision in context engineering is also an economic decision; ignoring the cost curve produces beautiful demos that can't ship.
- **Sections.** Cost-per-1k tokens table (Claude/GPT/Gemini, late-2025 prices) · Input vs output asymmetry · Prompt caching (Anthropic, OpenAI, Gemini) — what it is, what it doesn't cache, why it changes the architecture · Latency budget for an agent turn · Worked example: same agent, three pricing models · Cost guardrails to ship.
- **Diagrams.** (a) Cost-per-call breakdown stacked bar (system / tools / memory / RAG / history / user). (b) Prompt-cache token-flow with hit vs miss. (c) Latency waterfall.
- **Code.** Cost calculator (Python) given a turn's token breakdown.
- **References.** Anthropic prompt caching docs; OpenAI prompt caching docs; Gemini context caching docs; Manus blog (KV-cache section).

#### 05. The Economics of Context — Pricing, Prompt Caching, Latency
- **Thesis.** Every architectural decision in context engineering is also an economic one; ignoring the cost curve produces beautiful demos that can't ship.
- **Sections.** Cost-per-1k-token table (Claude/GPT/Gemini) · Input vs output asymmetry · Prompt caching — what it caches, what it doesn't, why it reshapes the architecture · Latency budget for an agent turn · Worked example: one agent under three pricing models · Cost guardrails to ship.
- **Diagrams.** (a) Cost-per-call stacked bar by layer. (b) Prompt-cache token flow, hit vs miss. (c) Latency waterfall.
- **References.** Anthropic prompt caching docs; OpenAI prompt caching docs; Gemini context caching docs; Manus blog (KV-cache section).

#### 06. Five Context Failure Modes — Rot, Poisoning, Distraction, Confusion, Clash
- **Thesis.** Context degrades in five distinct ways; naming them is the first step to debugging an agent that "used to work".
- **Sections.** Drew Breunig's taxonomy in detail · Chroma's "context rot" findings · How each failure mode shows up in a coding agent vs a customer-support agent · Detection signals · Mitigations mapped to WSCI · A debug checklist.
- **Diagrams.** (a) Five-panel "before/after" of each failure mode. (b) Decision tree: symptom → likely failure mode → WSCI mitigation.
- **Code.** Reproducible failure-mode notebooks (one per mode, small synthetic prompts).
- **References.** Breunig "How Long Contexts Fail"; Chroma "Context Rot"; RULER; MRCR.

### Part II — The WSCI Operating System

#### 06. The WSCI Framework
- **Thesis.** Every operation a context engineer performs is one of four primitives: Write, Select, Compress, Isolate.
- **Sections.** Origin (LangChain) · Each primitive defined formally · Mapping the six layers onto WSCI · A worked trace of one Claude Code session through WSCI · How the rest of Part II is organised.
- **Diagrams.** Hero — WSCI Quadrants. A trace diagram showing one Claude Code session annotated with W/S/C/I events.
- **Code.** None.
- **References.** LangChain "Context Engineering" essay; Lance Martin.

#### 07. WRITE — Scratchpads, `task.md`, Persistent Files, Plan Files
- **Thesis.** When something might be needed later but not now, write it to disk; the filesystem is your cheap, durable extension to the context window.
- **Sections.** Three things you typically write (scratchpads, plans, persistent memory) · `task.md` patterns from Claude Code · Spec-driven development · The `.skills/` directory · When to write to a vector store vs a flat file · Anti-patterns.
- **Diagrams.** Filesystem-as-context diagram. A `task.md` lifecycle.
- **Code.** Minimal `task.md` runner.
- **References.** Claude Code docs; GitHub `Specify`; Manus blog (append-only history); 12-Factor Agents.

#### 08. SELECT (Part 1) — RAG Done Right
- **Thesis.** RAG is the dominant Select primitive; doing it well is mostly a matter of good chunking, good embeddings, and a reranker.
- **Sections.** What RAG is in WSCI terms · Chunking (fixed / recursive / semantic / parent-child / late chunking) · Embedding models in 2026 · Vector DBs in 2 paragraphs · Hybrid search (BM25 + dense) · Reranking (Cohere, BGE, Voyage) · Anthropic Contextual Retrieval (the +49% trick) · Putting it together.
- **Diagrams.** Hero — RAG Pipeline. Chunking strategies side-by-side. Hybrid search Venn. Contextual Retrieval before/after.
- **Code.** `code/11-rag-from-scratch/` — a runnable RAG chatbot, modernised with hybrid search + reranker + contextual retrieval.
- **References.** Anthropic Contextual Retrieval (Sept 2024); Jina late chunking; Cohere Rerank docs; Voyage embeddings.

#### 10. Data Ingestion & Document Pipelines
- **Thesis.** Retrieval quality is capped by ingestion quality; parsing, OCR, table handling, and provenance are where most RAG systems silently lose accuracy.
- **Sections.** The ingestion pipeline end-to-end · File formats and parsers (PDF, HTML, DOCX, slides) · OCR and layout-aware extraction · Tables and figures — the hard cases · Metadata and provenance (source, page, timestamp) · Deduplication and incremental re-indexing · Ingestion evals.
- **Diagrams.** (a) Ingestion pipeline from raw file to indexed chunk. (b) Layout-aware parse of a table-heavy page. (c) Provenance metadata flowing through to a citation.
- **References.** Unstructured docs; Docling; LlamaParse; Nougat/OCR papers; Anthropic Contextual Retrieval (provenance angle).

#### 09. SELECT (Part 2) — Advanced RAG
- **Thesis.** When vanilla RAG isn't enough, six named patterns cover almost every real failure: HyDE, query rewriting, agentic RAG, Self-RAG, CRAG, GraphRAG.
- **Sections.** When vanilla RAG breaks · HyDE · Query rewriting / decomposition · Agentic RAG · Self-RAG · Corrective RAG (CRAG) · GraphRAG (Microsoft) · Multimodal retrieval — ColBERT / ColPali · A decision tree for picking one.
- **Diagrams.** One mini-architecture diagram per pattern, drawn in the same visual language. A decision tree at the end.
- **Code.** A small notebook per pattern.
- **References.** HyDE paper; Self-RAG paper; CRAG paper; Microsoft GraphRAG; ColBERT/ColPali papers.

#### 10. COMPRESS — `/compact`, Summarisation, LLMLingua, Information Loss
- **Thesis.** Compression buys context-window space at the price of fidelity; doing it well means knowing what you're allowed to lose.
- **Sections.** Why compress · `/compact` vs `/clear` in Claude Code · Auto-compaction thresholds · Summarisation strategies (rolling, hierarchical, structured) · LLMLingua / LLMLingua-2 / RECOMP · Information-loss budget · When compression is the wrong answer (hint: when Isolate is the right one).
- **Diagrams.** Context-window timeline with `/compact` event. Summarisation strategies side-by-side. LLMLingua before/after token view.
- **Code.** A rolling-summary memory implementation.
- **References.** LLMLingua paper; RECOMP; Claude Code docs.

#### 11. ISOLATE — Sub-agents, Parallelism, "Don't Build Multi-Agents"
- **Thesis.** Isolation is powerful and dangerous; the right default is a single agent with sub-tasks, and multi-agent designs need a real reason.
- **Sections.** What isolation means at the context level · Sub-agents in Claude Code · Parallel vs serial sub-agents · Shared files as the inter-agent bus · Anthropic "Building Effective Agents" patterns (workflow vs agent) · Cognition's "Don't Build Multi-Agents" — the steelman · A decision framework.
- **Diagrams.** Hero — Sub-agent Isolation (parent + isolated children + shared files). Workflow vs agent patterns gallery. Decision tree.
- **Code.** A small orchestrator-worker example, written without a framework.
- **References.** Anthropic "Building Effective Agents" (Dec 2024); Cognition "Don't Build Multi-Agents"; Claude Code sub-agent docs.

### Part III — Layers in Depth

#### 12. System Prompts — `CLAUDE.md` / `AGENTS.md` Anatomy
- **Thesis.** A good system prompt is five named sections; treating it as freeform prose is the most common mistake.
- **Sections.** The five sections (Identity, Rules, Format, Knowledge, Tools) with examples · The fluid boundaries (rules vs format, knowledge vs format) · `CLAUDE.md` vs `AGENTS.md` vs Cursor `.cursorrules` vs OpenAI `instructions` · Sectioning long system prompts so only relevant parts load · Anti-patterns.
- **Diagrams.** Five-section anatomy diagram. A real-world `CLAUDE.md` annotated.
- **Code.** Example `CLAUDE.md` files for three different agents (coding, support, research).
- **References.** Anthropic Claude Code docs; OpenAI Agents SDK docs.

#### 13. Tools, Function Calling, and Structured Output
- **Thesis.** A tool is a contract written in tokens; good schemas teach the model when *not* to call you.
- **Sections.** Function calling refresher · Tool schema as token cost · Naming and descriptions that survive · Structured output (JSON Schema, Pydantic, Outlines, Instructor) · Constrained decoding · When to prefer "response_format" over a tool · Tool-loadout strategies for >20 tools.
- **Diagrams.** Tool-schema → tokens diagram. JSON-Schema vs free-form output reliability chart.
- **Code.** A tools-as-token-budget calculator. A minimal structured-output example using each major provider's native API.
- **References.** OpenAI structured outputs; Anthropic tool use docs; Outlines paper.

#### 14. MCP — Model Context Protocol End-to-End
- **Thesis.** MCP standardises *how* a tool exposes itself, which decouples LLM choice from tool choice; understanding host/client/server is enough to use 90% of it.
- **Sections.** The problem MCP solves · Host vs Client vs Server · Transports (stdio, HTTP/SSE) · Resources vs Tools vs Prompts · Anatomy of a minimal MCP server · Anatomy of an MCP client integration · Security considerations (bridges to post 18) · The MCP ecosystem in 2026.
- **Diagrams.** Hero — MCP Triangle. Sequence diagram for a tool call. Anatomy of a server.
- **Code.** `code/15-mcp-quickstart/` — a 50-line server.
- **References.** MCP spec; Anthropic MCP launch post; community MCP registry.

#### 15. Memory — Short-term, Long-term, Episodic, Semantic, Procedural
- **Thesis.** "Memory" is a family of orthogonal capabilities; an agent that "remembers things" usually needs three of them, not one.
- **Sections.** Statelessness of LLMs · Short-term vs long-term · Episodic vs semantic vs procedural (cog-sci borrowing, applied) · Vector-based memory (Mem0) · Graph-based memory (Zep / Graphiti) · Letta / MemGPT · ChatGPT's "memories" feature, decoded · How to choose.
- **Diagrams.** Hero — Memory taxonomy tree. A side-by-side of vector vs graph memory for the same conversation.
- **Code.** A minimal Mem0-style memory layer in ~80 lines.
- **References.** MemGPT/Letta paper; Mem0 docs; Zep/Graphiti paper; OpenAI memory product post.

#### 18. Context for Reasoning Models — Thinking Budgets and Traces
- **Thesis.** Reasoning models spend a thinking budget before answering, and that budget is a new context resource to engineer, not just a knob to max out.
- **Sections.** What "reasoning"/"thinking" models actually do · Thinking budgets and effort levels · What belongs in the prompt vs what the model should derive · Reading and using reasoning traces · Interleaved thinking with tool calls · Cost and latency of thinking tokens · When a reasoning model is the wrong tool.
- **Diagrams.** (a) Thinking-budget flow from prompt to trace to answer. (b) Accuracy vs thinking-token curve with a plateau. (c) Interleaved thinking and tool-call timeline.
- **References.** Anthropic extended thinking docs; OpenAI reasoning models guide; DeepSeek-R1 paper; "Let's Verify Step by Step".

#### 19. Multimodal Context — Images, PDF Pages, ColPali
- **Thesis.** Not all context is text; images, rendered PDF pages, and screenshots are first-class context that changes how you retrieve and pack a window.
- **Sections.** How vision-language models tokenise images · When to send an image vs its extracted text · PDF-page-as-image retrieval · ColPali / visual document retrieval · Screenshots for computer-use agents · Cost of image tokens · Multimodal evals.
- **Diagrams.** (a) Image-to-tokens illustration. (b) Text-parse vs page-as-image retrieval, side by side. (c) ColPali late-interaction over page patches.
- **References.** ColPali paper; Anthropic vision docs; OpenAI/Gemini image-input docs; "screenshots beat parsing" studies.

### Part IV — Production-Grade Practice

#### 16. Evaluation — Ragas, promptfoo, DeepEval, LLM-as-judge Pitfalls
- **Thesis.** Eval is the only thing that turns context engineering from craft into engineering; without evals, every change is vibes.
- **Sections.** Why evals are the bottleneck · Offline vs online · Golden sets · Ragas for RAG · promptfoo for prompts · DeepEval for general · LLM-as-judge — the pitfalls (position bias, verbosity bias, self-preference) · Pairwise vs absolute · CI integration.
- **Diagrams.** Eval pipeline diagram. Pitfall illustrations for LLM-as-judge.
- **Code.** `code/20-eval-ragas/` — full eval suite over the post-08 RAG bot.
- **References.** Ragas paper/docs; promptfoo docs; "Judging LLM-as-a-judge" paper; LMSYS arena.

#### 21. Structured Output & Guardrails — Constrained Decoding
- **Thesis.** Free-form text is a liability in production; constrained decoding and guardrails turn model output into a contract you can rely on downstream.
- **Sections.** Why structured output · JSON Schema, Pydantic, Outlines, Instructor · Constrained/grammar-based decoding under the hood · Native `response_format` vs tool-calling for structure · Guardrails — validation, retries, and repair · Input and output guardrails (topic, safety, PII) · Failure handling when the schema can't be met.
- **Diagrams.** (a) Constrained-decoding token mask illustration. (b) Free-form vs schema-constrained reliability chart. (c) Guardrail pipeline: input → model → validate → repair.
- **References.** OpenAI structured outputs; Anthropic tool use docs; Outlines paper; Guardrails AI / NeMo Guardrails docs.

#### 17. Observability, Tracing, and Cost
- **Thesis.** You cannot improve what you cannot see; tracing every call is non-negotiable past prototype.
- **Sections.** What to log (inputs, outputs, tokens, latency, tool calls, sub-agent spans) · LangSmith · Langfuse (open source) · Phoenix (Arize) · Helicone · Braintrust · Cost dashboards · Replays and regression detection · A minimal OTel-based DIY stack.
- **Diagrams.** A trace tree for one agent turn. Cost dashboard mock.
- **Code.** Langfuse + OTel hello-world.
- **References.** LangSmith / Langfuse / Phoenix / Helicone docs; OpenTelemetry GenAI semconv.

#### 18. Security — Prompt Injection, Indirect Injection via Tools / MCP
- **Thesis.** Any input that reaches the context window is executable; tools and MCP make this dangerous in ways most teams don't audit.
- **Sections.** Direct vs indirect prompt injection · The data-exfiltration pattern · Real-world incidents (catalogue) · MCP-specific risks · Defence in depth (allow-lists, sandboxing, dual-LLM, output filtering) · Threat-model template.
- **Diagrams.** Indirect-injection sequence diagram. Defence-in-depth layered diagram.
- **Code.** A deliberately vulnerable agent + the patched version.
- **References.** Simon Willison's prompt-injection corpus; OWASP LLM Top 10; Anthropic safety docs.

#### 24. Privacy, PII, and Governance — Retention and Tenant Isolation
- **Thesis.** Every token you retrieve, log, or cache is data you now govern; privacy and tenant isolation are context-engineering concerns, not a compliance afterthought.
- **Sections.** PII in prompts, retrieval, and traces · Detection and redaction before the model sees it · Data retention and deletion (right-to-be-forgotten across a vector store) · Multi-tenant isolation — per-tenant indexes, filters, and key scoping · Provider data-use and zero-retention modes · Regional and residency constraints · A governance checklist.
- **Diagrams.** (a) PII flow with redaction gates on ingest, prompt, and log. (b) Multi-tenant isolation boundary across index, cache, and traces. (c) Retention/deletion lifecycle.
- **References.** OWASP LLM Top 10 (sensitive-information disclosure); NIST AI RMF; provider data-processing/zero-retention docs; Microsoft Presidio.

#### 19. Long Context vs RAG — A Decision Framework
- **Thesis.** Long context did not kill RAG; the choice between them is a function of recall depth, freshness, cost, and audit needs.
- **Sections.** State of long context (Gemini 2M, Claude 1M, GPT-4.1) · Benchmarks beyond NIAH (RULER, LongBench, BABILong, MRCR) · Where long context wins · Where RAG wins · Hybrid patterns (long-context-then-RAG, RAG-then-long-context) · A decision tree.
- **Diagrams.** Benchmark comparison chart. Decision tree.
- **Code.** A small benchmark harness running the same task under both regimes.
- **References.** RULER paper; LongBench; BABILong; MRCR; Gemini long-context papers.

### Part V — Workflow & Builds

#### 20. The Modern Agentic Workflow — Claude Code, Skills, Sub-agents, Hooks
- **Thesis.** Claude Code 2.x is a small operating system for agentic work; using it well means knowing skills, sub-agents, hooks, and slash commands.
- **Sections.** Installation refresher · Project layout (`CLAUDE.md`, `.claude/`, `.skills/`) · Global vs local skills · Sub-agents · Hooks · Slash commands · Plan mode and spec-driven dev · Output styles.
- **Diagrams.** Project-layout map. Skills resolution order diagram.
- **Code.** A reference `.claude/` skeleton repo.
- **References.** Claude Code docs; Anthropic skills launch.

#### 21. Remote Agentic Workflow — EC2, VS Code SSH, tmux, OpenClaude, Telegram
- **Thesis.** The agent should keep working when you close the laptop; a small remote setup pays for itself in a week.
- **Sections.** Why remote · EC2 setup (AMI, security groups, IAM) · VS Code SSH · tmux essentials · OpenClaude / CCO · Telegram bridge · Cost guardrails · A reproducible setup script.
- **Diagrams.** Network diagram. tmux session map.
- **Code.** Bash + Terraform skeleton.
- **References.** OpenClaude / CCO repos; AWS docs.

#### 22. Build #1 — RAG Chatbot from Scratch
- **Thesis.** A production-leaning RAG chatbot is ~500 lines if you've internalised Posts 08–09 and 16.
- **Sections.** Spec · Architecture · Data ingestion · Retrieval pipeline · Generation · Eval · Deployment · What we deliberately left out.
- **Diagrams.** End-to-end architecture. Sequence diagram of a single chat turn.
- **Code.** `code/28-rag-chatbot/` — full repo with tests and a one-command demo.
- **References.** Posts 08, 09, 16.

#### 23. Build #2 — MCP Server from Scratch
- **Thesis.** Writing an MCP server is small and teaches you the protocol better than any blog post; this is that build.
- **Sections.** Spec · Choice of transport · Implementing tools/resources/prompts · Testing with Claude Desktop · Publishing.
- **Diagrams.** Server-internals diagram. Test-loop sequence.
- **Code.** `code/29-mcp-server-full/`.
- **References.** Post 14; MCP spec.

#### 24. Capstone — Email Reply Agent
- **Thesis.** Putting all six layers, all four WSCI primitives, and a real eval suite into one product, end-to-end.
- **Sections.** Product spec · Gmail API setup · Backend (Python/FastAPI) · Frontend (Next.js on Vercel) · DB on Railway · Memory of past replies · Eval suite · Deployment · What to ship next.
- **Diagrams.** Product architecture. Data-flow diagram. Memory schema.
- **Code.** `code/30-email-reply-agent/` — production-shaped repo.
- **References.** Posts 12, 13, 15, 16, 17.

---

## 6. Reference Assets

### `GLOSSARY.md`
Every term used anywhere in the series, alphabetised, one or two lines each. Linked from the first occurrence in every post. Examples: *agentic RAG, attention, BM25, chunking, compaction, context window, context rot, contextual retrieval, embedding, function calling, GraphRAG, HyDE, isolate, KV cache, lost-in-the-middle, MCP, Mem0, MRCR, NIAH, prompt caching, rerank, RULER, scratchpad, Self-RAG, sub-agent, system prompt, WSCI*…

### `CHEATSHEET.md`
Single page, designed to be saved as a wallpaper / printed:
- The 6 layers (with order).
- WSCI four-quadrant.
- Failure-mode taxonomy.
- Long-context-vs-RAG decision tree.
- A "first-aid" debug checklist.

### `assets/poster/reference-architecture.svg`
A single A2-printable SVG that places every concept on one canvas — system prompt, tools/MCP, memory, RAG, conversation history, user prompt, sub-agents, observability, evals, security boundary. Becomes the recurring "you are here" mini-map shown at the top of each post.

---

## 7. Style Guide (short version)

- Voice: **third person, neutral, textbook**. Never "I", never "we" except in code-along sections.
- Sentences: short. Paragraphs: 2–4 sentences.
- Define every acronym on first use, in every post (don't assume linear reading).
- Inline citations as numbered footnotes; full bibliography in `REFERENCES.md`.
- Code: runnable, with `requirements.txt` / `pyproject.toml`. Use up-to-date official SDKs (Anthropic, OpenAI, Google) and the MCP reference SDK. The series is **framework-agnostic**: examples are written in plain Python first, then optionally shown in a popular framework only when the framework genuinely changes the shape of the code. No single framework is the protagonist.
- Every post starts with: a 2-sentence TL;DR, an estimated reading time, a list of the 3–5 things the reader will be able to do after.
- Every post ends with: a "Common pitfalls" block, a "Further reading" block, and a "What to read next" pointer.

---

## 8. Build & Review Workflow

1. **Spec lock.** A post is only written after its spec in §5 is reviewed and pinned.
2. **Diagram-first.** Diagrams are drafted before prose; prose adapts to the diagram, not the other way around.
3. **Draft → review → diagram polish → code → eval pass.** Each post passes a five-step gate.
4. **Lint.** `tools/lint-posts.ps1` enforces frontmatter, alt-text, dead links.
5. **Cross-link.** Every post links forward to at least one upcoming post and back to at least one prior post; the linker script verifies coverage.
6. **License.** Prose CC-BY 4.0, code MIT.

---

## 9. Decisions

1. **Publishing order.** Strict numerical for the canonical reading path. Posts ship to the site **a Part at a time** once each Part is fully drafted and its diagrams polished — readers always consume a coherent unit, and the project never waits for all 30 to be perfect before anything goes live.
2. **Companion repo.** Hosted under the author's personal GitHub.
3. **Cadence.** All 30 posts and the companion code are produced together; cadence is determined by readiness of each Part, not a fixed weekly schedule.
4. **Mailing list / RSS.** Out of scope; handled by the author's site.
5. **Translation.** English only for v1.
6. **Series expansion.** Six posts (05, 10, 18, 19, 21, 24) were added after the initial 24-post plan, and the whole series was renumbered so that reading-order still equals post number.

---

## 10. Immediate Next Actions

1. Scaffold the repository per §2 (empty folders, templates, lint scripts).
2. Produce the nine canonical hero diagrams listed in §4.
3. Draft `GLOSSARY.md` and `CHEATSHEET.md` skeletons.
4. Write Post 01 and Post 02 in full as the style-locking pair.
5. Lock the visual system on those two posts before writing Posts 03+.
