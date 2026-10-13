"""Replay captured traces against a changed prompt and diff the results, standard library only.

Run from the series root:  uv run python posts/22-observability/snippets/replay.py

Offline: `stand_in_model` replaces the model call, so the run is deterministic and needs no key. It answers
refund questions with the refund window only when the system prompt tells it to, which is the dependence a
real model can have on an instruction nobody remembers writing. In a live replay the same loop calls the
model and grades the generative step with the rubric or judge of post 20.
"""

PROMPT_V12 = (
    "You are the support agent for Acme.\n"
    "Always state the refund window: 30 days from delivery.\n"
    "Answer in at most three sentences."
)
# The "cleanup" release: the refund-window line was judged redundant and removed.
PROMPT_V13 = "You are the support agent for Acme.\nAnswer in at most three sentences."

# Fixtures frozen from the trace store: the input, and the route recorded at capture time.
FIXTURES = [
    ("fx-01", "Where is my order 4417?", "orders"),
    ("fx-02", "Can I return the blue kettle?", "refunds"),
    ("fx-03", "Change my delivery address, please.", "orders"),
    ("fx-04", "Why was I charged twice?", "billing"),
    ("fx-05", "How do I get a refund for a broken lamp?", "refunds"),
    ("fx-06", "Do you ship to Canada?", "orders"),
    ("fx-07", "I want my money back for the chair.", "refunds"),
    ("fx-08", "Update the card on my account.", "billing"),
]


def route(question):
    """The deterministic router: checked exactly against the recorded route."""
    q = question.lower()
    if any(w in q for w in ("refund", "return", "money back")):
        return "refunds"
    if any(w in q for w in ("charged", "card", "invoice")):
        return "billing"
    return "orders"


def stand_in_model(system, question):
    """A deterministic stand-in for the model call."""
    if route(question) == "refunds":
        answer = "Yes, start the return from the Orders page."
        if "refund window" in system:
            answer += " Refunds are accepted within 30 days from delivery."
        return answer
    return "Here is how to do that from your account page."


def rubric(question, answer):
    """The generative check: a refund answer must state the window."""
    return route(question) != "refunds" or "30 days" in answer


def replay(system):
    route_diffs, failures = [], []
    for fid, question, recorded_route in FIXTURES:
        if route(question) != recorded_route:
            route_diffs.append(fid)
        if not rubric(question, stand_in_model(system, question)):
            failures.append(fid)
    return route_diffs, failures


def main():
    print(f"fixtures frozen from the trace store: {len(FIXTURES)}")
    for name, system in (("v12 (baseline)", PROMPT_V12), ("v13 (cleanup)", PROMPT_V13)):
        route_diffs, failures = replay(system)
        n = len(FIXTURES)
        print(f"prompt {name}: routes match {n - len(route_diffs)}/{n}, "
              f"rubric passes {n - len(failures)}/{n}"
              + (f"; failing {', '.join(failures)}" if failures else ""))
    print("gate: " + ("block v13" if replay(PROMPT_V13)[1] else "pass v13"))


if __name__ == "__main__":
    main()
