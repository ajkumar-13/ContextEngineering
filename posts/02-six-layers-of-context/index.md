# 02 - The six layers of context

> **TL;DR.** On every call a large language model (LLM) receives one flat sequence of tokens, and in any real application that sequence is assembled from six layers: the system prompt, the tool and Model Context Protocol (MCP) descriptions, memory and state, retrieved chunks, the conversation history, and the user instruction. Each layer has its own job and its own lifetime, from the stable prefix that can be cached to the user instruction that is new on every call. This post shows the six layers in a raw request to three providers, explains why they are sent in that order, and turns them into a checklist for finding the layer at fault when an application misbehaves.
>
> **Prerequisites:** [Post 01](../01-why-context-engineering/index.md).
> **Safe to skip?** Skip it if a raw request body can already be split into the six layers by eye, and the reason the stable layers go first is already familiar.
>
> **After reading, you will be able to:**
>
> - Name the six layers of a context window in their fixed order and state the job and the lifetime of each.
> - Identify every layer in a raw Anthropic, OpenAI, or Gemini request body.
> - Explain why the stable layers are sent first and the user instruction last, in terms of prompt caching and position.
> - Predict which layer is most likely at fault for a reported symptom, and say what to inspect in it.

![Six horizontal bands stacked from the top, 01 System prompt, 02 Tools and MCP descriptions, 03 Memory and state, 04 Retrieved chunks, 05 Conversation history and 06 User instruction, each with a one-clause job, bracketed on the right by lifetime: stable prefix, per-turn injection, growing tail and trigger.](diagrams/01-six-layer-stack.svg)

*The window the model reads on one call, sent from the top. Hue marks the lifetime class; the number and the name identify the layer.*

---

## 1. The question: what does the model literally receive?

Before splitting the context window into parts, it helps to see what an LLM actually gets on a single call. There is no hidden state, no database it queries behind the application's back, and no memory of the last conversation. The model receives **one flat sequence of tokens** and produces the next token. Everything an application "knows" has to be serialised into that one sequence, on every call.

That flat sequence is not shapeless, though. In any real application it is assembled from a handful of recurring parts, each written by a different piece of code, each with its own job. The question of this post is why it pays to see the sequence as six such parts, which the series calls layers, with different lifetimes and costs. The stack at the top of the post is the answer in one picture: six layers, sent from the top, grouped by how long each one lives.

---

## 2. Why "layers"?

The word *layer* is borrowed from networking and graphics for the same reason it is useful there: it lets an engineer reason about one concern at a time.

Each layer in a context window has:

- a **purpose**: the question it answers for the model,
- a **lifetime**: how often it changes,
- a **cost shape**: how it interacts with the prompt cache,
- and a **failure mode**: the kind of bug it is responsible for when it goes wrong.

These four properties differ from layer to layer, and they are why an LLM application cannot be debugged by squinting at the raw prompt. It is debugged by asking *"which layer is wrong?"*

There is nothing magical about the number six. Other authors split the same material differently: Anthropic's engineering post on context engineering discusses system prompts, tools, examples and message history as its components, and IBM Think lists the system prompt, the user's query, retrieved documents, structured data, the interaction history and tool outputs. The six layers used here are the split this series finds most useful for teaching; the other groupings map onto it with small regroupings.

---

## 3. The six layers, briefly

The "typical size" column below is an illustrative order-of-magnitude guide, not a measured figure; real sizes vary widely by application.

| # | Layer | Purpose | Lifetime | Typical size (illustrative) |
|---|-------|---------|----------|--------------|
| 01 | **System prompt** | Identity, rules, format, knowledge the model always needs | rarely changes | 500 to 10,000 tokens |
| 02 | **Tools and MCP descriptions** | The schema of every callable function | rarely changes | 1,000 to 20,000 tokens |
| 03 | **Memory and state** | Persistent facts about the user, the session or the task | the store changes between sessions; what is injected is chosen per call | 100 to 5,000 tokens |
| 04 | **Retrieved chunks** | Evidence retrieved for *this* turn | changes every turn | 1,000 to 50,000 tokens |
| 05 | **Conversation history** | Previous user and assistant turns of the current session | grows every turn | 0 to 100,000 tokens |
| 06 | **User instruction** | The current turn: what the user just asked | new every turn | 10 to 1,000 tokens |

