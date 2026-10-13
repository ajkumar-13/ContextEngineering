"""Post 29 hero: the acme-support server, its five capabilities, where each lands in the window, and the one rule in code.

Run from the series root:  uv run python posts/29-build-mcp-server/diagrams/src/00-hero-build-mcp-server.py
Writes posts/29-build-mcp-server/diagrams/00-hero-build-mcp-server.svg.
Every name is read from the companion code/29-mcp-server-full/server.py and asserted; the threshold (1,000 dollars)
is its REFUND_THRESHOLD and the line count its len(splitlines()). Where each primitive enters the window (tools in
02, a resource in 04 when the host attaches it, a prompt in 06 when the user picks it) is post 15's table, which
the body repeats; the transport is the companion's default, mcp.run() over stdio. Layer bands take their lifetime
role colour, and each server row takes the colour of the layer its text reaches.
"""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
SERVER = (POST.parents[1] / "code" / "29-mcp-server-full" / "server.py").read_text(encoding="utf-8")
SERVER = SERVER.replace("\r\n", "\n")

TOOLS = re.findall(r"@mcp\.tool\([\s\S]*?\)\n(?:@\w+\n)*def (\w+)\(", SERVER)
RESOURCE = re.search(r'@mcp\.resource\("([^"]+)"\)', SERVER).group(1)
PROMPT = re.search(r'@mcp\.prompt\("([^"]+)"\)', SERVER).group(1)
THRESHOLD = int(re.search(r"^REFUND_THRESHOLD = (\d+)", SERVER, re.M).group(1))
LINES = len(SERVER.splitlines())
assert TOOLS == ["search_orders", "issue_refund", "escalate_to_human"], TOOLS
assert RESOURCE == "file://refunds_policy.md" and PROMPT == "triage_intake"
assert THRESHOLD == 1000 and LINES == 133
assert "if amount > REFUND_THRESHOLD:" in SERVER and re.search(r"^    mcp\.run\(\)$", SERVER, re.M)
for phrase in ("`server.py` is 133 lines", "a refund over 1,000 dollars is not made",
               "An MCP host does not; nothing in the protocol sends a repository file to the host",
               "With **stdio**", "placed MCP in the window",
               "file://refunds_policy.md layer 04 when the host attaches it"):
    assert phrase in BODY, phrase

LAYERS = ["System prompt", "Tools and MCP descriptions", "Memory and state", "Retrieved chunks",
          "Conversation history", "User instruction"]
ROLE = {1: "stable", 2: "stable", 3: "turn", 4: "turn", 5: "history", 6: "user"}

desc = ("Left, a host application holds the model's window as six layer bands, 01 System prompt to 06 User "
        "instruction, and an MCP client. The client starts the acme-support server over stdio. The server, "
        "server.py of 133 lines, exposes three tools, search_orders (read), issue_refund (write) and "
        "escalate_to_human (workflow), whose schemas reach 02 Tools and MCP descriptions; the resource "
        "file://refunds_policy.md, which reaches 04 Retrieved chunks when the host attaches it; and the prompt "
        "triage_intake, which reaches 06 User instruction when the user picks it. Inside issue_refund a gate "
        "checks amount against REFUND_THRESHOLD, 1,000 dollars, in code. AGENTS.md sits below the server: read by "
        "people and coding agents, not sent by the protocol.")
fig = Figure("00-hero-build-mcp-server", "One server, five capabilities, one rule in code", desc,
             subtitle="The companion acme-support over stdio; every name is read from its server.py.",
             height=720, data_w=True)

# the host and the window inside it
host = Box(40, 112, 400, 520)
fig.fill(host, "neutral-soft", radius=8, fit=False)
fig.outline(host, "border", radius=8)
fig.text(host.x + 16, host.y + 32, "Host application", "head")
fig.text(host.x + 16, host.y + 56, "Claude Desktop, Cursor, Continue", "note")

SX, SW, Y0, BH, GAP = 56, 216, 216, 40, 8
fig.text(SX, Y0 - 12, "The model's window", "label")
tops = {k: Y0 + (k - 1) * (BH + GAP) for k in range(1, 7)}
for k, name in enumerate(LAYERS, start=1):
    band = Box(SX, tops[k], SW, BH)
    fig.fill(band, f"{ROLE[k]}-soft", radius=4, fit=False)
    fig.outline(band, f"{ROLE[k]}-line", radius=4)
    fig.text(SX + 12, tops[k] + 26, f"{k:02d} {name}", "label")

client = Box(344, tops[1], 80, tops[6] + BH - tops[1])
fig.fill(client, "surface", radius=8, fit=False)
fig.outline(client, "rule", radius=8)
fig.text(client.cx, client.y + 28, "MCP", "head", anchor="middle")
fig.text(client.cx, client.y + 48, "client", "head", anchor="middle")
for k, role, label in ((2, "stable", "tools"), (4, "turn", "resource"), (6, "user", "prompt")):
    y = tops[k] + BH // 2
    fig.arrow((client.x, y), (SX + SW + 2, y), color=role)
    fig.text(client.x - 8, y - 8, label, "note", anchor="end")
fig.text(host.x + 16, 560, "starts server.py as a subprocess", "note")
fig.text(host.x + 16, 584, "asks the user before a tool runs", "note")

# the server
SV = Box(520, 112, 400, 408)
fig.fill(SV, "neutral-soft", radius=8, fit=False)
fig.outline(SV, "border", radius=8)
fig.text(SV.x + 16, SV.y + 32, "Server: acme-support", "head")
fig.text(SV.x + 16, SV.y + 56, f"server.py, {LINES} lines", "note")

ROWS = [("tool", TOOLS[0], "read", "stable"), ("tool", TOOLS[1], "write", "stable"),
        ("tool", TOOLS[2], "workflow", "stable"), ("resource", RESOURCE, "", "turn"), ("prompt", PROMPT, "", "user")]
ys = [184, 232, 360, 408, 456]
for (kind, ident, note, role), y in zip(ROWS, ys):
    r = Box(SV.x + 16, y, SV.w - 32, 40)
    fig.fill(r, f"{role}-soft", radius=4, fit=False)
    fig.outline(r, f"{role}-line", radius=4)
    fig.text(r.x + 12, y + 26, kind, "note")
    fig.text(r.x + 96, y + 26, ident, "code")
    if note:
        fig.text(r.right - 12, y + 26, note, "note", anchor="end")

gate = Box(SV.x + 96, 280, SV.w - 112, 64)
fig.fill(gate, "surface", radius=4, fit=False)
fig.outline(gate, "ink", width=2.5, radius=4)
fig.text(gate.x + 12, gate.y + 26, "if amount > REFUND_THRESHOLD:", "code")
fig.text(gate.x + 12, gate.y + 50, f"threshold {THRESHOLD:,} dollars, checked in code", "label")
fig.text(SV.x + 16, gate.y + 38, "the gate", "note")

fig.arrow((client.right, 300), (SV.x - 2, 300), label="stdio")

agents = Box(520, 536, 400, 96)
fig.fill(agents, "surface", radius=8, fit=False)
fig.outline(agents, "rule", width=1, dash="lead", radius=8)
fig.text(agents.x + 16, agents.y + 32, "AGENTS.md", "code")
fig.text(agents.x + 16, agents.y + 60, "read by people and coding agents,", "note")
fig.text(agents.x + 16, agents.y + 80, "not sent by the protocol", "note")

fig.caption("Tools are the model's to call, the resource the host's to attach, the prompt the user's to pick.")
fig.write()
