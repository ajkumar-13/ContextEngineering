# 15 - Tools and MCP

> **TL;DR.** A tool is text in the prompt: its name, description and parameter schema ride in layer 02, tools and MCP descriptions, on every call. The iron triangle (catalogue size, description quality, runtime selection) names the trade every tool catalogue makes. The Model Context Protocol (MCP) standardises how a host loads tools from many servers, and leaves catalogue size, permissions and observability to the host.
>
> **Prerequisites:** [Post 09](../09-select-strategies/index.md), [Post 14](../14-system-prompt-as-software/index.md).
> **Safe to skip?** Skip it if a six-part tool description can already be written, a catalogue priced per call and cut by selection without breaking the cache, and MCP's three roles placed in the six layers.
>
> **After reading, you will be able to:**
>
> - Design a tool description with a name, a summary, when to use it, when not to, typed parameters and an example, so the model calls it correctly.
> - Price a tool catalogue in tokens per call, cut it with a runtime selection step, and say what selection does to the prompt cache.
> - Name what MCP's host, client and server each own, and decide when MCP is the right integration and when bespoke glue still wins.
> - Choose between a tool call and a structured response format for a task, and say what a strict schema does and does not guarantee.
> - Enforce a tool's permissions and output size in code, with confirmations, capability scoping, an audit log and a sandbox, rather than in the prompt.

![A host holds the model's six-layer window and one MCP client per server. The refunds-demo server exposes a tool, a resource and a prompt over stdio; the tool's schema lands in 02 Tools and MCP descriptions, an attached resource in 04 Retrieved chunks, a picked prompt in 06 User instruction.](diagrams/00-hero-mcp-roles.svg)

*The model decides on tools, the application on resources, the user on prompts; each reaches the model only as text in a layer.*

---

## 1. The question: why are tools a context-engineering topic?

A tool, from the model's side, is text: a name, a description and a JavaScript Object Notation (JSON) Schema for its parameters, sent in layer 02, tools and MCP descriptions, on every call. OpenAI's "Function calling" guide (consulted October 2026) says function definitions are injected into the system message and "count against the model's context limit and are billed as input tokens". Anthropic's "Tool use with Claude" page (consulted October 2026) adds a tool-use system prompt that the application programming interface (API) writes whenever tools are present: 496 tokens for Claude Sonnet 4.5 with automatic tool choice, on top of the definitions.

Every tool the model can see costs window space and money on every call, used or not; every tool it cannot see is a capability it lacks. The companion `code/15-tool-schemas` puts a number on it: fifty toy shop tools, each described as section 3 recommends, come to an estimated 6,348 tokens per call (section 4).

---

## 2. The iron triangle

Three properties of a tool catalogue pull against each other:

- **Catalogue size**: how many tools the system as a whole exposes.
- **Description quality**: how specific, complete and exemplified each description is.
- **Runtime selection**: how aggressively the host filters the catalogue for each turn before the model sees it.

Size and quality multiply: the tokens in layer 02 are roughly the tools shown times the tokens per tool, so without selection both cannot grow inside a fixed budget. A design gets any two of a large catalogue, rich descriptions and no selection machinery, as the figure below draws.

![A triangle of three goods: no selection step, a large catalogue, rich descriptions. No selection with a large catalogue cuts descriptions and confuses the model; no selection with rich descriptions keeps the catalogue small; a large catalogue with rich descriptions pays for runtime selection. All three at once, in red, overflows layer 02 into tool-storm.](diagrams/01-iron-triangle.svg)

*The trade is made whether or not anyone chooses it; choosing it deliberately is the difference.*

- *Large catalogue and rich descriptions, no selection*: layer 02 outgrows its budget and the tool-storm of [post 06](../06-context-failure-modes/index.md) follows. A demo that connects every MCP server a team owns lands here.
- *Large catalogue, no selection, descriptions cut to fit*: the model chooses from one-line summaries, the confusion of post 06.
- *Rich descriptions, no selection, a small catalogue*: the comfort zone, until the product needs more capabilities.

Keeping a large catalogue and rich descriptions means paying for the third vertex: a selection pipeline, a retrieval step per turn, and a cache decision (section 4).

---

## 3. Designing a single tool

Anthropic's "Define tools" page (consulted October 2026) calls detailed descriptions "by far the most important factor in tool performance" and asks for at least three to four sentences per tool. Six parts make a description a newcomer could use correctly; the figure below marks them on one tool of the toy catalogue.

