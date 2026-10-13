"""Post 29, section 8: the same arguments on three call paths, and which path checks the schema.

Run from the series root (the companion needs the MCP SDK, which the series environment does not install):
    uv run --no-project --with "mcp==2.3.0" --with pydantic python posts/29-build-mcp-server/diagrams/src/03-validation-paths.py
Writes posts/29-build-mcp-server/diagrams/03-validation-paths.svg.
All three outcomes are computed here with the companion's escalate_to_human and the arguments of its test
test_escalate_validates_queue: lane 1 calls the tool through the server object's call_tool (the SDK's tools/call
path), lane 2 calls the function without its decorator (inspect.unwrap), as the original companion had it, lane 3
calls the companion's function as it is, wrapped in pydantic.validate_call. Each outcome is asserted, and so are the body's sentences about them. The failing lane, the one
that accepts the bad queue, is drawn in the error hue.
"""
import asyncio
import inspect
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
COMP = POST.parents[1] / "code" / "29-mcp-server-full"
BODY = (POST / "index.md").read_text(encoding="utf-8")
sys.path.insert(0, str(COMP))
import server  # noqa: E402
from pydantic import ValidationError  # noqa: E402

TEST = (COMP / "tests" / "test_server.py").read_text(encoding="utf-8")
ARGS = {"summary": "enough characters here", "queue": "bogus"}
assert 'escalate_to_human(summary="enough characters here", queue="bogus")' in TEST
PATTERN = "String should match pattern"


async def through_protocol():
    try:
        res = await server.mcp.call_tool("escalate_to_human", ARGS)
    except Exception as e:  # the 1.x and 2.x SDKs raise ToolError here; a host receives isError: true
        return str(e)
    return f"accepted {res!r}"


lane1 = asyncio.run(through_protocol())
assert PATTERN in lane1, lane1
bare = inspect.unwrap(server.escalate_to_human)
lane2 = bare(**ARGS)
assert lane2.queue == "bogus" and lane2.ticket_id.startswith("TKT-")
assert bare is not server.escalate_to_human, "the companion's tool is expected to carry validate_call"
try:
    server.escalate_to_human(**ARGS)
    lane3 = "accepted"
except ValidationError as e:
    lane3 = str(e)
assert PATTERN in lane3, lane3
for phrase in ("the function returned a ticket in queue `\"bogus\"`", "the SDK validates every `tools/call` against it",
               "Pydantic's `validate_call` under `@mcp.tool(...)`", "returns what the specification calls a tool "
               "execution error, a result with `isError: true`", "and the run ended `1 failed, 5 passed`", "The companion now decorates each tool"):
    assert phrase in BODY, phrase

desc = ("Three lanes for the arguments of the companion's test: summary \"enough characters here\" and queue "
        "\"bogus\". Lane 1, tools/call through the MCP SDK: the arguments are validated against the tool's input "
        "schema and refused with a string-pattern error, which a host receives as isError true. Lane 2, a direct "
        "Python call of escalate_to_human without a decorator, as first written: nothing checks the arguments, "
        "and it returns a ticket in queue bogus; this lane is marked as the failure. Lane 3, a direct call of the "
        "companion's function as it is, wrapped in pydantic's validate_call: refused with the same string-pattern "
        "error.")
fig = Figure("03-validation-paths", "The schema guards one path of three", desc,
             subtitle='The arguments of test_escalate_validates_queue: queue "bogus"; all three outcomes computed.',
             data_w=True)

fig.text(40, 128, "Call path", "head")
fig.text(352, 128, "What checks the arguments", "head")
fig.text(656, 128, "Outcome", "head")
LANES = [
    ("tools/call", "from a host", "the SDK, against", "the tool's inputSchema", "refused", "isError: true", None),
    ("escalate_to_human()", "undecorated, as first written", "nothing:", "a plain Python call", "accepted",
     'queue: "bogus"', "error"),
    ("escalate_to_human()", "with @validate_call, as now", "Pydantic, with the", "same Field constraints",
     "refused",
     "ValidationError", None),
]
for i, (code, note, c1, c2, verdict, out, role) in enumerate(LANES):
    y = 144 + 104 * i
    p = Box(40, y, 280, 80)
    c = Box(352, y, 272, 80)
    o = Box(656, y, 264, 80)
    for b in (p, c):
        fig.fill(b, "neutral-soft", radius=8, fit=False)
        fig.outline(b, "border", radius=8)
    fig.fill(o, f"{role}-soft" if role else "surface", radius=8, fit=False)
    fig.outline(o, role or "ink-muted", width=1.5, radius=8)
    fig.text(p.x + 16, y + 32, code, "code")
    fig.text(p.x + 16, y + 56, note, "note")
    fig.text(c.x + 16, y + 32, c1, "label")
    fig.text(c.x + 16, y + 56, c2, "label")
    fig.text(o.x + 16, y + 32, verdict, "head", color=f"{role}-ink" if role else None)
    fig.text(o.x + 16, y + 56, out, "code")
    fig.chain([p, c, o])

fig.caption("The test of a safety rule passes only when the function itself checks its inputs.")
fig.write()
