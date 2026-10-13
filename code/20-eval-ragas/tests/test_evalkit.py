"""Offline tests for evalkit. stdlib + pytest only; no network, no key."""
from __future__ import annotations

from pathlib import Path

from evalkit import (
    answer_match,
    check_regression,
    load_golden_set,
    recall_at_k,
    score_run,
)

FIXTURE = Path(__file__).parent / "fixtures" / "golden_set.json"


def test_recall_at_k():
    assert recall_at_k(["a", "b", "c"], {"b", "d"}, k=3) == 0.5
    assert recall_at_k(["b", "d"], {"b", "d"}, k=2) == 1.0
    assert recall_at_k(["x"], {"b"}, k=1) == 0.0
    assert recall_at_k(["x"], set(), k=1) == 1.0  # nothing to find


def test_answer_match_is_normalised():
    assert answer_match("It is  0.1 times  the base input price.", "0.1 times the base input price") == 1.0
    assert answer_match("no idea", "0.1 times the base input price") == 0.0


def test_load_and_score_a_run():
    cases = load_golden_set(FIXTURE)
    assert len(cases) == 3
    # a system that retrieves and answers q1/q2 well but misses q3
    outputs = {
        "q1": {"answer": "It costs 0.1 times the base input price.",
               "retrieved_ids": ["c_caching_1", "c_caching_2", "junk"]},
        "q2": {"answer": "Use 400 to 600 tokens for prose.",
               "retrieved_ids": ["c_chunk_1"]},
        "q3": {"answer": "not sure", "retrieved_ids": ["wrong"]},
    }
    scores = score_run(cases, outputs, k=5)
    assert scores["answer_match"] == 2 / 3
    # recall: q1 got both (1.0), q2 got its one (1.0), q3 got none (0.0) -> mean 2/3
    assert abs(scores["context_recall@5"] - 2 / 3) < 1e-9


def test_gate_passes_when_metrics_hold():
    res = check_regression({"answer_match": 0.80}, {"answer_match": 0.82}, tolerance=0.05)
    assert res.passed  # 0.80 is within 0.05 of 0.82
    # a drop of exactly the tolerance passes, despite float rounding (0.20 - 0.15 > 0.05 in floats)
    assert check_regression({"m": 0.15}, {"m": 0.20}, tolerance=0.05).passed


def test_gate_fails_on_a_drop():
    res = check_regression({"answer_match": 0.70}, {"answer_match": 0.82}, tolerance=0.05)
    assert not res.passed
    assert "answer_match" in res.regressions


def test_gate_fails_on_a_missing_metric():
    res = check_regression({}, {"answer_match": 0.82})
    assert not res.passed
    assert res.regressions["answer_match"][1] is None
