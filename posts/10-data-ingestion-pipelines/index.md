# 10 - Data ingestion and document pipelines

> **TL;DR.** Retrieval can only find text that ingestion produced: a table cell the parser dropped, or two columns it scrambled, cannot be put back by any embedding model or reranker downstream. Of the six ingestion stages (source, parse, clean, enrich, chunk, index), the first four decide which text exists at all. This post covers them: choosing among born-digital extraction, optical character recognition (OCR) and a layout-aware parser, keeping tables, stripping boilerplate, attaching provenance, and re-indexing only what changed.
>
> **Prerequisites:** [Post 09](../09-select-strategies/index.md).
> **Safe to skip?** Skip it if every document type in the corpus already has a tested parser, tables survive parsing with their cells bound to their headers, every chunk carries its source, page and date, and a one-page edit re-indexes only that page.
>
> **After reading, you will be able to:**
>
> - Choose a parsing strategy for a source file (born-digital extraction, OCR or a layout-aware parser) and name what escalates from one to the next.
> - Preserve tables and reading order through parsing, and check a parsed table cell against the source.
> - Strip boilerplate before chunking: main-content extraction for web pages, and repeated headers, footers and navigation.
> - Attach provenance at ingest (source, page, section, timestamp, document type) and name what citations, conflict resolution and filtering need from it.
> - Re-index incrementally with content hashes, so that a changed page is re-embedded and its old chunk replaced while unchanged pages are skipped.