![The JSON definition of search_shipments with six numbered markers: the name; the summary; when to use it; when not to, naming get_shipment; the parameters, with a status enum and additionalProperties false; and an input example.](diagrams/02-tool-anatomy.svg)

*Parts 2 to 4 are sentences of the description, part 5 is the schema, part 6 an example; the model reads all of it on every call.*

1. **Name.** A `verb_object` form: `search_shipments`, `get_order`, `cancel_subscription`, with one convention across the catalogue. `get_user`, `fetch_user` and `list_users` side by side are the near-identical names behind the confusion of [post 06](../06-context-failure-modes/index.md), section 3. When a catalogue spans services, the same page recommends a service prefix (`github_list_prs`).
2. **One-line summary.** What the tool does, in about 10 to 15 words; the model reads it to decide whether to reach for the tool at all.
3. **When to use it.** One sentence naming the situation: *"Use it when the user describes shipments but gives no shipment id."*
4. **When not to use it.** One sentence naming the tool to use instead: *"Do not use it when a shipment id is known; use get_shipment instead."* It is post 06's first fix for confusion.
5. **Parameters.** Each with a type, whether it is required, and a one-line description. A `status` free string that the model fills with "failed", "Failed" or "delivery failed" is a bug; an enum lets the schema reject all three, and `additionalProperties` set to false rejects an invented argument.
6. **One worked example.** An input the tool accepts. Anthropic's API has a field for it, `input_examples`; each entry must validate against the schema and costs about 20 to 50 tokens for a simple example, the page says.

An anti-pattern: a 300-token description (an illustrative size) that is mostly disclaimers. Disclaimers belong in code, because the tool can refuse an invalid input; the description should make the tool easy to call right, not hard to call wrong.

---

## 4. The catalogue problem and runtime selection

Loading every tool fails twice. The window fills: Anthropic's "Tool search tool" page (consulted October 2026) puts five MCP servers (GitHub, Slack, Sentry, Grafana and Splunk) at about 55,000 tokens of definitions before any work starts. And choice degrades: the same page says Claude's ability to pick the right tool degrades past 30 to 50 tools; OpenAI's guide suggests fewer than 20 functions at the start of a turn, as "a soft suggestion"; and post 06 recounts Breunig's report of a small model that failed with 46 tools and succeeded with 19.

The way out is the select operation of [post 09](../09-select-strategies/index.md) with tool schemas as the corpus: index each schema offline (name, description and parameter descriptions together, since names alone make every `search_` tool look alike), retrieve candidates for the rewritten turn, re-rank, and pack the survivors into layer 02. Agent Skills applies the same idea to instructions, loading only each skill's name and description up front ([post 08](../08-write-strategies/index.md)).

The snippet `snippets/catalogue_budget.py` runs the smallest version against the companion's calculator, over ten services of a toy shop with five operations each. Its selection step scores each schema by the words it shares with the turn:

```python
def select_tools(turn, catalogue, k=5):
    """Score each schema by the words it shares with the turn, rarer words weighing more; keep the top k."""
    docs = [words(json.dumps(tool)) for tool in catalogue]
    df = Counter(w for d in docs for w in d)
    query = words(turn)
    scores = [sum(math.log(len(docs) / df[w]) for w in query & d) for d in docs]
    ranked = sorted(range(len(catalogue)), key=lambda i: -scores[i])  # ties keep catalogue order
    return [catalogue[i] for i in ranked[:k]]
```

Run from the series root as `uv run python posts/15-tools-and-mcp/snippets/catalogue_budget.py`, it prints:

```text
catalogue: 50 tools; one turn: 'Order A-4821 shipped last week, but the tracking number shows no delivery. Where is it?'
selected: get_shipment, search_orders, get_order, search_shipments, create_order
trim(keep=5) instead: search_orders, get_order, create_order, update_order, cancel_order (644 estimated tokens)

tools in layer 02            estimate  o200k_base  dollars per call at 3 per million
50 rich, no selection            6348        5680  0.019044
50 thin, no selection            2430        2075  0.007290
5 rich, selected                  681         621  0.002043
selection keeps 681 of 6348 estimated tokens (10.7 percent)
50 rich read from cache at 0.30 per million: 0.001904 dollars per call

validate {"email": "ana@example.com", "status": "delivery_failed"}: valid
validate {"email": "ana@example.com", "status": "failed"}: ["$.status: 'failed' not in enum ['in_transit', 'delivered', 'delivery_failed']"]
validate {"shipment": "A-4821"}: ["$: additional property 'shipment' is not allowed"]
```

