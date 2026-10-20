# 07 - Write, select, compress, isolate

> **TL;DR.** [Post 02](../02-six-layers-of-context/index.md) named the six layers of a context window and [post 06](../06-context-failure-modes/index.md) the five ways it fails; this post names the four operations that act on it: write, select, compress and isolate (WSCI), after the four strategies of Lance Martin's essay "Context Engineering for Agents". Two axes separate them: whether information goes into a window or out of one, and whether the move stays inside one window or spans several. Every technique in the rest of the series is one of the four, and every first fix in [post 06](../06-context-failure-modes/index.md)'s catalogue is a select, a compress or an isolate.
>
> **Prerequisites:** [Post 02](../02-six-layers-of-context/index.md), [Post 06](../06-context-failure-modes/index.md).
> **Safe to skip?** Skip it if any technique (a memory store, a reranker, a rolling summary, a sub-agent) can already be placed under write, select, compress or isolate, and each failure mode of [post 06](../06-context-failure-modes/index.md) can be named with the operation behind its first fix.
>
> **After reading, you will be able to:**
>
> - Name the four operations of WSCI, place each on the two axes, and state the question each one answers.
> - Classify a context-engineering technique as exactly one of write, select, compress or isolate.
> - Map each of the six layers to the operations that act on it.
> - Name the operation behind the first fix of each of the five failure modes.
> - Annotate each event of an agent session as W, S, C or I.

![A two-by-two grid with columns into a window and out of the window, and rows one window and several windows. Select, into one window: retrieve, rerank, pack. Compress, out of one window: rolling summary. Isolate, into several windows: a sub-agent with its own window. Write, out to several windows: a memory store or scratchpad.](diagrams/01-wsci-quadrants.svg)

*Each operation owns one cell of the two axes. Select and compress act inside one window; isolate and write reach past it.*

---

## 1. The question: what can be done to a context window?

[Post 02](../02-six-layers-of-context/index.md) split the window into six layers, and [post 06](../06-context-failure-modes/index.md) named five ways it fails. Neither says what an engineer can *do* about it. Without a vocabulary for that, a discussion of a large language model (LLM) bug turns into a list of techniques: retrieval-augmented generation (RAG), summarisation, sub-agents, memory files. These are answers, not questions.

This post asks for the smallest set of operations that covers every context-engineering technique, and for how the six layers and the five failure modes map onto it. The answer comes from Lance Martin's essay "Context Engineering for Agents" (June 2025), which sorts the strategies it surveys into four groups: saving information outside the window, pulling information into it, keeping only the tokens the task needs, and splitting the context up. The series calls them write, select, compress and isolate, abbreviated WSCI and always in that order.

Two axes separate the four:

- **Direction:** does the operation put information *into* a window, or take it *out of* the window?
- **Scope:** does it act inside *one* window, or does it span *several* windows?

| | **Into a window** | **Out of the window** |
|---|---|---|
| **One window** | **Select:** pull the right items in for this call | **Compress:** shrink what is already inside |
| **Several windows** | **Isolate:** give a sub-task a fresh window of its own | **Write:** move information to a store that later windows can read |

Select and compress work inside the one window the model is about to read: one adds, the other removes. Write and isolate reach past it. Write parks information in a store (a file, a database, an index) that a later call or session can read. Isolate fills new windows: each sub-agent's window receives only what its sub-task needs, and only the result comes back into the parent's window. The figure at the top of the post draws the grid, with one canonical technique and a small picture of the move in each cell.

Other authors use other words, and their techniques land in the same cells. Anthropic's engineering post "Effective context engineering for AI agents" (September 2025) describes just-in-time retrieval (select), compaction (compress), structured note-taking (write) and sub-agent architectures (isolate). IBM Think's "What is context engineering?" (2025) names context selection, retrieval and compression and the storing of key facts as memory, and has no counterpart to isolate.

---

## 2. Write: move information out for later

**The question it answers:** what should be kept, even though it cannot be paid for on every call?

