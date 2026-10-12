"""Post 02, section 11: why the stable layers go first. Two consecutive calls, drawn as flat strips, under two layouts.

Run from anywhere:  python posts/02-six-layers-of-context/diagrams/src/03-prefix-cache.py
Writes posts/02-six-layers-of-context/diagrams/03-prefix-cache.svg.
No numbers are drawn. The rule drawn is the one section 11 cites (Anthropic, "Prompt caching"): a cache hit needs
an identical prefix, so reuse stops at the first entry that differs between the two calls. Which entries differ
follows from section 3's lifetimes: 01 and 02 are the same on every call; 03 and 04 are assembled for each call;
05 gains the previous turn; 06 is new. In the second layout a per-turn value (the time of the call) is written into
01, the first pitfall of the post. The names come from snippets/context_inspector.py (LAYERS).
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "context_inspector.py"
LAYERS = runpy.run_path(str(SNIP), run_name="snippet")["LAYERS"]
assert LAYERS[2] == "Tools and MCP descriptions" and LAYERS[5] == "Conversation history"
NAME_LINES = {1: ["System prompt"], 2: ["Tools and MCP", "descriptions"], 3: ["Memory and state"],
              4: ["Retrieved chunks"], 5: ["Conversation", "history"], 6: ["User instruction"]}
assert all(" ".join(v) == LAYERS[k] for k, v in NAME_LINES.items())
ROLE = {1: "stable", 2: "stable", 3: "turn", 4: "turn", 5: "history", 6: "user"}

CHANGES_A = {1: False, 2: False, 3: True, 4: True, 5: True, 6: True}   # section 3's lifetimes
CHANGES_B = {**CHANGES_A, 1: True}                                        # the time of the call written into 01


def cached(changes):
    """How many leading entries an identical-prefix cache can reuse: up to the first one that differs."""
    n = 0
    for k in sorted(changes):
        if changes[k]:
            break
        n += 1
    return n


assert cached(CHANGES_A) == 2 and cached(CHANGES_B) == 0

fig = Figure(
    "03-prefix-cache", "A prompt cache reuses the prefix up to the first change",
    "Two panels, each with two consecutive calls drawn as flat strips of the six layers, 01 System prompt on "
    "the left to 06 User instruction on the right, with an equals or not-equals sign between the calls under "
    "each layer. Top panel, stable layers first: 01 and 02 are equal, 03 to 06 differ, so on call 2 layers 01 "
    "and 02 are read from the cache and 03 to 06 are billed at the full input rate. Bottom panel, the time of "
    "the call written into the system prompt: 01 already differs, so nothing is read from the cache and all "
    "six are billed at the full input rate.",
    subtitle="Two calls, cached in the layer order 01 to 06. Reuse stops at the first entry that differs.",
    height=720, data_w=True)

X0, CW, GAP, CH = 104, 128, 8, 64


def cell_box(k, y):
    return Box(X0 + (k - 1) * (CW + GAP), y, CW, CH)


def strip(y, label):
    fig.text(40, y + 38, label, "label")
    for k in LAYERS:
        b = cell_box(k, y)
        fig.fill(b, f"{ROLE[k]}-soft", radius=8, fit=False)
        fig.outline(b, f"{ROLE[k]}-line", radius=8)
        fig.text(b.x + 12, y + 24, f"{k:02d}", "head")
        for i, line in enumerate(NAME_LINES[k]):
            fig.text(b.x + 12, y + 42 + 16 * i, line, "tick", color="ink")


def panel(top, heading, changes, broken):
    fig.text(40, top, heading, "head")
    y1, y2 = top + 16, top + 120
    strip(y1, "call 1")
    strip(y2, "call 2")
    for k in LAYERS:
        b = cell_box(k, y1)
        sym = "\u2260" if changes[k] else "="
        fig.op(b.cx, y1 + CH + 20, sym, color="error" if (broken and k == 1) else None)
    n = cached(changes)
    yb = y2 + CH + 8
    if n:
        fig.brace(cell_box(1, y2).x, cell_box(n, y2).right, yb, "read from the cache", kind="bracket",
                  color="stable")
    fig.brace(cell_box(n + 1, y2).x, cell_box(6, y2).right, yb,
              "nothing read from the cache: all billed at the full input rate" if broken
              else "billed at the full input rate", kind="bracket", color="error" if broken else None)


panel(136, "Stable layers first", CHANGES_A, broken=False)
panel(408, "The time of the call written into the system prompt", CHANGES_B, broken=True)

fig.caption("Per-turn data in layer 01 ends the reusable prefix before it starts, however stable the rest is.")
fig.write()
