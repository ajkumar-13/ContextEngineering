"""Post 24, section 6: tenant B's first query ranked over the whole shared store, and filtered to tenant B first.

Run from anywhere:  python posts/24-privacy-and-governance/diagrams/src/04-filter-then-rank.py
Writes posts/24-privacy-and-governance/diagrams/04-filter-then-rank.svg.
Every chunk id, tenant, score and pack is computed here by snippets/governed_stores.py (loaded with runpy):
build() over its documents, words() for the overlap score, retrieve_unscoped() and retrieve(tenant_id="tenant-b")
for the two packs. The unscoped pack is asserted against the leak-test line the body quotes.
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
chunks, manifest, index = M["build"](M["DOCS"])
q = M["B_QUERIES"][0]
score = {c["id"]: len(M["words"](q) & M["words"](c["text"])) for c in chunks}
unscoped = [c["id"] for c in M["retrieve_unscoped"](chunks, index, q)]
scoped = [c["id"] for c in M["retrieve"](chunks, index, q, tenant_id="tenant-b")]
tenant = {c["id"]: c["tenant"] for c in chunks}
assert f"first query, unscoped, rank 1: {unscoped[0]} ({tenant[unscoped[0]]})" in BODY
assert all(tenant[c] == "tenant-a" for c in unscoped) and all(tenant[c] == "tenant-b" for c in scoped)
assert "  rank, no tenant filter:  5 of 5 packs hold tenant-a chunks" in BODY
assert "  filter, then rank:       0 of 5 packs hold tenant-a chunks" in BODY
rows = sorted((c for c in chunks if score[c["id"]] > 0), key=lambda c: (-score[c["id"]], c["id"]))
naming = [c for c in unscoped if "Priya Raman" in next(x["text"] for x in chunks if x["id"] == c)]
assert len(naming) == 2

desc = (f"Tenant B asks \"{q}\". Word-overlap scores of every chunk that shares a word with it: "
        + "; ".join(f"{c['id']} ({c['tenant']}) {score[c['id']]}" for c in rows) + ". "
        f"Left, ranked over the whole store: the top 3, {', '.join(unscoped)}, are all tenant A's, two of them naming "
        f"Priya Raman. Right, filtered to tenant B first: tenant A's chunks are not candidates and the pack is "
        f"{' and '.join(scoped)}, tenant B's returns policy and a tenant B ticket.")

fig = Figure("04-filter-then-rank", "Ranking cannot keep tenants apart; a filter can", desc,
             subtitle="Tenant B's first query in snippets/governed_stores.py; score is the number of shared words.",
             height=720, data_w=True)

qb = Box(40, 104, 880, 48)
fig.fill(qb, "user-soft", radius=8, fit=False)
fig.outline(qb, "user-line", radius=8)
fig.text(56, 134, "tenant-b asks", "note")
fig.text(176, 134, f"\u201c{q}\u201d", "label")

left, right = fig.row(2, y=208, h=416)
RH = 48
for panel, head, packed, fill in ((left, "Rank the whole store", unscoped, "error-soft"),
                                  (right, "Filter to tenant-b, then rank", scoped, "turn-soft")):
    fig.text(panel.x, panel.y - 16, head, "head")
    fig.text(panel.x + 16, panel.y + 24, "chunk", "note")
    fig.text(panel.x + 136, panel.y + 24, "tenant", "note")
    fig.text(panel.x + 264, panel.y + 24, "score", "note", anchor="end")
    for i, c in enumerate(rows):
        cid = c["id"]
        y = panel.y + 40 + i * RH
        rb = Box(panel.x, y, panel.w, RH - 4)
        out = panel is right and c["tenant"] != "tenant-b"
        if cid in packed:
            fig.fill(rb, fill, radius=4, fit=False)
        fig.text(panel.x + 16, y + 28, cid, "code", color="ink-muted" if out else None)
        fig.text(panel.x + 136, y + 28, c["tenant"], "label" if not out else "note")
        fig.text(panel.x + 264, y + 28, str(score[cid]), "label" if not out else "note", anchor="end")
        if cid in packed:
            fig.text(panel.right - 16, y + 28, f"packed {packed.index(cid) + 1}", "label", anchor="end",
                     color="error-ink" if panel is left else "turn-ink")
        elif out:
            fig.text(panel.right - 16, y + 28, "not a candidate", "note", anchor="end")
    yb = panel.y + 40 + len(rows) * RH + 28
    if panel is left:
        fig.text(panel.x, yb, "3 of 3 packed chunks are tenant A's", "label", color="error-ink")
    else:
        fig.text(panel.x, yb, f"{len(scoped)} packed: every tenant B chunk that scores", "label")
    fig.outline(Box(panel.x, panel.y, panel.w, len(rows) * RH + 40), "border", radius=8)

fig.caption("The filter decides what is a candidate before similarity gets a vote.")
fig.write()
