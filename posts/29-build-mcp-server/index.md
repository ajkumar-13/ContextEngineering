# 29 - Build #2: MCP server from scratch

> **TL;DR.** A Model Context Protocol (MCP) server of about 130 lines of Python exposes three tools, one resource and one prompt to any MCP host, and each design choice in it applies [post 15](../15-tools-and-mcp/index.md) or [post 23](../23-security/index.md): descriptions that say when to call each tool, a refund threshold enforced in code rather than in a description, typed parameters that become the tool's schema, and structured results. The schema is checked when a host calls the tool over the protocol, not when Python calls the function, so the companion's tools also check their own inputs.
>
> **Prerequisites:** [Post 15](../15-tools-and-mcp/index.md), [Post 23](../23-security/index.md).
> **Safe to skip?** Skip it if an MCP server with typed tools, a permission boundary in code and tests of its safety rules has already been written and connected to a host.
>
> **After reading, you will be able to:**
>
> - Write an MCP server with tools, a resource and a prompt, typed parameters and structured results, and say what each becomes on the wire.
> - Enforce a write tool's permission boundary in the server's code, so a refund over the threshold asks for confirmation instead of acting.
> - Audit a server against the iron triangle and the four architectural defences, and name the line of code or the gap behind each.
> - Choose between stdio and Streamable HTTP for a server, and name the protections an HTTP server needs before it is reachable.
> - Connect the server to a host, verify it from a live session, and test its safety rules both as functions and through the protocol.

