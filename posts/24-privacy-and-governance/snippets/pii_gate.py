"""Post 24: a detect-and-redact gate in front of the model and the trace store.

Run from the series root:  uv run python posts/24-privacy-and-governance/snippets/pii_gate.py
Standard library only; no network, no model call. Twenty synthetic prompts carry seeded personal data (names,
email addresses, phone numbers, payment card numbers, National Insurance numbers). Each prompt passes the gate
once: detectors run cheapest first, every hit becomes a typed placeholder, and the mapping goes to a separate
vault. The trace store always receives the redacted text; the model receives the redacted text only when the
task does not need the values. The script checks that no seeded value reaches the trace store.

Every name, address and number is synthetic: email domains are the reserved example.com and example.org, the
phone numbers are in ranges reserved for drama, the card numbers are published test numbers, and QQ is not an
allocated National Insurance prefix. The name list stands in for a named-entity recognition (NER) model, and
the prompts were written for these detectors, so a clean run tests the plumbing, not the detection rate.
"""
import re

FIRST_NAMES = {"Priya", "Tom", "Elena", "Sam", "Ana", "Kenji", "Lucy", "Omar", "Grace", "Ravi"}


def luhn_ok(digits: str) -> bool:
    """The Luhn checksum that every payment card number satisfies."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch) * (2 if i % 2 else 1)
        total += d - 9 if d > 9 else d
    return total % 10 == 0


# Detectors, cheapest first: each is (type, pattern, check). A check can reject a format match.
DETECTORS = [
    ("CARD", re.compile(r"\b\d(?:[ -]?\d){12,18}\b"), lambda s: luhn_ok(re.sub(r"\D", "", s))),
    ("NINO", re.compile(r"\b[A-Z]{2}(?: ?\d{2}){3} ?[A-D]\b"), None),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), None),
    ("PHONE", re.compile(r"\+\d{1,3}(?: \d{2,6}){2,4}\b|\b0\d{2,4}(?: \d{3,4}){2}\b"), None),
    ("PERSON", re.compile(r"\b(?:%s) [A-Z][a-z]+\b" % "|".join(sorted(FIRST_NAMES))), None),
]


def detect(text: str) -> list[tuple[str, str]]:
    """Return (type, value) for every hit; a span taken by an earlier detector is not matched again."""
    hits, taken = [], []
    for kind, pattern, check in DETECTORS:
        for m in pattern.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            if check is None or check(m.group()):
                hits.append((kind, m.group()))
                taken.append(m.span())
    return hits


def redact(text: str, hits: list[tuple[str, str]]) -> tuple[str, dict[str, str]]:
    """Replace each value with a typed placeholder; return the text and the placeholder-to-value map."""
    vault, seen, counts = {}, {}, {}
    for kind, value in hits:
        if value not in seen:
            counts[kind] = counts.get(kind, 0) + 1
            seen[value] = f"<{kind}_{counts[kind]}>"
            vault[seen[value]] = value
    for value in sorted(seen, key=len, reverse=True):
        text = text.replace(value, seen[value])
    return text, vault


def gate(call_id: str, task: str, text: str, trace_store: list, vault_store: dict) -> str:
    """Run once at the trust boundary. Returns what the model receives; writes the trace and the vault."""
    hits = detect(text)
    redacted, vault = redact(text, hits)
    trace_store.append({"call": call_id, "task": task, "prompt": redacted})   # always the redacted copy
    vault_store[call_id] = vault                                              # kept apart, tighter access
    return redacted if task == "summarise" else text                          # raw only when the task is the PII


# (task, prompt, seeded values). "summarise" does not need the values; "act" does (the task is the PII).
PROMPTS = [
    ("summarise", "Summarise this ticket: Priya Raman (priya.raman@example.com) says her card 4111 1111 1111 1111 was charged twice.",
     ["Priya Raman", "priya.raman@example.com", "4111 1111 1111 1111"]),
    ("act", "Email Tom Okafor at tom.okafor@example.org to confirm the refund.", ["Tom Okafor", "tom.okafor@example.org"]),
    ("summarise", "Summarise the call notes: Elena Varga rang from 020 7946 0018 about order 1234 5678 9012 3456.",
     ["Elena Varga", "020 7946 0018"]),
    ("act", "Call Sam Whitfield back on +44 20 7946 0321 before noon.", ["Sam Whitfield", "+44 20 7946 0321"]),
    ("summarise", "Summarise: Ana Costa, National Insurance number QQ 12 34 56 C, asks why her payslip changed.",
     ["Ana Costa", "QQ 12 34 56 C"]),
    ("act", "Update the billing email for Kenji Mori to kenji.mori@example.com.", ["Kenji Mori", "kenji.mori@example.com"]),
    ("summarise", "Summarise this complaint from Lucy Hart, lucy.hart@example.org, phone 0161 496 0702.",
     ["Lucy Hart", "lucy.hart@example.org", "0161 496 0702"]),
    ("act", "Refund the payment on card 5555 5555 5555 4444 for Omar Haddad.", ["5555 5555 5555 4444", "Omar Haddad"]),
    ("summarise", "Summarise the thread: Grace Lin forwarded a statement for card 4012 8888 8888 1881.",
     ["Grace Lin", "4012 8888 8888 1881"]),
    ("act", "Send Ravi Menon the contract at ravi.menon@example.com.", ["Ravi Menon", "ravi.menon@example.com"]),
    ("summarise", "Summarise: the caller on +1 202 555 0147 asked for Priya Raman's manager.", ["+1 202 555 0147", "Priya Raman"]),
    ("act", "Book a call with Elena Varga on 0113 496 0555.", ["Elena Varga", "0113 496 0555"]),
    ("summarise", "Summarise this form: name Sam Whitfield, NI number QQ 65 43 21 A, email sam.w@example.org.",
     ["Sam Whitfield", "QQ 65 43 21 A", "sam.w@example.org"]),
    ("act", "Confirm the address change for Ana Costa by email to ana.costa@example.com.", ["Ana Costa", "ana.costa@example.com"]),
    ("summarise", "Summarise: Lucy Hart disputes a charge on card 3782 822463 10005.", ["Lucy Hart", "3782 822463 10005"]),
    ("act", "Tell Kenji Mori his case number by text to +44 7700 900123.", ["Kenji Mori", "+44 7700 900123"]),
    ("summarise", "Summarise the escalation: Omar Haddad (omar.haddad@example.org) threatened to cancel.",
     ["Omar Haddad", "omar.haddad@example.org"]),
    ("act", "Reply to Grace Lin at grace.lin@example.com with the invoice.", ["Grace Lin", "grace.lin@example.com"]),
    ("summarise", "Summarise the chat: the patient in bed 4 has a penicillin allergy; Ravi Menon is the duty nurse.",
     ["Ravi Menon"]),
    ("act", "Add Tom Okafor, 020 7946 0999, as the emergency contact.", ["Tom Okafor", "020 7946 0999"]),
]
DECOY = "1234 5678 9012 3456"                     # an order number: card-shaped, fails the Luhn check
CONTEXT_DEPENDENT = "the patient in bed 4 has a penicillin allergy"   # health data no pattern or name list catches


def main() -> None:
    trace_store, vault_store, to_model = [], {}, []
    caught, missed = {}, []
    for i, (task, text, seeded) in enumerate(PROMPTS, 1):
        call_id = f"call-{i:02d}"
        found = dict((v, k) for k, v in detect(text))
        for value in seeded:
            if value in found:
                caught[found[value]] = caught.get(found[value], 0) + 1
            else:
                missed.append((call_id, value))
        to_model.append((call_id, task, gate(call_id, task, text, trace_store, vault_store)))
    seeded_all = [v for _, _, s in PROMPTS for v in s]
    in_trace = [v for v in seeded_all if any(v in r["prompt"] for r in trace_store)]
    raw_to_model = sum(1 for (_, task, sent), (_, _, s) in zip(to_model, PROMPTS) if any(v in sent for v in s))

    print(f"detect-and-redact gate: {len(PROMPTS)} prompts, {len(seeded_all)} seeded values")
    for kind, _, _ in DETECTORS:
        print(f"  {kind:<8} {caught.get(kind, 0):>2} caught")
    print(f"  missed   {len(missed):>2}")
    decoy_left = all(DECOY in r["prompt"] for r in trace_store if r["call"] == "call-03")
    print(f"card-shaped order number {DECOY}: Luhn {'pass' if luhn_ok(DECOY.replace(' ', '')) else 'fail'}, "
          f"{'left in the text' if decoy_left else 'redacted'}")
    cd_left = any(CONTEXT_DEPENDENT in r["prompt"] for r in trace_store)
    print(f"context-dependent health detail: {'not caught' if cd_left else 'caught'} (a case for the classifier layer)")
    n_sum = sum(1 for t, _, _ in PROMPTS if t == "summarise")
    print(f"to the model: {n_sum} summarise prompts redacted, {raw_to_model} act prompts sent with the values")
    print(f"to the trace store: {len(trace_store)} records, {len(in_trace)} seeded values found")
    rec, vault = trace_store[0], vault_store["call-01"]
    print("example, call-01:")
    print(f"  trace: {rec['prompt']}")
    print("  vault: " + ", ".join(f"{k} = {v}" for k, v in vault.items()))
    ok = not missed and not in_trace and decoy_left and raw_to_model == len(PROMPTS) - n_sum
    print(f"gate: {'pass' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