The six fall into four lifetime classes. Layers 01 and 02 are the **stable prefix**: identical on every call, which makes them the material a prompt cache can reuse. Layers 03 and 04 are the **per-turn injection**: assembled for this call, so in general they cannot be relied on as cached prefix and are paid at the full input rate. Layer 05 is the **growing tail**: it gains a turn on every call and is the layer that runs out of room first. Layer 06 is the **trigger**: small, last, and the reason all the other layers exist.

---

## 4. Layer 01: System prompt

The system prompt is the first thing the model reads. It tells the model who it is, how to behave, what format to answer in, and what knowledge to assume.

In well-run projects, the system prompt is **software**. It lives in version control, it has a changelog, and it is reviewed in pull requests. Two file conventions carry this idea into coding agents: `CLAUDE.md` (Anthropic's Claude Code) and `AGENTS.md` (OpenAI's Codex, Cursor, and other tools). Both are plain Markdown files that the host application loads at the start of a session as standing instructions, which makes them layer 01 in function; where exactly a host places that text, in the system field or in an early message, differs from host to host.

A system prompt typically covers five blocks:

1. **Identity**: "You are a senior backend engineer working in this monorepo."
2. **Rules**: "Never run `rm -rf` without explicit confirmation. Always run the test suite after edits."
3. **Format**: "Answer in Markdown. Use fenced code blocks. Cite file paths as `src/foo.py:42`."
4. **Knowledge**: short, stable facts: the project's stack, the team's conventions, the build command.
5. **Tool-use guidance**: when to reach for which tool; the schemas themselves are layer 02.

What does *not* belong in the system prompt: anything that changes per turn (that is layer 04 or 06), anything large (that is layer 04), and anything user-specific that varies between users of the same application (that is layer 03).

[Post 14](../14-system-prompt-as-software/index.md) goes deep on system prompts, including the `CLAUDE.md` and `AGENTS.md` conventions.

---

## 5. Layer 02: Tools and MCP descriptions

If the model can call functions, every callable function's schema, written in JavaScript Object Notation (JSON), rides in the prompt on every call. The model sees the name, the description and the parameters of each tool, and uses them to decide whether to call a tool and which one.

Two practical consequences follow.

**Tool schemas are a token bill.** With illustrative numbers: ten tools whose descriptions and parameter documentation run to 400 tokens each occupy 4,000 tokens on every call, before the user has typed anything. Names, descriptions and parameter documentation are not "documentation" to be lazy about; they are the prompt.

**The Model Context Protocol (MCP)** is the open protocol through which a host application (Claude Desktop, Cursor, VS Code, a custom application) connects to external servers. An MCP server exposes three kinds of capability: **tools** (functions the model can call), **resources** (data the application can read), and **prompts** (reusable templates). The host's client lists a server's tools, and the host passes their names, descriptions and input schemas to the model in the request's tools field, where they become part of layer 02 like any other tool.

[Post 15](../15-tools-and-mcp/index.md) covers tool design, MCP, and the question of how many tools is too many.

---

## 6. Layer 03: Memory and state

Anything that should persist beyond a single call but is not literally part of the conversation lives here. In practice this splits into:

- **Short-term memory**: working scratchpads and plan files for the current task.
- **Long-term memory**, in three kinds:
  - **Episodic**: past interactions ("on April 4 the user asked about webhooks"), stored as events and retrieved by similarity.
  - **Semantic**: distilled facts and preferences ("user prefers Python, stack is AWS"), curated and slowly changing.
  - **Procedural**: reusable skills and routines, often as Markdown skill files or slash commands.

Whatever the store, what reaches the model is text in the request. A common pattern, and the one this post's snippet uses (section 10), replays the selected memories as a synthetic exchange at the start of the message list: a user message the application writes, holding the stored facts, followed by a short assistant acknowledgement. Other applications put the same facts in a block of the system prompt or of the first user message. The model does not "remember" anything; it reads what is put there. [Post 16](../16-memory-systems/index.md) is an entire post on this.

---

## 7. Layer 04: Retrieved chunks

Retrieval-augmented generation (RAG) is the pattern of fetching relevant text at query time and pasting it into the prompt. Layer 04 answers the question *"what evidence does the model need for this specific question?"*

The basic pipeline has four steps:

1. **Index**: split the documents into chunks, embed each chunk, store the vectors.
2. **Retrieve**: at query time, embed the user's question and find the top-N candidate chunks by vector similarity, often combined with a BM25 pass (Best Matching 25, a classic keyword relevance score), a setup called *hybrid search*.
3. **Rerank**: a cross-encoder (a model that scores the query and a chunk together, rather than comparing precomputed vectors) re-scores the candidates.
4. **Pack**: the top-k chunks after reranking, usually a handful, are concatenated into the prompt as an evidence block.

