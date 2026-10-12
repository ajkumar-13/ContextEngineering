"""Post 02, section 10: the request body that snippets/context_inspector.py prints, with each entry bracketed to its layer.

Run from anywhere:  python posts/02-six-layers-of-context/diagrams/src/02-request-xray.py
Writes posts/02-six-layers-of-context/diagrams/02-request-xray.svg.
The snippet is run here (well under a second); the listing is its printed JSON, line for line, and the brackets
come from its layer map (the path of every entry and the layer it belongs to), asserted against the listing.
"""
import contextlib
import io
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Raw, text_width  # noqa: E402
import html  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "context_inspector.py"
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    runpy.run_path(str(SNIP), run_name="__main__")
OUT = buf.getvalue()
listing, _, mapping = OUT.partition("\n\nlayer map:\n")
LINES = listing.split("\n")
MAP = [ln.split(None, 1) for ln in mapping.strip().split("\n")]   # [path, "NN Name"]
assert len(LINES) == 22 and LINES[0] == "{" and LINES[-1] == "}"
assert [p for p, _ in MAP] == ["system", "tools[0]"] + [f"messages[{i}]" for i in range(6)]

# the listing line(s) of every entry in the layer map
start = {"system": 1}
ti = LINES.index('  "tools": [')
te = LINES.index("  ],", ti)
mi = LINES.index('  "messages": [')
span = {"system": (1, 1), "tools[0]": (ti + 1, te - 1)}
for i in range(6):
    span[f"messages[{i}]"] = (mi + 1 + i, mi + 1 + i)
assert LINES[mi + 7] == "  ],"
assert LINES[1].startswith('  "system": ') and LINES[ti + 1] == "    {" and LINES[te - 1] == "    }"
assert '"<memory>' in LINES[mi + 1] and '"<chunk>' in LINES[mi + 3] and "rotate the signing secret" in LINES[mi + 6]
SETTINGS = (LINES.index('  "model": "claude-sonnet-4-5",'), LINES.index('  "max_tokens": 1024'))

# group consecutive entries of one layer
groups = []
for path, label in MAP:
    a, b = span[path]
    if groups and groups[-1][0] == label:
        groups[-1][2] = b
    else:
        groups.append([label, a, b])
assert [g[0] for g in groups] == ["01 System prompt", "02 Tools and MCP descriptions", "03 Memory and state",
                                  "04 Retrieved chunks", "05 Conversation history", "06 User instruction"]
ROLE = {"01": "stable", "02": "stable", "03": "turn", "04": "turn", "05": "history", "06": "user"}

fig = Figure(
    "02-request-xray", "Layers 03 to 06 share one messages list, in order",
    "The request body that snippets/context_inspector.py prints, in Anthropic Messages shape, with a bracket "
    "from each entry to its layer. The system field is 01 System prompt. The one tool object in the tools list "
    "is 02 Tools and MCP descriptions. In the messages list, the memory message and the assistant reply "
    "Acknowledged are 03 Memory and state, the chunk message is 04 Retrieved chunks, the earlier question about "
    "webhooks and its answer are 05 Conversation history, and the last user message, asking how to rotate the "
    "signing secret, is 06 User instruction. The model and max_tokens fields are call settings, not a layer.",
    subtitle="The body printed by snippets/context_inspector.py, in Anthropic Messages shape.",
    height=720, data_w=True)

X, Y0, LEAD = 40, 128, 24
# a line holding < or > goes in as escaped Raw, so the kit measures the angle brackets as text, not markup
SHOWN = [Raw(html.escape(s, quote=False)) if "<" in s else s for s in LINES]
box = fig.code_block(X, Y0, SHOWN, size=13, leading=LEAD)
BR = int(-(-(X + box.w + 16) // 4) * 4)


def base(k):
    return Y0 + k * LEAD


for label, a, b in groups:
    role = ROLE[label[:2]]
    fig.brace(base(a) - 14, base(b) + 4, BR, side="right", kind="bracket", vertical=True, color=role)
    fig.text(BR + 20, (base(a) + base(b)) / 2 - 1, label, "label", color=role)
a, b = SETTINGS
fig.brace(base(a) - 14, base(b) + 4, BR, side="right", kind="bracket", vertical=True)
fig.text(BR + 20, (base(a) + base(b)) / 2 + 3, "call settings, not a layer", "note")

fig.caption("Layers 01 and 02 have top-level fields of their own; the order inside messages is the layer order.")
fig.write()
