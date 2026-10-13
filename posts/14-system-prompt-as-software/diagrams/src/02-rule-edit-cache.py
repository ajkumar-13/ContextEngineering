"""Post 14, section 5: what one rule edit does to the cached prefix, in Anthropic's cache order.

Run from anywhere:  python posts/14-system-prompt-as-software/diagrams/src/02-rule-edit-cache.py
Writes posts/14-system-prompt-as-software/diagrams/02-rule-edit-cache.svg.
The mechanism is section 5's, from Anthropic's "Prompt caching" documentation as post 05 states it (consulted
October 2026): the prefix runs tools, system, messages; a write costs 1.25 times and a read 0.1 times the base
input price (most models). Both multipliers and the order are asserted against index.md. The edit is the
snippet's (snippets/prompt_ci.py): only the Rules block differs between PARTS_V1 and PARTS_V2 (asserted).
No token counts are drawn; segment widths are not to scale.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
SNIP = runpy.run_path(str(POST / "snippets" / "prompt_ci.py"), run_name="snippet")
changed = [b for b in SNIP["BLOCKS"] if SNIP["PARTS_V1"][b] != SNIP["PARTS_V2"][b]]
assert changed == ["Rules"] and SNIP["PARTS_V2"]["Rules"][0] == "1.3.0" and SNIP["PARTS_V1"]["Rules"][0] == "1.2.0"

WRITE, READ = "1.25", "0.1"
for phrase in (f"a cache write costs {WRITE} times the base input price for the default five-minute lifetime",
               f"a cache read costs {READ} times the base input price on most models",
               "the prefix is built in the order `tools`, `system`, `messages`",
               "the snippet's change from rules 1.2.0 to 1.3.0"):
    assert phrase in BODY, phrase

SEGS = [("02 Tools and MCP", "descriptions", "stable"), ("01 System prompt", "five blocks", "stable"),
        ("03 to 06", "per-turn layers", "turn")]
W_, R_, F_ = f"write at {WRITE} times", f"read at {READ} times", "full rate"
ROWS = [("First call, v1", "rules 1.2.0", [W_, W_, F_]),
        ("Later call, v1", "rules 1.2.0", [R_, R_, F_]),
        ("First call, v2", "rules 1.3.0", [R_, W_, F_])]

desc = ("Three rows of one request in Anthropic's cache order: 02 Tools and MCP descriptions, then 01 System prompt "
        "with its five blocks, then the per-turn layers 03 to 06, with a cache breakpoint after the tools and "
        "another after the system prompt. ")
for name, note, states in ROWS:
    desc += f"{name} ({note}): tools {states[0]}, system prompt {states[1]}, layers 03 to 06 {states[2]}. "
desc += "In the last row the system prompt segment is marked Rules block edited. Multipliers are of the base input price; segment widths are not to scale."

fig = Figure("02-rule-edit-cache", "A rule edit rewrites the system prompt's cache entry", desc,
             subtitle="Anthropic's cache order with two breakpoints; prices as multiples of the base input price.",
             data_w=True)

X = [232, 420, 732]
W = [180, 304, 188]
TOP, RH, RG = 176, 64, 24

# column heads
for (l1, l2, role), x in zip(SEGS, X):
    fig.text(x + 12, 124, l1, "head", color=role)
    fig.text(x + 12, 146, l2, "note")

for r, (name, note, states) in enumerate(ROWS):
    y = TOP + r * (RH + RG)
    fig.text(40, y + 28, name, "head")
    fig.text(40, y + 50, note, "note")
    for (_, _, role), x, w, state in zip(SEGS, X, W, states):
        b = Box(x, y, w, RH)
        if state == R_:
            fig.fill(b, "stable-soft", radius=6, fit=False)
            fig.outline(b, "stable", radius=6, width=1.5)
        elif state == W_:
            fig.fill(b, "surface", radius=6, fit=False)
            fig.outline(b, "stable", radius=6, width=2.5)
        else:
            fig.fill(b, "neutral-soft", radius=6, fit=False)
            fig.outline(b, "border", radius=6)
        fig.text(x + 12, y + 38, state, "label")
        if r == 2 and role == "stable" and state == W_:
            fig.text(x + w - 12, y + 38, "Rules block edited", "note", anchor="end")

# the two breakpoints
bottom = TOP + 2 * (RH + RG) + RH
for i in (0, 1):
    bx = X[i] + W[i] + 4
    fig.edge((bx, TOP - 8), (bx, bottom + 8), color="ink-muted", width=1.5, dash="ref")
    fig.text(bx, bottom + 32, "breakpoint", "note", anchor="middle")

fig.caption("The tools before the first breakpoint stay readable; the edited system prompt is written once more.")
fig.write()
