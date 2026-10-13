"""Deterministic, offline evaluation metrics for a RAG system.

These are the metrics computed without a model in the loop: the cheap,
fast base of the eval pyramid (Post 20). The LLM-as-judge layer (``judge.py``)
sits above them and needs a key.
"""
from __future__ import annotations


def recall_at_k(retrieved_ids: list, relevant_ids: set, k: int) -> float:
    """Fraction of the ground-truth relevant chunks that appear in the top-k retrieved."""
    if not relevant_ids:
        return 1.0  # nothing to find; vacuously perfect
    if k <= 0:
        raise ValueError("k must be positive")
    top = set(retrieved_ids[:k])
    return len(top & relevant_ids) / len(relevant_ids)


def _normalise(s: str) -> str:
    return " ".join(s.lower().split())


def answer_match(answer: str, ideal: str) -> float:
    """1.0 if the ideal answer's normalised text is contained in the answer, else 0.0.

    A blunt proxy for correctness, enough to catch regressions on a golden set
    without a judge. Faithfulness/relevancy live in ``judge.py`` and Ragas.
    """
    return 1.0 if _normalise(ideal) in _normalise(answer) else 0.0


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0
