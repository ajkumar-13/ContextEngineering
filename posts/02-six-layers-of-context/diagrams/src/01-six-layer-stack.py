"""Post 02 hero: the context window as a stack of six layers, sent top to bottom, bracketed by lifetime.

Run from anywhere:  python posts/02-six-layers-of-context/diagrams/src/01-six-layer-stack.py
Writes posts/02-six-layers-of-context/diagrams/01-six-layer-stack.svg.
The layer names come from snippets/context_inspector.py (LAYERS), the post's fixed vocabulary; the clauses
are section 3's purpose column, shortened; the four lifetime classes are section 3's. The figure shows no sizes:
the post's sizes are illustrative, and this figure is about order and lifetime, not size.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "context_inspector.py"
LAYERS = runpy.run_path(str(SNIP), run_name="snippet")["LAYERS"]
assert list(LAYERS.values()) == ["System prompt", "Tools and MCP descriptions", "Memory and state",
                                 "Retrieved chunks", "Conversation history", "User instruction"]

CLAUSE = {1: "identity, rules, output format",
          2: "the schema of every callable tool",
          3: "facts kept beyond this call",
          4: "evidence fetched for this turn",
          5: "the earlier turns of this session",
          6: "what the user just asked"}
# lifetime class: (first layer, last layer, role, name, note)
CLASSES = [(1, 2, "stable", "Stable prefix", "same on every call"),
           (3, 4, "turn", "Per-turn injection", "assembled for this call"),
           (5, 5, "history", "Growing tail", "longer every turn"),
           (6, 6, "user", "Trigger", "small, sent last")]
ROLE = {k: role for a, b, role, _, _ in CLASSES for k in range(a, b + 1)}

fig = Figure(
    "01-six-layer-stack", "One call, six layers, four lifetimes",
    "A stack of six horizontal bands, sent from the top. 01 System prompt: identity, rules, output format. "
    "02 Tools and MCP descriptions: the schema of every callable tool. 03 Memory and state: facts kept beyond "
    "this call. 04 Retrieved chunks: evidence fetched for this turn. 05 Conversation history: the earlier turns "
    "of this session. 06 User instruction: what the user just asked. Brackets on the right group them by "
    "lifetime: 01 and 02 the stable prefix, the same on every call; 03 and 04 the per-turn injection, assembled "
    "for this call; 05 the growing tail, longer every turn; 06 the trigger, small and sent last. An arrow on the "
    "left runs from sent first at the top to sent last at the bottom.",
    subtitle="The window the model reads on one call, in the order it is sent.",
    data_w=True)

X0, X1 = 112, 680            # the bands
Y0, BH, GAP = 104, 52, 12    # first band top, band height, gap
NAME_X, CLAUSE_X = X0 + 20, X0 + 292
BR_X = X1 + 16               # the lifetime brackets
tops = {k: Y0 + (k - 1) * (BH + GAP) for k in LAYERS}

for k, name in LAYERS.items():
    band = Box(X0, tops[k], X1 - X0, BH)
    fig.fill(band, f"{ROLE[k]}-soft", radius=8, fit=False)
    fig.outline(band, f"{ROLE[k]}-line", radius=8)
    fig.text(NAME_X, tops[k] + 32, f"{k:02d} {name}", "head")
    fig.text(CLAUSE_X, tops[k] + 32, CLAUSE[k], "label")

for a, b, role, name, note in CLASSES:
    ya, yb = tops[a] + 4, tops[b] + BH - 4
    fig.brace(ya, yb, BR_X, side="right", kind="bracket", vertical=True, color=role)
    mid = (tops[a] + tops[b] + BH) / 2
    fig.text(BR_X + 24, mid - 2, name, "head", color=role)
    fig.text(BR_X + 24, mid + 18, note, "note")

# sent first at the top, sent last at the bottom
fig.text(40, tops[1] + 32, "first", "note")
fig.text(40, tops[6] + 32, "last", "note")
fig.arrow((60, tops[1] + 48), (60, tops[6] + 12))

fig.caption("The order runs from the layers that rarely change to the one that is new on every call.")
fig.write()
