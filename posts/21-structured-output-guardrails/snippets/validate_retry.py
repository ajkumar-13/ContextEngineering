"""Validate, feed the error back, retry with a cap: the loop, then the plan's lab at toy scale.

Run from the series root:
    uv run python posts/21-structured-output-guardrails/snippets/validate_retry.py

The task extracts four fields from a support ticket. The validator is a small JSON Schema subset
(type, enum, required, additionalProperties, minimum, maximum) plus one cross-field rule the schema
does not state. The model is a stub: its first reply for each input is scripted, and on a retry it
follows the repair instruction, except where a fault is scripted to persist. Every failure count below
is an illustrative input to the stub, not a measurement of any model; what the run shows is which kinds
of failure a retry clears and which it cannot. Standard library only, no network.
"""
import json
import random

SCHEMA = {
    "type": "object",
    "properties": {
        "order_id": {"type": "string"},
        "category": {"type": "string", "enum": ["refund", "shipping", "account", "other"]},
        "priority": {"type": "integer", "minimum": 1, "maximum": 5},
        "refund_amount": {"type": ["number", "null"]},
    },
    "required": ["order_id", "category", "priority", "refund_amount"],
    "additionalProperties": False,
}
TYPES = {"object": dict, "string": str, "integer": int, "number": (int, float), "null": type(None)}


def schema_errors(record, schema=SCHEMA):
    """The JSON Schema subset this task uses; returns one message per violation."""
    if not isinstance(record, dict):
        return ["the reply is not a JSON object"]
    errors = [f"missing required field '{k}'" for k in schema["required"] if k not in record]
    if schema.get("additionalProperties") is False:
        errors += [f"unexpected field '{k}'" for k in record if k not in schema["properties"]]
    for key, rule in schema["properties"].items():
        if key not in record:
            continue
        value, types = record[key], rule["type"] if isinstance(rule["type"], list) else [rule["type"]]
        if isinstance(value, bool) or not isinstance(value, tuple(TYPES[t] for t in types)):
            errors.append(f"'{key}' must be {' or '.join(types)}")
        elif "enum" in rule and value not in rule["enum"]:
            errors.append(f"'{key}' must be one of {', '.join(rule['enum'])}, not '{value}'")
        elif "minimum" in rule and not rule["minimum"] <= value <= rule["maximum"]:
            errors.append(f"'{key}' must be from {rule['minimum']} to {rule['maximum']}, not {value}")
    return errors


def rule_errors(record):
    """The cross-field rule: a refund carries an amount, nothing else does."""
    if (record["category"] == "refund") != isinstance(record["refund_amount"], (int, float)):
        return ["'refund_amount' must be a number for a refund and null otherwise"]
    return []


def check(reply):
    """Parse, then validate the shape, then the rule; returns (record or None, errors)."""
    try:
        record = json.loads(reply)
    except json.JSONDecodeError as e:
        return None, [f"not valid JSON ({e})"]
    errors = schema_errors(record) or rule_errors(record)
    return (None, errors) if errors else (record, [])


class Refused(Exception):
    """The model declined: a guardrail decision, not a parse error."""


class CutOff(Exception):
    """The reply hit max_tokens: rewording cannot fix it, a larger budget can."""


class Exhausted(Exception):
    """Every attempt failed validation: count it, never swallow it."""


def parse_with_retry(call, messages, max_attempts=3):
    """Call the model until its reply validates, feeding each error back as the repair instruction."""
    messages = list(messages)
    for attempt in range(1, max_attempts + 1):
        reply, stop = call(messages)
        if stop == "refusal":
            raise Refused(reply)
        if stop == "max_tokens":
            raise CutOff(reply)
        record, errors = check(reply)
        if not errors:
            return record, attempt
        messages += [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": "That reply did not validate: "
             + "; ".join(errors) + ". Return the corrected JSON object only."},
        ]
    raise Exhausted(errors)


# ---- a stub model: scripted first replies, repairs on request -----------------------------------

GOOD = {"order_id": "A-1043", "category": "refund", "priority": 4, "refund_amount": 59.0}
FAULTS = {  # fault -> (first reply, stop reason)
    "preamble": ("Sure, here is the JSON: " + json.dumps(GOOD), "end"),
    "code fence": ("```json\n" + json.dumps(GOOD) + "\n```", "end"),
    "trailing comma": (json.dumps(GOOD)[:-1] + ",}", "end"),
    "extra field": (json.dumps({**GOOD, "note": "customer is upset"}), "end"),
    "enum case": (json.dumps({**GOOD, "category": "Refund"}), "end"),
    "out of range": (json.dumps({**GOOD, "priority": 7}), "end"),
    "cross-field": (json.dumps({**GOOD, "refund_amount": None}), "end"),
    "two faults": (json.dumps({**GOOD, "category": "Refund", "note": "x"}), "end"),
    "persistent": (json.dumps({**GOOD, "refund_amount": None}), "end"),
    "cut off": (json.dumps(GOOD)[:40], "max_tokens"),
    "refusal": ("I can't help with that request.", "refusal"),
}
SECOND = {  # a reply after one repair: two faults fixes one of them; persistent fixes nothing
    "two faults": json.dumps({**GOOD, "category": "Refund"}),
    "persistent": json.dumps({**GOOD, "refund_amount": None}),
}