Write puts information somewhere other than the live window. Once written, it is no longer billed on every call, and it can still be recovered later. Write covers:

- **Persistent memory:** episodic events, semantic facts and preferences, procedural rules ([post 16](../16-memory-systems/index.md)).
- **Scratchpads and plan files:** an agent's intermediate notes, saved to disk between steps so they survive a long task.
- **Repository documentation:** `AGENTS.md`, `CLAUDE.md` and the `SKILL.md` files of Agent Skills (Anthropic, 2025), written once and loaded when a session needs them.
- **Audit logs:** full transcripts kept for debugging and evaluation, outside every prompt.
- **The embedding index:** the offline write side of RAG, where documents are chunked, embedded and indexed before any question arrives.

The cost of a write is paid once: a store insert, sometimes a model call to summarise what is written. The benefit appears only when a select brings the item back into a window.

The common write mistake is to write everything, with no schema. A store whose rows carry no source, date or expiry fills with stale entries, each read back as trusted data on a later call. An error the agent wrote and keeps citing is handled in [post 06](../06-context-failure-modes/index.md) as conflict; content planted on purpose is an attack, treated in [post 23](../23-security/index.md). [Post 08](../08-write-strategies/index.md) is the deep dive on write.

---

## 3. Select: pull the right information in for this call

**The question it answers:** of everything that could be included, what does the model need for this call?

Select decides what enters the window. The classic instance is RAG: a corpus far larger than any window lives outside it, a query at inference time fetches the handful of chunks most relevant to the current question, and only those chunks are packed into layer 04, retrieved chunks. RAG is one species of select among several:

- **Tool selection:** the application has many tools, and only the schemas relevant to this turn go into layer 02. Running retrieval over the tool descriptions is one way to choose them ([post 15](../15-tools-and-mcp/index.md)).
- **Memory recall:** a few facts pulled from a store of a user's history into layer 03, memory and state.
- **Few-shot example selection:** the two or three prior examples most similar to the current input, instead of a fixed set.
- **History selection:** the last few turns plus an older turn that matches the current topic.
- **Loading a rules file:** reading `CLAUDE.md` or `AGENTS.md` into the window at the start of a session. Writing the file was a write; loading it is a select, and Martin's essay lists it there.

Every select trades **recall against precision:** does the pipeline find the right item (recall@N, over the top-N candidates), and does it pack *only* right items (precision@k, over the top-k it packs)? [Post 09](../09-select-strategies/index.md) treats select as one pipeline with four levers (query, candidates, re-rank, pack), and [post 11](../11-rag-in-depth/index.md) and [post 17](../17-advanced-retrieval/index.md) take RAG apart in depth.

The levers matter. In Anthropic's "Introducing Contextual Retrieval" (September 2024), contextual embeddings reduced the top-20-chunk retrieval failure rate by 35% (from 5.7% to 3.7%), adding contextual BM25 (Best Matching 25, a keyword relevance score) reduced it by 49% (to 2.9%), and adding a reranker reduced it by 67% (to 1.9%).

---

## 4. Compress: shrink what is already inside

**The question it answers:** this information cannot be dropped and cannot be afforded verbatim, so what is the smallest form of it that still works?

Compress acts on tokens already in the window, or about to enter it: it changes how many tokens the content takes, not what it is about. [Post 12](../12-compress-strategies/index.md) covers six techniques:

1. **Windowing:** keep the last N turns and drop the rest. Cheap, and lossy in a known way.
2. **Summarisation:** replace a span of the window with a model-written summary. It costs an extra call and keeps the gist.
3. **Tool-result clearing:** drop the body of a tool result once the agent has taken what it needed. The result can be fetched again, so little is lost.
4. **Priority pruning:** give each part of the window a priority class and trim the lowest class first. Rule-based and cheap.
5. **Semantic chunking:** group the history by topic and summarise each topic on its own.
6. **Token-level prompt compression:** a small model removes the tokens that carry least information (LLMLingua is one example).