Each of these terms is defined properly in [post 09](../09-select-strategies/index.md); the one-line glosses here are enough to place the layer. This basic pipeline is the floor, not the ceiling. Contextual retrieval (Anthropic, September 2024), agentic retrieval (the model decides what to fetch next), GraphRAG and Self-RAG build on it; [post 11](../11-rag-in-depth/index.md) does the deep dive and [post 17](../17-advanced-retrieval/index.md) covers the graph and corpus-shape variants.

---

## 8. Layer 05: Conversation history

This is the layer most people think of as "the chat". It is also the layer that runs out of room first, because it gains a turn on every call while the other layers stay roughly the same size.

Three strategies are in common use:

- **Sliding window**: keep the last N turns and drop the rest. Cheap and simple; loses everything older than N.
- **Rolling summary**: keep a summary of older turns plus the most recent turns verbatim. Claude Code's `/compact` command is an instance: Anthropic's engineering post describes Claude Code passing the message history to the model to summarise and continuing from the summary.
- **Selective recall**: embed the conversation and retrieve only the turns relevant to the current question. More work, often worth it.

There is a fourth option: **keep no history at all.** For a stateless task (a one-shot translation, a fresh code review), starting fresh is often both the cheapest and the best behaviour. [Post 12](../12-compress-strategies/index.md) treats these strategies as compression.

---

## 9. Layer 06: The user instruction

The thing the user typed.

Three properties matter for engineering:

1. **It is small.** Usually a sentence or two.
2. **It is placed last.** It is the one part of the window that is new on every call, so placing it last keeps the reusable prefix as long as possible, and the end of a long input is one of the two places where models use information most reliably (section 11).
3. **It is the only layer the user sees.** Everything else is invisible, which is why good context engineering looks, to users, as if the model "just got better".

When users complain about an LLM application, they describe the problem in the language of layer 06, even when the fault lies in one of layers 01 to 05. Recognising which underlying layer is at fault is the skill section 12 turns into a lookup table.

---

## 10. The six layers, in a real API call

The layers become concrete in a request to an application programming interface (API). The sketch below is provider-agnostic Python that assembles a request body in the shape of the Anthropic Messages API and records which layer every entry belongs to. It is an excerpt of `snippets/context_inspector.py`:

```python
def assemble_context(
    *,
    system_prompt: str,
    tool_schemas: list[dict[str, Any]],
    memory: list[str],
    retrieved_chunks: list[str],
    history: list[dict[str, str]],
    user_instruction: str,
) -> tuple[dict[str, Any], list[tuple[str, int]]]:
    """Return a request body in Anthropic Messages shape and the layer of every entry."""
    messages: list[dict[str, str]] = []
    layer_map: list[tuple[str, int]] = [("system", 1)]
    layer_map += [(f"tools[{i}]", 2) for i in range(len(tool_schemas))]

    def add(message: dict[str, str], layer: int) -> None:
        layer_map.append((f"messages[{len(messages)}]", layer))
        messages.append(message)

    # Layer 03: memory replayed as a synthetic exchange
    if memory:
        notes = "\n".join(memory)
        add({"role": "user", "content": f"<memory>{notes}</memory>"}, 3)
        add({"role": "assistant", "content": "Acknowledged."}, 3)

    # Layer 04: retrieved chunks as a user-side evidence block
    if retrieved_chunks:
        evidence = "\n".join(f"<chunk>{c}</chunk>" for c in retrieved_chunks)
        add({"role": "user", "content": evidence}, 4)

    # Layer 05: the prior turns of this session
    for turn in history:
        add(turn, 5)

    # Layer 06: the current user turn, placed last
    add({"role": "user", "content": user_instruction}, 6)

    body = {
        "system": system_prompt,  # layer 01
        "tools": tool_schemas,  # layer 02
        "messages": messages,  # layers 03 to 06
        "model": "claude-sonnet-4-5",  # illustrative; model ids change over time
        "max_tokens": 1024,
    }
    return body, layer_map
```

Running `python posts/02-six-layers-of-context/snippets/context_inspector.py` from the series root needs nothing beyond the standard library and makes no network call. It prints the assembled body, drawn below with each entry bracketed to its layer, and then the layer of every entry:

![The JSON request body printed by the snippet, in Anthropic Messages shape, with coloured brackets on the right: the system field is 01 System prompt, the one tool object is 02 Tools and MCP descriptions, the memory message and its acknowledgement are 03, the chunk message is 04, the earlier question and answer are 05, and the last user message is 06; model and max_tokens are bracketed as call settings, not a layer.](diagrams/02-request-xray.svg)

