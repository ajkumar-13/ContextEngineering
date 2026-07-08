# 29 · Build #2 — MCP server from scratch

> **TL;DR.** A working MCP (Model Context Protocol) server can be built in about 150 lines, and every design choice in it is a direct instance of the principles from [Post 15](../15-tools-and-mcp/index.md) and [Post 23](../23-security/index.md). This post delivers that server end-to-end: three tools (`search_orders`, `issue_refund`, `escalate_to_human`), one resource (`refunds_policy`), one prompt (`triage_intake`), typed parameter validation, a permission boundary on `issue_refund`, structured tool results, a one-page `AGENTS.md`, and the host wiring to run it in Claude Desktop, Cursor, Continue, or any MCP host.
>
> **After reading this you will be able to:**
> - Write a production-shaped MCP server end-to-end.
> - Apply the iron-triangle of tool design and the four security defences.
> - Connect the server to a host and verify it from a real LLM session.
>
> **Companion code:** `code/29-mcp-server-full/`. Full sources, tests, install instructions.

![The MCP triangle plus server internals: host and client on one side, a server exposing tools, resources, and prompts over a stdio or HTTP transport.](diagrams/00-hero-build-mcp-server.svg)
*An MCP server exposes tools, resources, and prompts to any host over a standard transport.*

---

## 1. Goals and scope

Goal: a small, real MCP server for the same imaginary Acme product as the RAG build. The functional surface area:

- **Three tools.** A read tool (`search_orders`), a write tool with a permission boundary (`issue_refund`), and a workflow tool (`escalate_to_human`).
- **One resource.** A read-only document the host can fetch on demand (`refunds_policy.md`).
- **One prompt.** A reusable prompt template the user can invoke (`triage_intake`).
- **Parameter validation** with a typed schema.
- **Structured results** that the model can use directly without re-parsing.
- **A permission boundary** that requires confirmation for `issue_refund` over $1 000.
- **An `AGENTS.md`** the host loads to teach the agent how to use the server safely.

What is *not* in scope: a full DB, multi-tenant auth, signed audit logs, OAuth flows. Those are extensions; the core works without them.

---

## 2. The MCP wire shape: minimum to know

MCP (the Model Context Protocol) is JSON-RPC 2.0 carried over one of two transports. JSON-RPC 2.0 is a simple request/response format: the caller names a method and passes a `params` object, and the server replies with a `result` or an `error`. The two transports are **stdio** (the host launches the server as a child process and talks to it over standard input/output) and **HTTP** (the server runs as a long-lived network service). The local stdio mode is the right default for development and most personal-or-team installations.

The methods that matter for a starter server:

- `initialize`: handshake, capabilities exchange.
- `tools/list`: return the catalog.
- `tools/call`: invoke a tool with args; return a structured result.
- `resources/list`, `resources/read`: expose static or dynamic documents.
- `prompts/list`, `prompts/get`: expose reusable prompt templates.

The official Python SDK (`mcp`, installable via `pip install mcp`) wraps all of this and is used throughout (Model Context Protocol, "Python SDK", 2024–25). Its `FastMCP` helper turns plain Python functions into MCP tools, resources, and prompts through decorators, so most of the wire protocol stays invisible.

### Choice of transport: stdio vs HTTP

The two transports differ on more than syntax, and the choice has security consequences:

| | **stdio** | **HTTP (streamable-http)** |
|---|---|---|
| Process model | host spawns one child per session | one long-lived service, many clients |
| Reach | same machine only | network-reachable |
| Auth | inherited from the OS user | you must add it (tokens, a reverse proxy) |
| Attack surface | local process only | any client that can reach the port |
| Best for | development, personal/single-team installs | shared, remote, or multi-user deployments |

For a build like this one, prefer stdio: it needs no ports, no auth layer, and no network exposure, and it is exactly what Claude Desktop and most local hosts expect. Reach for HTTP only when the server must be shared across machines or users, and treat that move as a security decision, not a config flag: an HTTP-exposed tool server is an unauthenticated remote-code path unless you put authentication in front of it. §9 shows the one-line transport change; §7 covers the boundary that has to come with it.

---

## 3. Layout

```
code/29-mcp-server-full/
├── README.md
├── pyproject.toml
├── server.py                    # the whole server
├── AGENTS.md                    # how an agent should use this server
├── data/
│   ├── orders.json              # toy dataset for demo
│   └── refunds_policy.md
├── prompts/
│   └── triage_intake.md
└── tests/
    └── test_server.py
```

