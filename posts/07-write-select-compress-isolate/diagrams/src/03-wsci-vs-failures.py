"""Post 07, section 8: the five failure modes of post 06 against the four operations, each cell naming the fix.

Run from anywhere:  python posts/07-write-select-compress-isolate/diagrams/src/03-wsci-vs-failures.py
Writes posts/07-write-select-compress-isolate/diagrams/03-wsci-vs-failures.svg.
No numbers are drawn. The modes, their fixes and the operations of each mode are post 06's table "Fixes map to
WSCI" (post 06, section 7), read from post 06's index.md and asserted below; the note that bookend packing is the
packing step of select is the sentence under that table. Which fix of a row sits under which of its operations is
this post's reading (section 8 of index.md); the set of operations per row is post 06's, unchanged.
Failure modes are not layers, so no layer hue is used; the operations are neutral.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POSTS = Path(__file__).resolve().parents[3]
BODY = (POSTS / "07-write-select-compress-isolate" / "index.md").read_text(encoding="utf-8")
P06 = (POSTS / "06-context-failure-modes" / "index.md").read_text(encoding="utf-8")

OPS = ["write", "select", "compress", "isolate"]
# mode: post 06's table row, post 06's operations, {op: fix as drawn (two lines)}, dashed {op: fix}
MODES = [
    ("Distraction", "| Distraction | Select | Lower top-k, add a reranker, scope the index. |", "Select",
     {"select": ("lower top-k,", "add a reranker")}, {}),
    ("Confusion", "| Confusion | Select (of rules) | Explicit, motivated, exemplified rules; push them into code. |",
     "Select (of rules)", {"select": ("explicit, motivated,", "exemplified rules")}, {}),
    ("Conflict", "| Conflict | Select, compress | Provenance and recency stamp with a precedence rule; "
     "deduplicate the candidates. |", "Select, compress",
     {"select": ("provenance stamp,", "precedence rule"), "compress": ("deduplicate the", "candidates")}, {}),
    ("Lost-in-the-middle", "| Lost-in-the-middle | Compress, isolate | Bookend packing; summarise old history; "
     "split across sub-agents. |", "Compress, isolate",
     {"compress": ("summarise", "old history"), "isolate": ("split across", "sub-agents")},
     {"select": ("bookend packing", "(the pack step)")}),
    ("Tool-storm", "| Tool-storm | Select, isolate | Trim the catalogue, add a stop budget, cap the result size. |",
     "Select, isolate", {"select": ("trim the", "catalogue"), "isolate": ("cap the", "result size")}, {}),
]
for mode, row, ops, fixes, dashed in MODES:
    assert row in P06, row
    assert sorted(o.split(" ")[0].lower() for o in ops.split(", ")) == sorted(fixes), mode
for phrase in ("Bookend packing is itself the packing step of select",
               "compress and isolate are what remain when packing no longer rescues the middle"):
    assert phrase in P06, phrase
for phrase in ("Select appears in four of the five rows", "And write appears in no row",
               "Lost-in-the-middle touches select as well, because bookend packing is the packing step of select"):
    assert phrase in BODY, phrase
assert sum("select" in f for _, _, _, f, _ in MODES) == 4
assert not any("write" in f or "write" in d for _, _, _, f, d in MODES)

desc = ("A grid with one row per failure mode of post 06 and one column per operation: write, select, compress, "
        "isolate. Each filled cell names the fix that performs that operation. ")
for mode, _, _, fixes, dashed in MODES:
    parts = [f"{op}, {' '.join(fixes[op])}" for op in OPS if op in fixes]
    parts += [f"{op}, dashed, {' '.join(dashed[op])}" for op in OPS if op in dashed]
    desc += f"{mode}: {'; '.join(parts)}. "
desc += ("The write column is empty: what is written acts later, when it is selected. A dashed cell touches "
         "select through bookend packing, the pack step of select.")

fig = Figure("03-wsci-vs-failures", "Every fix is a select, a compress or an isolate", desc,
             subtitle="Post 06's five modes, with one of post 06's fixes under each operation it names.",
             height=720, data_w=True)

MODE_X = 40
COL_X, COL_W = 232, 172
HEAD_Y, ROW_Y, ROW_H = 120, 152, 88
col_x = {op: COL_X + i * COL_W for i, op in enumerate(OPS)}

fig.text(MODE_X, HEAD_Y + 12, "Failure mode", "head")
for op in OPS:
    fig.text(col_x[op] + COL_W / 2, HEAD_Y + 12, op.capitalize(), "head", anchor="middle")

for r, (mode, _, _, fixes, dashed) in enumerate(MODES):
    top = ROW_Y + r * ROW_H
    fig.text(MODE_X, top + 48, mode, "head")
    for cells, dash in ((fixes, None), (dashed, "lead")):
        for op, (a, b) in cells.items():
            cell = Box(col_x[op] + 4, top + 8, COL_W - 8, ROW_H - 16)
            fig.fill(cell, "neutral-soft", radius=6, fit=False)
            fig.outline(cell, "ink-muted" if dash is None else "rule", width=1, radius=6, dash=dash)
            fig.text(cell.cx, top + 40, a, "label", anchor="middle")
            fig.text(cell.cx, top + 60, b, "label", anchor="middle")

# the empty write column, said in words
wx = col_x["write"] + COL_W / 2
mid = ROW_Y + 2 * ROW_H
fig.text(wx, mid + 40, "in no row:", "note", anchor="middle")
fig.text(wx, mid + 60, "acts later, via select", "note", anchor="middle")

ky = ROW_Y + 5 * ROW_H + 40
sw = Box(MODE_X, ky - 16, 48, 24)
fig.fill(sw, "neutral-soft", radius=6, fit=False)
fig.outline(sw, "rule", radius=6, dash="lead")
fig.text(MODE_X + 64, ky, "dashed: bookend packing, the first fix, is the pack step of select (post 06)", "note")

fig.caption("Select is in every row, four as post 06 states them: a tighter select is the first lever to check.")
fig.write()
