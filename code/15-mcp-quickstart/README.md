# MCP quickstart

Companion code for **[Post 15 — Tools and MCP](../../posts/15-tools-and-mcp/index.md)** and **[Post 29 — Build #2: MCP server from scratch](../../posts/29-build-mcp-server/index.md)**.

A minimal Model Context Protocol server: **one tool** (`check_refund`), **one resource** (`refunds://policy`), and **one prompt** (`draft_refund_reply`). The business rules live in a pure module (`mcp_quickstart.refunds`) that tests offline; `server.py` is a ~60-line MCP wrapper around them.

## Run the tests (offline)

```bash
cd code/15-mcp-quickstart
python -m pip install -e ".[dev]"
pytest                 # the refund rules are tested without the MCP runtime
```

## Run the server

```bash
python -m pip install -e ".[server]"   # installs the official `mcp` SDK
python server.py                        # speaks MCP over stdio
```

Wire it into a host by adding it to the host's MCP config. For Claude Desktop (`claude_desktop_config.json`), Cursor (`~/.cursor/mcp.json`), or any other host, the block is the same shape — only the file differs:

```json
{
  "mcpServers": {
    "refunds-demo": { "command": "python", "args": ["/abs/path/to/server.py"] }
  }
}
```

## What's stubbed / deliberately small

- **The refund rules are illustrative.** The point is the *shape*: keep policy in code (a pure function), expose it over MCP, and never make the model the permission system (Post 23).
- **Pin the `mcp` SDK version** you test against — the server API still moves; if `mcp.run()` or the decorators differ in your version, check the SDK's quickstart.
- **stdio transport only.** HTTP/SSE is a one-line change once you've seen the shape.
