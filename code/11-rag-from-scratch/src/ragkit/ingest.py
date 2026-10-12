"""Read a corpus off disk, keeping provenance.

Real corpora are rarely clean plain text; Post 10 (Data ingestion and document
pipelines) is the upstream half of this story (parsing PDFs, HTML, tables, OCR).
This module deliberately reads only .md/.txt so the RAG core stays the focus; each
document keeps its source path so retrieved chunks can be cited.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Document:
    source: str  # provenance: where this text came from
    text: str


def read_file(path: str | Path) -> Document:
    p = Path(path)
    return Document(source=str(p), text=p.read_text(encoding="utf-8"))


def read_corpus(root: str | Path, patterns: tuple[str, ...] = ("*.md", "*.txt")) -> list[Document]:
    root = Path(root)
    files: list[Path] = []
    for pat in patterns:
        files.extend(sorted(root.rglob(pat)))
    return [read_file(f) for f in files]
