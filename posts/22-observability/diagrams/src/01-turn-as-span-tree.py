"""Post 22, figure 1 (hero; sections 2 and 4): one agent turn as a span tree on a time axis, beside the four
dashboard cards that aggregate every trace.

Run from the series root:  uv run python posts/22-observability/diagrams/src/01-turn-as-span-tree.py
Writes posts/22-observability/diagrams/01-turn-as-span-tree.svg.

Where every number comes from: snippets/trace_store.py, imported and run (simulate_turn on its fake clock);
the start, end and cost of every span are read from the trace it stores and asserted against the tree that
section 2 quotes. Timings and token counts are illustrative, so the bars have dashed outlines and the subtitle
says so. The four card names are section 4's four numbers.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, num  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "trace_store.py"
M = runpy.run_path(str(SNIP), run_name="snippet")
clock = M["Clock"]()
tracer = M["Tracer"](clock)
M["simulate_turn"](tracer, clock)
TRACE = tracer.store[0]
ROWS = []
for depth, r in M["walk"](TRACE):
    name = r["name"] if "tool" not in r["attrs"] else f"{r['name']} {r['attrs']['tool']}"
    cost = M["total_cost"](r) if depth == 0 else r["attrs"].get("cost_usd")
    ROWS.append((depth, name, r["start_ms"], r["end_ms"], cost))
assert [(n, e - s) for _, n, s, e, _ in ROWS] == [
    ("turn", 4500), ("assemble_context", 40), ("load_memory", 30), ("select_tools", 10), ("retrieve", 560),
    ("query_rewrite", 350), ("hybrid_search", 90), ("rerank", 120), ("llm_call", 3800),
    ("tool_call issue_refund", 100), ("db_query", 60)]
COSTS = {n: c for _, n, _, _, c in ROWS if c is not None}
assert {k: f"{v:.5f}" for k, v in COSTS.items()} == {
    "turn": "0.02558", "query_rewrite": "0.00050", "llm_call": "0.02508"}
TOTAL = ROWS[0][3]

fig = Figure(
    "01-turn-as-span-tree", "One turn is a tree of timed, priced spans",
    "Left: one support-agent turn as a span tree, one row per span, indented by depth, with a dashed bar on a "
    "time axis from 0 to 4,500 milliseconds and its duration and cost at the right. turn 4,500 ms, 0.02558 "
    "dollars; assemble_context 40 ms; load_memory 30; select_tools 10; retrieve 560; query_rewrite 350 ms, "
    "0.00050 dollars; hybrid_search 90; rerank 120; llm_call 3,800 ms, 0.02508 dollars; tool_call "
    "issue_refund 100; db_query 60. Right: four dashboard cards fed by every trace: cost per session at the "
    "median and p95, latency at p95, quality as the evaluation score of sampled traffic, and errors by kind.",
    subtitle="A support-agent turn from snippets/trace_store.py; timings and token counts illustrative.",
    height=720, data_w=True)

NAME_X, BAR_X0, BAR_X1, MS_X, USD_X = 40, 224, 528, 600, 680
TOP, PITCH, BAR_H = 160, 40, 24
fig.text(40, 120, "One trace, 11 spans", "head")
fig.text(MS_X, 148, "ms", "note", anchor="end")
fig.text(USD_X, 148, "dollars", "note", anchor="end")
scale = (BAR_X1 - BAR_X0) / TOTAL
for k, (depth, name, start, end, cost) in enumerate(ROWS):
    y = TOP + k * PITCH
    fig.text(NAME_X + 16 * depth, y + 16, name, "code13")
    with fig.data():
        b = Box(BAR_X0 + start * scale, y, max(4.0, (end - start) * scale), BAR_H)
        fig.fill(b, "neutral-soft", fit=False)
        fig.outline(b, "ink", width=1, dash="proj")
    fig.text(MS_X, y + 16, num(end - start), "label", anchor="end")
    if cost is not None:
        fig.text(USD_X, y + 16, f"{cost:.5f}", "value" if depth == 0 else "label", anchor="end")

# time axis under the bars
AX_Y = TOP + len(ROWS) * PITCH
fig.edge((BAR_X0, AX_Y), (BAR_X1, AX_Y), color="ink-muted", width=1)
for t in (0, 1500, 3000, 4500):
    x = BAR_X0 + t * scale
    fig.edge((x, AX_Y), (x, AX_Y + 8), color="ink-muted", width=1)
    fig.text(x, AX_Y + 28, num(t), "tick", anchor="middle")
fig.text((BAR_X0 + BAR_X1) / 2, AX_Y + 52, "time from the start of the turn, ms", "note", anchor="middle")

# the dashboard
CX, CW, CH = 712, 208, 92
fig.text(CX, 120, "Dashboard, every trace", "head")
cards = [("Cost per session", "median and p95"), ("Latency", "p95, not the mean"),
         ("Quality", "eval score, sampled traffic"), ("Errors", "rate, by kind")]
for k, (head, line) in enumerate(cards):
    fig.card(CX, TOP + k * (CH + 24), CW, CH, heading=head, lines=[line], style="note")
fig.caption("The model call is 3,800 of the 4,500 ms and 0.02508 of the 0.02558 dollars.")
fig.write()