A single `pyproject.toml` declares `mcp`, `pydantic`, `pytest`. The dependency set is small, so a fresh install is quick.

---

## 4. The server

```python
# server.py
import hashlib
import json
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

# -- domain stubs (replace with real DB / API) --------------------------------

DATA = Path(__file__).parent / "data"
ORDERS = json.loads((DATA / "orders.json").read_text())

REFUND_THRESHOLD = 1000  # dollars; over this, require human confirmation

mcp = FastMCP("acme-support")

# -- tool 1: search_orders (read) ---------------------------------------------

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
def search_orders(
    email: Annotated[str | None, Field(description="Customer email")] = None,
    order_id: Annotated[str | None, Field(description="Order id (e.g. ORD-1234)")] = None,
) -> SearchOrdersResult:
    if not email and not order_id:
        raise ValueError("Provide email or order_id (or both).")
    matches = [
        o for o in ORDERS
        if (not email or o["email"] == email)
        and (not order_id or o["id"] == order_id)
    ]
    return SearchOrdersResult(matches=matches, count=len(matches))

# -- tool 2: issue_refund (write, with permission boundary) -------------------

class IssueRefundResult(BaseModel):
    ok: bool
    refund_id: str | None = None
    requires_confirmation: bool = False
    reason: str | None = None

@mcp.tool(
    description=(
        "Issue a refund for an order. Confirm the amount and order id with "
        "the user before calling. Refunds over ${} require human confirmation; "
        "the tool will return requires_confirmation=true and not actually refund."
    ).format(REFUND_THRESHOLD),
)
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

# -- tool 3: escalate_to_human ------------------------------------------------

class EscalateResult(BaseModel):
    ticket_id: str
    queue: str

@mcp.tool(
    description=(
        "Create a human-handoff ticket. Use when the user asks for a human, "
        "when the issue is outside Acme product scope, or when "
        "issue_refund returns requires_confirmation=true."
    ),
)
def escalate_to_human(
    summary: Annotated[str, Field(min_length=10)],
    queue: Annotated[str, Field(pattern="^(general|billing|engineering)$")] = "general",
) -> EscalateResult:
    # Demo ticket id. hashlib gives a stable id across runs; Python's builtin
    # hash() is salted per process (PYTHONHASHSEED), so ids would differ each
    # run. A real backend returns the id its ticketing system assigns.
    digest = hashlib.sha256(summary.encode()).hexdigest()
    ticket_id = f"TKT-{int(digest, 16) % 10_000:04d}"
    return EscalateResult(ticket_id=ticket_id, queue=queue)

# -- resource: refunds_policy ------------------------------------------------
# The URI below is the address the host surfaces (resources/read); the Python
# function name is just local. Keep the two aligned so the host shows one name.

@mcp.resource("resource://refunds_policy")
def refunds_policy() -> str:
    return (DATA / "refunds_policy.md").read_text()

# -- prompt: triage_intake ---------------------------------------------------

@mcp.prompt(name="triage_intake")
def triage_intake(customer_msg: str) -> str:
    template = (Path(__file__).parent / "prompts" / "triage_intake.md").read_text()
    return template.format(customer_msg=customer_msg)

if __name__ == "__main__":
    mcp.run()                                      # stdio transport by default
```

Three things to notice. Each tool description follows the six-element pattern from Post 15, §3: *what it does, when to use it, when not to, parameters with descriptions, structured return.* The `issue_refund` tool enforces the threshold *in code*, not in the prompt (Post 23, §3, Defence 2 in literal form). The structured returns (Pydantic models) become typed JSON the host hands the model; no re-parsing required.

---

## 5. The `AGENTS.md` for this server

```markdown
# acme-support MCP server

## Identity
This MCP server connects an agent to the Acme customer-support backend.
It exposes three tools, one resource, and one prompt template.

## Rules
- Always confirm the refund amount with the user before calling `issue_refund`.
- Do NOT call `issue_refund` if the requested amount exceeds the visible
  order total in `search_orders` results.
- Refunds over $1 000 are not auto-approved. The tool returns
  `requires_confirmation=true`; in that case, call `escalate_to_human` with
  a clear summary so the manager queue can pick it up.
- For any query unrelated to Acme orders, refunds, or the refunds policy,
  call `escalate_to_human` with `queue="general"`.

## Format
- When citing the refunds policy, quote it with the section heading.
- After every tool call, summarise the structured result in one sentence
  before continuing.

## Knowledge
- Office hours for human handoff are 9:00–18:00 IST. (Demo value; set your own.)
- Refunds threshold: $1 000.
- The `orders.json` data is a demo set; production servers replace it.

## Tools (summary)
- `search_orders(email?, order_id?)`: read; safe; idempotent.
- `issue_refund(order_id, amount, reason)`: write; bounded by threshold.
- `escalate_to_human(summary, queue?)`: workflow; safe.
```

