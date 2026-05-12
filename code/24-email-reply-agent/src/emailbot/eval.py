"""Eval harness scaffold.

Runs the pipeline against held-out historical threads with the user's actual
replies as ground truth. Reports three metrics:
  - tone fidelity (LLM-judge, 1-5)
  - factual faithfulness (LLM-judge, 1-5)
  - decision accuracy (triager bucket vs. revealed preference)

Fixtures format: data/eval_fixtures.json
  [
    {"thread_id": "t1", "thread": [...], "actual_reply": "...", "actual_bucket": "reply_needed"}
  ]
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from statistics import mean

from .draft import draft as draft_thread
from .llm import chat
from .triage import triage as triage_thread

JUDGE_MODEL = os.environ.get("EMAILBOT_JUDGE_MODEL", "gpt-4o-mini")

JUDGE_PROMPT = """You are an evaluator. On a 1-5 scale, score how well the
candidate reply matches the reference reply on the dimension below.
Return JSON only: {"score": <int>, "reason": "<short>"}.

Dimension: {dimension}

Reference reply:
---
{reference}
---

Candidate reply:
---
{candidate}
---
"""


def _judge(reference: str, candidate: str, dimension: str) -> dict:
    raw = chat(
        [{"role": "user", "content": JUDGE_PROMPT.format(dimension=dimension, reference=reference, candidate=candidate)}],
        model=JUDGE_MODEL,
        response_format={"type": "json_object"},
        max_tokens=120,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"score": 0, "reason": "judge_parse_error"}


def run(fixtures_path: Path | str = Path("data/eval_fixtures.json")) -> dict:
    fixtures = json.loads(Path(fixtures_path).read_text(encoding="utf-8"))
    tone, faith, decision_hits = [], [], 0
    for fx in fixtures:
        triage_out = triage_thread(fx["thread"])
        if triage_out["bucket"] == fx["actual_bucket"]:
            decision_hits += 1
        if fx["actual_bucket"] != "reply_needed":
            continue
        d = draft_thread(fx["thread"])
        candidate = d.get("draft") or ""
        ref = fx["actual_reply"]
        tone.append(_judge(ref, candidate, "tone fidelity (voice match)").get("score", 0))
        faith.append(_judge(ref, candidate, "factual faithfulness (no invented facts)").get("score", 0))
    return {
        "tone_fidelity_mean": mean(tone) if tone else 0.0,
        "faithfulness_mean": mean(faith) if faith else 0.0,
        "decision_accuracy": decision_hits / len(fixtures) if fixtures else 0.0,
        "n": len(fixtures),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
