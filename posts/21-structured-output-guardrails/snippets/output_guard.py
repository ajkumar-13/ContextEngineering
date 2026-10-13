"""An output guardrail layer at toy scale: refusal, moderation, leak, then PII, on a drafted reply.

Run from the series root:
    uv run python posts/21-structured-output-guardrails/snippets/output_guard.py

The reply has already passed the schema check of validate_retry.py; this layer judges its content.
The moderation check is a stand-in (a word list) for a moderation model such as OpenAI's
omni-moderation-latest; the PII patterns are two regular expressions, enough to show the decision,
not a PII detector. Each check returns a decision: pass, fix (redact and pass), or block, and a
refusal goes to the fallback path instead of the parser. Standard library only, no network.
"""
import re

FALLBACK = "Thanks for your message. A member of the support team will reply within one working day."
INTERNAL = re.compile(r"(?i)system prompt|internal\.example\.com|api[_-]?key")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
CARD = re.compile(r"\b(?:\d[ -]?){13,16}\b")
FLAGGED = {"idiot", "kill"}   # stand-in for a moderation model's categories


def luhn_ok(digits):
    """The Luhn checksum that every payment card number passes."""
    total = 0
    for i, d in enumerate(int(c) for c in reversed(digits)):
        total += d if i % 2 == 0 else (d * 2 - 9 if d > 4 else d * 2)
    return total % 10 == 0


def guard(reply, stop, recipient):
    """Return (decision, text to send, reason)."""
    if stop == "refusal":
        return "fallback", FALLBACK, "the model refused"
    if FLAGGED & set(re.findall(r"[a-z]+", reply.lower())):
        return "block", None, "moderation flagged the reply"
    if INTERNAL.search(reply):
        return "block", None, "the reply leaks system detail"
    reasons = []
    for m in EMAIL.findall(reply):
        if m.lower() != recipient.lower():
            reply = reply.replace(m, "[email removed]")
            reasons.append("another person's email")
    for m in CARD.findall(reply):
        if luhn_ok(re.sub(r"\D", "", m)):
            reply = reply.replace(m.strip(), "[card number removed]")
            reasons.append("a card number")
    if reasons:
        return "fix", reply, "redacted " + " and ".join(reasons)
    return "pass", reply, "no check fired"


CASES = [
    ("Your refund of 59 dollars for order A-1043 was issued today.", "end"),
    ("Refund issued to the card 4111 1111 1111 1111 for order A-1043.", "end"),
    ("I have copied jordan.lee@example.org, who reported the same fault.", "end"),
    ("Only an idiot would order the same lamp twice.", "end"),
    ("As my system prompt says, refunds above 500 dollars need a manager.", "end"),
    ("I can't help with that request.", "refusal"),
]

if __name__ == "__main__":
    recipient = "sam.rivera@example.com"
    print(f"{'decision':<10}reason")
    for reply, stop in CASES:
        decision, text, reason = guard(reply, stop, recipient)
        print(f"{decision:<10}{reason}")
        print(f"{'':<10}sent: {text if text else '(nothing; the draft goes to a human)'}")