Every lossy technique can drop a fact that a later turn needs, typically the reason behind a decision while keeping the decision. [Post 12](../12-compress-strategies/index.md) measures a compression pass by what it calls the information retention ratio, the fraction of key facts that survive the pass; the ratio is a teaching construct of this series, not a standard metric.

A long-running agent reaches the point where compression is not optional. Anthropic's Claude Code documentation ("Manage costs effectively", consulted October 2026) says Claude Code compacts automatically, summarising the conversation history when it approaches the context limit, and the same page lets a user tell `/compact` what to preserve. The automatic trigger decides *when*; *what* is safe to summarise and what is load-bearing remains a policy someone has to design.

---

## 5. Isolate: split the work into separate windows

**The question it answers:** can this task be done in pieces, each with its own clean window, instead of one long one?

Isolate gives up on a single window and uses several. Two instances recur:

- **Sub-agents.** A research task splits into "find sources", "read each source" and "synthesise". Each sub-task runs in its own window, with its own tools and its own instructions, and the orchestrator sees only each sub-task's *result*, not its transcript ([post 13](../13-isolate-strategies/index.md)).
- **Sandboxes.** A tool runs in an environment whose raw output does not flow back into the window. Only a structured result returns; the noisy `npm install` log stays out.

Isolation buys a clean window and costs tokens. A sub-agent whose window never held the parent's context cannot be distracted by it, but each sub-agent carries its own instructions, tools and inputs. Anthropic's Claude Code documentation (same page, consulted October 2026) says of its agent teams that each teammate runs its own context window, so token usage is roughly proportional to team size. Results also have to be merged.

One rule decides most cases: **isolate when the sub-task has a clean input contract and a clean output contract.** "Find the three most relevant papers and return their titles and links" is a good sub-agent: it needs a topic and returns a short list. "Help me think through the problem" is a poor one: there is no output the orchestrator can integrate.

---

## 6. Placing a technique in exactly one cell

The series' rule ([notation guide](../../notation_guide.md), Section 3) is that every technique sits in exactly one of the four cells. The test that makes the rule work is to classify an event by **what it does to the window the model reads next**, not by the tool that performs it. One event is one operation; a technique that seems to need two operations is two events.

- Writing a `CLAUDE.md` is write; loading it at the start of a session is select. Two events.
- A sub-agent that summarises turns 1 to 17 of a long history is a compress: the parent's history shrinks. The sub-agent is how the summary is made, not what happens to the window.
- Bookend packing, which places the best chunk first and the second best last, is the packing step of select ([post 06](../06-context-failure-modes/index.md), section 7).
- Dropping a tool result's body after use is compress; running the tool in a sandbox so the body never arrives is isolate.

Two pairs are easily confused. Select chooses what *enters*; compress shrinks what is *already there*. Write moves *information* to a store; isolate moves *work* to another window.

---

## 7. Mapping the six layers onto WSCI

