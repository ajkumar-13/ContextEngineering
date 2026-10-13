"""Post 24, section 5: one erasure request fanned out to every store, against a deletion that stops at memory.

Run from anywhere:  python posts/24-privacy-and-governance/diagrams/src/03-erasure-fan-out.py
Writes posts/24-privacy-and-governance/diagrams/03-erasure-fan-out.svg.
Every count and chunk id is computed here by snippets/governed_stores.py (loaded with runpy), repeating the
steps of its main(): the memory write gate, the retention rule, then mentions() before, after a memory-only
deletion, and after erase(), and retrieve() for the query before and after. The counts are asserted against
the erasure table the body quotes.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
M = runpy.run_path(str(POST / "snippets" / "governed_stores.py"), run_name="snippet")
audit = []
memory = [r for r in M["CANDIDATES"] if M["check_memory_write"](r) is None]
chunks, manifest, index = M["build"](M["DOCS"])
traces = M["apply_retention"](M["TRACES"], audit)
WHO, Q = {"u-017", "Priya Raman", "priya.raman@example.com"}, "Priya Raman duplicate card charge refund"
before_pack = [c["id"] for c in M["retrieve"](chunks, index, Q, tenant_id="tenant-a")]
before = M["mentions"](WHO, memory, M["DOCS"], chunks, traces)
partial = M["mentions"](WHO, [r for r in memory if r["subject"] != "u-017"], M["DOCS"], chunks, traces)
memory, docs, chunks, traces = M["erase"]("u-017", memory, M["DOCS"], chunks, manifest, index, traces, audit)
after = M["mentions"](WHO, memory, docs, chunks, traces)
after_pack = [c["id"] for c in M["retrieve"](chunks, index, Q, tenant_id="tenant-a")]
for store in before:
    assert f"  {store:<12} {before[store]:>6} {partial[store]:>12} {after[store]:>8}" in BODY, store
assert f"    before: {', '.join(before_pack)}" in BODY and f"    after:  {', '.join(after_pack)}" in BODY
left = sum(partial.values())
assert left == 7 and not any(after.values()) and "A memory-only deletion leaves 7 copies." in BODY
gone = [c for c in before_pack if c not in after_pack]
assert gone == ["doc-a2-c1", "doc-a3-c1"]

FOUND = {"memory rows": "subject = u-017", "documents": "about u-017", "chunks": "listed in the manifest",
         "traces": "user = u-017"}
NAMES = {"memory rows": "Memory rows", "documents": "Source documents", "chunks": "Chunks and index",
         "traces": "Trace store"}

desc = ("One erasure request for u-017 (Priya Raman, tenant-a) fans out to five stores. Counts are before, after a "
        "deletion that stops at the memory store, and after the fan-out: "
        + "; ".join(f"{NAMES[s]}, found by {FOUND[s]}: {before[s]}, {partial[s]}, {after[s]}" for s in before)
        + f". The provider's copy is drawn dashed: its retention terms apply. A memory-only deletion leaves {left} "
        f"copies. The query \"{Q}\" retrieves {', '.join(before_pack)} before and {', '.join(after_pack)} after, so "
        f"{' and '.join(gone)} are gone from the index.")

fig = Figure("03-erasure-fan-out", "An erasure has to reach every copy", desc,
             subtitle="One request for u-017 in snippets/governed_stores.py; the provider's copy is outside the application.",
             height=720, data_w=True)

req = Box(40, 248, 168, 104)
fig.fill(req, "surface", radius=8, fit=False)
fig.outline(req, "ink", radius=8, width=2.5)
fig.text(56, 284, "Erasure request", "head")
fig.text(56, 308, "u-017", "code")
fig.text(56, 332, "Priya Raman", "note")

RX0, RX1, RH, RG, RY = 248, 920, 56, 12, 144
COL = {"before": 696, "memory only": 800, "fan-out": 904}     # right edges of the number columns
fig.text(RX0 + 16, RY - 16, "store", "note")
fig.text(RX0 + 216, RY - 16, "found by", "note")
for name, x in COL.items():
    fig.text(x, RY - 16, name, "note", anchor="end")
rows = list(before) + ["provider"]
for i, s in enumerate(rows):
    y = RY + i * (RH + RG)
    b = Box(RX0, y, RX1 - RX0, RH)
    prov = s == "provider"
    fig.fill(b, "surface", radius=8, fit=False)
    fig.outline(b, "rule" if prov else "border", radius=8, dash="proj" if prov else None)
    fig.text(RX0 + 16, y + 34, "Provider's copy" if prov else NAMES[s], "label")
    if prov:
        fig.text(RX0 + 216, y + 34, "its retention terms, section 4", "note")
    else:
        fig.text(RX0 + 216, y + 34, FOUND[s], "code" if "=" in FOUND[s] else "label")
        fig.text(COL["before"], y + 34, str(before[s]), "label", anchor="end")
        fig.text(COL["memory only"], y + 34, str(partial[s]), "value", anchor="end",
                 color="error-ink" if partial[s] else None)
        fig.text(COL["fan-out"], y + 34, str(after[s]), "value", anchor="end")
    fig.arrow(req.anchor("right", 0.5), (RX0 - 2, y + RH // 2), dash="proj" if prov else None)

ly = RY + len(rows) * (RH + RG) + 4
fig.text(COL["memory only"], ly + 16, f"{left} copies left", "label", anchor="end", color="error-ink")
fig.text(COL["fan-out"], ly + 16, "none", "label", anchor="end")

# the index, before and after
qb = Box(40, 552, 880, 96)
fig.fill(qb, "neutral-soft", radius=8, fit=False)
fig.outline(qb, "border", radius=8)
fig.text(56, 584, f"Query \u201c{Q}\u201d, tenant-a, top 3", "label")
fig.text(56, 616, "before", "note")
fig.text(56, 636, "after", "note")
x = 136
for cid in before_pack:
    fig.text(x, 616, cid, "code", color="error-ink" if cid in gone else None)
    x += 112
x = 136
for cid in after_pack:
    fig.text(x, 636, cid, "code")
    x += 112
fig.text(904, 616, "the person's ticket and call note", "note", anchor="end")
fig.text(904, 636, "general policy, another customer", "note", anchor="end")

fig.caption("A deletion that stops at memory leaves the person in the index and the traces.")
fig.write()
