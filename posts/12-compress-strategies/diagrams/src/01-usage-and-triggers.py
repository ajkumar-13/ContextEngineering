"""Post 12, hero and section 9: input-budget usage over one simulated session under three policies.

Run from anywhere:  python posts/12-compress-strategies/diagrams/src/01-usage-and-triggers.py
Writes posts/12-compress-strategies/diagrams/01-usage-and-triggers.svg.
Every plotted value is computed by snippets/compaction_policy.py (run(policy): usage before and after each turn's
compression, as a share of the 180,000-token input budget); the session's sizes are the snippet's illustrative
constants, and the triggers are section 9's illustrative policy values. The events the post states are asserted.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
M = runpy.run_path(str(POST / "snippets" / "compaction_policy.py"), run_name="snippet")
assert (M["BUDGET"], M["SOFT"], M["HARD"], M["SOFT_TARGET"], M["TURNS"]) == (180_000, 0.80, 0.95, 0.60, 110)
RUNS = {p: M["run"](p) for p in ("none", "summarise-only", "two-trigger")}

# the events the post and the alt text state
first_over = next(t for t, b, a, e in RUNS["none"] if a > 1.0)
assert first_over == 31
assert [t for t, b, a, e in RUNS["summarise-only"] if e == "hard"] == [30, 56, 83, 108]
assert [t for t, b, a, e in RUNS["two-trigger"] if e == "hard"] == [98]
assert [t for t, b, a, e in RUNS["two-trigger"] if e == "soft" and a < 0.60] == [25, 32, 38, 46, 53, 61]
BODY = (POST / "index.md").read_text(encoding="utf-8")
for phrase in ("Without compression the input passes the budget at turn 31",
               "at the price of four lossy summaries in 110 turns", "the one summary comes at turn 98"):
    assert phrase in BODY, phrase


def sawtooth(rows):
    """One point per turn before compression, and a second at the same turn after it when usage dropped."""
    xs, ys = [], []
    for t, before, after, _ in rows:
        xs.append(t)
        ys.append(100 * min(before, 1.3))
        if after < before:
            xs.append(t)
            ys.append(100 * after)
    return xs, ys


# the three runs are identical until the first soft pass at turn 25; the uncompressed run is drawn from there
none_x, none_y = sawtooth([r for r in RUNS["none"] if r[0] >= 24])
k = next(i for i, v in enumerate(none_y) if v > 120)          # stop the line where it leaves the plot at 120%
x0, y0, x1, y1 = none_x[k - 1], none_y[k - 1], none_x[k], none_y[k]
none_x, none_y = none_x[:k] + [x0 + (x1 - x0) * (120 - y0) / (y1 - y0)], none_y[:k] + [120]
assert RUNS["none"][:24] == RUNS["two-trigger"][:24] == RUNS["summarise-only"][:24]
sum_x, sum_y = sawtooth(RUNS["summarise-only"])
two_x, two_y = sawtooth(RUNS["two-trigger"])

desc = ("A line chart of input-budget usage, in percent of 180,000 tokens, over 110 turns of one simulated agent "
        "session, with dotted lines at the 95 percent hard trigger, the 80 percent soft trigger and the 60 percent "
        "soft target. Without compression usage climbs steadily and passes the budget at turn 31. Summarising "
        "alone drops it at turns 30, 56, 83 and 108, four summaries. The two-trigger policy clears stale tool "
        "results at 80 percent, back under 60 percent at turns 25, 32, 38, 46, 53 and 61; later passes fall short, "
        "and its only summary comes at turn 98, from 95.1 to 17.8 percent.")

fig = Figure("01-usage-and-triggers", "Clearing tool results first postpones the lossy summary", desc,
             subtitle="One simulated session, illustrative sizes: 110 turns against a 180,000-token input budget.",
             data_w=True)

ax = fig.line_chart(
    Box(40, 104, 880, 372),
    [dict(xs=sum_x, ys=sum_y, color="ink-muted", label="summarise only", points=False, dash="proj"),
     dict(xs=two_x, ys=two_y, color="ink", label="two triggers", points=False),
     dict(xs=none_x, ys=none_y, color="error", label=None, points=False)],
    x=(0, 110, [0, 20, 40, 60, 80, 100]), y=(0, 120, [0, 20, 40, 60, 80, 100, 120]),
    x_label="turn", y_label="input tokens, percent of the budget", fmt_y=lambda v: f"{v:.0f}%",
    label_w=152, hbands=[(100, 120, "error")],
    ref_lines=[dict(y=95, label="hard trigger 95%", at="right"), dict(y=80, label="soft trigger 80%", at="right"),
               dict(y=60, label="soft target 60%", at="left")])
ax.text(2, 110, "over the input budget", style="label", color="error-ink", dy=5)
ax.text(38, 110, "no compression: over it from turn 31", style="label", color="error-ink", dy=5)
fig.caption("The soft pass needs no model call; the summary is kept for when nothing cheaper is left.")
fig.write()
