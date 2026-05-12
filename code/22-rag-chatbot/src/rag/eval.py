"""Eval harness: the four Ragas metrics on a held-out fixture set."""
from __future__ import annotations

import json
from pathlib import Path

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from .chat import answer
from .retrieve import retrieve


def run(fixtures_path: Path | str = Path("tests/fixtures.json")) -> dict:
    fixtures = json.loads(Path(fixtures_path).read_text(encoding="utf-8"))
    rows: list[dict] = []
    for fx in fixtures:
        out = answer(fx["question"])
        ctxs = [h["text"] for h in retrieve(fx["question"], k=5)]
        rows.append({
            "question": fx["question"],
            "answer": out["answer"],
            "contexts": ctxs,
            "ground_truth": fx["answer"],
        })
    ds = Dataset.from_list(rows)
    res = evaluate(
        ds,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )
    return res.to_pandas().mean(numeric_only=True).to_dict()


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
