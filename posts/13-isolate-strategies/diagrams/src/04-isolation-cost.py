"""Post 13, section 8: input tokens of one agent against an orchestrator with workers, in two cases.

Run from anywhere:  uv run python posts/13-isolate-strategies/diagrams/src/04-isolation-cost.py
Writes posts/13-isolate-strategies/diagrams/04-isolation-cost.svg.
Every value is computed by snippets/isolation_cost.py (its loop() function and its one_shot and looped tables, all
sizes illustrative). The split of the isolated design into workers and orchestrator is recomputed here with the
snippet's loop() and the snippet's arguments, and asserted to add up to the snippet's totals; the totals and the
dollar figures are asserted against the output section 8 quotes.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
S = runpy.run_path(str(POST / "snippets" / "isolation_cost.py"), run_name="figure")
loop, N, P, dollars = S["loop"], S["N"], S["PREAMBLE"], S["dollars"]

# the isolated design, split into its parts (the same calls the snippet adds up)
parts = {
    "one shot": (N * loop(P + 8_000, 0, 0, 0, 1_000)[0], loop(P + N * 1_000, 0, 0, 0, 1_000)[0]),
    "agent loop": (N * loop(P, 4, 100, 2_000, 300)[0], loop(P, N, 100, 300, 1_000)[0]),
}
cases = {"one shot": S["one_shot"], "agent loop": S["looped"]}
for k, case in cases.items():
    assert sum(parts[k]) == case["orchestrator and workers"][0], k

BODY = (POST / "index.md").read_text(encoding="utf-8")
for case in cases.values():
    for design, (t_in, t_out) in case.items():
        line = f"  {design:25} {t_in:>6} in {t_out:>5} out  {dollars(t_in, t_out):.4f} dollars"
        assert line in BODY, line
assert parts == {"one shot": (50_000, 7_000), "agent loop": (155_000, 18_000)}

desc = ("Two panels of horizontal bars of input tokens, illustrative sizes. One shot, five 8,000-token documents "
        "and no tool calls: one agent reads 42,000 tokens; the orchestrator and workers read 57,000, 50,000 in the "
        "five workers and 7,000 in the merge call; 0.1410 against 0.2610 dollars. Agent loop, four tool calls per "
        "piece returning 2,000 tokens each: one agent reads 483,000 tokens; the orchestrator and workers read "
        "173,000, 155,000 in the workers and 18,000 in the orchestrator; 1.4940 against 0.5940 dollars.")
fig = Figure("04-isolation-cost", "Isolation adds tokens to one shot and saves them in a loop", desc,
             subtitle="Input tokens of five pieces of work. Illustrative sizes, computed by snippets/isolation_cost.py.",
             height=720, data_w=True)

COLORS = ["ink", "ink-muted", "stable"]
panels = [
    ("One shot: five documents pasted in, no tool calls", "one shot", 60_000, [0, 20_000, 40_000, 60_000], 128),
    ("Agent loop: four tool calls per piece, 2,000-token results", "agent loop", 500_000,
     [0, 100_000, 200_000, 300_000, 400_000, 500_000], 384),
]
for heading, key, hi, ticks, top in panels:
    fig.text(40, top, heading, "head")
    single = cases[key]["one agent"]
    multi = cases[key]["orchestrator and workers"]
    rows = [("one agent", [single[0], 0, 0]), ("orchestrator and workers", [0, *parts[key]])]
    whole = {single[0]}  # a one-segment bar: its total, printed after it, is its only label
    fig.stacked_bars(Box(40, top + 16, 880, 152), rows, COLORS, 0, hi, ticks, label_w=200, value_w=200,
                     segment_labels=lambda v, whole=whole: "" if v in whole else f"{v:,}")
    fig.text(40, top + 200, f"One agent {dollars(*single):.4f} dollars, orchestrator and workers {dollars(*multi):.4f} dollars", "note")

fig.text(40, 604, "Dollars at Claude Sonnet 4.5's rates: 3 and 15 dollars per million tokens (Anthropic's pricing page, early 2026).", "note")
fig.legend(40, 636, [dict(color="ink", label="one agent"), dict(color="ink-muted", label="workers"),
                                   dict(color="stable", label="orchestrator or merge call")], direction="row")
fig.caption("Splitting a one-shot job pays the preamble five times; a split loop stops re-reading other pieces' results.")
fig.write()