![A host with an MCP client talks over stdio to the acme-support server. Its three tools reach layer 02, its resource file://refunds_policy.md layer 04 when the host attaches it, its prompt triage_intake layer 06 when the user picks it. A gate in issue_refund checks the 1,000-dollar threshold in code; AGENTS.md sits beside the server, outside the protocol.](diagrams/00-hero-build-mcp-server.svg)

*Five capabilities reach the window by three different hands; the one rule that must hold is a line of code.*

---

## 1. The question: what does a production-shaped MCP server look like?

[Post 15](../15-tools-and-mcp/index.md) placed MCP in the window: a host runs one client per server, a server exposes tools, resources and prompts, and each reaches the model only as text in a layer. [Post 23](../23-security/index.md) showed why a tool that acts on the world needs its permissions in code. This post builds one server that does both, for the imaginary Acme product of the retrieval-augmented generation (RAG) chatbot of `ctx-028`, and wires it into a host:

- **Three tools**: a read tool (`search_orders`), a write tool with a permission boundary (`issue_refund`) and a workflow tool (`escalate_to_human`).
- **One resource**, the refunds policy, and **one prompt**, the template `triage_intake`.
- **Typed parameters** that become each tool's input schema, and **structured results**.
- **A permission boundary**: a refund over 1,000 dollars is not made; the tool asks for confirmation.
- **An `AGENTS.md`** documenting the server's rules.

Out of scope: a real database, per-user permissions, a durable audit log and OAuth; section 10 says how each is added. Every listing below is an excerpt of a file in the companion, [`code/29-mcp-server-full`](../../code/29-mcp-server-full/).

---

## 2. The wire shape, and the transport choice

MCP messages are JSON-RPC 2.0 (JavaScript Object Notation remote procedure call): the caller names a method and passes `params`, and the server replies with a `result` or an `error`. A starter server answers `tools/list` and `tools/call`, `resources/list` and `resources/read`, `prompts/list` and `prompts/get`.

How a conversation starts depends on the revision. In the specification's current revision, 2026-07-28 (modelcontextprotocol.io, consulted October 2026), there is no handshake: "Every request declares the protocol version it is using in its `_meta` field", and a client may call `server/discover` for the server's versions, capabilities and optional `instructions`. Revisions up to 2025-11-25 opened a session with an `initialize` handshake; the 2.x Python SDK under the companion answers both. The wire, the transports and the fallback between the two eras belong to the MCP series, whose `mcp-005` builds a first server on the 2.x SDK from first principles.

The official Python software development kit (SDK), the `mcp` package, hides all of it: its `MCPServer` class, in `mcp.server.mcpserver`, turns plain functions into tools, resources and prompts through decorators. In the 1.x line it was `FastMCP`; the companion pins `mcp==2.3.0`.

**Two transports.** With **stdio**, "the client launches the MCP server as a subprocess" and the two exchange newline-delimited JSON-RPC over its standard input and output; the server "MUST NOT write anything to its `stdout` that is not a valid MCP message" and logs to standard error. With **Streamable HTTP** (Hypertext Transfer Protocol), the server is one process serving many clients, each message a POST to one endpoint, and the specification says servers "MUST validate the `Origin` header", "SHOULD bind only to localhost" when local, and "SHOULD implement proper authentication". Credentials differ too: a stdio server should "retrieve credentials from the environment", an HTTP one uses OAuth 2.1 bearer tokens on every request when authorisation is used (specification, Authorization page). The figure below draws both.

![Left, stdio: a host launches the server as a subprocess; requests go down standard input, responses come back on standard output, one JSON-RPC message per line, and standard error goes to the host's log. Right, Streamable HTTP: several clients POST to /mcp on one long-lived server, through an Origin check and authentication; the SDK binds 127.0.0.1 port 8000 by default.](diagrams/01-transport-choice.svg)

*stdio reaches one user on one machine; HTTP reaches whatever can route to the port, so its checks come first.*

For this build stdio is the right default: no port and no listener, and it is what Claude Desktop starts. It is not harmless: a stdio server runs with the user's own permissions, as Claude Desktop's "Connect to local MCP servers" guide (consulted October 2026) warns, so its tools reach whatever the user can. Streamable HTTP is for a server shared across machines or users, and choosing it is a security decision, not a configuration flag: the SDK binds 127.0.0.1 port 8000 at `/mcp` by default and checks `Origin` only on such a local bind, but authentication stays off until the server is given an authorisation provider, and without it anyone who can reach the port can call `issue_refund`.

---

## 3. Layout

```text
code/29-mcp-server-full/
├── README.md
├── pyproject.toml               # mcp, pydantic; pytest as a dev extra
├── server.py                    # the whole server
├── AGENTS.md                    # how an agent should use this server
├── data/
│   ├── orders.json              # four demo orders
│   └── refunds_policy.md        # served as the resource
├── prompts/
│   └── triage_intake.md         # the prompt template
└── tests/
    └── test_server.py           # six tests
```

`server.py` is 133 lines, 105 of them not blank.

---

## 4. The server

The module loads the orders, fixes the threshold and creates the server (`server.py`):

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, validate_call
from mcp.server.mcpserver import MCPServer

DATA = Path(__file__).parent / "data"
ORDERS: list[dict] = json.loads((DATA / "orders.json").read_text(encoding="utf-8"))
REFUND_THRESHOLD = 1000  # dollars; over this, require human confirmation

mcp = MCPServer("acme-support")
```

The read tool. The decorator's `description` and the typed parameters become the tool's entry in `tools/list`, and the return type its output schema; `@validate_call` is the third point below:

```python
# -- tool 1: search_orders (read) --------------------------------------------

class SearchOrdersResult(BaseModel):
    matches: list[dict]
    count: int


@mcp.tool(
    description=(
        "Search orders by customer email or by order id. "
        "Use this when the user provides either piece of information. "
        "Do NOT use for refunds; use `issue_refund` for refunds."
    ),
)
@validate_call
def search_orders(
    email: Annotated[str | None, Field(description="Customer email")] = None,
    order_id: Annotated[str | None, Field(description="Order id (e.g. ORD-1234)")] = None,
) -> SearchOrdersResult:
    if not email and not order_id:
        raise ValueError("Provide email or order_id (or both).")
    matches = [
        o for o in ORDERS
        if (not email or o["email"].lower() == email.lower())
        and (not order_id or o["id"] == order_id)
    ]
    return SearchOrdersResult(matches=matches, count=len(matches))
```

The write tool, with its permission boundary:

```python
# -- tool 2: issue_refund (write, with permission boundary) ------------------

class IssueRefundResult(BaseModel):
    ok: bool
    refund_id: str | None = None
    requires_confirmation: bool = False
    reason: str | None = None


@mcp.tool(
    description=(
        f"Issue a refund for an order. Confirm the amount and order id with "
        f"the user before calling. Refunds over ${REFUND_THRESHOLD} require "
        f"human confirmation; the tool will return requires_confirmation=true "
        f"and not actually refund."
    ),
)
@validate_call
def issue_refund(
    order_id: Annotated[str, Field(description="Order id")],
    amount: Annotated[float, Field(gt=0, description="Refund amount in USD")],
    reason: Annotated[str, Field(min_length=4, description="Short reason")],
) -> IssueRefundResult:
    order = next((o for o in ORDERS if o["id"] == order_id), None)
    if order is None:
        return IssueRefundResult(ok=False, reason="order_not_found")
    if amount > order["total"]:
        return IssueRefundResult(ok=False, reason="amount_exceeds_order_total")
    if amount > REFUND_THRESHOLD:
        return IssueRefundResult(
            ok=False,
            requires_confirmation=True,
            reason=(
                f"Refund of ${amount:.2f} exceeds the ${REFUND_THRESHOLD} "
                "auto-approve threshold. Route to manager queue."
            ),
        )
    refund_id = f"RF-{order_id[-4:]}-{int(amount)}"
    return IssueRefundResult(ok=True, refund_id=refund_id)
```

The workflow tool:

```python
# -- tool 3: escalate_to_human ----------------------------------------------

class EscalateResult(BaseModel):
    ticket_id: str
    queue: str


@mcp.tool(
    description=(
        "Create a human-handoff ticket. Use when the user asks for a human, "
        "when the issue is outside Acme product scope, or when issue_refund "
        "returns requires_confirmation=true."
    ),
)
@validate_call
def escalate_to_human(
    summary: Annotated[str, Field(min_length=10)],
    queue: Annotated[str, Field(pattern="^(general|billing|engineering)$")] = "general",
) -> EscalateResult:
    digest = hashlib.sha256(summary.encode("utf-8")).hexdigest()
    ticket_id = f"TKT-{int(digest, 16) % 10_000:04d}"
    return EscalateResult(ticket_id=ticket_id, queue=queue)
```

The resource, the prompt and the entry point:

```python
# -- resource: refunds_policy -----------------------------------------------

@mcp.resource("file://refunds_policy.md")
def refunds_policy() -> str:
    return (DATA / "refunds_policy.md").read_text(encoding="utf-8")


# -- prompt: triage_intake --------------------------------------------------

@mcp.prompt("triage_intake")
def triage_intake(customer_msg: str) -> str:
    template = (Path(__file__).parent / "prompts" / "triage_intake.md").read_text(encoding="utf-8")
    return template.format(customer_msg=customer_msg)


if __name__ == "__main__":
    mcp.run()
```

Four things to notice.

**The descriptions, against [post 15](../15-tools-and-mcp/index.md)'s six parts.** [Post 15](../15-tools-and-mcp/index.md), section 3, asks for a name, a summary, when to use the tool, when not to, described parameters and one example. `search_orders` has the first five; its last sentence is the "when not to" line naming `issue_refund`. `issue_refund` has no "when not to" line. `escalate_to_human` leaves both parameters undescribed, and its queue is a regular-expression `pattern` where [post 15](../15-tools-and-mcp/index.md) recommends an enum: `Literal["general", "billing", "engineering"]` would list the values in the schema. None has an example. With three tools the iron triangle of [post 15](../15-tools-and-mcp/index.md), section 2, is easy: rich descriptions fit in layer 02 without a selection step.

**The threshold is in code.** The description tells the model that large refunds need confirmation; the `if amount > REFUND_THRESHOLD` line makes it true whatever the model does. It is D1 of [post 23](../23-security/index.md), section 5, the model is not the permission system, in its most literal form.

**Typed parameters become the input schema, checked on both paths.** The `Field` constraints are written into `inputSchema` (`exclusiveMinimum: 0` for `amount`, `minLength: 4` for `reason`, the `pattern` for `queue`), and the SDK validates every `tools/call` against it before the function runs; a bad argument returns what the specification calls a tool execution error, a result with `isError: true` the model can act on. A direct Python call skips that layer, so each tool also carries Pydantic's `validate_call`: without it, `issue_refund(order_id="ORD-9001", amount=-5, reason="x")` called from Python returns a refund. Section 8 shows where that matters.

**Results are structured.** Each return type is a Pydantic model, which the SDK publishes as the tool's `outputSchema` and returns as `structuredContent`, with the same JSON as a text block "for backwards compatibility", as the specification recommends. It also notes that `structuredContent` "is unrelated to LLM 'structured outputs'", the constrained decoding of [post 21](../21-structured-output-guardrails/index.md): the server produces it, not the model.

---

## 5. The permission boundary

A refund passes three checks, and only one of them is the model's. The figure below draws them, with what the companion's `issue_refund` returns for three calls.

![Top: the model proposes issue_refund on ORD-9004 for 1,500 dollars, the host asks the user to approve, the server compares the amount with the order total of 12,000 and the threshold of 1,000 in code, and a person in the manager queue decides. Bottom: three calls, their results and the check that stopped each: ORD-9001 for 50 gives refund RF-9001-50; ORD-9004 for 1,500 gives requires_confirmation true at the threshold; ORD-9001 for 1,500 gives amount_exceeds_order_total at the order total.](diagrams/02-permission-boundary.svg)

*The model proposes, the host asks, the code decides, and a person approves what the code will not.*

1. **The model proposes** `issue_refund(order_id="ORD-9004", amount=1500, reason=...)`, having read a description it may still disregard.
2. **The host asks.** The specification says there "SHOULD always be a human in the loop with the ability to deny tool invocations"; Claude Desktop's guide says it "will request your approval" before each operation of its example server, and Cursor "asks for approval before using MCP tools by default" (pages consulted October 2026).
3. **The server checks in code.** 1,500 is under the order's total of 12,000 but over the threshold, so the tool returns `requires_confirmation: true` and refunds nothing.
4. **A person decides.** The agent calls `escalate_to_human`, and the manager queue, outside the model's reach, approves or refuses.

The host's prompt is the weakest check: a person who has approved a long run of calls may approve the next without reading it, and Cursor lets allow-listed tools run without asking. Step 3 holds even when steps 1 and 2 fail.

---

## 6. The server's `AGENTS.md`

The companion's `AGENTS.md` follows the five-block form of [post 14](../14-system-prompt-as-software/index.md). Its first three blocks:

```markdown
# acme-support MCP server

## Identity
This MCP server connects an agent to the Acme customer-support backend.
It exposes three tools, one resource, and one prompt template.

## Rules
- Always confirm the refund amount with the user before calling `issue_refund`.
- Do NOT call `issue_refund` if the requested amount exceeds the visible order total in `search_orders` results.
- Refunds over $1 000 are not auto-approved. The tool returns `requires_confirmation=true`; in that case, call `escalate_to_human` with a clear summary so the manager queue can pick it up.
- For any query unrelated to Acme orders, refunds, or the refunds policy, call `escalate_to_human` with `queue="general"`.

## Format
- When citing the refunds policy, quote it with the section heading.
- After every tool call, summarise the structured result in one sentence before continuing.
```

The Knowledge and Tools blocks restate the threshold and summarise each tool. **Who reads it matters.** `AGENTS.md` is a repository file for coding agents ([post 14](../14-system-prompt-as-software/index.md), section 4): an agent editing this server reads it. An MCP host does not; nothing in the protocol sends a repository file to the host. The protocol's channel is the server's `instructions`, "natural-language guidance for LLMs on how to use this server effectively", returned by `server/discover` in revision 2026-07-28 and by `initialize` before it, and passed to the SDK as `MCPServer("acme-support", instructions=...)`. The companion sets none, so for the host's model to see the Rules block it belongs there too; whether and where the host puts instructions in the window is the host's decision. Either way the file enforces nothing: every rule that must hold is also in code.

---

## 7. Connecting to a host

**Claude Desktop** reads `claude_desktop_config.json` (on Windows in `%APPDATA%\Claude\`, on macOS in `~/Library/Application Support/Claude/`; Settings, Developer, Edit Config creates it) and starts every server under `mcpServers`. For the companion, with `uv` supplying the pinned SDK:

```json
{
  "mcpServers": {
    "acme-support": {
      "command": "uv",
      "args": ["run", "--no-project", "--with", "mcp==2.3.0", "--with", "pydantic",
               "python", "/absolute/path/to/code/29-mcp-server-full/server.py"]
    }
  }
}
```

The path must be absolute, and the application must be quit and restarted to read the file (Model Context Protocol, "Connect to local MCP servers", consulted October 2026). Cursor reads the same `mcpServers` object from `.cursor/mcp.json` in a project or `~/.cursor/mcp.json` (Cursor, "Model Context Protocol"). Continue lists servers in YAML under `mcpServers`, picks up JSON files from Claude Desktop or Cursor copied into `.continue/mcpServers/`, and uses MCP only in agent mode (Continue, "MCP"; both consulted October 2026).

**The live check.** After the restart the three tools appear, and two turns test the wiring:

> *"Look up orders for alex@example.com."*

The agent should call `search_orders` and summarise the two orders it returns. Then:

> *"Refund 1,500 dollars on order ORD-9004."*

The agent should call `issue_refund`, receive `requires_confirmation: true`, and call `escalate_to_human`: the confirmation gate firing from a live session. This turn has not been run for this post; the tool's answer to that call is verified offline (section 5). The order matters: ORD-9001 totals 1,499 dollars, so a 1,500-dollar refund on it stops at the order-total check and never reaches the threshold.

**Then iterate on descriptions, not only code.** Give a realistic instruction, read the call the model made (the right tool, the right arguments, a stop when it should stop), and treat a wrong call as a description bug: edit the description or a parameter's description, restart the host, repeat. The tests pin the tools' behaviour; this loop pins the descriptions that decide whether the model reaches for the right tool at all.

---

## 8. Tests

The companion's six tests call the tools as plain functions, with no host and no network. Three of them, from `tests/test_server.py`:

```python
def test_refund_over_threshold_requires_confirmation():
    r = issue_refund(
        order_id="ORD-9004",
        amount=REFUND_THRESHOLD + 1,
        reason="customer cancelled",
    )
    assert r.requires_confirmation and not r.ok


def test_refund_unknown_order():
    r = issue_refund(order_id="ORD-DOES-NOT-EXIST", amount=10, reason="test")
    assert not r.ok and r.reason == "order_not_found"


def test_escalate_validates_queue():
    try:
        escalate_to_human(summary="enough characters here", queue="bogus")
    except Exception:
        return
    assert False, "expected validation error"
```

The other three search by email, refuse a search with no input, and refund 50 dollars under the threshold. **The last test failed on the original companion, the file as first written.** It expects the `pattern` on `queue` to reject `"bogus"`, but a direct call never meets the schema: the function returned a ticket in queue `"bogus"`, and the run ended `1 failed, 5 passed`. Through the protocol the same arguments are refused, as the figure below shows.

![Three lanes for the arguments summary and queue bogus. A tools/call through the SDK is validated against the input schema and refused with a pattern error. A direct Python call of the function without a decorator, as first written, is not checked and returns a ticket in queue bogus. The companion's function, wrapped in pydantic's validate_call, refuses the call with the same pattern error.](diagrams/03-validation-paths.svg)

*The schema guards the protocol path only; a function that checks its own inputs guards every path.*

The test was right and the function incomplete. The companion now decorates each tool with Pydantic's `validate_call` under `@mcp.tool(...)`, which applies the same `Field` constraints to a direct call and leaves the published schema unchanged: all six tests pass, and `issue_refund` rejects the negative amount of section 4 on both paths. A test through the protocol, calling `call_tool` on the server object, would cover the other path.

---

## 9. The security checklist

The four architectural defences of [post 23](../23-security/index.md), section 5, applied to this server:

- **D1, the model is not the permission system.** The threshold lives in `issue_refund`. The refunds policy's 30-day window, by contrast, is enforced nowhere: the resource states it and no code checks a purchase date.
- **D2, a bounded blast radius.** The server reads one JSON file and mints refund identifiers, nothing else. A real version runs as a database user that can read orders and write refunds only.
- **D3, filter at trust boundaries.** Every call is validated, by the schema or by `validate_call`, and results are structured data from the server's own files. The prompt template puts the customer's message between two `---` lines, a weak wrapper; [post 23](../23-security/index.md)'s trust tag would mark that text `external`, data the model must not obey.
- **D4, never silently merge attacker text into trusted context.** The resource is a project file, and the server writes no memory. A tool returning customer-written text would need D3's tag on its result.

The specification's Tools page adds four obligations: servers MUST validate all tool inputs, implement proper access controls, rate limit tool invocations and sanitise tool outputs. This build meets the first on both paths and the last by construction; with one identity it has no access control, and it has no rate limit.

---

## 10. What this build leaves out, and how to add it

- **Refund history.** The tool is stateless: two refunds of 750 dollars on ORD-9004 both succeed, together over the threshold. A real version checks the running total per order.
- **An audit log** written by `issue_refund` and `escalate_to_human`: time, arguments, result, session. The trace store of [post 22](../22-observability/index.md) is the same idea on the model's side.
- **Streamable HTTP.** `mcp.run(transport="streamable-http")` serves the same tools at `/mcp`; the SDK's other value, `"sse"`, selects the HTTP+SSE transport the specification has deprecated since 2025-03-26. Authentication comes first (section 2).
- **Per-user permissions.** Over HTTP each request carries an OAuth bearer token, and the server scopes each tool to its user; over stdio, credentials come from the environment.
- **Rate limits and real ticket ids.** The demo derives the ticket id from a SHA-256 (Secure Hash Algorithm) digest of the summary, so two escalations with the same summary share an id, and there are only 10,000 ids; a real ticketing system assigns the id.

The hard part is not adding tools; it is keeping the catalogue small and the boundaries in code.

---

## 11. Publishing and distribution

A server that runs only from an absolute path on one laptop is not shipped. Three levels, in order of effort:

- **Ship the repository**: the server, its `AGENTS.md` and a README with the `mcpServers` block, enough for one team.
- **Package it.** A console entry point, which the companion does not define yet, lets the host run a command such as `uvx acme-support-mcp` instead of a path. Pin the SDK: the original companion declared `mcp>=1.2.0`, which today resolves to 2.x, where importing `mcp.server.fastmcp` fails; it now pins `mcp==2.3.0`.
- **List it in a registry.** The MCP Registry, "currently in preview", is "the official centralized metadata repository for publicly accessible MCP servers": a `server.json` pointing to a package on PyPI, npm or Docker Hub under a verified namespace such as `io.github.user/server-name`. It is "not intended to be directly consumed by host applications"; marketplaces read it, and hosts read them (Model Context Protocol, "The MCP Registry", consulted October 2026).

At every level, **version the interface**: tool names, parameters and result shapes are a contract, and a rename is a breaking change.

---

## 12. The lesson the build teaches

An MCP server is the working shape of layer 02, tools and MCP descriptions. The model's behaviour is set by descriptions, capabilities and boundaries, and all three are code in one file. The prompt and the `AGENTS.md` help the model use the server well; the code decides what the server does.

---

## 13. Make it run

From the series root, the six tests run with the pinned SDK installed for the run, in under a minute once the packages are cached:

```text
uv run --with pytest --with "mcp==2.3.0" --with pydantic python -m pytest -q -p no:cacheprovider code/29-mcp-server-full/tests
```

They end `6 passed`; inside the companion, `uv run --extra dev pytest -q` runs the same tests. No test needs a key.

The live steps need a host and have not been run for this post: install Claude Desktop or Cursor, add the block of section 7 with the absolute path to `server.py`, restart, check that the three tools are listed, and run the two turns of section 7. When a server does not appear, Claude Desktop's guide points to `mcp.log` and to `mcp-server-acme-support.log`, which holds the server's standard error.

---

## 14. What can go wrong?

- **A refund split in two.** A refused amount is retried as two halves under the threshold, and both succeed, because the check sees one call at a time. Check the running total per order.
- **A smoke test that tests the wrong rule.** A 1,500-dollar refund on ORD-9001 is refused for exceeding the order total, the run looks like the gate working, and the gate is never exercised. Choose inputs that reach the rule under test.
- **Validation only the protocol performs.** A unit test, a script or another tool calls the function directly and skips its constraints. Validate inside the function, and test once through `tools/call`.
- **Debug output on standard output.** A `print` in a stdio server lands in the protocol stream, and the host fails to parse the next message. Log to standard error.
- **An unpinned SDK.** The original companion's `mcp>=1.2.0` installed 2.x on a fresh machine, and the server failed at import. Pin the version the code was written for.

---

## Common pitfalls

1. **Permissions in the description.** The model follows them most of the time; that is not a control.
2. **Tool names that look alike.** `get_order`, `get_orders` and `find_order` in one server are the confusion of [post 06](../06-context-failure-modes/index.md), section 3.
3. **Verbose results.** Every byte enters the window; return the fields the model needs ([post 15](../15-tools-and-mcp/index.md), section 7).
4. **A rule stated in a resource and enforced nowhere.** The policy is read as text; only code makes it hold.
5. **Guidance that never reaches the host.** An `AGENTS.md` informs people and coding agents; the host's model sees the descriptions and the server's `instructions`.

---

## Further reading

- Model Context Protocol, ["Specification"](https://modelcontextprotocol.io/), revision 2026-07-28 (consulted October 2026): the Tools, Resources, Discovery, Versioning, stdio, Streamable HTTP and Authorization pages.
- Model Context Protocol, ["Python SDK"](https://github.com/modelcontextprotocol/python-sdk) (GitHub, consulted October 2026): `FastMCP` in the 1.x line, `MCPServer` in 2.x.
- Model Context Protocol, ["Connect to local MCP servers"](https://modelcontextprotocol.io/docs/develop/connect-local-servers) and ["The MCP Registry"](https://modelcontextprotocol.io/registry/about) (consulted October 2026).
- FastMCP, ["Running Your Server"](https://gofastmcp.com/deployment/running-server) (gofastmcp.com, consulted October 2026): the standalone FastMCP project, whose HTTP transport string is `"http"` where the official SDK's is `"streamable-http"`.
- Anthropic, ["Introducing the Model Context Protocol"](https://www.anthropic.com/news/model-context-protocol) (November 2024).
- agents.md project, ["AGENTS.md"](https://agents.md/) (consulted October 2026).
- Cursor, ["Model Context Protocol"](https://cursor.com/docs/context/mcp), and Continue, ["MCP"](https://docs.continue.dev/customize/deep-dives/mcp) (documentation, consulted October 2026).

---

## What to read next

- **[Post 30 - Capstone: email reply agent](../30-capstone-email-reply-agent/index.md):** the capstone, whose email tools gate the send the way this server gates the refund.
- **[Post 23 - Security and prompt injection](../23-security/index.md):** the threat model behind these boundaries, and what a host must add when it connects many servers.