![Six stages joined left to right: source, parse, clean, enrich, chunk, index. Braces mark the first four as deciding which text exists and the last two as post 11's subject. A select arrow runs from the index to 04 Retrieved chunks; red notes mark a cell dropped at parse and provenance not written at enrich.](diagrams/01-ingestion-pipeline.svg)

*Every stage after parse works on what parse kept; the select step of each turn can only bring back what the index holds.*

---

## 1. The question: what decides which tokens can ever be retrieved?

Retrieval-augmented generation (RAG) puts the chunks a retrieval pipeline selects into layer 04, retrieved chunks, of the window ([post 02](../02-six-layers-of-context/index.md)). [Post 09](../09-select-strategies/index.md) tunes that select step and [post 11](../11-rag-in-depth/index.md) builds it, and both assume the corpus is already clean text: paragraphs in reading order, tables that are still tables, no navigation menus or page numbers mixed into the content. Real corpora arrive as Portable Document Format (PDF) files exported from design tools, scans of paper, HyperText Markup Language (HTML) pages thick with cookie banners, slide decks, and spreadsheets whose meaning lives in the grid.

Ingestion is invisible until answers go wrong. A demonstration built on three tidy Markdown files retrieves well, ships, and meets a real document store, where the embedded chunk is half a table caption glued to a footer line and the answer sits in a cell the parser dropped. Nothing in the retrieval stack is broken: the embedding model, the reranker and the vector database all work. The tokens that carried the answer never entered the index, and recall@N, the share of the relevant chunks that reach the top-N candidates ([post 09](../09-select-strategies/index.md)), cannot recover a fact destroyed at parse time.

Debugging attention flows to what is easy to instrument, such as retrieval scores, and away from parsing scripts nobody owns. The cheapest check comes first: **before tuning retrieval, read the text the parser actually produced.** The question of this post is what the parse, clean and enrich stages must do so that the right text exists, and how a corpus that changes daily is kept from going stale.

---

## 2. The six stages of an ingestion pipeline

Every ingestion pipeline, whatever its sources, has the same six stages, drawn as the hero figure at the top of the post.

- **Source**: fetch the raw bytes and record where they came from: a PDF from a document management system, an HTML page from a crawl, an export from a wiki.
- **Parse**: turn bytes into structured text, keeping reading order, headings and tables. Most of this post lives here: this stage makes or breaks everything after it.
- **Clean**: remove what is not content (boilerplate, repeated headers and footers, navigation, advertisements) and normalise whitespace and encoding.
- **Enrich**: attach metadata (source path or web address (URL), page, section heading, timestamp, document type) so that the text carries its provenance into the index (section 7).
- **Chunk**: split the cleaned, enriched text into the units retrieval returns.
- **Index**: embed each chunk and write it to the dense (vector) index and the sparse index, a BM25 index (BM25 is the classic lexical ranking function).

The last two stages are the subject of [post 11](../11-rag-in-depth/index.md): chunk size, overlap, splitter choice, contextual chunk headers and the sparse index are treated there and not repeated here. In the vocabulary of [post 07](../07-write-select-compress-isolate/index.md), the whole pipeline is a write operation, the offline write side of RAG that [post 08](../08-write-strategies/index.md) names: it moves information out of any window into a store, and every later select into layer 04 reads from that store.

Separate stages make a failure diagnosable on its own: if the extracted text is wrong, no chunking strategy can fix it, so the stages are inspected in order, source first.

---

## 3. Parsing PDFs: three strategies, three situations

A PDF is not one format but at least three, and each needs a different extractor. Using one code path for all of them is an easy mistake, because it silently works on the first kind.

**Born-digital text extraction.** A PDF exported from a word processor or a web page carries its text as character data with positions on the page. A library that reads this text layer directly, such as pdfminer.six, pdfplumber (built on pdfminer.six) or PyMuPDF, extracts it quickly and with no model (each project's documentation, consulted October 2026). It is close to free, so it is tried first. Its weakness is that it reads glyphs by position. On a two-column page, a reader that goes top to bottom and left to right crosses the gutter on every line, as `snippets/reading_order.py` shows on a toy page:

```text
by position: Refunds over 500 dollars Shipping is free on orders need a manager's approval above 50 dollars to the within two working days. mainland only.
by column:   Refunds over 500 dollars need a manager's approval within two working days. Shipping is free on orders above 50 dollars to the mainland only.
```

The first line is what reaches the index when the extractor does not reconstruct reading order: two policies braided together, each sentence in three pieces.

**Layout-aware parsing.** When reading order matters (multi-column papers, forms, invoices), a layout-aware parser detects regions first (title, paragraph, table, figure, caption) and emits the text in reading order with its structure kept, for example as Markdown. It is heavier, since many such parsers run a detection or vision model. Section 6 treats them as a class.

**OCR for scans.** A scanned document is an image of text with no text layer to read. Optical character recognition, recognising characters from pixels, is the only route. Tesseract (Smith, 2007), developed at Hewlett-Packard and open-sourced in 2005, is the long-standing open-source engine; cloud OCR services and vision-language models are the alternatives, at a higher cost per page. OCR brings its own class of error ("rn" read as "m", a dropped decimal point), so its character accuracy is measured on a sample of the corpus before the corpus is trusted.

![A decision walk for one PDF: try born-digital extraction; if the text layer is empty or the page an image, use OCR; else if reading order or tables are mangled, use a layout-aware parser; else index the born-digital text. Each strategy carries its risk.](diagrams/02-pdf-decision.svg)

*Start cheap and escalate on evidence: each strategy brings its own failure, so each output is still read before it is indexed.*

The decision procedure is simple enough to write into the pipeline, as the figure above walks it: **try born-digital extraction; if the text layer is empty or the page is an image, fall back to OCR; if reading order or tables come out mangled, escalate to a layout-aware parser.** A single corpus often needs all three, because it contains all three kinds of PDF.

---

## 4. Tables and structure: the hardest case

Tables are where naive extraction fails most destructively, and where the failure is easiest to miss, because the output still looks like text.

Consider a pricing table with illustrative prices. To a reader it is a grid: rows are products, columns are tiers, and a cell's meaning comes from its row and column headers. A text-layer reader that takes every non-empty cell left to right and top to bottom turns the grid into a stream. This excerpt of `snippets/flatten_table.py` does that:

```python
def flatten(header, rows):
    """What a reader of glyphs produces: every non-empty cell, left to right, top to bottom."""
    cells = header + [c for r in rows for c in r]
    return " ".join(c for c in cells if c)
```

Product C has no Basic tier, so the table has one empty cell. The snippet flattens the table, reads the stream back into a grid by position (the only cue the stream still carries), and asks two questions of the stream and of the same table as Markdown:

```text
flattened: Product Basic Pro Product A $10 $20 Product B $15 $30 Product C $25
  read back by position, Product A: {'Basic': '$10', 'Pro': '$20'}
  read back by position, Product B: {'Basic': '$15', 'Pro': '$30'}
  read back by position, Product C: {'Basic': '$25'}
as Markdown:
| Product | Basic | Pro |
|---|---|---|
| Product A | $10 | $20 |
| Product B | $15 | $30 |
| Product C |   | $25 |
  Product B, Pro: flat stream says $30, Markdown says $30
  Product C, Basic: flat stream says $25, Markdown says (empty)
```

![A pricing table with Product C's Basic cell empty, outlined in red; the same table flattened to one stream, read back so that Product C's Basic price is 25 dollars, marked wrong; and the table as Markdown, where that cell stays empty.](diagrams/03-table-flattening.svg)

*A flat stream keeps every number and loses the one thing that said where each belongs.*

The flat stream keeps every number and loses the grid. When every cell is full, binding `$30` to Product B and Pro takes counting positions, which a model reading a chunk does unreliably. When a cell is empty, as the figure above shows, position reads wrong: the stream has no gap where Product C's Basic price should be, so `$25` slides into the Basic column and a question about it gets a confident wrong answer. A chunk boundary inside the table makes it worse: the rows after it arrive without the header row.

The fix is to keep the grid. A table-aware parser emits the table as **Markdown or HTML**, with rows, columns and headers explicit in the token stream, and the empty cell stays empty, so a model reading the chunk can bind each price to its product and tier. HTML is the better target when cells span several rows or columns (invoices and financial statements are full of them), because HTML's `rowspan` and `colspan` have no Markdown equivalent.

Getting there requires a parser that detects table regions and reconstructs cell boundaries, the job of table-recognition models such as the Table Transformer, trained on the PubTables-1M dataset (Smock et al., 2022), and of the parsers of section 6. **When tables in the corpus carry answers, table fidelity is the first parsing capability to check**: read a parsed table and compare a cell with the source.

Spreadsheets are the neighbouring case: a sheet is serialised as a grid (one row per record, headers kept), not as a run of cell values, and its sheet and column names go into the metadata.

---

## 5. HTML and boilerplate

HTML is easy to extract and hard to extract well. Removing the tags is trivial; the problem is that much of a web page is not content. Navigation bars, footers, cookie banners, related-article rails and share buttons can outweigh the article itself, and every one of their tokens, once embedded, is a chance for retrieval to match on furniture instead of substance.

The task is **main-content extraction**: isolate the article and discard the rest. Mature open-source tools exist. Mozilla's Readability is the library behind Firefox Reader View, and Trafilatura (Barbaresi, 2021) is built for extraction at corpus scale; both use heuristics over the page's structure, such as text length and link density, to find the main content. Trafilatura's paper reports that it performed significantly better than other open-source tools in its evaluation and in external benchmarks.

Two boilerplate patterns survive naive cleaning and deserve their own pass:

- **Repeated headers and footers.** In a PDF, the running header and the page footer repeat on every page. Concatenate the pages and every chunk near a page boundary carries `Confidential, page 2 of 3`. The fix is to find lines that recur across many pages, with their page numbers masked, and drop them.
- **Navigation duplicated across a crawl.** Every page of a documentation site shares the same sidebar. Embedded once per page, it fills the index with near-identical navigation chunks that match any query naming a section. Near-identical blocks are deduplicated across documents at clean time.

The first pass fits in a few lines. This excerpt of `snippets/strip_furniture.py` masks the digits of each line and drops every line whose shape appears on at least 60 percent of the pages (an illustrative threshold):

```python
def shape(line):
    """A line with its digits masked, so 'page 1 of 3' and 'page 2 of 3' count as one line."""
    return re.sub(r"\d+", "#", line.strip().lower())


def strip_furniture(pages, min_share=0.6):
    """Drop every line whose shape appears on at least min_share of the pages."""
    seen = Counter(s for page in pages for s in {shape(ln) for ln in page})
    furniture = {s for s, n in seen.items() if n / len(pages) >= min_share}
    kept = [[ln for ln in page if shape(ln) not in furniture] for page in pages]
    return kept, sorted(furniture)
```

On its three-page toy policy document it prints:

```text
repeated lines dropped: ['acme ltd refund policy', 'confidential, page # of #']
words before 60, after 33: 27 words (45%) were page furniture
  page 1: Refunds are paid to the original card. A refund over 500 dollars needs a manager's approval.
  page 2: Approval is given within two working days. Refused refunds can be appealed once.
  page 3: Store credit never expires.
```

The 45 percent belongs to a toy document with short pages; on long pages the share is smaller, but the furniture still lands in every chunk near a page boundary. The test is to read a sample of cleaned documents: a cookie banner or a `page 14 of 210` in text bound for the index means the cleaner is not done.

---

## 6. Layout-aware parsers as a class

Born-digital extraction, OCR fallback, table reconstruction, reading-order recovery and boilerplate removal are a lot to assemble from separate libraries. A class of document parsers packages most of it behind one call. Three examples, named as a category and not as a recommendation, as their documentation described them when consulted in October 2026:

- **Docling**, started by IBM Research Zurich and released under the MIT licence, parses PDF, Word, PowerPoint, Excel, HTML and image files, among others, with page layout, reading order, table structure and OCR for scans, and exports Markdown, HTML or JavaScript Object Notation (JSON).
- **Unstructured** is an open-source library that partitions documents into typed elements (titles, narrative text, tables) in its own JSON schema; its documentation says that the open-source version is a starting point for prototyping and that its hosted service has stronger OCR and table extraction.
- **LlamaParse**, from LlamaIndex, is a parsing service called through an application programming interface or software development kits, which returns Markdown, text or JSON.

Their formats, limits and prices change quickly, so the documentation is read again on the day a choice is made.

Adopting one is a build-or-buy decision:

- **Adopt a document parser** when the corpus is mixed (PDFs, scans, decks, tables) and the alternative is a set of format-specific scripts to maintain: the parser absorbs the long tail of format quirks.
- **Assemble from libraries** when the corpus is narrow and stable, for example one supplier's born-digital PDFs, where a text-layer library plus a table pass does the whole job at a fraction of the cost.

Either way, a parser still errs on hard tables and unusual layouts, so the discipline does not change: sample the output, check tables against the source, and measure extraction quality on a held-out set of documents. The tool changes how much is built, not whether the output is checked.

---

## 7. Metadata and provenance at ingest

Provenance is captured at ingest or it is lost. Once a document has been parsed, cleaned, chunked and embedded, nothing can recover which page a chunk came from unless that fact was attached on the way through. So the enrich stage writes onto every chunk at least its **source** (path or URL), **page** (or slide, or sheet), **section** (the nearest heading), **timestamp** (when the source last changed) and **document type**, and a corpus in several languages adds the **language**. It costs almost nothing at ingest and cannot be backfilled afterwards.

The manifest row that `snippets/reindex.py` (section 8) keeps for one page shows the shape, here for page 2 of a toy refunds policy after an edit:

```text
manifest row for refunds.pdf p2:
  source=refunds.pdf, page=2, section=Approval, type=pdf, modified=2026-10-12, hash=1c9875b4b381, chunk=refunds.pdf#p2@1c9875
```

Provenance pays off in three places downstream:

- **Citations.** [Post 11](../11-rag-in-depth/index.md) has the model cite the header of each packed chunk, a source the user can check. That header is built from the provenance captured here.
- **Conflict.** When two chunks disagree, such as an old policy and its replacement, the timestamp and the source let the window say which one wins. Conflict is one of the five failure modes of [post 06](../06-context-failure-modes/index.md), and its first fix is exactly this: a provenance and recency stamp on every retrieved chunk, with a precedence rule in the system prompt ("when sources disagree, the most recent one wins").
- **Filtered retrieval.** Metadata filtering, one of the ways [post 09](../09-select-strategies/index.md) narrows the candidate set, scopes a query to one document, date range, document type or language, but only if those fields rode along from ingest.

A **manifest** turns provenance into a record of the index: one row per source document (per page in the snippet) with its content hash and chunk ids; a production row adds the parser and embedding-model versions and the ingest time. [Post 11](../11-rag-in-depth/index.md) keeps the same table from the indexing side; it is the record that answers "what changed in the index, and what parsed it".

---

## 8. Incremental re-indexing and change detection

A corpus is a stream: documents are added, revised and retired, and an index that was right at launch drifts out of date. Re-embedding everything on every change is affordable for a small corpus and wasteful for a large one, so production pipelines re-index incrementally.

The mechanism is **content hashing**. For each source document, the manifest stores a hash of its extracted text (or of its bytes); for each page, a hash of that page's text. On every ingest run, four cases fall out:

- **Unchanged** (the document hash matches): skip it without embedding again. On a corpus that changes a little each day, most documents fall here, which is why incremental indexing is cheap.
- **Changed** (the document hash differs): compare the page hashes, re-parse, re-chunk and re-embed only the changed pages, and *replace* their old chunks. Replacement is the step teams forget: if the old chunks stay, the agent can retrieve and cite a superseded policy, one of the ways [post 11](../11-rag-in-depth/index.md) lists for production RAG to go wrong.
- **Deleted** (in the manifest, absent from the source): remove its chunks from both indexes.
- **New** (in the source, absent from the manifest): parse and index it.

Hashing the extracted text rather than the bytes avoids a re-index when only a file's metadata changed, such as a PDF re-exported with a new creation date. Content hashing also gives exact deduplication for free: two documents with the same hash are the same text and are indexed once. Near-duplicates, such as the shared sidebars of section 5, have different hashes and need the clean-time deduplication described there.

`snippets/reindex.py` runs a toy corpus through two ingest runs. The second run follows a day in which page 2 of `refunds.pdf` was edited, `faq.md` was retired and `warranty.md` was added; `shipping_copy.html` has the same text as `shipping.html`:

```text
run 2, the next day:
  skip      refunds.pdf p1, page hash unchanged
  replace   refunds.pdf p2: delete refunds.pdf#p2@d8f24b, embed refunds.pdf#p2@1c9875
  skip      refunds.pdf p3, page hash unchanged
  skip      shipping.html, document hash unchanged
  duplicate shipping_copy.html = shipping.html, not indexed
  embed     warranty.md p1: warranty.md#p1@6dc176
  delete    faq.md p1: faq.md#p1@6446d9
  delete    faq.md p2: faq.md#p2@f8f96d
  pages embedded: 1, replaced: 1, deleted: 2, skipped: 3
```

![A table of the second run of snippets/reindex.py: two refunds.pdf pages and shipping.html skipped, refunds.pdf page 2 replaced, shipping_copy.html not indexed as a duplicate, warranty.md embedded, and both faq.md pages deleted, shaded red.](diagrams/04-incremental-reindex.svg)

*The manifest turns a day of edits into a short list of work: two pages embedded, three old chunks deleted, the rest untouched.*

Of the five pages in the corpus after the second run, two were embedded (the edited page and the new document), and the edited page's old chunk was deleted in the same step, as the figure above lays out. The scheme rests on the manifest of section 7: the metadata captured at ingest is what keeps the index honest over time.

---

## 9. Make it run: the four snippets

The four snippets use the standard library only, make no network call, and run from the series root in well under a second each:

```text
uv run python posts/10-data-ingestion-pipelines/snippets/reading_order.py
uv run python posts/10-data-ingestion-pipelines/snippets/flatten_table.py
uv run python posts/10-data-ingestion-pipelines/snippets/strip_furniture.py
uv run python posts/10-data-ingestion-pipelines/snippets/reindex.py
```

They print the outputs quoted in sections 3, 4, 5, 7 and 8. Every input is a toy written into the file; a real pipeline replaces it with a parser's output and keeps the checks.

---

## 10. What can go wrong?

- **One code path for every PDF.** The pipeline was built on born-digital reports and later receives scans. The scanned documents index as empty or near-empty chunks, nothing errors, and questions about them come back with "not found in the sources".
- **A table read as a stream.** A pricing sheet is extracted by a text-layer reader. Retrieval finds the right chunk, the answer quotes a real number from it, and the number belongs to the next column, because an empty cell shifted every value after it.
- **Footers in every chunk.** Running headers and page footers are left in. Queries that mention the company name or the word "confidential" retrieve chunks that matched on the furniture, and precision@k, the share of the packed chunks that are relevant, falls.
- **Re-embedding without replacing.** A changed page is re-indexed but its old chunk is never deleted. Both versions are retrieved, and the answer wavers between the old rule and the new one: conflict, created by the pipeline.
- **Hashing the bytes of a regenerated file.** A nightly export rewrites every PDF with a new timestamp. Every byte hash changes, the whole corpus re-embeds every night, and the cost of indexing looks like a full rebuild.

---

## Common pitfalls

1. **Tuning retrieval before reading the parser's output.** Opening the extracted text of a few documents is the fastest ingestion check there is; many parsing failures are visible on the first page.
2. **Discarding provenance at ingest.** Source, page, section and timestamp cannot be backfilled after chunking; without them there are no citations and no way to resolve conflict.
3. **Treating a document parser as infallible.** Adopted or assembled, the parser still errs on hard tables and odd layouts; verify on a held-out sample either way.
4. **Re-indexing everything on every change, or never.** Full rebuilds waste work at scale, and never re-indexing leaves stale chunks the agent will cite; hash-based incremental re-indexing with replacement sits between them.
5. **Embedding web pages whole.** Without main-content extraction, navigation and banners are indexed beside the article and compete with it for every query.

---

## Further reading

- Smith, R., *["An Overview of the Tesseract OCR Engine"](https://doi.org/10.1109/ICDAR.2007.4376991)* (ICDAR 2007): the open-source OCR engine of section 3.
- [pdfminer.six](https://github.com/pdfminer/pdfminer.six), [pdfplumber](https://github.com/jsvine/pdfplumber) and [PyMuPDF](https://pymupdf.readthedocs.io/) documentation (consulted October 2026): text-layer extraction for born-digital PDFs.
- Smock, B., Pesala, R. and Abraham, R., *["PubTables-1M: Towards Comprehensive Table Extraction from Unstructured Documents"](https://arxiv.org/abs/2110.00061)* (CVPR 2022): the dataset and the Table Transformer models behind table-region detection in section 4.
- Barbaresi, A., *["Trafilatura: A Web Scraping Library and Command-Line Tool for Text Discovery and Extraction"](https://trafilatura.readthedocs.io/)* (ACL 2021, system demonstrations): main-content extraction from HTML, section 5.
- Mozilla, *["Readability"](https://github.com/mozilla/readability)* (GitHub): the library behind Firefox Reader View, section 5.
- [Docling](https://github.com/docling-project/docling), [Unstructured](https://unstructured.io/) and [LlamaParse](https://developers.llamaindex.ai/python/cloud/llamaparse/) documentation (consulted October 2026): the layout-aware parsers of section 6, cited as a class.

---

## What to read next

- **[Post 11 - RAG in depth](../11-rag-in-depth/index.md):** takes the clean, dated text this post produces and turns chunking, embedding and indexing into a production pipeline.
- **[Post 19 - Multimodal context: images, PDF pages, and audio](../19-multimodal-context/index.md):** the other way to send a PDF page, as an image rather than as extracted text, and when it wins.
