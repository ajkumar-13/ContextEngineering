"""Post 22, figure 4 (section 6): the replay loop, and its diff fixture by fixture.

Run from the series root:  uv run python posts/22-observability/diagrams/src/04-replay-loop.py
Writes posts/22-observability/diagrams/04-replay-loop.svg.

Where every number comes from: snippets/replay.py, imported and run (FIXTURES, route, replay with PROMPT_V12
and PROMPT_V13); the counts and the failing ids are asserted against what section 6 quotes. The fixtures and
the stand-in model are a toy, so nothing here is a measurement.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Box, Figure  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "replay.py"
M = runpy.run_path(str(SNIP), run_name="snippet")
FIX = M["FIXTURES"]
N = len(FIX)
assert M["replay"](M["PROMPT_V12"]) == ([], [])
ROUTE_DIFFS, FAILS = M["replay"](M["PROMPT_V13"])
assert (N, ROUTE_DIFFS, FAILS) == (8, [], ["fx-02", "fx-05", "fx-07"])
ROUTES = {fid: M["route"](q) for fid, q, _ in FIX}
assert all(ROUTES[fid] == "refunds" for fid in FAILS)

fig = Figure(
    "04-replay-loop", "A replay blocks the release that broke refunds",
    "Top: five boxes left to right joined by arrows: the trace store of captured traces; capture, 8 fixtures "
    "frozen; re-run on prompt v13; diff, routes 8 of 8 and rubric 5 of 8; gate, block v13. Bottom: the diff "
    "fixture by fixture, fx-01 to fx-08, each with its route. fx-02, fx-05 and fx-07, the refund questions, "
    "fail the rubric; the other five pass, and every route matches the recorded one.",
    subtitle="snippets/replay.py: 8 fixtures, prompt v12 against the cleanup release v13; a toy, offline.",
    data_w=True)

STEPS = [
    ("Trace store", ["captured traces"], None),
    ("Capture", [f"{N} fixtures frozen"], None),
    ("Re-run", ["on prompt v13"], None),
    ("Diff", [f"routes {N - len(ROUTE_DIFFS)}/{N}", f"rubric {N - len(FAILS)}/{N}"], None),
    ("Gate", ["block v13"], "error"),
]
W, GAP, Y, H = 152, 30, 128, 112
boxes = []
for k, (head, lines, color) in enumerate(STEPS):
    x = 40 + k * (W + GAP)
    fig.card(x, Y, W, H, heading=head, lines=lines, color=color)
    boxes.append(Box(x, Y, W, H))
fig.chain(boxes)

fig.text(40, 320, "Diff on prompt v13, fixture by fixture", "head")
CW, CG, CY, CH = 96, 16, 344, 96
for k, (fid, _, _) in enumerate(FIX):
    x = 40 + k * (CW + CG)
    failed = fid in FAILS
    b = Box(x, CY, CW, CH)
    fig.fill(b, "error-soft" if failed else "neutral-soft", fit=False)
    fig.outline(b, "error" if failed else "border", width=1.5 if failed else 1)
    fig.text(x + 12, CY + 32, fid, "code13")
    fig.text(x + 12, CY + 56, ROUTES[fid], "note")
    fig.text(x + 12, CY + 80, "fail" if failed else "pass", "label",
             color="error-ink" if failed else None, bold=failed)
fig.caption("Every route still matches; the three refund answers lost the refund window.")
fig.write()
