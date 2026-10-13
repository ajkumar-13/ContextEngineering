"""Constrained decoding at toy scale: a token mask that only lets valid JSON through.

Run from the series root:
    uv run python posts/21-structured-output-guardrails/snippets/constrained_decoding.py

The "model" is a fixed ranking of next tokens, not a language model: for each context it lists the
tokens it prefers, best first. Left alone it writes a preamble, a code fence, a capitalised enum value,
a priority of 7 and an extra key. The grammar accepts exactly one shape,
{"category": <one of four labels>, "priority": <1 to 5>}, and at every step masks every token that
would leave that shape; the decoder then takes the model's best remaining token. Standard library only.
"""
import json

LABELS = ['"refund"', '"shipping"', '"account"', '"other"']
DIGITS = [str(d) for d in range(1, 10)]
VOCAB = (['Sure, here is the JSON:', '\n~~~json\n', '{', '"category": ', '"Refund"'] + LABELS
         + [', ', '"priority": '] + DIGITS + ['"note": ', '"urgent"', '}', '\n~~~', '<end>'])

# The model's preferences: context (last token, or last two) -> tokens it ranks first, second, ...
RANK = {
    (None,): ['Sure, here is the JSON:', '{'],
    ('Sure, here is the JSON:',): ['\n~~~json\n'],
    ('\n~~~json\n',): ['{'],
    ('{',): ['"category": '],
    ('"category": ',): ['"Refund"', '"refund"', '"shipping"'],
    ('"Refund"',): [', '],
    ('"refund"',): [', '],
    ('"Refund"', ', '): ['"priority": '],
    ('"refund"', ', '): ['"priority": '],
    ('"priority": ',): ['7', '5', '4'],
    ('7',): [', ', '}'],
    ('5',): [', ', '}'],
    ('7', ', '): ['"note": '],
    ('"note": ',): ['"urgent"'],
    ('"urgent"',): ['}'],
    ('}',): ['\n~~~', '<end>'],
    ('\n~~~',): ['<end>'],
}


def ranking(out):
    """The model's full ranking for the next token: its listed preferences, then vocabulary order."""
    prev = tuple(out[-2:]) if len(out) >= 2 else None
    listed = RANK.get(prev) or RANK.get(tuple(out[-1:]) if out else (None,), [])
    return listed + [t for t in VOCAB if t not in listed]


# The grammar as a finite-state machine: state -> (allowed tokens, next state).
GRAMMAR = [
    (['{'], 1), (['"category": '], 2), (LABELS, 3), ([', '], 4), (['"priority": '], 5),
    (DIGITS[:5], 6), (['}'], 7), (['<end>'], None),
]


def decode(constrained, max_tokens=20):
    out, trace, state = [], [], 0
    while len(out) < max_tokens:
        ranked = ranking(out)
        if constrained:
            allowed, nxt = GRAMMAR[state]
            token = next(t for t in ranked if t in allowed)   # the mask, then the best survivor
            trace.append((len(out) + 1, len(allowed), ranked[0], token))
            state = nxt
        else:
            token = ranked[0]
        if token == '<end>':
            break
        out.append(token)
    return "".join(out), trace


def try_parse(text):
    try:
        return "parses: " + json.dumps(json.loads(text))
    except json.JSONDecodeError as e:
        return f"json.loads fails: {e}"


free, _ = decode(constrained=False)
print("unconstrained, the model's first choice at every step:")
print("  " + free.replace("\n", "\\n"))
print("  " + try_parse(free))

masked, trace = decode(constrained=True)
print("\nconstrained, the grammar masks every token that would break the shape:")
print("step  allowed  model's first choice      emitted")


def show(token):
    """A token as printed: newlines written as \\n, trailing spaces not shown."""
    return token.replace("\n", "\\n").strip()


for step, n, first, token in trace:
    flag = "" if first == token else "  (first choice masked)"
    print(f"{step:>4}  {n:>7}  {show(first):<24}  {show(token)}{flag}")
print("  " + masked)
print("  " + try_parse(masked))
overrides = sum(1 for _, _, first, token in trace if first != token)
print(f"  the mask overrode the model at {overrides} of {len(trace)} steps")

cut, _ = decode(constrained=True, max_tokens=5)
print("\nconstrained, but max_tokens = 5:")
print("  " + cut.rstrip())
print("  " + try_parse(cut))
