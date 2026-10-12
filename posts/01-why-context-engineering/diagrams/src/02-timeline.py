"""Post 01, section 2: the work changed (below the axis) years before the name arrived (above it).

Run from anywhere:  python posts/01-why-context-engineering/diagrams/src/02-timeline.py
Writes posts/01-why-context-engineering/diagrams/02-timeline.svg.
Every date is one index.md states with its source (sections 1 and 2, and Further reading); the table below names
the source of each, and the script asserts that the post states the date in those words. An event dated only to
the year (the RAG paper) is placed at mid-year; a month at its middle. IBM Think (2025, undated on the page) and
12-Factor Agents (2025) carry no month and are not placed.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure  # noqa: E402

BODY = (Path(__file__).resolve().parents[2] / "index.md").read_text(encoding="utf-8")

# (year, month or None, label above or below, date text, event, source, phrase the post must contain)
EVENTS = [
    (2020, None, "below", "2020", "RAG paper, Lewis et al.", "Lewis et al. (NeurIPS 2020)",
     "named by Lewis et al. in 2020"),
    (2023, 6, "below", "June 2023", "OpenAI function calling", "OpenAI, \"Function calling and other API updates\"",
     "OpenAI added function calling to its application programming interface (API) in June 2023"),
    (2024, 11, "below", "November 2024", "Model Context Protocol", "Anthropic, \"Introducing the Model Context "
     "Protocol\"", "which Anthropic introduced in November 2024"),
    (2025, 6, "above", "June 2025", "Martin's essay, Karpathy's post", "Martin's blog; Karpathy on X",
     "on his own blog in June 2025"),
    (2025, 9, "above", "September 2025", "Anthropic Engineering article", "Anthropic Engineering, \"Effective "
     "context engineering for AI agents\"", "published \"Effective context engineering for AI agents\" in September 2025"),
]
for *_, phrase in EVENTS:
    assert phrase in BODY, phrase
assert "in a post on X on 25 June 2025" in BODY

X0, X1, Y0, Y1 = 72, 888, 2020, 2026            # the axis: 1 January 2020 to 1 January 2026
AY = 328                                        # axis baseline


def xof(year, month):
    t = year + (0.5 if month is None else (month - 0.5) / 12)
    return X0 + (t - Y0) / (Y1 - Y0) * (X1 - X0)


fig = Figure(
    "02-timeline", "The work changed for years before the name did",
    "A horizontal timeline from 2020 to 2026 with a tick at each year. Below the axis, the changes to the work: "
    "the RAG paper by Lewis et al. in 2020, OpenAI function calling in June 2023, and the Model Context Protocol "
    "in November 2024. Above the axis, the naming of the work: Lance Martin's essay and Andrej Karpathy's post in "
    "June 2025, and Anthropic Engineering's article in September 2025.",
    subtitle="Dates as the post cites them: changes to the work below the axis, the naming of the work above it.",
    data_w=True)

fig.edge((X0, AY), (X1, AY), color="ink", width=1.5)
for yr in range(Y0, Y1 + 1):
    x = X0 + (yr - Y0) / (Y1 - Y0) * (X1 - X0)
    fig.edge((x, AY - 6), (x, AY + 6), color="ink-muted", width=1)
    fig.text(x, AY - 16, str(yr), "tick", anchor="middle")   # above: the leaders below pass clear

ROW = {"below": (AY + 48, AY + 68), "above": (AY - 76, AY - 56)}
for year, month, side, date, event, _src, _ in EVENTS:
    x = xof(year, month)
    date_y, event_y = ROW[side]
    if month == 9:                                # the September label goes one row higher, clear of June's
        date_y, event_y = AY - 148, AY - 128
    anchor = "end" if side == "above" else "start"
    with fig.data():
        if side == "above":                       # a flag: the leader runs up beside the label to its top
            fig.edge((x, AY - 8), (x, date_y - 14), color="rule", width=1)
        else:
            fig.edge((x, AY + 8), (x, event_y + 4), color="rule", width=1)
        fig.marker(x, AY, "circle", "ink", size=10)
        dx = 8 if anchor == "start" else -8
        fig.text(x + dx, date_y, date, "value", anchor=anchor, snap=False)
        fig.text(x + dx, event_y, event, "label", anchor=anchor, snap=False)

fig.caption("Function calling shipped two years before \"context engineering\" became the common term.")
fig.write()