![Left, estimated tokens per call in layer 02: 50 rich tools 6,348, 50 thin tools 2,430, 5 selected rich tools 681. Right, the five tools kept for the turn about order A-4821, with create_order marked as a near miss that matched only the word order.](diagrams/03-selection-budget.svg)

*Selection cuts layer 02 to about a tenth and keeps the tools that fit and one near miss, which is what a reranker is for.*

Selection keeps 681 of 6,348 estimated tokens, 10.7 percent, and four of its five tools fit the turn, `search_orders` only by its rank; `create_order` got in on the word "order", the near miss a cross-encoder reranker ([post 09](../09-select-strategies/index.md), section 4) is there to demote. The companion's `trim` keeps the first five tools: 644 tokens, but three of them are wrong for the turn and no shipment tool is among them. Thin descriptions save less and pay in miscalls. Prices use Claude Sonnet 4.5's input rate as of early 2026, 3 dollars per million tokens ([post 05](../05-economics-of-context/index.md)). The estimates assume four characters per token; OpenAI's `o200k_base` encoding counts 9 to 15 percent fewer, and neither is Claude's tokeniser ([post 04](../04-tokens-windows-budgets/index.md)). The last lines are the companion's validator rejecting a near-miss value and an invented argument.

**Selection and the cache.** Layer 02 belongs to the stable prefix, so a tool list that changes every turn changes the prefix a prompt cache reuses (post 09, section 6). With a cache read at 0.1 times the base input price, the rule post 05 states for most Claude models, the full fifty-tool catalogue read from cache costs 0.001904 dollars per call, less than the five selected tools sent uncached at 0.002043. When the catalogue caches, selection buys attention and window space, not money. To keep both, a design keeps a fixed core in the prefix and adds selected tools after it. Anthropic's tool search tool does this: tools marked `defer_loading` stay out of the prefix, Claude searches for them, and the API expands what it finds inline in the conversation; in the page's words, "The prefix is untouched, so prompt caching is preserved."

**At larger scale.** Anthropic's "Code execution with MCP" (November 2025) presents MCP servers to the agent as code APIs in a file tree, so it reads a definition only when needed and filters tool results in code; its example task falls from 150,000 tokens to 2,000.

**In production.** Always include a few essential tools whatever their score, as priority pruning never trims its P0 band ([post 12](../12-compress-strategies/index.md), section 5), and log every turn's selection with its scores in the trace, so that "why did the agent not use tool X?" can be answered afterwards.

---

## 5. MCP: host, client and server

The **Model Context Protocol** is the open standard, introduced by Anthropic in November 2024, through which a host application connects to servers that expose capabilities in one uniform way. This post follows the specification's revision of 2026-07-28 (modelcontextprotocol.io, consulted October 2026), as the MCP series does; its opening post, `mcp-001`, explains the problem the protocol solves. The hero figure draws the three roles:

- **Host**: the application the user works in (Claude Desktop, Cursor, VS Code). It owns the model, the conversation and every consent decision.
- **Client**: a connector inside the host; each client communicates with exactly one server.
- **Server**: a process, local or remote, that exposes three primitives.

Messages are JSON-RPC 2.0 (JSON remote procedure call), over standard input and output (stdio) to a server the client launches as a subprocess, or over Streamable HTTP (Hypertext Transfer Protocol) to a remote one. The primitives differ in who decides to use them, and so in where they enter the window:

| Primitive | Controlled by (specification) | Enters the window as |
|---|---|---|
| Tools | the model | layer 02, tools and MCP descriptions |
| Resources | the application | content the host attaches, for example in layer 04, retrieved chunks |
| Prompts | the user | a template the user picks, which becomes layer 06, the user instruction |

One server reaches Claude Code, Cursor and a custom agent, where three adapters were needed before.

**When bespoke glue still wins.** MCP pays when a capability is reused across hosts or comes from someone else's server. A tool used by one application and tied to its own state is simpler as a plain tool definition in that application's request: no subprocess, no protocol, one place to test. The model sees the same layer 02 text either way; MCP changes the integration cost, never the context cost.

