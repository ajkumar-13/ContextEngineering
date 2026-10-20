# 08 - Write strategies

> **TL;DR.** Write puts information somewhere other than the live window, so that a later call can bring back only what it needs. This post asks where information that is needed later but not now should be written, and what must be written alongside it so the store stays useful. Four destinations cover practice: memory stores, scratchpads, repository files (`AGENTS.md`, `CLAUDE.md`, a skill's `SKILL.md`) and embedding indexes; every write carries its metadata, and three classes of bug (no provenance, the wrong content, no expiry) are what turn a store into a liability.
>
> **Prerequisites:** [Post 07](../07-write-select-compress-isolate/index.md).
> **Safe to skip?** Skip it if every piece of state an agent keeps already has a destination, a recorded source and date, and a way to expire or be reviewed.
>
> **After reading, you will be able to:**
>
> - Choose the write destination for a piece of information (memory store, scratchpad, repository file or embedding index), or decide it belongs in none.
> - Specify the nine metadata fields of a memory row and say what each one is for.
> - Recognise the three classes of bug that turn a memory store into a liability, and the guard against each.
> - Explain how repository files such as AGENTS.md and a skill's SKILL.md reach the window, and why every change to them is reviewed like code.
> - Describe the offline write path of an embedding index and the metadata each chunk must carry so the index can be traced and rebuilt.

![Four destination cards fed by write arrows from the agent at work: repository files, written by people by review, lasting until a reviewed change; memory store, weeks to months; scratchpad, one task; embedding index, until the source changes. Select arrows run from them to layers 01, 03, 03 and 04 of a later call's window.](diagrams/01-four-destinations.svg)

*Write takes information out of the window; a later select brings it back, each destination through its own layer. Until then it costs no tokens.*

---

## 1. The question: where does information go when it is needed later but not now?

[Post 07](../07-write-select-compress-isolate/index.md) places write in the four operations: it moves information out of the window and spans several windows. The question this post answers is practical: given a fact, a plan, a rule or a document, which store should hold it, and what must be recorded with it so that a later call can trust it?

The figure at the top of the post is the answer in outline. Each destination is written by someone different, lasts a different time, and returns through its own layer: repository files through layer 01, the system prompt; memory stores and scratchpads through layer 03, memory and state; an embedding index through layer 04, retrieved chunks. The returning half is select ([post 09](../09-select-strategies/index.md)); this post is about the writing half.

Writing is mechanically the easiest of the four operations; the difficulty is governance. Anything written becomes data that some future call will trust, and three classes of bug turn a useful store into a liability:

1. **No provenance.** An entry with no source and no date cannot be checked or overruled. When an error the agent wrote is read back and cited again, [post 06](../06-context-failure-modes/index.md) treats it as conflict (its section 8); when the content was planted on purpose, it is memory poisoning, an attack that belongs to [post 23](../23-security/index.md).
2. **The wrong content.** A transient value (a tool result, a turn of the live conversation) or a secret is written into a long-lived store, where it is read back as if it were still true, or leaked, long after anyone remembers writing it.
3. **No expiry.** Nothing decays, nobody reviews the file, the index is never rebuilt. The store drifts away from the world it describes.

The discipline that prevents all three fits in one rule: **every write carries metadata.** At minimum, who or what wrote it, when, from what source, and with what confidence. The rest of the post applies the rule to the four destinations.

---

## 2. Memory stores

A memory store is the persistent counterpart of layer 03, memory and state: it holds what an agent learned about a user, a project or a task, and the application selects from it on later calls ([post 16](../16-memory-systems/index.md) is the deep dive). It holds three kinds of data, often in three different tables:

- **Episodic**: events with a timestamp. *"User X resolved ticket 4321 on 14 March by escalating to engineering."*
- **Semantic**: facts and preferences. *"User X prefers replies in formal English; uses Postgres in production."*
- **Procedural**: rules and how-tos. *"Export this client's reports as CSV first; their system rejects a PDF on its own."*

The three kinds have different write patterns, lifetimes and access policies, which is why storing them in one undifferentiated table is a mistake: a procedural rule that decays like a passing preference eventually disappears.

![Three cards for the episodic, semantic and procedural kinds of memory, with an example each, beside a table of one semantic row with its nine fields and values, bracketed as identity, content, provenance and upkeep.](diagrams/02-memory-row.svg)

*One row of the store as the snippet prints it. Provenance and upkeep take five of the nine fields; the fact itself is one.*

**The minimum row schema.** Whatever the store (a SQL table, a document database, a vector index with metadata fields), every row carries the nine fields below; the figure above shows one row filled in.

| Field | Why |
|---|---|
| `id` | Stable reference for updates and deletes |
| `kind` | `episodic`, `semantic` or `procedural`: different decay and access rules |
| `subject` | The entity the memory is about (a user id, a project id, an agent id) |
| `content` | The fact itself, in whatever representation is used to recall it |
| `source` | Where the fact came from (a web address, a tool name, a conversation id) |
| `created_at` | Timestamp of the original write |
| `last_accessed_at` | Updated on every read; drives decay |
| `confidence` | 0 to 1; lowered as a fact goes unread; decides whether the agent asserts or asks |
| `expires_at` | Optional; some facts are knowingly short-lived ("the user is on holiday until 1 May") |

A write gate that refuses the first two classes of bug fits in a few lines of standard-library Python. This excerpt of `snippets/memory_store.py` checks a candidate `MemoryRow`, a dataclass with the nine fields, before it is stored:

```python
SECRET = re.compile(r"\bsk-[A-Za-z0-9-]{8,}|\b(password|api[_ ]?key)\s*[:=]", re.IGNORECASE)


def check_write(row: MemoryRow, origin: str) -> str | None:
    """Return why the write must be refused, or None when it may go in."""
    if not row.source:
        return "no provenance: the row has no source"
    if SECRET.search(row.content):
        return "secret: it belongs in a secret manager, not a memory store"
    if origin == "tool_result":
        return "transient: a tool result is called again, not remembered"
    if row.kind not in KINDS:
        return f"unknown kind: {row.kind!r}"
    return None
```

Running `uv run python posts/08-write-strategies/snippets/memory_store.py` from the series root prints the row of the figure, then offers the gate four candidate writes: the row itself, a fact with an empty `source`, a message that contains a key, and a weather reading from a tool.

```text
write gate:
  mem-0042: written
  mem-0043: refused, no provenance: the row has no source
  mem-0044: refused, secret: it belongs in a secret manager, not a memory store
  mem-0045: refused, transient: a tool result is called again, not remembered
```

**When to write.** Three triggers recur: at the **end of a session** (summarise what the user said today), on an **explicit user assertion** ("remember that I work in Pacific time"), and on an **observed contradiction** (a stored fact disagrees with this turn's evidence: write the new version and keep the old one, because resolving the conflict is its own step). Harrison Chase's "Memory for Agents" (LangChain, October 2024) names two places for the write: in the hot path, where the agent decides to remember (usually with a tool call) before it answers, at the price of latency; or in the background, during or after the conversation.

**When not to write.** Tool results are not memories, and neither is the conversation history: both are transient and have their own layers. If a tool returns "temperature: 32" for Mumbai, writing it to long-term semantic memory makes every later question about the weather start from a stale reading. Secrets never enter a writable store at all.

**Decay.** A simple scheme lowers `confidence` by a fixed amount for every day without a read, and demotes the row to a colder tier, or deletes it, below a threshold; the agent asks before asserting anything below a cutoff. With an illustrative rate of 0.01 per idle day and an illustrative cutoff of 0.6, the snippet's row starting at 0.9 falls below the cutoff once it has gone more than 30 days without a read (0.9 minus 0.6 is 0.3, and 0.3 divided by 0.01 is 30):

```text
decay of mem-0042 without a read:
  2026-09-01:  0 idle days, confidence 0.90, assert
  2026-09-21: 20 idle days, confidence 0.70, assert
  2026-10-11: 40 idle days, confidence 0.50, ask first
```

Both numbers are tuned per application, against how fast its facts go stale.

---

## 3. Scratchpads

A scratchpad is a short-lived, write-mostly destination that a single agent or sub-agent uses to keep its working state across iterations. The simplest is a Markdown file the agent appends to between tool calls: *"Files A and B are checked. C is still to check. The most likely root cause is X."* Lance Martin's "Context Engineering for Agents" (June 2025) gives it as the first form of write; Anthropic's "Effective context engineering for AI agents" (September 2025) calls the practice structured note-taking, with Claude Code's to-do list and a custom agent's `NOTES.md` file as its examples.

Scratchpads matter because they separate two questions that the window would otherwise conflate:

- "What does the agent need to *keep* across the next few iterations?" (goes to the scratchpad)
- "What does the model need *in this call* to make the next decision?" (stays in the window)

Without a scratchpad the agent keeps its working state in layer 05, conversation history, where it competes with everything else for attention and budget, and where a compaction step ([post 12](../12-compress-strategies/index.md)) may summarise it away.

**Three scratchpad patterns** recur:

- **Plan and checklist.** A plan at the top of the task with checkboxes. Each iteration ticks the items it completed and re-reads the plan; Claude Code's to-do list is one instance.
- **Findings log.** Append-only notes during a research task. The orchestrator can compress the log later without losing the trail.
- **Hypothesis stack.** A debugging agent writes its current hypothesis, the evidence for and against, and the next test. When the hypothesis is disproved, it pops the stack instead of forgetting.

The implementation does not need to be elaborate. A file per task, named after the task id, in a `.scratch/` folder, is enough; the agent gets read and write tools scoped to that folder, and everything else is convention.

**A worked `task.md` lifecycle.** The agent writes a single `task.md`, then re-reads and edits it on every iteration. The snippet `snippets/task_scratchpad.py` replays the lifecycle with the tool calls stubbed out. It starts from a fresh file with four unchecked plan items and an empty Notes section; after two iterations the same file has grown a record of what happened, so the agent never has to reconstruct it from the history. The snippet prints:

```markdown
# Task: add rate limiting to the /login endpoint

## Plan
- [x] Find where /login is defined (routes/auth.py:42)
- [x] Add a token-bucket limiter (5 attempts / 15 min / IP)
- [ ] Return 429 with a Retry-After header
- [ ] Add a test for the limit and the reset

## Notes
- Existing middleware stack is in app/middleware.py; add the limiter there, not in the route, so it also covers /login/mfa.
- Redis is already a dependency: use it for the bucket, not in-process state.
```

The lifecycle is three moves repeated until the boxes are ticked: **read** the file to recover the state, **act** on the first unchecked item, **write** back the result and any note the next iteration will need. Because the plan lives in a file rather than in the transcript, a long task does not depend on early turns that compaction may drop. When the task finishes, the file is deleted or promoted: a durable decision ("use Redis, not in-process state") belongs in `AGENTS.md`, not in a scratch file that disappears with the task.

---

## 4. Repository documentation: `AGENTS.md`, `CLAUDE.md`, `SKILL.md`

Repository files are the write destination whose return compounds: a rule written once is read in every later session, by every agent that works on the repository. They are plain Markdown files that live alongside the code, and they are checked into the repository: reviewed, version-controlled and diffed like code. Their content reaches the model as the standing instructions of a session, the job of layer 01, the system prompt.

`AGENTS.md` is an open, vendor-neutral format; the agents.md site (consulted October 2026) lists support from many coding agents, and says the format is now stewarded by the Agentic AI Foundation under the Linux Foundation. `CLAUDE.md` is Claude Code's own file. Claude Code's documentation ("How Claude remembers your project", consulted October 2026) says that it reads `CLAUDE.md` at the start of every session, reads a repository's `AGENTS.md` in its place when there is no `CLAUDE.md`, and supports an `@AGENTS.md` import inside `CLAUDE.md`. A project that wants both portability and Claude-specific tuning therefore keeps a shared `AGENTS.md` and a thin `CLAUDE.md` that imports it:

| | `AGENTS.md` | `CLAUDE.md` |
|---|---|---|
| Read by | agents that support the format (Codex, Cursor, Aider, Gemini CLI and others; Claude Code when there is no `CLAUDE.md`) | Claude Code |
| Scope | vendor-neutral project rules | Claude-specific instructions |
| Best for | portable build, test and style rules | Claude Code commands and conventions |
| Nested files | the closest file to the edited file wins | files above the working directory load at launch; a subdirectory's file loads when work reaches that subdirectory |

Both conventions are recursive: in the agents.md site's words, "The closest AGENTS.md to the edited file wins". A monorepo can therefore carry one set of rules for the front-end and another for the data pipelines, without either drowning the other.

A typical `AGENTS.md` has five blocks, the same five as the system prompt of [post 14](../14-system-prompt-as-software/index.md):

1. **Identity**: what this codebase is, in one paragraph.
2. **Rules**: testing requirements, commit conventions, what *not* to refactor.
3. **Format**: how to cite files, how to write commit messages, how to lay out responses.
4. **Knowledge**: the build commands, the deploy commands, the names of the key modules.
5. **Tools and commands**: the commands the agent can invoke, and the servers of the Model Context Protocol (MCP), the open protocol through which external tools reach a host application, configured for this project ([post 15](../15-tools-and-mcp/index.md)).

**Skills** are a more specialised variant: one capability (for example, "review a Terraform diff" or "draft a pull-request description in the project's format") packaged with its own instructions, loaded only when a task needs it. In Anthropic's Agent Skills format (Anthropic Engineering, "Equipping agents for the real world with Agent Skills", October 2025), a skill is a directory that contains a `SKILL.md` file, alongside any scripts or resources the skill uses; the file starts with YAML front matter that must give a `name` and a `description`. The agent pre-loads the name and description of every installed skill into its system prompt, and reads the full `SKILL.md` into the window only when it judges the skill relevant. The pattern is the point: one file per concern, loaded on demand, instead of one large prompt that is always on.

Three rules of thumb follow from how these files are loaded:

- **Keep the file short.** The host loads it on every session, so a sprawling file makes the cached prefix large and the instructions hard for people to read. Claude Code's documentation (consulted October 2026) gives a target of under 200 lines per `CLAUDE.md` file and says that longer files "consume more context and reduce adherence".
- **Iterate from minimal.** Anthropic's "Effective context engineering for AI agents" (September 2025) advises, for prompts generally, to "start by testing a minimal prompt with the best model available" and to add instructions and examples "based on failure modes found during initial testing". A rule added on speculation answers no observed failure.
- **Review every change like code.** A diff that adds a rule deserves the scrutiny of a diff that adds an `if` statement, because that is what it is.

**Spec-driven development.** A stronger form of this discipline puts the checked-in file *upstream of the code*. Instead of prompting an agent turn by turn, the operator writes a specification (a plan file describing what to build, the constraints and the acceptance tests), reviews and edits it like any other artefact, and only then hands it to the agent to implement. The specification is a write destination in the sense of this post: durable, versioned, reviewed and re-read. Unlike a `task.md` scratchpad, which is the agent's private state for one task, it is a contract written by people that outlives the run and can be handed to a different agent. The two chain together: a reviewed specification generates a `task.md` plan, the agent works the plan, and durable decisions flow back into `AGENTS.md`. The review happens on the specification, where a mistake costs one edit, rather than on a thousand lines of generated code, where it costs a re-run.

---

## 5. Embedding indexes: the offline write side of retrieval

Every retrieval-augmented generation (RAG) system, which fetches relevant text at query time and adds it to the window, has two halves: an *online* read path that retrieves at inference time ([post 11](../11-rag-in-depth/index.md)) and an *offline* write path that prepares the corpus. The write side decides what the read side can ever find. [Post 10](../10-data-ingestion-pipelines/index.md) covers getting text out of documents; the minimum write pipeline from clean text onwards is:

1. **Source collection.** Pull the canonical version of every document. Keep a hash, and re-index when it changes.
2. **Cleaning.** Strip boilerplate (navigation, footers, marketing), normalise whitespace, fix the encoding.
3. **Chunking.** Split into chunks of 400 to 600 tokens for prose (200 to 300 for code), with an overlap of 10 to 20 percent, roughly 50 to 100 tokens, between adjacent chunks. These are illustrative starting values, not measured constants; sentence-aware splitters suit prose, and code is best split by symbol.
4. **Enrichment.** Prepend a short context to each chunk. In Anthropic's contextual retrieval ("Introducing Contextual Retrieval", September 2024), a model reads the whole document and the chunk and writes a short context, usually 50 to 100 tokens, that situates the chunk in its document; a cheaper variant prepends the document title and the section path.
5. **Embedding.** Run each chunk through an embedding model. Store the vector alongside the chunk text and its metadata.
6. **Indexing.** Insert into a vector store (FAISS, Chroma, pgvector, Pinecone, Weaviate), and keep a parallel keyword index such as BM25 (Best Matching 25, a classic keyword relevance score).
7. **Manifest.** Write one manifest row per source: its hash, the chunks it produced, the embedding model version and the timestamp.

The figure below draws the pipeline with the metadata each step records.

![A chain of six steps, collect, clean, chunk, enrich, embed and index, with the metadata four steps record underneath, a manifest row per source below, and a select arrow from the index to 04 Retrieved chunks.](diagrams/03-index-write-pipeline.svg)

*Provenance is written along the way: by the time a chunk reaches the index, it can say where it came from and which model embedded it.*

Anthropic's page measures the effect of enrichment as the top-20 retrieval failure rate (1 minus recall@20) on its test sets. Contextual embeddings cut it by 35% (from 5.7% to 3.7%), adding contextual BM25 by 49% (to 2.9%), and adding a reranker on top by 67% (to 1.9%). The same results are the evidence for keeping the keyword index beside the vector index.

**Metadata on every chunk**, besides the vector and the text: `source_id`, `source_url`, `chunk_index`, `tokens`, `created_at`, `embedding_model`. Without them, nobody can answer "where did this answer come from?", and nothing can be re-indexed when an upstream document changes.

One write-side mistake is to **embed the wrong unit of text**. With illustrative sizes: a 5,000-token document is too coarse, because retrieval returns 5,000 tokens to land on one paragraph; a 50-token fragment is too fine, because the model gets a piece without enough context to use it. The aim is a chunk that is self-contained when read alone.

Another is to **never re-index**. Documents change and embedding models improve. The index is treated like a database: backed up, versioned and rebuildable from source.

---

## 6. The "what to write where" cheat sheet

| Information | Destination | Lifetime |
|---|---|---|
| The user said "I prefer Markdown tables" | Memory store, kind `semantic` | Months, decays |
| The user resolved ticket 4321 yesterday | Memory store, kind `episodic` | Weeks to months |
| Refunds above $1,000 go to the manager queue | `AGENTS.md` rules block | Until the policy changes |
| The build command is `pnpm run build:prod` | `AGENTS.md` knowledge block | Until the build changes |
| The 200-page product manual | Embedding index | Until the manual changes |
| "Still to check: file C" (mid-task) | Scratchpad | This task |
| A tool returned `temperature: 32` | **Nothing.** It is transient. | None |
| "My access key is sk-..." | **Nothing.** Secrets never enter a writable store. | None |

Each of the first six rows names a destination whose lifetime matches the information. The last two are the second class of bug, the wrong content: a transient value or a secret written into a long-lived store is read back, or leaked, long after the call that wrote it.

---

## 7. What can go wrong?

- **One store for all three kinds.** Procedural rules sit in the same table as preferences and decay with them. Months later a routing rule that nobody contradicted is below the cutoff, and the agent starts asking the user how this client's reports are exported.
- **Overwriting on contradiction.** A new fact replaces the old row in place. The agent's behaviour changes and nobody can say why, because the old value and its source are gone.
- **A scratchpad that is never promoted.** The decision to use Redis lives only in `task.md`, which is deleted with the task. The next task on the same code rediscovers it, or makes the opposite choice.
- **A `CLAUDE.md` that only grows.** Rules are added after every incident and none are removed. Adherence falls, and two rules that contradict each other are followed in turn; Claude Code's documentation warns that the model "may pick one arbitrarily".
- **A new embedding model without a re-index.** Queries are embedded with the new model and compared with vectors from the old one. Retrieval quality collapses while every component reports healthy; only the chunks' `embedding_model` field shows the mismatch.

---

## Common pitfalls

1. **Writing without provenance.** A memory row with no `source` cannot be checked when it turns out to be wrong.
2. **Treating tool results as memories.** A tool result describes the moment of the call; when it is needed again, the tool is called again.
3. **Storing secrets in any writable store.** Secrets belong in a secret manager, fetched per call.
4. **Letting `AGENTS.md` grow without review.** Each new rule is a change to every future session.
5. **Embedding without re-indexing.** An index that is never rebuilt drifts further from its sources every day.

---

## Further reading

- Lance Martin, ["Context Engineering for Agents"](https://rlancemartin.github.io/2025/06/23/context_engineering/) (June 2025): write as the first of the four operations, with scratchpads and memories as its forms.
- Harrison Chase, ["Memory for Agents"](https://www.langchain.com/blog/memory-for-agents) (LangChain blog, October 2024): the three kinds of memory, and hot-path against background writes.
- Anthropic, ["How Claude remembers your project"](https://code.claude.com/docs/en/memory) (Claude Code documentation, consulted October 2026): how `CLAUDE.md` and `AGENTS.md` are loaded.
- Anthropic Engineering, ["Effective context engineering for AI agents"](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (September 2025): structured note-taking and starting from a minimal prompt.
- Anthropic Engineering, ["Building Effective AI Agents"](https://www.anthropic.com/engineering/building-effective-agents) (December 2024): the augmented model, with retrieval, tools and memory, as the building block of agents.
- Anthropic Engineering, ["Equipping agents for the real world with Agent Skills"](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) (October 2025): the `SKILL.md` format and loading on demand.
- agents.md project, ["AGENTS.md"](https://agents.md/) (2025): the vendor-neutral convention of section 4.
- Anthropic, ["Introducing Contextual Retrieval"](https://www.anthropic.com/news/contextual-retrieval) (September 2024): the enrichment step and its failure-rate results in section 5.
- Park, J. S. *et al.*, ["Generative Agents: Interactive Simulacra of Human Behavior"](https://arxiv.org/abs/2304.03442) (2023): an early agent architecture built on a memory stream of timestamped observations.

---

## What to read next

- **[Post 09 - Select strategies](../09-select-strategies/index.md):** the read path that brings written information back into the window.
- **[Post 16 - Memory systems](../16-memory-systems/index.md):** the memory store of section 2 in depth, with retrieval and decay for each of the three kinds.
