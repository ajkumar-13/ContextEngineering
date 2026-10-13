"""Post 16, section 8: confidence over time for one rule, two events and one fact, by decay on read.

Run from anywhere:  python posts/16-memory-systems/diagrams/src/03-decay.py
Writes posts/16-memory-systems/diagrams/03-decay.svg.
Every plotted value is confidence_on() of snippets/memory_layer.py (loaded with runpy), evaluated day by day on the
snippet's own rows from their last read to 12 October; the two horizontal lines are the snippet's ASK_BELOW and
COLD_BELOW. The rate and both thresholds are illustrative (the snippet and the body say so), which the subtitle
repeats. The end values are asserted against the decay table the body quotes from the snippet's output.
"""
import runpy
import sys
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
M = runpy.run_path(str(POST / "snippets" / "memory_layer.py"))
TODAY, conf, ROWS = M["TODAY"], M["confidence_on"], {r.id: r for r in M["ROWS"]}
ASK, COLD, RATE = M["ASK_BELOW"], M["COLD_BELOW"], M["DECAY_PER_IDLE_DAY"]
assert (ASK, COLD, RATE) == (0.6, 0.4, 0.01)
D0 = date(2026, 5, 20)
END = (TODAY - D0).days
assert END == 145


def day(d):
    return (d - D0).days


# (row, label, colour, shape)
SHOWN = [("mem-10", "rule", "ink", "square"), ("mem-05", "event", "turn", "circle"),
         ("mem-03", "fact", "turn", "diamond"), ("mem-07", "event", "turn", "triangle")]
series, ends = [], {}
for rid, what, color, shape in SHOWN:
    r = ROWS[rid]
    start = date.fromisoformat(r.last_accessed_at)
    xs = list(range(day(start), END + 1))
    ys = [conf(r, D0 + timedelta(d)) for d in xs]
    ends[rid] = ys[-1]
    series.append(dict(xs=xs, ys=ys, color=color, points=False, label=f"{rid} {what}, {ys[-1]:.2f}"))
for rid, v in ends.items():
    assert f"  {rid}  " in BODY and f"{v:.2f}  " in BODY.split(f"  {rid}  ")[1][:40], rid
assert ends == {"mem-10": 1.0, "mem-05": 0.72, "mem-03": 0.5, "mem-07": 0.0}

m7 = ROWS["mem-07"]
cold_day = next(d for d in range(day(date.fromisoformat(m7.last_accessed_at)), END + 1)
                if conf(m7, D0 + timedelta(d)) < COLD)
zero_day = next(d for d in range(cold_day, END + 1) if conf(m7, D0 + timedelta(d)) == 0.0)
assert (D0 + timedelta(cold_day), D0 + timedelta(zero_day)) == (date(2026, 8, 3), date(2026, 9, 11))
assert "is cold from 3 August" in BODY and "to 0.00 by 11 September" in BODY

TICKS = [date(2026, 6, 1), date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)]
MONTH = {6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct"}

desc = ("Confidence, from 0 to 1, against the date from 20 May to 12 October 2026, computed by the snippet's "
        "confidence_on for four rows from their last read. The rule mem-10 stays flat at 1.00 from 20 May. "
        "The event mem-07, last read on 3 June, falls by 0.01 a day, crosses the cold line at 0.4 on 3 August "
        "(marked) and reaches 0.00 on 11 September. The event mem-05, last read on 14 September, is at 0.72 on "
        "12 October. The fact mem-03, last read on 12 September at 0.80, is at 0.50 on 12 October, between the "
        "ask line at 0.6 and the cold line at 0.4.")

fig = Figure("03-decay", "Events and facts fade; a rule does not", desc,
             subtitle="Decay on read in snippets/memory_layer.py: 0.01 per idle day; rate and lines illustrative.",
             data_w=True)
ax = fig.line_chart(Box(40, 104, 880, 372), series, x=(0, END, [day(t) for t in TICKS]), y=(0, 1, [0, 0.2, 0.4, 0.6, 0.8, 1]),
                    x_label="date, 2026", y_label="confidence", label_w=176,
                    fmt_x=lambda v: f"1 {MONTH[(D0 + timedelta(v)).month]}", fmt_y=lambda v: f"{v:.1f}",
                    ref_lines=[dict(y=ASK, label="ask below 0.6", at="left"),
                               dict(y=COLD, label="cold below 0.4", at="left")])
for rid, what, color, shape in SHOWN:
    r = ROWS[rid]
    d = day(date.fromisoformat(r.last_accessed_at))
    ax.point(d, conf(r, D0 + timedelta(d)), shape, color, size=10, hollow=(rid != "mem-10"))
    ax.point(END, ends[rid], shape, color, size=10)
    if rid != "mem-10":
        ax.text(d, conf(r, D0 + timedelta(d)), f"{rid} read {date.fromisoformat(r.last_accessed_at).day} {MONTH[date.fromisoformat(r.last_accessed_at).month]}", "note", dx=(12 if rid == "mem-07" else 0), dy=(24 if rid == "mem-07" else -14))
ax.point(cold_day, conf(m7, D0 + timedelta(cold_day)), "circle", "error", size=10, hollow=True)
ax.text(cold_day, conf(m7, D0 + timedelta(cold_day)), "mem-07 cold from 3 Aug", "note", anchor="end", dx=-12, dy=28)

fig.caption("Hollow marks sit at each row's last read, solid ones at 12 October; the snippet computes every value.")
fig.write()