The `AGENTS.md` ships in the repository with the server. Any host that respects the convention loads it when the server is enabled. The agent reads it once and behaves correctly on every call.

---

## 6. Connecting to a host

The client config for **Claude Desktop** is one block in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "acme-support": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

The same `mcpServers` block goes in a different file for other hosts: `~/.cursor/mcp.json` for Cursor and `~/.continue/config.json` (or the project `.continue/config.json`) for Continue. The block itself is identical; only the file path and, for some hosts, an outer key change. Check each host's docs for the exact path (Cursor and Continue both document an `mcpServers` object). That uniformity, one server definition, many hosts, is the whole point of MCP.

After restarting the host, a quick smoke test in the chat:

> *"Look up orders for alex@example.com."*

The agent should call `search_orders`, get back a structured list, and summarise. A second turn:

> *"Refund $1500 for order ORD-9001."*

The agent should call `issue_refund`; the tool returns `requires_confirmation=true`; the agent then calls `escalate_to_human`. The whole chain happens with no further configuration.

### The test loop: iterate on descriptions, not just code

The smoke test above confirms the wiring; the real work is a loop on the *descriptions*. Watch how the model actually calls each tool and treat every wrong call as a description bug, not a model failure:

1. Give a realistic instruction in the host chat.
2. Read the tool call the model made: did it pick the right tool, fill the right parameters, and stop when it should have?
3. If it reached for the wrong tool or invented an argument, edit the tool description or parameter descriptions, restart the host, and repeat.

A model that keeps calling `search_orders` when it should escalate usually has an over-broad `search_orders` description or an under-specified `escalate_to_human` "when to use" clause. Two or three passes of this loop tighten the catalog far more than more code does. To confirm success beyond eyeballing the chat, the unit tests in §8 pin the tool *behaviour*; the loop pins the *descriptions* that decide whether the model reaches for the right tool in the first place.

---

## 7. The security checklist

The build above hits the four architectural defences from Post 23, §3:

- **The model is not the permission system.** The $1 000 threshold is enforced in `issue_refund`. The system prompt is a hint; the code is the rule.
- **Constrained blast radius.** The server has access to a JSON file, not the full database. A real version would scope the DB user similarly.
- **Filter at trust boundaries.** Tool parameters are typed and validated by Pydantic; invalid args raise before any work happens. Tool results are structured JSON, not free-form prose.
- **Never silently merge attacker text into trusted context.** The `refunds_policy.md` resource is a project-controlled file. If you add a tool that returns user-generated content (e.g., reading customer messages), wrap that content as data, not instructions (Post 23, §3, Defence 3).

A useful drill: hand the server to a colleague and ask them to break it. The first round usually surfaces a missing validation or an over-broad capability; the second round, a permission boundary that lives only in the description; the third round you start trusting the design.

---

## 8. Tests

```python
# tests/test_server.py
import json
from server import (
    search_orders, issue_refund, escalate_to_human,
    REFUND_THRESHOLD,
)

def test_search_by_email():
    r = search_orders(email="alex@example.com")
    assert r.count == len([o for o in r.matches if o["email"] == "alex@example.com"])

def test_search_requires_some_input():
    try:
        search_orders()
    except ValueError:
        return
    assert False, "expected ValueError"

def test_refund_under_threshold():
    r = issue_refund(order_id="ORD-9001", amount=50, reason="duplicate charge")
    assert r.ok is True and r.refund_id is not None

def test_refund_over_threshold_requires_confirmation():
    r = issue_refund(order_id="ORD-9001", amount=REFUND_THRESHOLD + 1, reason="x")
    assert r.requires_confirmation and not r.ok

def test_escalate_validates_queue():
    try:
        escalate_to_human(summary="enough characters here", queue="bogus")
    except Exception:
        return
    assert False, "expected validation error"
```

Five tests cover the entire safety surface. They exercise pure Python functions with no I/O, so they run fast enough to live in CI on every push.

---

## 9. What this build leaves out, and how to add it

