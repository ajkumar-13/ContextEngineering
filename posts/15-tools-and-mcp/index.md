# 15 · Tools and MCP

> **TL;DR.** Tools are how an LLM acts on the world; tool *descriptions* are part of the prompt and obey the same scarcity laws as everything else in it. The **iron triangle of tool design**: *catalogue size*, *per-tool description quality*, *runtime selection* — captures every trade-off that matters. **MCP (Model Context Protocol)** is the open standard that lets a single host load tools from many vendors without bespoke glue. This post covers the design principles, the selection pipeline, MCP's place in the picture, and the failure modes that recur.
>
> **After reading this you will be able to:**
> - Design tool descriptions that the model will actually use correctly.
> - Manage a large tool catalogue without polluting the prompt.
> - Decide when MCP is the right integration choice and when bespoke glue still wins.
> - Choose between a tool call and a structured `response_format` for a given task.

![MCP has three roles: the host application, an MCP client inside it, and one or more MCP servers exposing tools, resources, and prompts](diagrams/05-mcp-triangle.svg)

*The Model Context Protocol in one picture: a host embeds an MCP client that speaks the protocol to one or more servers, each exposing tools, resources, and prompts. The design tensions those tools create, catalogued in [§2](#2-the-iron-triangle), are this post's real subject.*

---

## 1. Why tools are a context-engineering topic

A tool, from the model's perspective, is its **schema as text in the prompt**. Five tools cost a few hundred tokens; fifty cost a few thousand; five hundred do not fit. Every tool the model can see costs context space whether or not the model uses it on this turn. Every tool the model *cannot* see is a capability it does not have.

That is the entire problem. Everything else in this post is a way of resolving it.

---

## 2. The iron triangle

![A triangle whose vertices are catalogue size, description quality, and runtime selection, with a card for each pair a design can keep](diagrams/01-iron-triangle.svg)

*Each edge is a pair you can keep. The card beneath it names what that costs, and what it looks like when it goes wrong.*

Three properties of a tool catalogue trade off against each other.

- **Catalogue size**: how many tools the system as a whole exposes.
- **Per-tool description quality**: how rich, specific, and example-laden each schema is.
- **Runtime selection**: how aggressively the host filters the catalogue before it ever reaches the model.

A design can keep **any two**.

- *Big catalogue + rich descriptions, no selection* → the prompt is unusable. This is the most common failure of demo MCP setups.
- *Big catalogue + aggressive selection, but thin descriptions* → the model is inconsistent in its tool use because it has to guess from a one-line summary.
- *Rich descriptions + no selection, small catalogue* → the comfort zone. Works fine until the product needs more capabilities.

A production design picks two and accepts the trade-off on the third *consciously*. Most successful designs end up at "**big catalogue + rich descriptions + aggressive runtime selection**", accepting the engineering cost of the selection pipeline as the price of scaling.

---

## 3. Designing a single tool

![The six components of a tool description, numbered, beside one search_orders description that carries all six](diagrams/02-tool-description.svg)

*The numbers on the left match the numbers in the gutter on the right, so each component can be found in a real description.*

Treat a tool description like a function docstring that an unfamiliar contractor will read once. Six things every description should carry:

1. **Name.** A `verb_object` form: `search_orders`, `create_ticket`, `cancel_subscription`. Avoid adjectives, abbreviations, and family-prefix conventions that conflict ("`get_users` vs. `fetch_users` vs. `list_users`" is the recipe from [Post 06](../06-context-failure-modes/index.md), §4).
2. **One-line summary.** What this tool does, in 10–15 words. The model uses this to decide *whether* to reach for it.
3. **When to use it.** One sentence. *"Use this to look up an order when the user provides an order id."*
4. **When *not* to use it.** One sentence. *"Do NOT use this for refunds; use `issue_refund` for refunds."* Negative guidance prevents most miscalls.
5. **Parameters.** Each with a type, required/optional, default, and a one-line description. Types should be primitives or named enums; avoid free-form strings where an enum suffices.
6. **One worked example.** Input and expected output. Examples beat paragraphs of explanation for tool calls.

Anti-pattern: a 300-token tool description that is mostly disclaimers and edge-case caveats. The disclaimers belong in code (the tool itself can refuse invalid inputs). The description should make the tool *easy to call right*, not *hard to call wrong*.

---

## 4. The catalogue problem

A useful agent often has access to dozens or hundreds of tools: every endpoint of every internal service, every MCP server the team has installed, every legacy script wrapped for the agent. The naïve "load them all" approach breaks down once a catalogue reaches a few dozen tools (as a rule of thumb, somewhere in the low tens): the schemas alone bloat the prompt, and near-duplicate names start to confuse selection.

The way out is the same Select pipeline as RAG (retrieval-augmented generation; [Post 09](../09-select-strategies/index.md)) applied to tool schemas as the corpus.

```
all tools (~500) → embed offline
                ↓
user turn  →  query rewrite  →  hybrid retrieval (top-30)
                              ↓
                        cross-encoder rerank → top-K (4-8)
                              ↓
                        pack schemas into the tools layer
```

Vendor reports describe the pattern concretely. Anthropic's "Code execution with MCP" write-up (Anthropic, 2025) illustrates a connector exposing on the order of thousands of tool definitions, where loading only the handful relevant to the current turn behaves *better* than a small bespoke catalogue, because the retrieved few are exactly the relevant few. (The exact figures are illustrative of the shape, not a fixed benchmark.)

Two implementation details that make or break this pipeline:

- **The tool-schema embedding includes the description, not just the name.** Embedding "`search_orders`" alone produces near-collisions with every other search-named tool.
- **The rerank stage is non-optional.** Bi-encoder retrieval (embedding the query and each tool separately, then comparing vectors) over short tool descriptions is noisy; a cross-encoder reranker, which scores the query and candidate together (the reranker introduced in [Post 09](../09-select-strategies/index.md), §4), often improves precision substantially at the cost of a modest per-turn latency. The trade is almost always worth it for a tool catalogue.

Tool selection is the engineering practice that makes large catalogues *possible*. Without it, agents either run with permanently small toolboxes or with the chronic confusion described in [Post 06](../06-context-failure-modes/index.md), §4.

---

## 5. MCP: the integration story

The **Model Context Protocol (MCP)** is an open standard, first published by Anthropic in November 2024, that lets a host application (Claude Desktop, Claude Code, Cursor, Continue, Zed, and a growing list of others) connect to **MCP servers** that expose tools, resources, and prompts in a uniform way. The wire protocol is JSON-RPC over stdio or HTTP, and the specification is deliberately compact.

The value MCP delivers is **the same one OpenAPI delivered for REST**: a vendor-neutral way to publish capabilities so that any compliant host can use them. Before MCP, integrating an internal service into Claude Code, Cursor, and a custom agent meant writing three different adapters. With MCP, a team writes one MCP server; all three hosts can reach it.

Concretely an MCP server exposes three things:

- **Tools**: actions the model can invoke (`create_pull_request`, `query_warehouse`, `book_meeting`).
- **Resources**: read-only data sources the host can fetch and inject (a Confluence page, a database table, a file path).
- **Prompts**: re-usable prompt templates the user can invoke as commands.

The most common production deployment is **the local stdio server**: a small process the host launches; communication is over stdin/stdout; auth happens via local config. The newer **HTTP transport** is for remote / multi-tenant deployments.

What MCP does **not** solve, and what teams routinely underestimate:

- **MCP does not solve catalogue size.** A big MCP server with 200 tools will pollute the prompt unless the host runs the selection pipeline from §4. Several hosts now ship with built-in tool selection; some do not.
- **MCP does not solve security.** Any tool exposed via MCP is a tool the agent can be tricked into calling ([Post 23](../23-security/index.md)). The protocol carries no permission model worth the name; permissioning is the host's responsibility.
- **MCP does not solve observability.** What the agent did with a tool, why, and at what cost: those are the host's problem.

The right mental model: **MCP is the bus**, not the car. It standardises how tools are connected; the discipline of using them well is unchanged.

---

## 6. Permissions and confirmations

A tool that can act on the real world (issue a refund, send an email, deploy code, run a payment) needs a **permission boundary** that is *not* the model's good judgement.

Three patterns in production use:

- **Confirmation prompts.** The agent proposes the action; the user clicks confirm; the host executes. Default for any irreversible action. Costs one round-trip in latency; pays for itself the first time it prevents a mistake.
- **Capability scoping.** A tool is exposed to the agent with a narrowed scope: `issue_refund` is wired so it can only refund up to $X without escalation, regardless of what the model asks. Defence in code, not in prompt.
- **Tool-level audit.** Every tool call is logged with the prompt that produced it, the parameters, the result, and the user / session id. The audit log is what makes incident response possible after a misuse.

The general rule: **the model's prompt is not a permission system.** "Do not call `delete_account` without confirmation" in the system prompt will be obeyed most of the time and ignored some of the time. The host needs to enforce it whether or not the prompt asked.

---

## 7. Sandboxing: keep tool noise out of the context

A point already raised in [Post 13](../13-isolate-strategies/index.md), §6 and worth restating: anything a tool returns enters the model's context on the next turn. Verbose tool outputs (build logs, web pages, query results, stack traces) are how a 50 k context fills to 200 k in a few turns.

The discipline:

- **Return structured results, not raw streams.** `{ ok: true, duration_ms: 8742 }` instead of 4 000 lines of `npm install` output.
- **Keep the verbose log on disk for debugging.** A `log_path` in the structured result lets a human re-open it without forcing the model to read it.
- **Truncate or summarise where the result is genuinely large.** Web fetches in particular: extract the main content, return that; archive the full HTML.

Sandboxing is mechanically simple and operationally one of the largest cost wins in agent design.

---

## 8. The selection pipeline in production

A short reference for what a serious tool-selection layer looks like.

```python
# Once, offline
for tool in all_tools:
    text = f"{tool.name}\n{tool.description}\n" + \
           "\n".join(f"  {p.name}: {p.description}" for p in tool.params)
    index.upsert(id=tool.id, vector=embed(text), metadata=tool.metadata)

# On every user turn
def select_tools(user_turn, conversation):
    query = rewrite_query(user_turn, conversation)
    candidates = hybrid_search(index, query, k=30)
    reranked = cross_encoder_rerank(query, candidates, k=8)
    return [load_full_schema(t.id) for t in reranked]
```

Three operational notes:

- **Cache aggressively.** Tool schemas change rarely; the embedding index is mostly read-only.
- **Always include "essential" tools** (a couple that should never be filtered out) regardless of relevance, the equivalent of the P0 tier in priority pruning ([Post 12](../12-compress-strategies/index.md), §5).
- **Log the selection.** Every turn's chosen tools, with the rerank scores, in the same trace as the model's response. This is the only way to debug "why didn't the agent use tool X" after the fact.

---

## 9. Structured output: when the answer *is* the payload

Tool calling and structured output are two views of the same machinery. A tool call is the model emitting a JSON object that conforms to a schema (the tool's parameters) so that code can run; structured output is the model emitting a JSON object that conforms to a schema so that code can *parse the answer*. The second half of this topic is worth its own treatment, because a large fraction of production LLM work is not "act on the world" but "return a typed result the rest of the pipeline can trust".

**Function-calling refresher.** Every major provider exposes the same shape: alongside the prompt you pass a list of tool (or function) definitions, each a name, a description, and a JSON-Schema object for its parameters. The model may respond with normal text or with a structured call naming a tool and its arguments. The provider guarantees the arguments validate against the schema you supplied. Anthropic's tool-use API and OpenAI's function-calling API (OpenAI, "Function calling" docs) are the two references; the request shape differs, the mental model does not.

**Structured output proper.** When the goal is a typed answer rather than an action, prefer the provider's dedicated structured-output path over a dummy tool. In practice the schema is authored once and reused three ways:

- **JSON Schema** is the wire format every provider ultimately consumes.
- **Pydantic** (Python) lets you define the schema as a class and get validation plus `.model_json_schema()` for free; most SDKs accept a Pydantic model directly.
- **Instructor** and **Outlines** are thin libraries that wrap this pattern: Instructor patches the provider client so a call returns a validated Pydantic object (retrying on validation failure); Outlines enforces the schema during generation.

**Constrained decoding** is what makes the strong guarantee possible. Instead of asking the model nicely for JSON and hoping, the decoder masks the token distribution at each step so that only tokens consistent with the grammar (the JSON Schema, compiled to a state machine) can be sampled. The output is then valid JSON by construction, not by luck. This is the mechanism behind "strict" or "JSON mode" flags across providers.

**When to prefer `response_format` over a tool.** Use the structured-output path (`response_format` / a strict schema) when the model's job is to *return data* and there is exactly one shape you want back: classification labels, extraction results, a filled form. Use a *tool* when the model is *choosing whether and which* action to take, possibly among several, possibly none. A rough rule of thumb: one always-required shape → `response_format`; a menu of optional capabilities the model selects among → tools. Forcing a single structured answer through a tool works but muddies the trace (it looks like the model "called" something when it merely answered).

Structured output is where reliability lives: a downstream service that receives guaranteed-valid JSON needs no defensive parsing. The build posts put this to work end to end ([Post 28](../28-build-rag-chatbot/index.md) and [Post 30](../30-capstone-email-reply-agent/index.md)).

---

## Common pitfalls

- **Loading all tools.** Cap at the size your prompt budget can afford.
- **Tool names that look alike.** `get_user`, `get_users`, `fetch_user`, `list_users` in one catalogue is a Post 06 confusion bug waiting to happen.
- **No "when not to use".** The single highest-leverage line in a tool description.
- **Free-form parameters where an enum exists.** A `status: string` parameter the model fills with one of "open" / "closed" / "Open" / "OPEN" is a bug.
- **MCP integration without runtime selection.** Catalogue size dominates the prompt.
- **Treating the prompt as the permission system.** Permissions enforce in code.
- **Verbose tool outputs in context.** Sandbox the noisy ones.

---

## Further reading

- Anthropic, *"Introducing the Model Context Protocol"* (2024): the announcement.
- modelcontextprotocol.io, *"Specification"* (latest): the wire protocol.
- Anthropic Engineering, *"Equipping agents for the real world with Agent Skills"* (2025).
- Anthropic, *"Code execution with MCP"* (2025): the tool-result-clearing reference design.
- OpenAI, *"Function calling"* docs: the model-side counterpart, and the reference for `response_format` / structured outputs.
- Instructor and Outlines (project docs): structured-output and constrained-decoding libraries referenced in §9.
- Cognition, *"Don't build multi-agents"* (2025): argues that *better tools* often beat *more agents*, sharpens the discipline.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 16 — Memory systems](../16-memory-systems/index.md)**: the persistent counterpart to runtime tool selection.
- **[Post 14 — The system prompt as software](../14-system-prompt-as-software/index.md)**: where tool descriptions sit relative to the rest of the prompt.
- **[Post 23 — Security](../23-security/index.md)**: what tools enable an attacker to do, and how to constrain it.
- **[Post 13 — Isolate strategies](../13-isolate-strategies/index.md)**: when tools are not enough and you need sub-agents.
