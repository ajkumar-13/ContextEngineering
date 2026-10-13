"""Post 15, section 4: what a selection step does to layer 02, from the companion's budget calculator.

Run from anywhere:  uv run python posts/15-tools-and-mcp/diagrams/src/03-selection-budget.py
Writes posts/15-tools-and-mcp/diagrams/03-selection-budget.svg.
Every number and name is produced here by running snippets/catalogue_budget.py (its catalogues, its
select_tools on its TURN, and the companion's catalog_tokens estimate) and asserted against the output section 4
quotes. The bars are one series, so they are ink; the near miss takes the error role.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
SNIP = runpy.run_path(str(POST / "snippets" / "catalogue_budget.py"), run_name="figure")
tokens = SNIP["catalog_tokens"]
RICH, THIN, CHOSEN = tokens(SNIP["CATALOGUE"]), tokens(SNIP["THIN"]), tokens(SNIP["CHOSEN"])
NAMES = [t["name"] for t in SNIP["CHOSEN"]]
BODY = (POST / "index.md").read_text(encoding="utf-8")
assert f"50 rich, no selection            {RICH}" in BODY and f"50 thin, no selection            {THIN}" in BODY
assert f"5 rich, selected                  {CHOSEN}" in BODY
assert "selected: " + ", ".join(NAMES) in BODY
assert (RICH, THIN, CHOSEN) == (6348, 2430, 681)
assert NAMES[-1] == "create_order" and 'got in on the word "order"' in BODY
CUT = [t["name"] for t in SNIP["trim"](SNIP["CATALOGUE"], keep=5)]
assert not any("shipment" in n for n in CUT) and f"({tokens(SNIP['trim'](SNIP['CATALOGUE'], keep=5))} estimated tokens)" in BODY
assert f"Selection keeps {CHOSEN:,} of {RICH:,} estimated tokens, 10.7 percent" in BODY

desc = (f"Left, a bar chart of estimated tokens per call in layer 02, from the companion's calculator: 50 rich tools "
        f"with no selection {RICH:,}, 50 thin tools with no selection {THIN:,}, and 5 rich tools kept by the selection "
        f"step {CHOSEN:,}. Right, the five tools kept for the turn about order A-4821: "
        f"{', '.join(NAMES[:-1])}, and {NAMES[-1]}, marked in red as a near miss that matched only the word order.")
fig = Figure("03-selection-budget", "Selection keeps a tenth of the tokens", desc,
             subtitle="One turn, a fifty-tool toy catalogue; estimates by code/15-tool-schemas at four characters per token.",
             height=540, data_w=True)

left, right = fig.row([3, 2])
body = fig.panel(left, "Estimated tokens per call in layer 02")
rows = [("50 rich, no selection", RICH, "ink"), ("50 thin, no selection", THIN, "ink"),
        ("5 rich, selected", CHOSEN, "ink")]
fig.bar_chart(Box(body.x, body.y, body.w, 336), rows, 0, 8000, [0, 2000, 4000, 6000, 8000],
              fmt=lambda v: f"{v:,.0f}", label_w=168, value_w=64, axis_label="tokens")

rb = fig.panel(right, "Kept for this turn")
for i, name in enumerate(NAMES):
    y = rb.y + 28 + 40 * i
    fig.text(rb.x, y, f"{i + 1}", "note")
    fig.text(rb.x + 24, y, name, "code", color="error" if name == "create_order" else None)
fig.text(rb.x + 24, rb.y + 28 + 40 * 5, "matched only on the word order;", "note")
fig.text(rb.x + 24, rb.y + 28 + 40 * 5 + 20, "a reranker would demote it", "note")
fig.text(rb.x, rb.y + 316, "Turn: order A-4821 shipped, no delivery", "note")

fig.caption("Selection keeps a tenth of the tokens; create_order is the near miss a reranker would demote.")
fig.write()