*Layers 01 and 02 have top-level fields of their own; layers 03 to 06 share the messages list, in the layer order.*

```text
layer map:
  system       01 System prompt
  tools[0]     02 Tools and MCP descriptions
  messages[0]  03 Memory and state
  messages[1]  03 Memory and state
  messages[2]  04 Retrieved chunks
  messages[3]  05 Conversation history
  messages[4]  05 Conversation history
  messages[5]  06 User instruction
```

Every entry of the body belongs to exactly one layer, and the two fields that belong to none, `model` and `max_tokens`, are settings of the call rather than context. Printing the assembled body of a real application in this way is worth the trouble: a bug that looks like a model failure can turn out to be a visible layer 03 or layer 04 problem once the body is on screen.

The same six jobs appear in OpenAI's Chat Completions and Responses APIs and in Google's Gemini `generateContent`; only the field names differ:

| Layer | Anthropic Messages | OpenAI Chat Completions | OpenAI Responses | Gemini `generateContent` |
|---|---|---|---|---|
| 01 System prompt | `system` | first entry in `messages`, role `system` or `developer` | `instructions`, or a `developer` or `system` item in `input` | `systemInstruction` |
| 02 Tools and MCP descriptions | `tools` | `tools` | `tools` | `tools` (`functionDeclarations`) |
| 03 to 05 Memory and state, retrieved chunks, conversation history | entries in `messages` | entries in `messages` | items in `input` | entries in `contents` |
| 06 User instruction | last `user` message | last `user` message | last `user` item in `input` | last `user` entry in `contents` |

*The names change; the six jobs are constant. Anthropic, the Responses API and Gemini can carry the system prompt in a dedicated top-level field, while Chat Completions keeps it as the first entry of the message list. Gemini calls the assistant's role `model`.*

---

## 11. Why the order matters

Three reasons the layer order is not arbitrary.

**Caching.** A prompt cache reuses only an identical prefix. Anthropic's "Prompt caching" documentation states that a cache hit requires the cached segments to be 100% identical, up to and including the block marked for caching, and that a cache read is billed at 0.1 times the base input price for most models (as consulted in October 2026; a cache write costs more than a normal input token). Layers 01 and 02 are the same on every call; if they sit at the front, they can be read from the cache on later calls, provided the prefix reaches the provider's minimum cacheable length and the calls fall within the cache's lifetime. Anything per-turn placed in front of them, or inside them, ends the reusable prefix at that point, and every token after it is billed at the full input rate. One detail differs by provider: Anthropic builds its cache prefix in the order `tools`, `system`, `messages`, so on that API the tool definitions sit even before the system prompt, and a changed system prompt leaves a cached tool list reusable; the principle is the same. [Post 05](../05-economics-of-context/index.md) walks the cost arithmetic.

![Two panels of two consecutive calls drawn as strips of the six layers, with an equals or not-equals sign under each layer. With stable layers first, 01 and 02 are equal and read from the cache while 03 to 06 are billed at the full input rate. With the time of the call written into the system prompt, 01 already differs and nothing is read from the cache.](diagrams/03-prefix-cache.svg)

*Two calls in a row under two layouts, cached in the layer order 01 to 06. Writing the time of the call into the system prompt, an innocent-looking change, costs the whole cached prefix; on Anthropic, which caches the tools first, only the tool definitions survive.*

**Position.** Liu et al. ("Lost in the Middle", 2023) measured how well language models use information placed at different positions in a long input, on multi-document question answering and key-value retrieval. Accuracy was often highest when the relevant information sat at the start or the end of the input and dropped significantly when it sat in the middle. The user's question, the thing the answer must address, therefore belongs at the end; background the model should have read, but need not dwell on, can sit in the middle. [Post 03](../03-how-llms-read-context/index.md) shows the measured curve.

**Failure isolation.** A predictable layering makes debugging linear. If the system prompt is always in the same place and the user instruction is always last, a misbehaving application can be diagnosed by inspecting one layer at a time, rather than by reading tens of thousands of tokens of undifferentiated text.

---

## 12. A pragmatic mental model

The point of the six-layer split is diagnostic. When an application misbehaves, the symptom the user reports often points at a specific layer.

The table below maps common complaints to the layer to inspect first. It is a starting heuristic, not a law: some bugs span layers, and the last column names the post where each is treated in depth.