What MCP does not solve:

- **Catalogue size.** A server with 200 tools fills layer 02 like any 200 tools unless the host selects (section 4).
- **Security.** In the specification's words, "MCP itself cannot enforce these security principles at the protocol level"; enforcement is the host's (section 6), and [post 23](../23-security/index.md) covers the attacks.
- **Observability.** What the agent did with a tool, why and at what cost is the host's to record ([post 22](../22-observability/index.md)).

The mental model: **MCP is the bus, not the car.**

The companion `code/15-mcp-quickstart` is a 49-line server with one tool, one resource (`refunds://policy`) and one prompt (`draft_refund_reply`) around a pure module of refund rules. Its tool, from `server.py`:

```python
@mcp.tool()
def check_refund(order_id: str, amount_usd: float) -> dict:
    """Check whether a refund may proceed for an order. Returns a structured decision."""
    order = lookup_order(order_id)  # the order's facts come from the store, never from the model
    if order is None:
        return {"eligible": False, "requires_manager_approval": False, "reason": f"Unknown order {order_id}."}
    d = check_refund_eligibility(order, amount_usd)
    return {
        "eligible": d.eligible,
        "requires_manager_approval": d.requires_manager_approval,
        "reason": d.reason,
    }
```

The decorator turns the function's name, type hints and docstring into the tool's name, input schema and description: layer 02 text. The docstring falls short of section 3: no when-to-use or when-not-to-use line. The tool itself follows section 6: it takes only the order id and the amount from the model and looks the rest up, because a value the model supplies is one it can get wrong.

---

## 6. Permissions and confirmations

A tool that acts on the world (issue a refund, send an email, deploy code) needs a permission boundary that is not the model's judgement. Three patterns provide one.

**Confirmation.** The agent proposes, the user confirms, the host executes: the default for any irreversible action, at the cost of one round trip. The MCP specification asks the same of hosts: they "must obtain explicit user consent before invoking any tool".

**Capability scoping.** The tool cannot do more than its scope, whatever it is asked. The quickstart's rules are an example; `uv run python posts/15-tools-and-mcp/snippets/refund_gate.py` runs them on four requests and prints:

```text
A-4821    120.00  eligible=True, manager=False   Eligible for automatic refund.
B-1177   1500.00  eligible=True, manager=True    Eligible, but $1500.00 is over $1000 and needs manager approval.
C-0932     80.00  eligible=False, manager=False  Outside the 30-day return window (41 days since purchase).
D-5510     95.00  eligible=False, manager=False  Requested $95.00 exceeds order total $60.00.
```

A 1,500-dollar refund needs a manager's sign-off, and a request after 30 days or above the order total is refused, however it is worded.

**Audit.** Every tool call is logged with its request, arguments, result and user and session ids, so an incident can be traced.

The rule: **the prompt is not a permission system.** "Do not call `delete_account` without confirmation" in a system prompt is followed most of the time; the host enforces it every time.

---

## 7. Sandboxing: keep tool noise out of the window

