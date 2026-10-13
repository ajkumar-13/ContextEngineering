"""Post 29, section 2: the two standard transports drawn as mechanisms, stdio and Streamable HTTP.

Run from the series root:  uv run python posts/29-build-mcp-server/diagrams/src/01-transport-choice.py
Writes posts/29-build-mcp-server/diagrams/01-transport-choice.svg.
The mechanics are the specification's (revision 2026-07-28, stdio and Streamable HTTP pages, consulted October
2026) as section 2 quotes them, asserted against the body. The one set of numbers drawn, the default bind address
127.0.0.1, port 8000 and path /mcp, is the Python SDK's: run_streamable_http_async's defaults in mcp 2.3.0 and
FastMCP's settings in mcp 1.30.0, both read with inspect.signature on 13 October 2026; the body states it. The
host's log is Claude Desktop's mcp-server-NAME.log ("Connect to local MCP servers", consulted October 2026).
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
SDK_DEFAULTS = {"host": "127.0.0.1", "port": 8000, "path": "/mcp"}  # source: the SDK signatures named above
for phrase in ('"the client launches the MCP server as a subprocess"',
               '"MUST NOT write anything to its `stdout` that is not a valid MCP message"',
               "the server is one process serving many clients, each message a POST to one endpoint",
               '"MUST validate the `Origin` header"', '"SHOULD implement proper authentication"',
               "the SDK binds 127.0.0.1 port 8000 at `/mcp` by default",
               "a stdio server runs with the user's own permissions"):
    assert phrase in BODY, phrase

desc = ("Two panels. Left, stdio: a host launches the server as a subprocess. Requests go from host to server on "
        "standard input and responses come back on standard output, one JSON-RPC message per line; the server's "
        "standard error goes to a log file the host keeps. The server runs with the user's permissions. Right, "
        "Streamable HTTP: client A, client B and any process that can reach the port send HTTP POST requests to "
        "the endpoint /mcp. Each passes an Origin check and authentication before it reaches one long-lived server "
        "process, which the Python SDK binds to 127.0.0.1 port 8000 by default.")
fig = Figure("01-transport-choice", "stdio reaches one user; HTTP reaches the network", desc,
             subtitle="MCP's two standard transports, specification revision 2026-07-28.", data_w=True)
left, right = fig.row(2, y=128, h=344)


def card(b, heading, lines=(), color=None):
    fig.fill(b, "surface", radius=8, fit=False)
    fig.outline(b, color or "rule", width=1.5 if color else 1, radius=8)
    fig.text(b.x + 16, b.y + 28, heading, "head")
    for i, s in enumerate(lines):
        fig.text(b.x + 16, b.y + 52 + 20 * i, s, "note")


# stdio
fig.text(left.x, left.y, "stdio", "head")
host = Box(left.x, 152, 152, 176)
srv = Box(left.right - 152, 152, 152, 176)
card(host, "Host", ["launches the", "server process"])
card(srv, "Server", ["a subprocess with", "the user's", "permissions"])
fig.arrow((host.right + 2, 232), (srv.x - 2, 232), label="stdin: requests")
fig.arrow((srv.x - 2, 288), (host.right + 2, 288), label="stdout: responses")
fig.text(host.x, 360, "Each direction carries one", "note")
fig.text(host.x, 380, "JSON-RPC message per line;", "note")
fig.text(host.x, 400, "stdout carries nothing else.", "note")
log = Box(srv.right - 200, 376, 200, 72)
card(log, "Host's log", ["mcp-server-NAME.log"])
fig.arrow((srv.cx, srv.bottom + 2), (srv.cx, log.y - 2), label="stderr", side="left")

# Streamable HTTP
fig.text(right.x, right.y, "Streamable HTTP", "head")
clients = [Box(right.x, 152 + 72 * i, 96, 56) for i in range(3)]
for b, name in zip(clients, ["Client A", "Client B", "Any caller"]):
    fig.fill(b, "surface", radius=8, fit=False)
    fig.outline(b, "rule", radius=8)
    fig.text(b.x + 16, b.y + 34, name, "label")
gate = Box(right.x + 136, 152, 120, 200)
fig.fill(gate, "neutral-soft", radius=8, fit=False)
fig.outline(gate, "ink", width=2.5, radius=8)
for i, s in enumerate(["Origin check,", "then", "authentication"]):
    fig.text(gate.cx, gate.y + 84 + 24 * i, s, "label", anchor="middle")
for b in clients:
    fig.arrow((b.right + 2, b.cy), (gate.x - 2, b.cy))
hs = Box(right.right - 136, 152, 136, 200)
card(hs, "Server", ["one process,", "many clients"])
fig.text(hs.x + 16, hs.y + 132, SDK_DEFAULTS["host"], "code")
fig.text(hs.x + 16, hs.y + 156, f"port {SDK_DEFAULTS['port']}", "label")
fig.text(hs.x + 16, hs.y + 180, SDK_DEFAULTS["path"], "code")
fig.arrow((gate.right + 2, gate.cy), (hs.x - 2, gate.cy))
fig.text(right.x, 400, "Every request is a POST to /mcp. The bind shown is", "note")
fig.text(right.x, 420, "the SDK's default; reach is whatever can route there.", "note")

fig.caption("Moving from stdio to HTTP turns a local process into a network service; the checks come first.")
fig.write()