- **Real persistence.** Replace the JSON file with a database; scope the DB user to read-only on `orders` and write-only on `refunds`.
- **Audit log.** A small SQLite table written to in `issue_refund` and `escalate_to_human`, with timestamp, args, result, calling session id.
- **HTTP transport.** Run the server with `mcp.run(transport="streamable-http")` (the current SDK's network transport; `"sse"` remains only for older clients) and put it behind a reverse proxy with auth. As §2 notes, network exposure is a security decision, not a config flag.
- **Per-user permissions.** The server today has one identity. A real one accepts a token in the JSON-RPC `meta` field and scopes operations to that user.
- **Long-lived sessions.** Add a small in-memory cache for `search_orders` so repeated lookups in a session are free.
- **More tools.** Whatever your real backend exposes. Each follows the same pattern: typed args, structured result, clear description, threshold-enforced safety.
- **Resource subscriptions.** `resources/subscribe` lets the host be notified when a resource changes; useful for live documents.

The starter is the substrate. The hard work is *not* implementing more tools; the hard work is keeping the catalog small and the boundaries clear.

---

## 10. Publishing and distribution

A server that only runs from an absolute path on one laptop is not shipped. Three levels of distribution, in order of effort:

- **Ship the repository.** The simplest form: the server, its `AGENTS.md`, and a README with the `mcpServers` block. A user clones it, installs the dependencies, and points their host's config file at `server.py`. This is enough for a single team.
- **Package it.** Publish the server as a normal Python package (a `pyproject.toml` with a console entry point) so the host config runs a command instead of a file path. Users install it with `pip` or `uvx` and reference the command; no absolute paths, no cloned checkout.
- **List it in a registry.** The MCP ecosystem maintains a public server registry so hosts can discover servers by name rather than by hand-edited config (Model Context Protocol, "Specification", latest). Listing a server there is the equivalent of publishing to a package index: it makes the server findable and gives it a canonical identity.

Two discipline points apply at every level. **Version the interface, not just the code.** The tool names, parameters, and structured-result shapes are a contract; a model prompt or a downstream automation may depend on them. Treat a rename or a field removal as a breaking change and bump a version accordingly. **Publish the `AGENTS.md` with the server**, so every host that installs it inherits the same safe-usage rules rather than reconstructing them.

Before publishing an HTTP-transport server for others to reach, re-read §7: a network-reachable tool server without authentication is a remote-execution surface. Local stdio distribution carries no such exposure, which is another reason it is the right default for a first release.

---

## 11. The lesson the build teaches

The MCP server is the operational shape of the whole tool layer. Building one once teaches the same thing reading three Anthropic guides does, faster and more durably: the model's behaviour is shaped by the tool descriptions, the tool capabilities, and the permission boundaries; *all three are code*; the system prompt is a hint, not the spec.

A team that has shipped one MCP server understands more about the tools-and-MCP layer than a team that has installed twenty.

---

## Common pitfalls

- **Permissions in the tool description.** They will be respected most of the time; that is not a security control.
- **Free-form return values.** The model will mostly cope and occasionally hallucinate. Structured returns close the gap.
- **Tool names that look alike.** `get_order`, `get_orders`, `find_order` in one server is the Post 06 confusion bug.
- **Verbose return values.** Every byte enters the model's context. Return what is needed; archive the rest.
- **No tests on the safety surface.** The first incident reveals the gap.
- **No `AGENTS.md` shipped with the server.** Every host has to figure out the conventions for itself.

---

## Further reading

- Model Context Protocol, *"Specification"* (latest revision; check the current version, as the spec has iterated since 2024).
- Anthropic, *"Introducing the Model Context Protocol"* (2024).
- Model Context Protocol, *"Python SDK"* (GitHub, 2024–25). Source for the `mcp` install and the `FastMCP` decorators used here.
- FastMCP, *"Running Your Server"* (gofastmcp.com) — transport strings (`stdio`, `streamable-http`, `sse`) and the `mcp.run` API.
- agents.md project, *"AGENTS.md spec"* (2025).
- Cursor and Continue host docs — the `mcpServers` config block for non-Claude-Desktop hosts.
- See [Post 15](../15-tools-and-mcp/index.md) for the principles, and [Post 23](../23-security/index.md) for the security model.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 30 — Capstone: email reply agent](../30-capstone-email-reply-agent/index.md)**: the everything-together project.
- **[Post 28 — Build a RAG chatbot](../28-build-rag-chatbot/index.md)**: the complementary surface area, if you skipped it.
- **[Post 15 — Tools and MCP](../15-tools-and-mcp/index.md)** and **[Post 23 — Security](../23-security/index.md)**: the principles this build instantiates, if any design choice above felt unmotivated.
