"""Hybrid retrieval (dense + BM25) -> RRF -> cross-encoder rerank.

The four-stage pipeline from Post 08, §1.
"""
from __future__ import annotations

import os
import re
from collections import defaultdict
from functools import lru_cache

import cohere
import voyageai
from rank_bm25 import BM25Okapi

from .ingest import COLL

_vo = voyageai.Client()
_co = cohere.Client()
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


@lru_cache(maxsize=1)
def _all_docs() -> tuple[list[str], list[str], list[dict]]:
    got = COLL.get(include=["documents", "metadatas"])
    return got["ids"], got["documents"], got["metadatas"]


@lru_cache(maxsize=1)
def _bm25() -> BM25Okapi:
    _, docs, _ = _all_docs()
    return BM25Okapi([_tokenize(d) for d in docs])


def reset_caches() -> None:
    _all_docs.cache_clear()
    _bm25.cache_clear()


def rrf_merge(rankings: list[list[str]], *, k: int = 60) -> list[str]:
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, cid in enumerate(ranking):
            scores[cid] += 1.0 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)


def hybrid(query: str, *, top_n: int = 50) -> list[dict]:
    q_emb = _vo.embed([query], model=os.environ.get("RAG_EMBED_MODEL", "voyage-3-lite")).embeddings[0]
    dense = COLL.query(query_embeddings=[q_emb], n_results=top_n)
    dense_ids = dense["ids"][0]
    ids, docs, metas = _all_docs()
    bm25 = _bm25()
    scores = bm25.get_scores(_tokenize(query))
    sparse_ids = [cid for cid, _ in sorted(zip(ids, scores), key=lambda p: p[1], reverse=True)[:top_n]]
    fused = rrf_merge([dense_ids, sparse_ids])[:top_n]
    id_to_doc = dict(zip(ids, docs))
    id_to_meta = dict(zip(ids, metas))
    return [{"id": cid, "text": id_to_doc[cid], "meta": id_to_meta[cid]} for cid in fused if cid in id_to_doc]


def rerank(query: str, candidates: list[dict], *, k: int = 5) -> list[dict]:
    if not candidates:
        return []
    if not os.environ.get("COHERE_API_KEY"):
        return candidates[:k]
    resp = _co.rerank(
        model=os.environ.get("RAG_RERANK_MODEL", "rerank-english-v3.0"),
        query=query,
        documents=[c["text"] for c in candidates],
        top_n=k,
    )
    return [candidates[r.index] for r in resp.results]


def retrieve(query: str, *, k: int = 5, top_n: int = 50) -> list[dict]:
    return rerank(query, hybrid(query, top_n=top_n), k=k)
