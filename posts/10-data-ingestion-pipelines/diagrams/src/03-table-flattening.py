"""Post 10, section 4: a table flattened to a stream loses its empty cell; the same table as Markdown keeps it.

Run from anywhere:  python posts/10-data-ingestion-pipelines/diagrams/src/03-table-flattening.py
Writes posts/10-data-ingestion-pipelines/diagrams/03-table-flattening.svg.
Every value is computed here by snippets/flatten_table.py (imported): the table, the flat stream, the grid read back
by position and the Markdown. The prices are the snippet's illustrative prices; the result lines are asserted
against the output that section 4 quotes.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box, rich, span  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
S = runpy.run_path(str(POST / "snippets" / "flatten_table.py"), run_name="snippet")
HEADER, ROWS = S["HEADER"], S["ROWS"]
flat = S["flatten"](HEADER, ROWS)
back = S["rebind"](flat, HEADER, [r[0] for r in ROWS])
md = S["to_markdown"](HEADER, ROWS)
assert flat == "Product Basic Pro Product A $10 $20 Product B $15 $30 Product C $25"
assert back["Product C"] == {"Basic": "$25"}
assert S["lookup"](md, "Product C", "Basic") == "(empty)" and S["lookup"](md, "Product C", "Pro") == "$25"
for line in ("flattened: " + flat, "  read back by position, Product C: {'Basic': '$25'}",
             "  Product C, Basic: flat stream says $25, Markdown says (empty)", md):
    assert line in BODY, line

# the flat stream, broken for the figure after Product A's row (the break is layout only)
cut = flat.index(" Product B")
flat_lines = [flat[:cut], flat[cut + 1:]]
assert flat_lines[1].endswith(" $25")
flat_lines[1] = rich(flat_lines[1][:-3], span("$25", color="error"))   # the price that slides, in red

desc = ("Left, the source table: header Product, Basic, Pro; Product A $10 and $20; Product B $15 and $30; Product C "
        "with an empty Basic cell, outlined in red, and $25 under Pro. Right, top: the flattened stream, " + flat +
        ", with the final $25 in red; read back by position it gives Product C, Basic $25, marked wrong in red. Right, bottom: the same table "
        "as Markdown, in which Product C's Basic cell stays empty and Pro is $25.")

fig = Figure("03-table-flattening", "A flat stream keeps the numbers and loses the cells", desc,
             subtitle="Illustrative prices, run through snippets/flatten_table.py.", data_w=True)

T_X, T_Y, ROW_H, COLS = 40, 136, 40, [112, 72, 72]
fig.text(T_X, T_Y - 16, "The source table", "head")
rows = [HEADER] + [[c for c in r] for r in ROWS]
table = fig.table(T_X, T_Y, rows, COLS, row_h=ROW_H, col_align=["start", "end", "end"])
empty = Box(T_X + COLS[0], T_Y + 3 * ROW_H, COLS[1], ROW_H)
fig.outline(empty.inset(4), "error", width=1.5, dash="proj")
fig.note(table, ["The Basic cell of Product C", "is empty in the source."])

R_X = 352
fig.text(R_X, T_Y - 16, "Flattened, then read back by position", "head")
fig.code_block(R_X, T_Y + 24, flat_lines)
fig.text(R_X, T_Y + 88, "Product C, Basic: $25, wrong", "label", color="error")

M_Y = 296
fig.text(R_X, M_Y - 16, "Emitted as Markdown", "head")
fig.code_block(R_X, M_Y + 24, md.splitlines())
fig.text(R_X, M_Y + 24 + 5 * 24 + 8, "Product C, Basic: empty; Pro: $25", "label")

fig.arrow((table.right + 8, T_Y + 24), (R_X - 12, T_Y + 24))
fig.arrow((table.right + 8, M_Y + 24), (R_X - 12, M_Y + 24))

fig.caption("The stream has no gap where the empty cell was, so $25 slides into the Basic column.")
fig.write()
