"""Sentence-aware chunking with overlap.

A chunk is a window of consecutive sentences whose combined length is close to a
target token count, with a few sentences of overlap carried into the next chunk.
Token counts here are approximated by whitespace-delimited words — good enough to
teach the shape; a production pipeline would count real model tokens (see
``ragkit.tokens``-style helpers in the post). The approximation is documented so
the numbers in the tests are reproducible offline with no dependencies.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_SENTENCE = re.compile(r"\S.*?(?:[.!?]+(?=\s|$)|$)", re.S)


@dataclass(frozen=True)
class Chunk:
    text: str
    start_sentence: int  # index of the first sentence, for provenance
    n_tokens: int


def split_sentences(text: str) -> list[str]:
    """Split prose into sentences. Naive but deterministic and dependency-free."""
    return [m.group(0).strip() for m in _SENTENCE.finditer(text) if m.group(0).strip()]


def _tok(s: str) -> int:
    return len(s.split())


def chunk(
    text: str,
    target_tokens: int = 500,
    overlap_tokens: int = 75,
) -> list[Chunk]:
    """Group sentences into ~``target_tokens`` windows with ``overlap_tokens`` carryover.

    Guarantees: chunks never split a sentence; each chunk after the first repeats
    enough trailing sentences of the previous chunk to cover ``overlap_tokens``;
    a single over-long sentence becomes its own chunk rather than being dropped.
    """
    if target_tokens <= 0:
        raise ValueError("target_tokens must be positive")
    if not 0 <= overlap_tokens < target_tokens:
        raise ValueError("overlap_tokens must be in [0, target_tokens)")

    sents = split_sentences(text)
    if not sents:
        return []

    chunks: list[Chunk] = []
    i = 0
    while i < len(sents):
        cur: list[str] = []
        cur_tok = 0
        j = i
        while j < len(sents) and (cur_tok + _tok(sents[j]) <= target_tokens or not cur):
            cur.append(sents[j])
            cur_tok += _tok(sents[j])
            j += 1
        chunks.append(Chunk(" ".join(cur), start_sentence=i, n_tokens=cur_tok))
        if j >= len(sents):
            break
        # step back far enough to overlap ~overlap_tokens worth of trailing sentences
        back = 0
        acc = 0
        while back < len(cur) - 1 and acc < overlap_tokens:
            acc += _tok(cur[-1 - back])
            back += 1
        i = j - back
    return chunks
