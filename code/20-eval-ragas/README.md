# RAG evaluation harness (`evalkit`)

Companion code for **[Post 20 — Evaluation](../../posts/20-evaluation/index.md)**.

A small, honest eval harness that mirrors the eval pyramid: cheap deterministic checks at the base, an LLM judge at the top, and a **regression gate** that blocks a deploy on a drop.

```
Offline base (no key, unit-tested, CI-ready):
  golden set → recall@k + answer_match → regression gate
Online top (needs a key):
  LLM-as-judge (faithfulness) — with position/verbosity/self-preference notes
```

## Quickstart

```bash
cd code/20-eval-ragas
python -m pip install -e ".[dev]"
pytest                 # the whole gate runs with no key and no network
```

```python
from evalkit import load_golden_set, score_run, check_regression

cases = load_golden_set("tests/fixtures/golden_set.json")
scores = score_run(cases, my_system_outputs, k=5)          # {"context_recall@5": ..., "answer_match": ...}

gate = check_regression(scores, baseline=saved_baseline, tolerance=0.05)
if not gate.passed:
    raise SystemExit(f"eval regression: {gate.regressions}")  # fail the CI build
```

## The LLM judge (online)

```bash
python -m pip install -e ".[online]"
cp .env.example .env       # set ANTHROPIC_API_KEY
```

```python
from evalkit.judge import faithfulness
faithfulness(answer, context)   # 1 if every claim is supported by the context, else 0
```

The judge is biased — it favours the first option, longer answers, and its own family's outputs. `judge.py` documents the mitigations (run pairs both orders, length-normalise, judge with a different model family).

## What's stubbed / deliberately small

- **`answer_match` is a blunt containment check**, enough to catch regressions on a golden set without a judge; faithfulness/relevancy are the judge's and Ragas' job.
- **The 5% gate tolerance is a default**, set per metric to what your traffic allows.
- **`ragas` is the batteries-included alternative** for the online metrics; install the `ragas` extra. The core stays dependency-free so the gate runs in CI.
