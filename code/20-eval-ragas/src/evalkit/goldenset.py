"""Load and run a golden set.

A golden set is a small, fixed list of cases (question, ideal answer, and the ids
of the chunks that should be retrieved) that is run on every change (post 20).
This loader is dependency-free JSON; the runner is a pure function that scores a
system's outputs against the set.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .metrics import answer_match, mean, recall_at_k


@dataclass(frozen=True)
class Case:
    id: str
    question: str
    ideal_answer: str
    relevant_chunk_ids: list[str]


def load_golden_set(path: str | Path) -> list[Case]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Case(c["id"], c["question"], c["ideal_answer"], list(c["relevant_chunk_ids"]))
        for c in data
    ]


def score_run(cases: list[Case], outputs: dict[str, dict], k: int = 5) -> dict[str, float]:
    """Score a system's outputs against the golden set.

    ``outputs`` maps case id -> {"answer": str, "retrieved_ids": [str, ...]}.
    Returns aggregate metrics: ``context_recall@k`` and ``answer_match``.
    """
    recalls, matches = [], []
    for case in cases:
        out = outputs.get(case.id, {"answer": "", "retrieved_ids": []})
        recalls.append(recall_at_k(out["retrieved_ids"], set(case.relevant_chunk_ids), k))
        matches.append(answer_match(out["answer"], case.ideal_answer))
    return {f"context_recall@{k}": mean(recalls), "answer_match": mean(matches)}
