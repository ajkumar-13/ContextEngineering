# 07 · Write strategies

> **TL;DR.** *Write* is the operation that puts information **somewhere other than the live prompt**, so it can be recovered later without paying token cost on every call. The four destinations that matter in practice are **memory stores**, **scratchpads**, **repository documentation files** (`AGENTS.md`, `CLAUDE.md`, `skill.md`), and **embedding indexes**. This post takes each in turn: what it is, when to write to it, what to record alongside the data, and the failure modes peculiar to each.
>
> **Reading time:** ~12 minutes.
>
> **After reading this you will be able to:**
> - Choose the right write destination for a given piece of information.
> - Specify the metadata fields every memory or scratchpad row needs to remain useful.
> - Avoid the three classes of bug that turn a useful memory store into an active liability.

---

## 1. Why writing is hard

Writing is mechanically the easiest of the four WSCI operations: append a row, save a file, post to an index. The hardness is governance. Anything you write becomes data that some future call will trust. A memory entry with no provenance is indistinguishable from a poisoned one ([Post 05](../05-context-failure-modes/index.md), §2). A `CLAUDE.md` that has not been reviewed in six months silently shapes every code generation forever.

The discipline that prevents this can be summarised in a single rule: **every write must include metadata.** At minimum: who wrote it, when, from what source, with what confidence. The rest of this post applies that rule to four different destinations.

---

## 2. Memory stores

![Episodic, semantic, procedural memory taxonomy](../../assets/diagrams/exports/08-memory-taxonomy.svg)

A memory store is the persistent counterpart to the in-prompt memory layer ([Post 14](../14-memory-systems/index.md)). It holds three kinds of data, often in three different tables:

- **Episodic** — events with a timestamp. *"User X resolved ticket Y on 14 March by escalating to engineering."*
- **Semantic** — facts and preferences. *"User X prefers replies in formal English; uses Postgres in production."*
- **Procedural** — rules and how-tos. *"When refund > $1 000, route to manager queue."*

The three classes have different write patterns, lifetimes, and access policies. Storing them in one undifferentiated bag is the most common mistake.

**The minimum row schema.** Whatever store you use (a SQL table, a document database, a vector index with metadata fields), every row should carry:

| Field | Why |
|---|---|
| `id` | Stable reference for updates and deletes |
| `kind` | `episodic` / `semantic` / `procedural` — different decay and access rules |
| `subject` | The entity the memory is about (user id, project id, agent id) |
| `content` | The fact itself, in whatever representation you use to recall it |
| `source` | Where the fact came from (URL, tool name, conversation id) |
| `created_at` | Timestamp of the original write |
| `last_accessed_at` | Updated on every read; drives decay |
| `confidence` | 0–1; lowers as facts age unconfirmed; gates whether the agent asserts vs. asks |
| `expires_at` | Optional; some facts are knowingly short-lived ("user is on holiday until 1 May") |

**When to write.** Three triggers cover the majority of cases: at the **end of a session** (summarise what the user told you today), on **explicit user assertion** ("remember that I work in PST"), and on **observed contradiction** (the agent's stored fact disagrees with this turn's evidence — write the new version, do not silently overwrite the old one; conflict resolution is its own operation).

**When not to write.** Tool results are not memories. Conversation history is not a memory. Both are *transient* and live in their own layer. If a tool call returns "current temperature in Mumbai is 32°C", writing it to long-term semantic memory will poison the next refrigerator-sized question.

**Decay.** The simplest scheme that works: drop `confidence` by a small amount on every day without access; demote to a colder tier (or delete) below a threshold. The agent should *ask before asserting* anything below ~0.6.

---

## 3. Scratchpads

A scratchpad is a short-lived, write-mostly destination used by a single agent or sub-agent to externalise its working memory across iterations. The simplest scratchpad is a Markdown file the agent appends to between tool calls: *"I have looked at files A and B. I still need to check C. The most likely root cause is X."*

Scratchpads matter because they decouple two questions that the prompt would otherwise conflate:

