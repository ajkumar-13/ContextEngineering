"""LLM-as-judge scaffold (online, guarded).

The judge scores things the deterministic metrics cannot: faithfulness (is every
claim supported by the retrieved context?) and answer relevancy. It is powerful and
biased: judges favour the FIRST option (position bias) and LONGER answers (verbosity
bias), and may favour their OWN family's outputs (self-preference, which Zheng et al.
2023 could not establish). Mitigations are in the prompt and comments below (post 20).

The SDK is imported lazily; nothing here runs, or is needed, for the offline tests.
"""
from __future__ import annotations

import os

_FAITHFULNESS_RUBRIC = """\
You are grading whether an ANSWER is faithful to the CONTEXT.
Score 1 only if EVERY claim in the answer is supported by the context; else 0.
Judge only faithfulness, not style or length. Ignore how long the answer is.
Return just the digit 0 or 1.
"""


def faithfulness(answer: str, context: str, model: str = "claude-sonnet-4-5") -> int:
    """Ask a model whether the answer is fully supported by the context. Returns 0 or 1.

    Requires ANTHROPIC_API_KEY and the ``anthropic`` package.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set: the judge is the online layer; see README.")
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("Install the online extra: pip install '.[online]'") from e

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=4,
        system=_FAITHFULNESS_RUBRIC,
        messages=[{"role": "user", "content": f"CONTEXT:\n{context}\n\nANSWER:\n{answer}"}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    return 1 if text.startswith("1") else 0

# To reduce position/verbosity bias when comparing two answers: run each pair in BOTH
# orders and count a win only when it survives the swap, a tie otherwise; strip answers
# to comparable length before judging; and prefer a judge from a different model family
# than the one under test (self-preference).
