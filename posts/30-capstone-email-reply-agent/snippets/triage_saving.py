"""Post 30: what the triager saves, written out with illustrative per-call costs and an illustrative inbox.

Run from the series root:  uv run python posts/30-capstone-email-reply-agent/snippets/triage_saving.py
Standard library only. Every number below is illustrative, a stand-in for a reader's own prices and
inbox mix: a triage call (a short prompt, a small model, a reply capped at 200 tokens) at a tenth of a
cent, a drafter call at five cents, 90 threads of which 30 need a reply.
"""
from fractions import Fraction

TRIAGE_CENTS = Fraction(1, 10)   # illustrative cost of one triage call, cents
DRAFT_CENTS = Fraction(5)        # illustrative cost of one drafter call, cents
THREADS, NEED_REPLY = 90, 30     # illustrative inbox: one thread in three needs a reply


def cents(x: Fraction) -> str:
    return f"{float(x):.1f}"


if __name__ == "__main__":
    without = THREADS * DRAFT_CENTS
    with_triage = THREADS * TRIAGE_CENTS + NEED_REPLY * DRAFT_CENTS
    print(f"{THREADS} threads, {NEED_REPLY} need a reply; triage {cents(TRIAGE_CENTS)} c, draft {cents(DRAFT_CENTS)} c a call")
    print(f"drafter on every thread:   {THREADS} x {cents(DRAFT_CENTS)} = {cents(without)} cents")
    print(f"triager first:             {THREADS} x {cents(TRIAGE_CENTS)} + {NEED_REPLY} x {cents(DRAFT_CENTS)}"
          f" = {cents(with_triage)} cents")
    print(f"saving: {cents(without - with_triage)} cents, {float(1 - with_triage / without):.1%} of the bill")
    print(f"the triager pays for itself once more than {float(TRIAGE_CENTS / DRAFT_CENTS):.0%} of threads are filtered")