- "What does the agent need to *remember* across the next few iterations?" (goes to scratchpad)
- "What does the model need *in this prompt* to make the next decision?" (stays in context)

Without a scratchpad, the agent must keep the working state in conversation history, where it competes with everything else for attention and budget.

**Three scratchpad patterns** that recur:

- **Plan + checklist.** A top-of-task plan with checkboxes. Each iteration ticks the items it completed and re-reads the plan. Used heavily by coding agents.
- **Findings log.** Append-only notes during a research task. The orchestrator can compress the log later without losing the trail.
- **Hypothesis stack.** A debugging agent writes its current hypothesis, the evidence for and against, and the next test. When the hypothesis is disproved, it pops the stack instead of forgetting.

The implementation does not need to be fancy. A file per task, named after the task id, in a `.scratch/` folder, is enough. The agent gets read and write tools scoped to that folder; everything else is convention.

---

## 4. Repository documentation: `AGENTS.md`, `CLAUDE.md`, `skill.md`

This is the **most underrated write destination in the field** and the one that pays the largest compounding return.

`AGENTS.md` (the Linux Foundation–backed cross-vendor convention adopted by Codex, Cursor, Aider, Continue, and others) and the platform-specific `CLAUDE.md` (Anthropic's Claude Code) are plain Markdown files that live alongside the code. The host loads them at session start and prepends the relevant sections to every call. The files are *checked into the repository* — they are reviewed, version-controlled, and diffed like code.

The convention is recursive: a top-level `AGENTS.md` describes the project; subdirectory-specific `AGENTS.md` files override or refine for that subdirectory; the deepest matching file wins. This lets a monorepo carry one set of rules for the front-end, a different set for the data pipelines, and a third for the documentation, without any layer drowning the others.

A typical `AGENTS.md` has five blocks (the same five as the system prompt, [Post 12](../12-system-prompt-as-software/index.md)):

1. **Identity** — what this codebase is, in one paragraph.
2. **Rules** — testing requirements, commit conventions, what *not* to refactor.
3. **Format** — how to cite files, how to write commit messages, how to lay out responses.
4. **Knowledge** — the build commands, the deploy commands, the names of the key modules.
5. **Tools / commands** — slash commands the agent can invoke, MCP servers configured for this project.

**`skill.md` files** are a more specialised variant: a single skill (e.g., "review a Terraform diff", "draft a PR description in our house style") packaged as a Markdown file with its own rules and few-shot examples, loaded only when the agent decides it needs that skill. The community has assembled marketplaces of these files; the value is partly the content and partly the *pattern* (one file per concern, loaded conditionally).

Three rules of thumb that come from teams running these in production:

- **Keep the file under ~500 lines.** The host is going to load most of it on every relevant call. A 5 000-line `CLAUDE.md` makes the cached prefix huge and the system prompt unreadable to humans.
- **Iterate from minimal.** Anthropic's own guidance, repeated across their writing, is to start with a near-empty file and add rules *only when a real failure motivates them*. Speculative rules contradict each other.
- **Review every change like code.** A diff that adds a new rule deserves the same scrutiny as a diff that adds an `if` statement, because that is what it is.

This destination is the one that turns "agentic engineering" from a bag of tricks into something approaching a real software discipline.

---

## 5. Embedding indexes — the offline write side of RAG

Every RAG system has two halves: an *online* read path that retrieves at inference time (covered in [Post 09](../09-rag-in-depth/index.md)), and an *offline* write path that prepares the corpus. The write side is where the quality is decided.

The minimum write pipeline:

1. **Source collection.** Pull the canonical version of every document. Keep a hash; re-index on change.
2. **Cleaning.** Strip boilerplate (navigation, footers, marketing), normalise whitespace, fix encoding.
3. **Chunking.** Split into chunks of 200–800 tokens, with 10–20 % overlap between adjacent chunks. Sentence-aware splitters beat fixed-length ones for prose; code is best split by symbol.
4. **Enrichment.** Prepend a short *contextual header* to each chunk (the document title and section path, sometimes a 1–2 sentence summary of the parent document — Anthropic's "contextual retrieval" trick). This single step often improves retrieval recall by 30–50 %.
5. **Embedding.** Run each chunk through an embedding model. Store the vector alongside the chunk text and metadata.
6. **Indexing.** Insert into a vector store (FAISS, Chroma, pgvector, Pinecone, Weaviate). Keep a parallel keyword index — hybrid search beats either alone.
7. **Manifest.** Write a manifest row per source: its hash, the chunks it produced, the embedding model version, the timestamp.

**Metadata to attach to every chunk** (in addition to the vector and the text): `source_id`, `source_url`, `chunk_index`, `tokens`, `created_at`, `embedding_model`. Without these, you cannot answer "where did this answer come from?" and you cannot re-index when an upstream document changes.

The most common write-side mistake is to **embed the wrong unit of text**. A 5 000-token document is too coarse — retrieval returns 5 000 tokens to land on one paragraph. A 50-token snippet is too fine — the model gets a fragment without enough context to use it. Aim for a chunk that is self-contained when read alone.

The second most common mistake is to **never re-index**. Documents change; embedding models improve; the chunker you used in month one had a bug. Treat the index the way you treat a database: backed up, versioned, and rebuildable from source.

---

## 6. The "what to write where" cheat sheet

| Information | Destination | Lifetime |
|---|---|---|
| User said "I prefer markdown tables" | Memory store, kind=`semantic` | Months, decays |
| User resolved ticket #4321 yesterday | Memory store, kind=`episodic` | Weeks-months |
| Refund > $1 000 → manager queue | `AGENTS.md` rules block | Until the policy changes |
| Build command is `pnpm run build:prod` | `AGENTS.md` knowledge block | Until the build changes |
| The 200-page product manual | Embedding index | Until the manual changes |
| "I need to remember to check file C" (mid-task) | Scratchpad | Lifetime of this task |
| Tool returned `temperature: 32` | **Nothing.** It is transient. | — |
| "My API token is sk-…" | **Nothing.** Secrets never enter writable stores. | — |

The last two rows are the operational heart of this post. Most production incidents traceable to "weird agent behaviour months later" begin with someone writing transient or sensitive data into a long-lived store.

---

## Common pitfalls

- **Writing without provenance.** A memory cell with no `source` is unrecoverable when it turns out to be wrong.
- **Letting `AGENTS.md` grow without review.** Each new rule is a load-bearing change to every future call.
- **Embedding without re-indexing.** A six-month-old index drifts further from the current source corpus every day.
- **Using the memory store as a cache for tool results.** Tool results are deterministic; re-call them. Caching them as memories pollutes long-term recall with stale data.
- **Storing secrets in any writable store.** Secrets belong in a secret manager, fetched per call.
- **One mega-store for episodic + semantic + procedural.** They have different access patterns and different decay rules. Three small tables beat one big one.

---

## Further reading

- Anthropic Engineering, *"Building effective AI agents"* (2024) — agentic memory patterns.
- LangChain Blog, *"The state of AI agents — memory"* (2024) — episodic / semantic / procedural taxonomy.
- Anthropic Engineering, *"Contextual retrieval"* (2024) — the chunk-enrichment trick from §5.
- agents.md project, *"AGENTS.md spec"* (2025) — the cross-vendor convention.
- Park, J. *et al.*, *"Generative Agents: Interactive Simulacra of Human Behavior"* (2023) — the academic precursor of episodic-memory agents.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 08 — Select strategies](../08-select-strategies/index.md)** — the read-path counterpart to everything in this post.
- **[Post 14 — Memory systems](../14-memory-systems/index.md)** — the in-prompt memory layer, in depth.
- **[Post 12 — The system prompt as software](../12-system-prompt-as-software/index.md)** — how `AGENTS.md` and `CLAUDE.md` get treated like code.
