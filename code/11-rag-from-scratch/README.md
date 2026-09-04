# RAG from scratch (`ragkit`)

Companion code for **[Post 11 — RAG in depth](../../posts/11-rag-in-depth/index.md)**  (with roots in [Post 09 — Select strategies](../../posts/09-select-strategies/index.md) and upstream parsing in [Post 10 — Data ingestion](../../posts/10-data-ingestion-pipelines/index.md)).

A tiny, readable RAG pipeline in plain Python. It is deliberately split so that the interesting retrieval logic runs and tests **offline**, and only the last step — turning retrieved chunks into an answer — needs a provider key.

```
Offline core (no dependencies, unit-tested):
  ingest → chunk → BM25 index → hybrid + RRF fusion → bookend pack
Online adapter (needs a key, imported lazily):
  generate (grounded answer with citations)
```

## Quickstart

```bash
cd code/11-rag-from-scratch
python -m pip install -e ".[dev]"   # offline core + pytest
pytest -q                            # all tests pass with NO key and NO network
```

Use the offline core directly:

```python
from ragkit import read_corpus, chunk, BM25, rrf, bookend_pack

docs = read_corpus("my_notes/")
chunks = [c.text for d in docs for c in chunk(d.text, target_tokens=500, overlap_tokens=75)]

bm25 = BM25(chunks)
lexical = [i for i, _ in bm25.search("how does prompt caching work", top_k=50)]
# dense = ...  # a vector ranking over the same chunks (see the online extra)
fused = rrf([lexical])                # add the dense ranking as a second list
top = [chunks[i] for i, _ in fused[:5]]
packed = bookend_pack(top)
```

## Going online

```bash
python -m pip install -e ".[online]"
cp .env.example .env      # fill in ANTHROPIC_API_KEY (and OPENAI/VOYAGE/COHERE if used)
```

```python
from ragkit.generate import answer
print(answer("What does prompt caching cost?", [(src, text) for text in packed]))
```

## What's stubbed / deliberately small

- **Tokens are approximated by words** in `chunk` so the numbers are reproducible offline; a production pipeline counts real model tokens.
- **Dense embeddings and cross-encoder rerank are left as the online extra** — the offline core shows the lexical half and the fusion that combines the two.
- **Ingestion reads only `.md`/`.txt`.** Real-world parsing (PDF, HTML, tables, OCR) is the subject of Post 10.
