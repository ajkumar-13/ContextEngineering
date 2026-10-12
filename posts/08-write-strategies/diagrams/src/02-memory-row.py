"""Post 08, section 2: the three kinds of memory, and one row of the store with its nine fields.

Run from anywhere:  python posts/08-write-strategies/diagrams/src/02-memory-row.py
Writes posts/08-write-strategies/diagrams/02-memory-row.svg.
The row is the one snippets/memory_store.py builds and prints (imported and run here, its printed JSON parsed
and asserted against the drawn values); the field names are the dataclass's, asserted against the table of
section 2; the three kinds and their examples are section 2's (asserted). No measured numbers are drawn.
"""
import contextlib
import io
import json
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
out = io.StringIO()
with contextlib.redirect_stdout(out):
    runpy.run_path(str(POST / "snippets" / "memory_store.py"), run_name="__main__")
printed = out.getvalue()
assert printed.startswith("9 fields\n")
ROW = json.loads(printed[printed.index("{"):printed.index("}") + 1])
FIELDS = list(ROW)
assert len(FIELDS) == 9
for f in FIELDS:
    assert f"| `{f}` |" in BODY, f

def show(v):
    return "null" if v is None else str(v)

for phrase in ("**Episodic**: events with a timestamp. *\"User X resolved ticket 4321 on 14 March",
               "**Semantic**: facts and preferences. *\"User X prefers replies in formal English",
               "**Procedural**: rules and how-tos. *\"Export this client's reports as CSV first; their system rejects a PDF on its own.\"*"):
    assert phrase in BODY, phrase

KINDS = [("Episodic", "events with a timestamp", "resolved ticket 4321 on 14 March"),
         ("Semantic", "facts and preferences", "prefers replies in formal English"),
         ("Procedural", "rules and how-tos", "this client: CSV before PDF")]
GROUPS = [("identity", "id", "subject"), ("content", "content", "content"),
          ("provenance", "source", "created_at"), ("upkeep", "last_accessed_at", "expires_at")]
assert ROW["kind"] == "semantic"

desc = "Left: the three kinds of memory with an example each. "
desc += " ".join(f"{k}, {what}: {ex}." for k, what, ex in KINDS)
desc += " The semantic card is outlined, because the row on the right is semantic. Right: one row as the snippet prints it, "
desc += "; ".join(f"{f} {show(v)}" for f, v in ROW.items())
desc += ". Brackets group the fields as identity (id, kind, subject), content, provenance (source, created_at) and "
desc += "upkeep (last_accessed_at, confidence, expires_at)."

fig = Figure("02-memory-row", "A memory row carries nine fields, not just a fact", desc,
             subtitle="Three kinds of memory, and one semantic row as snippets/memory_store.py prints it.",
             data_w=True)

# the three kinds
fig.text(40, 128, "Three kinds", "head")
CX, CW, CH, CG = 40, 296, 96, 16
for i, (name, what, ex) in enumerate(KINDS):
    top = 144 + i * (CH + CG)
    b = Box(CX, top, CW, CH)
    fig.fill(b, "neutral-soft", radius=8, fit=False)
    if name == "Semantic":
        fig.outline(b, "turn", radius=8, width=2.5)
    else:
        fig.outline(b, "border", radius=8)
    fig.text(CX + 16, top + 32, name, "head")
    fig.text(CX + 16, top + 56, what, "note")
    fig.text(CX + 16, top + 80, ex, "label")

# one row, nine fields
TX, TY, RH = 472, 144, 32
fig.text(TX, 128, "One row in the memory store", "head")
rows = [["field", "value"]] + [[f, show(v)] for f, v in ROW.items()]
fig.table(TX, TY, rows, [152, 296], row_h=RH, style="code")
for label, first, last in GROUPS:
    a = TY + (FIELDS.index(first) + 1) * RH + 4
    b = TY + (FIELDS.index(last) + 2) * RH - 4
    fig.brace(a, b, TX - 12, label=label, side="left", kind="bracket", vertical=True)

fig.caption("Provenance and upkeep take five of the nine fields; the fact itself is one.")
fig.write()
