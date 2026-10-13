"""Post 19, section 7: where an image sits decides whether it caches. Two layouts of the same computer-use call.

Run from the series root:  uv run python posts/19-multimodal-context/diagrams/src/04-image-cache-boundary.py
Writes posts/19-multimodal-context/diagrams/04-image-cache-boundary.svg.

No numbers are drawn. The rule is Anthropic's "Prompt caching" page (consulted October 2026), as post 05 states it:
a hit needs 100% identical prompt segments, text and images, up to the block marked with cache control, so reuse
stops at the first entry that differs from the previous call. Both layouts carry breakpoints after layer 02 and
after the reference page. In the first, this turn's screenshot sits before the reference page; in the second, it
travels with layer 06, last. Which entries differ follows post 02's lifetimes.
"""
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

# (head, lines, role, changes between calls)
SYS = ("01", ["System prompt"], "stable", False)
TOOLS = ("02", ["Tools and MCP", "descriptions"], "stable", False)
PAGE = ("Reference", ["page image"], "stable", False)
SHOT3 = ("03", ["Memory and state", "live screenshot"], "turn", True)
MEM = ("03", ["Memory and state"], "turn", True)
RET = ("04", ["Retrieved chunks"], "turn", True)
HIST = ("05", ["Conversation", "history"], "history", True)
USER = ("06", ["User instruction", "+ live screenshot"], "user", True)
ROW_A = [SYS, TOOLS, SHOT3, PAGE, RET, HIST, ("06", ["User instruction"], "user", True)]
ROW_B = [SYS, TOOLS, PAGE, MEM, RET, HIST, USER]
BREAKS = {"A": (1, 3), "B": (1, 2)}   # breakpoint after these cell indices


def reusable(row, breaks):
    """Cells read from the cache: up to the last breakpoint that comes before the first changing cell."""
    first_change = next(i for i, c in enumerate(row) if c[3])
    ok = [b for b in breaks if b < first_change]
    return max(ok) + 1 if ok else 0


assert reusable(ROW_A, BREAKS["A"]) == 2 and reusable(ROW_B, BREAKS["B"]) == 3

fig = Figure(
    "04-image-cache-boundary", "Stable pixels before the breakpoint, live pixels after",
    "Two layouts of one call of a computer-use agent, drawn as strips of seven entries with cache breakpoints "
    "after layer 02 and after a reference page image. Top: this turn's screenshot sits in layer 03, before the "
    "reference page; it changes every call, so only 01 System prompt and 02 Tools and MCP descriptions are read "
    "from the cache, and the reference page is processed again every call, marked in red. Bottom: the reference "
    "page follows layer 02 and the live screenshot travels with 06 User instruction, last; 01, 02 and the "
    "reference page are read from the cache, and 03 to 06 are new on every call.",
    subtitle="Anthropic prompt caching (consulted October 2026): a hit needs identical text and images.",
    data_w=True)

X0, CW, GAP, CH = 40, 120, 4, 80


def cell(i, y):
    return Box(X0 + i * (CW + GAP), y, CW, CH)


def strip(top, heading, row, breaks, bad):
    fig.text(40, top, heading, "head")
    y = top + 24
    for i, (head, lines, role, changes) in enumerate(row):
        b = cell(i, y)
        fig.fill(b, f"{role}-soft", radius=8, fit=False)
        fig.outline(b, "error" if (bad and head == "03") else f"{role}-line", radius=8,
                    width=2.5 if (bad and head == "03") else 1)
        fig.text(b.x + 8, y + 24, head, "head")
        for j, line in enumerate(lines):
            fig.text(b.x + 8, y + 44 + 18 * j, line, "tick", color="ink")
    for k in breaks:
        x = cell(k, y).right + GAP / 2
        with fig.data():
            fig.edge((x, y - 12), (x, y + CH + 4), color="ink", width=1.5, dash="lead")
    n = reusable(row, breaks)
    yb = y + CH + 12
    fig.brace(cell(0, y).x, cell(n - 1, y).right, yb, "read from the cache", kind="bracket", color="stable")
    if bad:
        fig.brace(cell(n, y).x, cell(len(row) - 1, y).right, yb,
                  "processed again on every call, reference page included", kind="bracket", color="error")
    else:
        fig.brace(cell(n, y).x, cell(len(row) - 1, y).right, yb, "new on every call", kind="bracket")


strip(128, "This turn's screenshot early", ROW_A, BREAKS["A"], bad=True)
strip(312, "Reference page early, this turn's screenshot last", ROW_B, BREAKS["B"], bad=False)
fig.text(920, 128, "dashed line: cache breakpoint", "note", anchor="end")

fig.caption("An image that changes every call ends the reusable prefix wherever it sits.")
fig.write()