The four operations say *what* to do with context; the six layers of [post 02](../02-six-layers-of-context/index.md) say *where* the context lives. (MCP, in layer 02's name, is the Model Context Protocol, the open protocol through which external tools reach a host application.) Each layer except layer 06, the user instruction, has a main operation, and most have one or two others for the cases the main one cannot reach. The grid below draws the pairing, layer by layer.

![A grid of the six layers against the four operations. 01 System prompt: write main, select and compress also. 02 Tools and MCP descriptions: select main, isolate also. 03 Memory and state: write main and select main. 04 Retrieved chunks: select main, write also. 05 Conversation history: compress main, select and isolate also. 06 User instruction: no operation, the trigger.](diagrams/02-layers-to-wsci.svg)

*No layer needs all four operations, and several need two in sequence: content is written before it can be selected.*

| Layer | Main operation | Also | How it shows up |
|---|---|---|---|
| 01 System prompt | write | select, compress | Rules written once to a versioned file; choosing which rules it carries is [post 06](../06-context-failure-modes/index.md)'s select for confusion; compress it when bloated. |
| 02 Tools and MCP descriptions | select | isolate | Only the schemas this turn needs; a sub-agent gets its own tool set. |
| 03 Memory and state | write, select | none | Facts written between sessions; a few selected back on each call. |
| 04 Retrieved chunks | select | write | The offline write (chunk, embed, index) feeds the per-turn select (retrieve, rerank, pack). |
| 05 Conversation history | compress | select, isolate | Windowing and summaries keep the growing tail in budget; recall brings an older turn back; a sub-agent's transcript stays out. |
| 06 User instruction | none | none | The trigger: placed last, never compressed. |

Three readings follow. First, no layer needs all four operations. Second, the operations chain across layers: layers 03 and 04 are each written before they are selected, so a select that finds nothing often traces back to a write that never happened. Third, an operation can collide with a layer's lifetime class. Layer 02 belongs to the stable prefix, and a tool list selected afresh on every call changes that prefix, which ends the cached part of the request at the first change ([post 02](../02-six-layers-of-context/index.md), section 11). Selecting from a few fixed tool groups keeps the prefix stable.

---

## 8. WSCI and the five failure modes

[Post 06](../06-context-failure-modes/index.md) gives every failure mode a first fix and names the operations behind it (its section 7 table, also in the [cheatsheet](../../CHEATSHEET.md)); the figure below draws that table as a grid, with the five modes and their pairs unchanged.

![A grid of the five failure modes against the four operations, each filled cell naming the fix. Distraction: select, lower top-k, add a reranker. Confusion: select, explicit, motivated, exemplified rules. Conflict: select, provenance stamp and precedence rule; compress, deduplicate the candidates. Lost-in-the-middle: compress, summarise old history; isolate, split across sub-agents; select, dashed, bookend packing. Tool-storm: select, trim the catalogue; isolate, cap the result size. The write column is empty.](diagrams/03-wsci-vs-failures.svg)

*Every fix in [post 06](../06-context-failure-modes/index.md)'s catalogue is a select, a compress or an isolate. Write is in no row: what is written acts later, when it is selected.*

The grid makes three points. Select appears in four of the five rows, so a tighter select is the first lever to check for four of the five modes. Lost-in-the-middle touches select as well, because bookend packing is the packing step of select; compress and isolate are what remain when packing no longer rescues the middle. And write appears in no row: a provenance stamp is written with each memory, but it fixes conflict only when the select step uses it to pick the winner. Write prevents failures later rather than fixing one now.

Part II takes the four in the WSCI order: write ([post 08](../08-write-strategies/index.md)), select ([post 09](../09-select-strategies/index.md), with ingestion in [post 10](../10-data-ingestion-pipelines/index.md) and RAG in [post 11](../11-rag-in-depth/index.md)), compress ([post 12](../12-compress-strategies/index.md)) and isolate ([post 13](../13-isolate-strategies/index.md)).

---

## 9. A worked walk-through, annotated event by event

One agent session makes the four operations concrete. A customer-support agent for an online shop has been running for three months; every count and size below is illustrative. Each event is annotated with its operation, W, S, C or I, and the layer it serves.

| # | When | Event | Op | Layer |
|---|---|---|---|---|
| 1 | Setup | The product manuals are chunked, embedded and indexed. | W | 04 Retrieved chunks |
| 2 | Setup | Tone and refund rules are written to a versioned `AGENTS.md`. | W | 01 System prompt |
| 3 | Setup | Each customer's profile is stored in a key-value store. | W | 03 Memory and state |
| 4 | Session start | The rules file is loaded as the system prompt. | S | 01 System prompt |
| 5 | Every turn | The 5 chunks most relevant to the question are retrieved and packed. | S | 04 Retrieved chunks |
| 6 | Every turn | The customer's profile is fetched by customer id. | S | 03 Memory and state |
| 7 | Every turn | The schemas of the 4 tools that fit the request, from a few fixed groups, are exposed. | S | 02 Tools and MCP descriptions |
| 8 | After a tool call | An order lookup returns a long record; once its two needed fields are used, the record's body is cleared. | C | 05 Conversation history |
| 9 | Turn 20 | Turns 1 to 17 are summarised into a brief of about 200 tokens; turns 18 to 20 stay verbatim. | C | 05 Conversation history |
| 10 | Turn 20 | A preference found in the brief ("prefers email") is written to the profile with its date. | W | 03 Memory and state |
| 11 | "Build me a refund report" | A sub-agent with only the database tools, in a window of its own, builds the report and returns three lines and the file's path. | I | 05 Conversation history |
| 12 | Session end | The full transcript is written to an audit log, outside every prompt. | W | none |

Every event lands in exactly one cell. Where an event seemed to need two operations, it was split: summarising the history (9) and saving the preference it surfaced (10) are two events, and so are writing the rules file (2) and loading it (4). Event 11 is one isolate: the parent never sees the report-building transcript, only its result.

The count (five writes, four selects, two compresses, one isolate) belongs to this illustrative session, not to a law. The engineering is in the policies that decide *when* each event fires, and posts 08 to 13 are about those policies.

---

## 10. What can go wrong?

- **More retrieval for a distraction bug.** Top-k is raised from 5 to 20 (illustrative values) so that the right chunk is surely in the window. Answers drift further off topic, because distraction's fix is a tighter select (fewer, better chunks), not a wider one.
- **Isolating by default.** A task that one window holds comfortably is split across three sub-agents. The token bill rises with the number of agents, and a fact one sub-agent found never reaches another, so the merged answer contradicts itself.
- **Selecting tools per call inside the stable prefix.** A per-turn tool list is placed in layer 02 with no further thought. The answers improve, but the cache-read tokens in each response's usage block fall towards zero, and the cost per call rises.
- **Compressing without measuring.** A new summary prompt ships because the summaries read well. Users then report that the agent "forgot" an early decision: the summary kept the outcome and dropped the reason, and no replay set ([post 12](../12-compress-strategies/index.md)) caught the loss.
- **Filing a technique under the tool that runs it.** A summarising sub-agent is filed as isolate, so its retention is never measured: isolate's checks (contracts, cost) are applied instead of compress's.

---

## Common pitfalls

1. **Conflating select and compress.** Both shrink the prompt compared with "everything"; select chooses what enters, compress shrinks what is already inside.
2. **Reading only one axis.** On the direction axis alone, select and isolate look alike; scope separates them: select fills this window, isolate fills a new one.
3. **Writing without a schema.** A memory row with no source, date or expiry is a future conflict with nothing to rank it by.
4. **Writing without a matching select.** Information that is written and never selected back costs storage and fixes nothing.

---

## Further reading

- Martin, L., ["Context Engineering for Agents"](https://rlancemartin.github.io/2025/06/23/context_engineering/) (June 2025): the four strategies this series abbreviates as WSCI.
- Anthropic Engineering, ["Effective context engineering for AI agents"](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (September 2025): just-in-time retrieval, compaction, structured note-taking and sub-agent architectures.
- IBM Think, ["What is context engineering?"](https://www.ibm.com/think/topics/context-engineering) (2025): context selection, retrieval, compression and memory, in another vocabulary.
- Anthropic, ["Introducing Contextual Retrieval"](https://www.anthropic.com/news/contextual-retrieval) (September 2024): the retrieval-failure reductions quoted in section 3.
- Anthropic, Claude Code documentation, ["Manage costs effectively"](https://code.claude.com/docs/en/costs) (consulted October 2026): automatic compaction and the token cost of agent teams.

---

## What to read next

- **[Post 08 - Write strategies](../08-write-strategies/index.md):** the first operation in depth: where to write, and what to write alongside it so the store stays useful.
- **[Post 09 - Select strategies](../09-select-strategies/index.md):** the operation behind four of the five first fixes, as one pipeline with four levers.
