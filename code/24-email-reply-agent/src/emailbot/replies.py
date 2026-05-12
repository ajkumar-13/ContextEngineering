"""RAG over the user's prior sent replies. Tone-transfer corpus."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import chromadb
import voyageai

_client = chromadb.PersistentClient(path=os.environ.get("EMAILBOT_DATA_DIR", "data") + "/.chroma_replies")
COLL = _client.get_or_create_collection("replies")
_vo = voyageai.Client() if os.environ.get("VOYAGE_API_KEY") else None


def _embed(texts: list[str]) -> list[list[float]]:
    if _vo is None:
        # cheap fallback: hash-based pseudo-embedding for the offline demo
        return [[float((hash(t + str(i)) % 997) / 997.0) for i in range(64)] for t in texts]
    return _vo.embed(texts, model=os.environ.get("EMAILBOT_EMBED_MODEL", "voyage-3-lite")).embeddings


def index_sent_folder(folder: Path) -> int:
    n = 0
    docs: list[dict] = []
    for p in sorted(folder.glob("*.txt")):
        body = p.read_text(encoding="utf-8")
        # filename convention: 2025-09-12__anika@partnerco.io__partnership.txt
        parts = p.stem.split("__")
        recipient = parts[1] if len(parts) > 1 else "unknown"
        subject = parts[2].replace("_", " ") if len(parts) > 2 else p.stem
        cid = hashlib.sha256(p.name.encode()).hexdigest()[:16]
        docs.append({"id": cid, "text": body, "recipient": recipient, "subject": subject})
    if not docs:
        return 0
    existing = set(COLL.get(ids=[d["id"] for d in docs]).get("ids") or [])
    new = [d for d in docs if d["id"] not in existing]
    if not new:
        return 0
    embs = _embed([d["text"] for d in new])
    COLL.add(
        ids=[d["id"] for d in new],
        embeddings=embs,
        documents=[d["text"] for d in new],
        metadatas=[{"recipient": d["recipient"], "subject": d["subject"]} for d in new],
    )
    n = len(new)
    return n


def retrieve_prior_replies(query: str, *, recipient: str | None = None, k: int = 5) -> list[dict]:
    where = {"recipient": recipient.lower()} if recipient else None
    if COLL.count() == 0:
        return []
    q_emb = _embed([query])[0]
    res = COLL.query(query_embeddings=[q_emb], n_results=min(k, COLL.count()), where=where)
    out: list[dict] = []
    for cid, doc, meta in zip(res["ids"][0], res["documents"][0], res["metadatas"][0]):
        out.append({"id": cid, "text": doc, "meta": meta})
    return out


def pack_prior_replies(hits: list[dict]) -> str:
    if not hits:
        return "[prior replies: none on file]\n"
    if len(hits) > 1:
        ordered = [hits[0]] + hits[2:] + [hits[1]]
    else:
        ordered = hits
    lines = ["[prior replies, for tone reference]"]
    for h in ordered:
        m = h["meta"]
        lines.append(f"--- to {m['recipient']} re: {m['subject']} ---")
        lines.append(h["text"].strip())
    return "\n".join(lines) + "\n"
