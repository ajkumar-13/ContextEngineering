"""evalkit: a small, honest evaluation harness for RAG.

Companion code for Post 20 (Evaluation). It mirrors the eval pyramid:

    Offline base (pure, unit-tested):
        metrics    : recall@k, answer_match
        goldenset  : load a JSON golden set and score a run against it
        gate       : the regression gate that blocks a deploy on a drop

    Online top (needs a key; imported lazily):
        judge      : LLM-as-judge for faithfulness, with bias mitigations noted

``ragas`` is the batteries-included alternative for the online metrics; this keeps
the core dependency-free so the whole gate runs in CI without a key.
"""
from __future__ import annotations

from .gate import DEFAULT_TOLERANCE, GateResult, check_regression
from .goldenset import Case, load_golden_set, score_run
from .metrics import answer_match, mean, recall_at_k

__all__ = [
    "Case",
    "DEFAULT_TOLERANCE",
    "GateResult",
    "answer_match",
    "check_regression",
    "load_golden_set",
    "mean",
    "recall_at_k",
    "score_run",
]

__version__ = "0.1.0"
