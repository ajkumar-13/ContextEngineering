"""Post 10, sections 7 and 8: a manifest with provenance, and incremental re-indexing by content hash.

Run from the series root:  uv run python posts/10-data-ingestion-pipelines/snippets/reindex.py
Standard library only. Embedding is not run: an "embed" line stands for parse, chunk, embed and write.
The corpus is a toy; each page is already extracted text, and each page is one chunk.
"""
import hashlib

V1 = {
    "refunds.pdf": {"type": "pdf", "modified": "2026-09-01",
                    "pages": [("Refunds", "Refunds are paid to the original card."),
                              ("Approval", "A refund over 500 dollars needs a manager's approval."),
                              ("Appeals", "Refused refunds can be appealed once.")]},
    "shipping.html": {"type": "html", "modified": "2026-08-15",
                      "pages": [("Shipping", "Shipping is free on orders above 50 dollars.")]},
    "shipping_copy.html": {"type": "html", "modified": "2026-08-20",
                           "pages": [("Shipping", "Shipping is free on orders above 50 dollars.")]},
    "faq.md": {"type": "markdown", "modified": "2026-07-30",
               "pages": [("FAQ", "Orders ship within a day."), ("FAQ", "Gift cards cannot be refunded.")]},
}
# The next day: one page of refunds.pdf is edited, faq.md is retired, warranty.md is new.
V2 = {k: v for k, v in V1.items() if k != "faq.md"}
V2["refunds.pdf"] = dict(V1["refunds.pdf"], modified="2026-10-12",
                         pages=[V1["refunds.pdf"]["pages"][0],
                                ("Approval", "A refund over 200 dollars needs a manager's approval."),
                                V1["refunds.pdf"]["pages"][2]])
V2["warranty.md"] = {"type": "markdown", "modified": "2026-10-12",
                     "pages": [("Warranty", "Every product carries a two-year warranty.")]}


def h(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def ingest(corpus, manifest):
    """Bring the manifest (and so the index) up to date with the corpus; return the actions taken."""
    actions, by_doc_hash = [], {}
    for source in sorted(corpus):
        doc = corpus[source]
        doc_hash = h("\n".join(text for _, text in doc["pages"]))
        if doc_hash in by_doc_hash:                         # exact duplicate of a document already seen
            actions.append(("duplicate", f"{source} = {by_doc_hash[doc_hash]}, not indexed"))
            continue
        by_doc_hash[doc_hash] = source
        old = manifest.get(source)
        if old and old["doc_hash"] == doc_hash:             # unchanged document: nothing to embed again
            actions.append(("skip", f"{source}, document hash unchanged"))
            continue
        rows = {}
        for page, (section, text) in enumerate(doc["pages"], 1):
            page_hash = h(text)
            prev = old["pages"].get(page) if old else None
            if prev and prev["hash"] == page_hash:
                rows[page] = prev
                actions.append(("skip", f"{source} p{page}, page hash unchanged"))
                continue
            row = {"chunk": f"{source}#p{page}@{page_hash[:6]}", "hash": page_hash, "page": page,
                   "section": section, "source": source, "type": doc["type"], "modified": doc["modified"]}
            if prev:
                actions.append(("replace", f"{source} p{page}: delete {prev['chunk']}, embed {row['chunk']}"))
            else:
                actions.append(("embed", f"{source} p{page}: {row['chunk']}"))
            rows[page] = row
        if old:                                             # pages that no longer exist
            for page in sorted(set(old["pages"]) - set(rows)):
                actions.append(("delete", f"{source} p{page}: {old['pages'][page]['chunk']}"))
        manifest[source] = {"doc_hash": doc_hash, "pages": rows}
    for source in sorted(set(manifest) - set(corpus)):     # documents retired from the source
        for page, row in sorted(manifest[source]["pages"].items()):
            actions.append(("delete", f"{source} p{page}: {row['chunk']}"))
        del manifest[source]
    return actions


def report(title, actions):
    print(title)
    for verb, what in actions:
        print(f"  {verb:<9} {what}")
    counts = {v: sum(1 for a, _ in actions if a == v) for v in ("embed", "replace", "delete", "skip")}
    print("  pages embedded: {}, replaced: {}, deleted: {}, skipped: {}".format(
        counts["embed"], counts["replace"], counts["delete"], counts["skip"]))


if __name__ == "__main__":
    manifest = {}
    report("run 1, empty manifest:", ingest(V1, manifest))
    report("run 2, the next day:", ingest(V2, manifest))
    row = manifest["refunds.pdf"]["pages"][2]
    print("manifest row for refunds.pdf p2:")
    print("  " + ", ".join(f"{k}={row[k]}" for k in ("source", "page", "section", "type", "modified", "hash", "chunk")))
