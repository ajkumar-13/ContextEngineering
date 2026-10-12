"""Post 10, section 8: the second ingest run of snippets/reindex.py, one row per page, and what was done to it.

Run from anywhere:  python posts/10-data-ingestion-pipelines/diagrams/src/04-incremental-reindex.py
Writes posts/10-data-ingestion-pipelines/diagrams/04-incremental-reindex.svg.
The rows are computed here by running the snippet's two ingest runs (imported) and asserted against the run-2
output that section 8 quotes. The counts in the caption come from the same actions.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, rich, span  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
S = runpy.run_path(str(POST / "snippets" / "reindex.py"), run_name="snippet")
manifest = {}
S["ingest"](S["V1"], manifest)
run2 = S["ingest"](S["V2"], manifest)
for verb, what in run2:
    assert f"  {verb:<9} {what}\n" in BODY, (verb, what)

# (what, why, action) for each action of run 2, in the snippet's order
WHY = {"skip": "hash unchanged", "replace": "page hash changed", "embed": "not in the manifest",
       "delete": "source retired", "duplicate": "same hash as shipping.html"}
DOING = {"skip": "skip", "replace": "delete old chunk, embed new", "embed": "embed",
         "delete": "delete its chunk", "duplicate": "not indexed"}
rows = [["Page or document", "Hash against the manifest", "Action"]]
reds, plain = {}, []
for verb, what in run2:
    item = what.split(":")[0].split(" = ")[0].split(", ")[0]
    why = ("document " if verb == "skip" and " p" not in item else "page " if verb == "skip" else "") + WHY[verb]
    act = DOING[verb]
    plain.append(f"{item}, {why}, {act}")
    rows.append([item, why, rich(span(act, bold=True)) if verb in ("replace", "embed") else act])
    if verb == "delete":
        reds[len(rows) - 1] = "error"
assert [r[0] for r in rows[1:]] == ["refunds.pdf p1", "refunds.pdf p2", "refunds.pdf p3", "shipping.html",
                                    "shipping_copy.html", "warranty.md p1", "faq.md p1", "faq.md p2"]
pages_now = sum(len(d["pages"]) for d in manifest.values())
embedded = sum(1 for v, _ in run2 if v in ("embed", "replace"))
deleted = sum(1 for v, _ in run2 if v in ("delete", "replace"))
assert (pages_now, embedded, deleted) == (5, 2, 3)
assert "two were embedded (the edited page and the new document)" in BODY

desc = ("A table of the second ingest run of snippets/reindex.py, one row per page or document, with the hash "
        "check and the action: " + "; ".join(plain) +
        ". The two deleted faq.md rows are shaded red; the replace and embed actions are bold. Of the five pages "
        "in the corpus after the run, two were embedded.")

fig = Figure("04-incremental-reindex", "A one-page edit re-embeds one page", desc,
             subtitle="Run 2 of snippets/reindex.py: one page edited, one document retired, one document added.",
             data_w=True)
fig.table(40, 112, rows, [208, 304, 368], row_h=40, highlight_row=reds)
fig.caption(f"Of the {pages_now} pages now in the corpus, {embedded} were embedded; the rest were skipped.")
fig.write()
