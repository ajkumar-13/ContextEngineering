"""Post 14: a five-block system prompt assembled from versioned parts, and the CI gate that guards it.

Run from the series root:  uv run python posts/14-system-prompt-as-software/snippets/prompt_ci.py
Standard library only; no network and no model. The "model" below is a stand-in that reads the rules
block literally and picks a tool, so that the harness runs offline; a real suite sends each case to
the model and scores its reply. The stand-in follows the last rule that matches a request, which is
one arbitrary way to resolve two rules that contradict each other.
"""
from __future__ import annotations

import hashlib
import re

BLOCKS = ("Identity", "Rules", "Format", "Knowledge", "Tool-use guidance")

# Each block is its own versioned part, as if each lived in its own file under prompts/.
PARTS_V1: dict[str, tuple[str, str]] = {
    "Identity": ("1.0.0", "You are the support agent for Acme. You help customers with billing, account and\n"
                          "shipping questions, and hand anything else to a human."),
    "Rules": ("1.2.0", "- [#412] Refunds above 1000 dollars go to a manager for approval.\n"
                       "- [#377] Quote a delivery date only when it is in the order record.\n"
                       "- [#455] Reply in formal British English."),
    "Format": ("1.1.0", "Answer in plain prose of at most 150 words. Cite the order id in brackets,\n"
                        "as [A-1234], whenever the reply concerns an order."),
    "Knowledge": ("1.0.0", "Office hours are 9:00 to 18:00 IST, Monday to Saturday; the office is closed on Sunday."),
    "Tool-use guidance": ("1.0.0", "- lookup_order: questions about where an order is.\n"
                                   "- refund_order: refunds the rules let a support agent approve.\n"
                                   "- escalate_to_manager: refunds the rules send to a manager.\n"
                                   "- handoff_to_human: anything outside billing, account and shipping."),
}

# Version 1.3.0 of the rules block adds one rule, and the rule contradicts #412.
NEW_RULE = "- [#481] Refunds up to 2000 dollars may be approved without a manager."
PARTS_V2 = dict(PARTS_V1, Rules=("1.3.0", PARTS_V1["Rules"][1] + "\n" + NEW_RULE))

# Ten regression cases: a request and the one tool the prompt says it should lead to ("none" = answer directly).
CASES = [
    ("Please refund 40 dollars on order A-1001, the mug arrived broken.", "refund_order"),
    ("Refund 999 dollars for order A-1002, wrong size.", "refund_order"),
    ("Refund 1000 dollars for order A-1003.", "refund_order"),
    ("Refund 1001 dollars for order A-1004.", "escalate_to_manager"),
    ("I need a refund of 1500 dollars for order A-1005.", "escalate_to_manager"),
    ("Refund 2500 dollars for the sofa on order A-1006.", "escalate_to_manager"),
    ("Where is my order A-1007?", "lookup_order"),
    ("Where is order A-1008? It was due on Monday.", "lookup_order"),
    ("Is your office open on Sunday?", "none"),
    ("Can you recommend a good laptop?", "handoff_to_human"),
]

REFUND_RULE = re.compile(r"\[#(\d+)\] Refunds (above|up to) (\d+) dollars "
                         r"(go to a manager|may be approved without a manager)")
RULE_LINE = re.compile(r"^- \[#\d+\] ")


def assemble(parts: dict[str, tuple[str, str]]) -> str:
    """Join the five blocks, in their fixed order, into one system prompt."""
    return "\n\n".join(f"## {name}\n{parts[name][1]}" for name in BLOCKS)


def versions(parts: dict[str, tuple[str, str]]) -> str:
    return ", ".join(f"{name.lower()} {parts[name][0]}" for name in BLOCKS)


def stand_in_model(prompt: str, request: str) -> str:
    """Pick a tool as the prompt's rules say, read literally; the last matching rule wins."""
    text = request.lower()
    if "refund" in text:
        amount = int(re.search(r"(\d+) dollars", text).group(1))
        tool = "refund_order"
        for _, kind, limit, action in REFUND_RULE.findall(prompt):
            if (kind == "above" and amount > int(limit)) or (kind == "up to" and amount <= int(limit)):
                tool = "escalate_to_manager" if action == "go to a manager" else "refund_order"
        return tool
    if "where is" in text:
        return "lookup_order"
    if "office" in text:
        return "none"
    return "handoff_to_human"


def lint(parts: dict[str, tuple[str, str]]) -> list[str]:
    """Static checks that need no model: blocks present, rules traceable, rules consistent."""
    findings = [f"block {name} is empty" for name in BLOCKS if not parts.get(name, ("", ""))[1].strip()]
    for line in parts["Rules"][1].splitlines():
        if not RULE_LINE.match(line):
            findings.append(f"rule without an issue id: {line}")
        elif re.search(r"\band (always|never)\b", line):
            findings.append(f"two concepts in one rule: {line}")
    # Refund rules as ranges of amounts: "above L" is (L, inf), "up to L" is [0, L].
    ranges = [(rid, (int(limit), float("inf")) if kind == "above" else (0, int(limit)), action)
              for rid, kind, limit, action in REFUND_RULE.findall(parts["Rules"][1])]
    for i, (id_a, (lo_a, hi_a), act_a) in enumerate(ranges):
        for id_b, (lo_b, hi_b), act_b in ranges[i + 1:]:
            lo, hi = max(lo_a, lo_b), min(hi_a, hi_b)
            if act_a != act_b and lo < hi:
                findings.append(f"rules #{id_a} and #{id_b} disagree on refunds above {lo} dollars up to {hi} dollars")
    return findings


def run_suite(prompt: str) -> list[tuple[int, str, str, str]]:
    """Return the failing cases as (number, request, expected, got)."""
    failures = []
    for n, (request, expected) in enumerate(CASES, start=1):
        got = stand_in_model(prompt, request)
        if got != expected:
            failures.append((n, request, expected, got))
    return failures


def gate(parts: dict[str, tuple[str, str]]) -> bool:
    """The CI gate: any lint finding or any failing case blocks the merge (the stand-in has no noise)."""
    prompt = assemble(parts)
    findings, failures = lint(parts), run_suite(prompt)
    print(f"sha256 of the prompt: {hashlib.sha256(prompt.encode()).hexdigest()[:12]}")
    print("lint: " + ("no findings" if not findings else findings[0]))
    for extra in findings[1:]:
        print("      " + extra)
    print(f"regression: {len(CASES) - len(failures)}/{len(CASES)} cases pass")
    for n, request, expected, got in failures:
        print(f"  case {n:02d} \"{request}\": expected {expected}, got {got}")
    passed = not findings and not failures
    s_f, s_c = ("" if len(findings) == 1 else "s"), ("" if len(failures) == 1 else "s")
    print("gate: pass" if passed else
          f"gate: blocked ({len(findings)} lint finding{s_f}, {len(failures)} failing case{s_c})")
    return passed


def main() -> None:
    print(f"prompt v1 ({versions(PARTS_V1)})")
    print(assemble(PARTS_V1))
    print()
    gate(PARTS_V1)
    print()
    changed = [name for name in BLOCKS if PARTS_V1[name] != PARTS_V2[name]]
    print(f"prompt v2 ({versions(PARTS_V2)}); changed blocks: {', '.join(changed)}")
    print(f"rules 1.3.0 adds: {NEW_RULE}")
    gate(PARTS_V2)


if __name__ == "__main__":
    main()
