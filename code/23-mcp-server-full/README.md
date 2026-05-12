# 23 · MCP Server — runnable companion

A working Model Context Protocol server in ~150 lines. Exposes three tools
(`search_orders`, `issue_refund`, `escalate_to_human`), one resource
(`refunds_policy`), and one prompt (`triage_intake`). Implements the iron
triangle of tool design and the four security defences from
[Post 13](../../posts/13-tools-and-mcp/index.md) and
[Post 18](../../posts/18-security/index.md).

## Quickstart

```powershell
cd code/23-mcp-server-full
uv sync                          # or: pip install -e .
uv run python server.py          # serves over stdio
```

## Connect to a host

### Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "acme-support": {
      "command": "uv",
      "args": ["--directory", "C:/absolute/path/to/code/23-mcp-server-full",
               "run", "python", "server.py"]
    }
  }
}
```

Restart Claude Desktop. The three tools and the resource will appear.

### Cursor

`~/.cursor/mcp.json` with the same shape.

## Smoke test

In the host chat:

> Look up orders for alex@example.com.

Expected: the agent calls `search_orders`, gets back a structured list,
summarises.

> Refund $1500 for order ORD-9001.

Expected: the agent calls `issue_refund`; the tool returns
`requires_confirmation=true`; the agent calls `escalate_to_human` with
a clear summary.

## Tests

```powershell
uv run pytest -q
```

Five tests cover the safety surface (search input validation, refund
under threshold, refund over threshold, escalation queue validation,
search by email).

## What this starter is not

- It is not a real DB. Replace `data/orders.json` with whatever your
  backend uses; scope DB credentials accordingly.
- It is not multi-tenant. The server has one identity.
- It does not log to durable storage. Add an audit table for production.

See [Post 23 §9](../../posts/23-build-mcp-server/index.md) for the full
extension list.

## License

MIT for code; CC BY 4.0 for prose. See repo root.
