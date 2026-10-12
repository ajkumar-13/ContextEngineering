# isolation_cost.py: tokens and dollars of one agent against an orchestrator with isolated workers
#
# Run from the series root:  uv run python posts/13-isolate-strategies/snippets/isolation_cost.py
# Standard library only; no network call. Every token size below is illustrative.

# Dollars per million tokens: Claude Sonnet 4.5 as of early 2026. Anthropic, "Pricing"
# (platform.claude.com/docs/en/about-claude/pricing), consulted 12 October 2026.
IN_RATE, OUT_RATE = 3.00, 15.00

N = 5  # independent pieces of work, one per worker
PREAMBLE = 2_000  # system prompt and tool list that every window starts with


def loop(prefix, steps, step_out, result, final_out):
    """Input and output tokens of one agent loop that re-reads its whole window on every call.

    The window starts at prefix tokens. Each of the steps is a model call that writes a step_out-token
    tool call and gets back a result-token tool result; one last call writes final_out tokens.
    """
    calls = steps + 1
    tokens_in = sum(prefix + c * (step_out + result) for c in range(calls))
    tokens_out = steps * step_out + final_out
    return tokens_in, tokens_out


def dollars(tokens_in, tokens_out):
    return (tokens_in * IN_RATE + tokens_out * OUT_RATE) / 1_000_000


def add(*parts):
    return tuple(map(sum, zip(*parts)))


# Case 1, one shot: each piece is an 8,000-token document pasted into the prompt; no tool calls.
# One agent reads all five at once; five workers read one each, and a merge call reads their answers.
one_shot = {
    "one agent": loop(PREAMBLE + N * 8_000, 0, 0, 0, 1_000),
    "orchestrator and workers": add(*[loop(PREAMBLE + 8_000, 0, 0, 0, 1_000)] * N,
                                    loop(PREAMBLE + N * 1_000, 0, 0, 0, 1_000)),
}

# Case 2, an agent loop: each piece needs 4 tool calls (100 tokens each) that return 2,000 tokens each.
# One agent does all 20 calls in one window; each worker does its 4 in its own window and returns a
# 300-token result; the orchestrator's own loop makes 5 delegate calls and gets 5 results back.
looped = {
    "one agent": loop(PREAMBLE, N * 4, 100, 2_000, 1_000),
    "orchestrator and workers": add(*[loop(PREAMBLE, 4, 100, 2_000, 300)] * N,
                                    loop(PREAMBLE, N, 100, 300, 1_000)),
}

if __name__ == "__main__":
    for title, case in (("one shot", one_shot), ("agent loop", looped)):
        print(title)
        for design, (t_in, t_out) in case.items():
            print(f"  {design:25} {t_in:>6} in {t_out:>5} out  {dollars(t_in, t_out):.4f} dollars")
