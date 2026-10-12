"""ragkit: a minimal, readable RAG pipeline in plain Python.

Companion code for Post 11 - RAG in depth.

The package is split into an OFFLINE core (pure functions, no network, no
optional dependencies) and an ONLINE adapter (guarded behind an env key):

    Offline core (import-safe, unit-tested):
        ingest   - read .md / .txt files off disk (with provenance)
        chunk    - sentence-aware chunking (500 words with a 75-word overlap by default)
        bm25     - pure-Python lexical index (Okapi BM25)
        fuse     - Reciprocal Rank Fusion (RRF) of ranked lists
        pack     - bookend context packing (lost-in-the-middle mitigation)

    Online adapter (needs an API key; imported lazily inside the function):
        generate - grounded answer with citations via the Anthropic SDK

Nothing in the offline core imports an SDK, so ``import ragkit`` never fails
because a provider package or key is missing.
"""
from __future__ import annotations

from .bm25 import BM25, tokenize
from .chunk import Chunk, chunk, split_sentences
from .fuse import rrf
from .ingest import Document, read_corpus, read_file
from .pack import bookend_pack

__all__ = [
    "BM25",
    "Chunk",
    "Document",
    "bookend_pack",
    "chunk",
    "read_corpus",
    "read_file",
    "rrf",
    "split_sentences",
    "tokenize",
]

__version__ = "0.1.0"
