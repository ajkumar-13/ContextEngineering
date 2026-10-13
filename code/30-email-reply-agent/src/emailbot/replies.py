"""RAG over the user's prior sent replies. Tone-transfer corpus."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import chromadb
import voyageai

_coll = None
_voyage = None
_WORD_RE = re.compile(r"\w+")


def COLL():
    """The Chroma collection, opened on first use so importing creates nothing on disk."""
    global _coll
    if _coll is None:
        client = chromadb.PersistentClient(path=os.environ.get("EMAILBOT_DATA_DIR", "data") + "/.chroma_replies")
        _coll = client.get_or_create_collection("replies")
    return _coll


def _vo():
    """The Voyage client, built on first use; None without a key (offline fallback below)."""
    global _voyage
    if _voyage is None and os.environ.get("VOYAGE_API_KEY"):
        _voyage = voyageai.Client()
    return _voyage


def _embed(texts: list[str]) -> list[list[float]]:
    vo = _vo()
    if vo is None:
        # offline fallback: a deterministic hashed bag of words in 64 buckets (no semantics, same
        # vector for the same text on every run; a real embedding needs VOYAGE_API_KEY)
        out = []
        for t in texts:
            vec = [0.0] * 64
            for w in _WORD_RE.findall(t.lower()):
                vec[int(hashlib.sha256(w.encode()).hexdigest(), 16) % 64] += 1.0
            out.append(vec)
        return out
    return vo.embed(texts, model=os.environ.get("EMAILBOT_EMBED_MODEL", "voyage-3-lite")).embeddings


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
    existing = set(COLL().get(ids=[d["id"] for d in docs]).get("ids") or [])
    new = [d for d in docs if d["id"] not in existing]
    if not new:
        return 0
    embs = _embed([d["text"] for d in new])
    COLL().add(
        ids=[d["id"] for d in new],
        embeddings=embs,
        documents=[d["text"] for d in new],
        metadatas=[{"recipient": d["recipient"], "subject": d["subject"]} for d in new],
    )
    n = len(new)
    return n


def retrieve_prior_replies(query: str, *, recipient: str | None = None, k: int = 5) -> list[dict]:
    where = {"recipient": recipient.lower()} if recipient else None
    coll = COLL()
    if coll.count() == 0:
        return []
    q_emb = _embed([query])[0]
    res = coll.query(query_embeddings=[q_emb], n_results=min(k, coll.count()), where=where)
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