Anything a tool returns enters the window on the next call, so verbose output (build logs, web pages, stack traces) can fill a window in a few turns. [Post 13](../13-isolate-strategies/index.md), section 6 gives the pattern, sandboxing in its output-scoping sense (the security sense is post 23's): its snippet kept a 2,385-token install log on disk and passed 38 tokens to the model.

- **Return structured results, not raw streams.** `{"ok": true, "duration_ms": 8742}` instead of pages of install output.
- **Keep the verbose log on disk**, with its path in the result so a person can open it.
- **Extract or truncate large results.** From a web page, return the main text and archive the markup.

Anthropic's "Define tools" page agrees: "Bloated responses waste context and make it harder for Claude to extract what matters."

---

## 8. Structured output: when the answer is the payload

A tool call is the model emitting a JSON object that conforms to a schema so that code can run; structured output is the model emitting one so that code can parse the answer.

**The guarantee comes from strict mode, not from the schema.** By default a schema is guidance. OpenAI's guide says that setting `strict` to true makes function calls "reliably adhere to the function schema, instead of being best effort"; its Responses API tries to normalise schemas into strict mode, while Chat Completions stays non-strict by default. Anthropic's equivalents are `strict: true` on a tool and `output_config.format` for a typed answer, which its "Structured outputs" page says guarantee schema-compliant responses through constrained decoding (all consulted October 2026).

**Constrained decoding** lets only tokens the schema's grammar allows be sampled at each step. Anthropic's page still lists exceptions (a refusal, a reply cut off at `max_tokens`, an enum value differing only in capitalisation), so a validator such as the companion's `validate` checks at the boundary and sends its errors back in a retry.

**Tool or structured response?** The field is `response_format` in OpenAI's Chat Completions, `text.format` in its Responses API, and `output_config.format` in Anthropic's Messages API. When the answer has exactly one shape (a label, an extraction, a filled form), use that field; when the model chooses whether and which action to take, among several or none, use tools. OpenAI's "Structured Outputs" guide draws the same line. Forcing a single answer through a dummy tool works but muddies the trace: the model seems to have called something when it only answered.

Pydantic, Instructor and Outlines are Python libraries for authoring and enforcing such schemas; [post 21](../21-structured-output-guardrails/index.md) goes deep on structured output and its guardrails.

---

## 9. Make it run

Both companions have an offline core whose tests need no key and no network. From the series root:

```text
uv run --with pytest python -m pytest code/15-tool-schemas/tests
uv run --with pytest python -m pytest code/15-mcp-quickstart/tests
```

They end with `8 passed` and `7 passed`. The snippets import the same packages from each companion's `src` with no install:

```text
uv run python posts/15-tools-and-mcp/snippets/catalogue_budget.py
uv run python posts/15-tools-and-mcp/snippets/refund_gate.py
```

The first is this post's lab at toy scale; rewording `TURN` shows what each wording selects. The lab's last step, starting the quickstart server in an MCP host, needs the `mcp` software development kit (SDK), which the series environment does not install, so it is not run here. The companion's README gives the install command and the host configuration, the same shape for Claude Desktop and Cursor:

```json
{
  "mcpServers": {
    "refunds-demo": { "command": "python", "args": ["/abs/path/to/server.py"] }
  }
}
```

---

## 10. What can go wrong?

- **A catalogue that grows one server at a time.** Each MCP server added for one feature brings all its tools, and the bill and the miscalls rise unnoticed.
- **Selection that breaks the cache.** Schemas chosen per turn are written into layer 02. The tool-storms stop, and the input bill rises because the prefix differs on every call.
- **Thin descriptions that defeat selection too.** The index embeds one-line summaries, every `search_` tool looks like the others, and retrieval and the model guess together.
- **The model as the source of a limit.** A tool checks a refund rule against the order total the model passed in, and a wrong or injected argument passes the check.
- **A schema trusted as a guarantee.** The handler skips validation because "the schema says so", and a capitalised enum value, which even Anthropic's strict mode does not rule out, crashes it in production.

---

## Common pitfalls

1. **Loading every tool.** Size layer 02 to its budget and select the rest per turn.
2. **Tool names that look alike.** `get_user`, `get_users`, `fetch_user` and `list_users` in one catalogue is post 06's confusion waiting to happen.
3. **No "when not to use" line.** It is the cheapest line in a description, and it prevents miscalls between neighbouring tools.
4. **Free strings where an enum exists.** A `status` the model fills with "open", "Open" and "OPEN" is three bugs.
5. **Treating the prompt as the permission system.** Permissions are enforced in code, by the host and the tool.

---

## Further reading

- Anthropic, "Introducing the Model Context Protocol" (November 2024): the announcement.
- Model Context Protocol, "Specification", revision 2026-07-28 (consulted October 2026): roles, primitives, transports and security principles.
- Anthropic, "Define tools", "Tool use with Claude", "Tool search tool" and "Structured outputs" (Claude API documentation, consulted October 2026).
- Anthropic Engineering, "Code execution with MCP: building more efficient agents" (November 2025).
- Anthropic Engineering, "Equipping agents for the real world with Agent Skills" (16 October 2025).
- OpenAI, "Function calling" and "Structured Outputs" (documentation, consulted October 2026).
- Pydantic, Instructor and Outlines (project documentation).

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 16 - Memory systems](../16-memory-systems/index.md):** layer 03, what an agent remembers between sessions and how it is retrieved.
- **[Post 29 - Build #2: MCP server from scratch](../29-build-mcp-server/index.md):** a production-shaped MCP server with tools, a resource, a prompt and a permission boundary.