| Symptom the user reports | Most likely layer | Look at | Treated in |
|---|---|---|---|
| "It ignored an instruction it followed yesterday." | 01 System prompt | A rule was edited, truncated, or buried mid-prompt | [Post 14](../14-system-prompt-as-software/index.md) |
| "It calls the wrong tool or invents parameters." | 02 Tools and MCP descriptions | Vague names or descriptions; too many tools competing | [Post 15](../15-tools-and-mcp/index.md) |
| "It forgot a preference I set earlier." | 03 Memory and state | Nothing was persisted, or the memory was not replayed | [Post 16](../16-memory-systems/index.md) |
| "The answer is confidently wrong on a fact in our docs." | 04 Retrieved chunks | The right chunk was never retrieved, or was reranked out | [Post 11](../11-rag-in-depth/index.md) |
| "It loses the thread in long chats." | 05 Conversation history | The window overflowed, or the key turn fell out of the summary | [Post 12](../12-compress-strategies/index.md) |
| "It answers a different question than I asked." | 06 User instruction | The request is buried above other content, not placed last | [Post 06](../06-context-failure-modes/index.md) |

The layers double as a checklist. Faced with any context bug, walk them from 01 to 06 and ask *"is this layer carrying what it should, and nothing it should not?"* Once the layers are named, the faulty one is often easy to spot. The failure modes themselves (distraction, confusion, conflict, lost-in-the-middle, tool-storm) get their own systematic treatment in [post 06](../06-context-failure-modes/index.md).

---

## 13. What can go wrong?

- **A per-turn value lands in the stable prefix.** A timestamp, a user name or a retrieved snippet is formatted into the system prompt. Nothing looks wrong in the answers, but the usage block of every response reports few or no cache-read tokens (`cache_read_input_tokens` on Anthropic) and the cost per call never drops. The fix is to move the value into layer 03, 04 or 06.
- **The tool list changes between deploys.** Tools are added, removed or reordered on each release, or generated in an unstable order. Each change rewrites the cached prefix, so the first calls after every deploy run at the full input rate. Sorting the tool list and changing it deliberately keeps the prefix stable.
- **Memory and retrieval share one block.** Remembered preferences and freshly retrieved evidence are pasted together. When an answer is wrong, it is no longer possible to tell whether a stale memory or a bad chunk caused it, and fixing one layer silently changes the other.
- **The question is placed before the evidence.** The user instruction goes first and thirty retrieved chunks follow it. The model answers something adjacent to what was asked, or summarises the chunks instead of answering, because the instruction now sits far from the end of a long input.
- **The history is never trimmed.** Every turn is resent in full. The cost per call climbs turn after turn, and eventually the provider rejects the request because it exceeds the context window.

---

## Common pitfalls

1. **Stuffing per-turn data into the system prompt.** It feels important, and it ruins caching; per-turn data belongs in layer 03, 04 or 06.
2. **Letting tool schemas grow unbounded.** Every tool costs tokens on every call; as an illustrative rule of thumb, a tool that is not worth 200 tokens of the model's attention on every turn should not be a tool.
3. **Mixing memory and retrieval.** Memory answers "what is known and persists?", retrieval answers "what is needed for this turn?", and conflating them makes both layers harder to debug.
4. **Treating history as free.** Layer 05 is resent on every call, so in a long session it becomes the largest layer and the largest share of the input bill.
5. **Debugging the wall of text instead of the layer.** Name the symptom, map it to a layer with the table in section 12, and inspect that layer alone.

---

## Further reading

- Anthropic Engineering, *"Effective context engineering for AI agents"* (September 2025): the components of context and compaction in Claude Code.
- Anthropic, *"Prompt caching"* documentation: the identical-prefix rule, the cache order of tools, system and messages, and the cache-read price.
- Anthropic, *"Introducing Contextual Retrieval"* (September 2024): the contextual-chunking technique named in section 7.
- IBM Think, *"What is context engineering?"* (2025): an alternative list of the parts of a context.
- Liu, N. F. *et al.*, *"Lost in the Middle: How Language Models Use Long Contexts"* (arXiv 2023, TACL 2024): the position result of section 11.
- OpenAI, API reference for Chat Completions and Responses: the OpenAI field names in section 10.
- Google, Gemini API reference, *`generateContent`*: the Gemini field names in section 10.

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 03 - How LLMs actually read context](../03-how-llms-read-context/index.md):** the tokens, attention, positions and caching behind why the order of these layers matters.
- **[Post 06 - Five context failure modes](../06-context-failure-modes/index.md):** turns the symptom table of section 12 into five named failures, each with a first fix.
