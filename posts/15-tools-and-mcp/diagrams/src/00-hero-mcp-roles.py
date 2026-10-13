"""Post 15 hero: MCP's three roles, and where each of a server's three primitives enters the six-layer window.

Run from anywhere:  uv run python posts/15-tools-and-mcp/diagrams/src/00-hero-mcp-roles.py
Writes posts/15-tools-and-mcp/diagrams/00-hero-mcp-roles.svg.
No numbers are drawn. The roles (one client per server), the transports (stdio, Streamable HTTP) and the
control of each primitive (model, application, user) are section 5's, from the MCP specification, revision
2026-07-28; the server is the companion code/15-mcp-quickstart, whose tool, resource and prompt names are read
from its server.py and asserted. Layer bands take their lifetime role colour; the arrow into each band takes it too.
"""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
SERVER = (POST.parents[1] / "code" / "15-mcp-quickstart" / "server.py").read_text(encoding="utf-8")
assert 'MCPServer("refunds-demo")' in SERVER
assert re.search(r"@mcp\.tool\(\)\ndef check_refund\(", SERVER)
assert '@mcp.resource("refunds://policy")' in SERVER
assert re.search(r"@mcp\.prompt\(\)\ndef draft_refund_reply\(", SERVER)
for phrase in ("each client communicates with exactly one server", "over standard input and output (stdio)",
               "Streamable HTTP", "| Tools | the model | layer 02, tools and MCP descriptions |",
               "| Resources | the application | content the host attaches, for example in layer 04, retrieved chunks |",
               "| Prompts | the user | a template the user picks, which becomes layer 06, the user instruction |",
               "revision of 2026-07-28"):
    assert phrase in BODY, phrase

LAYERS = ["System prompt", "Tools and MCP descriptions", "Memory and state", "Retrieved chunks",
          "Conversation history", "User instruction"]
ROLE = {1: "stable", 2: "stable", 3: "turn", 4: "turn", 5: "history", 6: "user"}

desc = ("A host application, drawn as a large card, holds the model's window as a stack of six layers, 01 System "
        "prompt to 06 User instruction, and two MCP clients, one per server. Client 1 talks to the refunds-demo "
        "server over stdio; client 2 talks to a remote server over Streamable HTTP. The refunds-demo server exposes "
        "the tool check_refund, the resource refunds://policy and the prompt draft_refund_reply. From client 1, "
        "three arrows enter the window: the tool's schema into 02 Tools and MCP descriptions, decided by the model; "
        "the resource into 04 Retrieved chunks when the application attaches it; the prompt into 06 User "
        "instruction when the user picks it. The second server's primitives take the same three paths.")
fig = Figure("00-hero-mcp-roles", "Three primitives reach the window by three hands", desc,
             subtitle="MCP roles, specification revision 2026-07-28; the server is the companion refunds-demo.",
             height=720, data_w=True)

# the host
host = Box(40, 112, 544, 536)
fig.fill(host, "neutral-soft", radius=8, fit=False)
fig.outline(host, "border", radius=8)
fig.text(host.x + 16, host.y + 32, "Host application", "head")
fig.text(host.x + 16, host.y + 56, "owns the model, the conversation and consent", "note")

# the window inside the host
SX, SW, Y0, BH, GAP = 64, 248, 220, 44, 12
fig.text(SX, Y0 - 16, "The model's window", "head")
tops = {k: Y0 + (k - 1) * (BH + GAP) for k in range(1, 7)}
for k, name in enumerate(LAYERS, start=1):
    band = Box(SX, tops[k], SW, BH)
    fig.fill(band, f"{ROLE[k]}-soft", radius=4, fit=False)
    fig.outline(band, f"{ROLE[k]}-line", radius=4)
    fig.text(SX + 12, tops[k] + 28, f"{k:02d} {name}", "label")

# the clients: client 1 spans the window, so each primitive enters its layer on a straight arrow
CX, CW = 432, 136
c1 = Box(CX, tops[1], CW, tops[6] + BH - tops[1])
c2 = Box(CX, 564, CW, 72)
for b in (c1, c2):
    fig.fill(b, "surface", radius=8, fit=False)
    fig.outline(b, "rule", radius=8)
fig.text(c1.x + 16, c1.y + 28, "MCP client 1", "head")
fig.text(c2.x + 16, c2.y + 28, "MCP client 2", "head")
fig.text(c2.x + 16, c2.y + 52, "same three paths", "note")

# primitives into the window: tool -> 02, resource -> 04, prompt -> 06
paths = [(2, "stable", "tool", "the model calls"), (4, "turn", "resource", "the host attaches"),
         (6, "user", "prompt", "the user picks")]
for k, role, label, who in paths:
    y = tops[k] + BH // 2
    fig.arrow((c1.x, y), (SX + SW + 2, y), label=label, color=role)
    fig.text(c1.x + 16, y + 6, who, "note")

# the servers
SV = Box(664, tops[1], 256, 140)
fig.fill(SV, "neutral-soft", radius=8, fit=False)
fig.outline(SV, "border", radius=8)
fig.text(SV.x + 16, SV.y + 32, "Server: refunds-demo", "head")
rows = [("tool", "check_refund"), ("resource", "refunds://policy"), ("prompt", "draft_refund_reply")]
for i, (kind, ident) in enumerate(rows):
    fig.text(SV.x + 16, SV.y + 68 + 24 * i, kind, "note")
    fig.text(SV.x + 88, SV.y + 68 + 24 * i, ident, "code")
SV2 = Box(664, c2.y, 256, 72)
fig.fill(SV2, "neutral-soft", radius=8, fit=False)
fig.outline(SV2, "border", radius=8)
fig.text(SV2.x + 16, SV2.y + 28, "Server: a remote one", "head")
fig.text(SV2.x + 16, SV2.y + 52, "tools, resources, prompts", "note")

fig.arrow((c1.right + 2, SV.cy), (SV.x - 2, SV.cy), label="stdio")
fig.arrow((c2.right + 2, c2.cy), (SV2.x - 2, c2.cy), label="HTTP")

fig.caption("Tools are the model's to call, resources the application's to attach, prompts the user's to pick.")
fig.write()
