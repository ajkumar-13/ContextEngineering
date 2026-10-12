"""Post 08: the read, act, write lifecycle of a task.md scratchpad.

Run from the series root:  uv run python posts/08-write-strategies/snippets/task_scratchpad.py
Standard library only; no network, no model call. The "act" step is stubbed: each iteration's
finding is fixed in ITERATIONS, standing in for what the agent's tool calls returned.
"""

FRESH = """# Task: add rate limiting to the /login endpoint

## Plan
- [ ] Find where /login is defined
- [ ] Add a token-bucket limiter (5 attempts / 15 min / IP)
- [ ] Return 429 with a Retry-After header
- [ ] Add a test for the limit and the reset

## Notes
(empty)
"""

# what two iterations of tool calls found: (result for the plan item, note for later iterations)
ITERATIONS = [
    ("routes/auth.py:42",
     "Existing middleware stack is in app/middleware.py; add the limiter there, not in the route, "
     "so it also covers /login/mfa."),
    (None,
     "Redis is already a dependency: use it for the bucket, not in-process state."),
]


def first_open_item(text: str) -> str | None:
    """Read: recover the state and return the first unchecked plan item."""
    for line in text.splitlines():
        if line.startswith("- [ ] "):
            return line
    return None


def write_back(text: str, item: str, result: str | None, note: str) -> str:
    """Write: tick the item (with its result) and append the note the next iteration needs."""
    done = item.replace("- [ ] ", "- [x] ", 1) + (f" ({result})" if result else "")
    text = text.replace(item, done, 1)
    return text.replace("(empty)\n", "") + f"- {note}\n"


def main() -> None:
    text = FRESH
    print(text)
    for result, note in ITERATIONS:
        item = first_open_item(text)          # read
        # act: the agent's tool calls happen here; their outcome is (result, note)
        text = write_back(text, item, result, note)   # write
    print("--- after two iterations ---\n")
    print(text)
    print("next item:", first_open_item(text))


if __name__ == "__main__":
    main()