def stub(fault, log):
    """A model whose first reply carries `fault`; every call is appended to `log`."""
    def call(messages):
        log.append(fault)
        repairs = sum(1 for m in messages if m["content"].startswith("That reply did not validate"))
        if fault is None:
            return json.dumps(GOOD), "end"
        if repairs == 0:
            return FAULTS[fault]
        if fault == "persistent" or (fault == "two faults" and repairs == 1):
            return SECOND[fault], "end"
        return json.dumps(GOOD), "end"
    return call


def first_reply_class(fault):
    """What the validator makes of the first reply, before any retry."""
    if fault is None:
        return "valid"
    reply, stop = FAULTS[fault]
    if stop != "end":
        return {"max_tokens": "cut off", "refusal": "refused"}[stop]
    try:
        record = json.loads(reply)
    except json.JSONDecodeError:
        return "not JSON"
    return "schema" if schema_errors(record) else "rule"


# Illustrative fault counts per 100 inputs. Prompt-only replies show every shape; a schema sent without
# strict mode is followed on a best-effort basis; strict mode (constrained decoding) leaves what the
# provider pages list (a refusal, a cut-off at max_tokens, enum capitalisation on Anthropic's page),
# plus the range Anthropic does not support (its SDK helpers move minimum and maximum into the
# description) and the cross-field rule this schema does not state.
LAB = {
    "prompt instruction": {"preamble": 6, "code fence": 8, "trailing comma": 3, "extra field": 4,
                           "enum case": 3, "out of range": 2, "cross-field": 3, "two faults": 2,
                           "persistent": 1, "cut off": 1, "refusal": 1},
    "schema, not strict": {"trailing comma": 1, "extra field": 2, "enum case": 2, "out of range": 2, "cross-field": 3,
                           "two faults": 1, "persistent": 1, "cut off": 1, "refusal": 1},
    "strict (constrained)": {"enum case": 1, "out of range": 2, "cross-field": 3, "persistent": 1,
                             "cut off": 1, "refusal": 1},
}
FIRST = ["valid", "not JSON", "schema", "rule", "cut off", "refused"]
AFTER = ["valid", "cut off", "refused", "exhausted"]


def run_lab(counts, n=100, seed=21):
    """Run n inputs through the capped loop; return first-reply classes, outcomes and calls made."""
    faults = [f for f, k in counts.items() for _ in range(k)]
    faults += [None] * (n - len(faults))
    random.Random(seed).shuffle(faults)
    first, after, log = dict.fromkeys(FIRST, 0), dict.fromkeys(AFTER, 0), []
    ask = [{"role": "user", "content": "Ticket: order A-1043 arrived broken, refund the 59 dollars."}]
    for fault in faults:
        first[first_reply_class(fault)] += 1
        try:
            parse_with_retry(stub(fault, log), ask)
            after["valid"] += 1
        except CutOff:
            after["cut off"] += 1
        except Refused:
            after["refused"] += 1
        except Exhausted:
            after["exhausted"] += 1
    return first, after, len(log)


if __name__ == "__main__":
    ask = [{"role": "user", "content": "Ticket: order A-1043 arrived broken, refund the 59 dollars."}]
    print("one input whose first reply has two faults, capped at 3 attempts:")
    record, attempts = parse_with_retry(stub("two faults", []), ask)
    for reply in (FAULTS["two faults"][0], SECOND["two faults"]):
        print("  rejected: " + "; ".join(check(reply)[1]))
    print(f"  valid on attempt {attempts}: {json.dumps(record)}")

    results = {m: run_lab(c) for m, c in LAB.items()}
    print("\n100 inputs per mechanism, stub model, illustrative fault counts")
    print("first reply           " + "".join(f"{h:>10}" for h in FIRST))
    for m, (first, _, _) in results.items():
        print(f"{m:<22}" + "".join(f"{first[h]:>10}" for h in FIRST))
    print("after the capped loop " + "".join(f"{h:>10}" for h in AFTER) + f"{'calls':>10}")
    for m, (_, after, calls) in results.items():
        print(f"{m:<22}" + "".join(f"{after[h]:>10}" for h in AFTER) + f"{calls:>10}")
