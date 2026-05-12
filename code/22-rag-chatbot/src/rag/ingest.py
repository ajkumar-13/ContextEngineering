"""Ingest: chunk -> contextual header -> embed -> index in Chroma.

Idempotent on (file, chunk-index, chunk-text). Re-ingesting unchanged files
is a no-op.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

import chromadb
import voyageai

from .llm import small_llm

CHUNK_TARGET = 500
CHUNK_OVERLAP = 80

_client = chromadb.PersistentClient(path=os.environ.get("RAG_CHROMA_PATH", ".chroma"))
COLL = _client.get_or_create_collection("docs")
_vo = voyageai.Client()

CHUNK_HEADER_PROMPT = (Path(__file__).resolve().parents[2] / "prompts" / "chunk_header.md").read_text(encoding="utf-8")


def split_sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def chunk(text: str) -> list[str]:
    sentences = split_sentences(text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for s in sentences:
        s_len = len(s.split())
        if current_len + s_len > CHUNK_TARGET and current:
            chunks.append(" ".join(current))
            overlap: list[str] = []
            tail_len = 0
            for t in reversed(current):
                tail_len += len(t.split())
                overlap.insert(0, t)
                if tail_len >= CHUNK_OVERLAP:
                    break
            current, current_len = overlap, tail_len
        current.append(s)
        current_len += s_len
    if current:
        chunks.append(" ".join(current))
    return chunks


def contextual_header(doc_title: str, chunk_text: str) -> str:
    return small_llm(CHUNK_HEADER_PROMPT.format(title=doc_title, chunk=chunk_text)).strip()


def _chunk_id(title: str, idx: int, text: str) -> str:
    return hashlib.sha256(f"{title}:{idx}:{text}".encode("utf-8")).hexdigest()[:16]


def ingest_path(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    title = path.stem
    chunks = chunk(text)
    if not chunks:
        return 0
    ids = [_chunk_id(title, i, c) for i, c in enumerate(chunks)]
    existing = set(COLL.get(ids=ids).get("ids") or [])
    new_pairs = [(i, c, cid) for i, (c, cid) in enumerate(zip(chunks, ids)) if cid not in existing]
    if not new_pairs:
        return 0
    docs: list[dict] = []
    for i, c, cid in new_pairs:
        header = contextual_header(title, c)
        full = f"[Document: {title}]\n[Summary: {header}]\n\n{c}"
        docs.append({"id": cid, "text": full, "title": title, "idx": i})
    embs = _vo.embed([d["text"] for d in docs], model=os.environ.get("RAG_EMBED_MODEL", "voyage-3-lite")).embeddings
    COLL.add(
        ids=[d["id"] for d in docs],
        embeddings=embs,
        documents=[d["text"] for d in docs],
        metadatas=[{"title": d["title"], "idx": d["idx"]} for d in docs],
    )
    return len(docs)


def ingest_directory(root: Path) -> None:
    total = 0
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() in {".md", ".txt"} and p.is_file():
            n = ingest_path(p)
            print(f"  + {p.name}: {n} new chunks")
            total += n
    print(f"done. {total} new chunks indexed.")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/corpus")
    if not target.exists():
        raise SystemExit(f"corpus path not found: {target}")
    ingest_directory(target)
