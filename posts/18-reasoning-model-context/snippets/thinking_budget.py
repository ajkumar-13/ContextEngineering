# thinking_budget.py: one hard agent turn budgeted with a thinking line, at three effort levels
#
# Run from the series root:  uv run python posts/18-reasoning-model-context/snippets/thinking_budget.py
# Standard library only; no network call. Every price is a constant below with its source; every token
# count is illustrative (the thinking a real request spends is read from its usage block, not assumed).

# Claude Opus 4.6, the series' frontier model as of early 2026. Dollars per million tokens: Anthropic,
# "Pricing", consulted October 2026 (as post 05 quotes them). Cache read 0.1x and five-minute write 1.25x
# the base input price: Anthropic, "Prompt caching", consulted October 2026.
RATE = {"input": 5.00, "output": 25.00}
CACHE_READ = 0.1
CACHE_WRITE_5M = 1.25

# The input of one turn: post 04's agent, layer by layer (illustrative token counts).
LAYERS = [
    ("01 System prompt", 3000),
    ("02 Tools and MCP descriptions", 1600),
    ("03 Memory and state", 1200),
    ("04 Retrieved chunks", 2500),
    ("05 Conversation history", 2000),
    ("06 User instruction", 200),
]
PREFIX = sum(t for name, t in LAYERS if name[:2] in ("01", "02"))  # the stable prefix, read from the cache
REST = sum(t for _, t in LAYERS) - PREFIX

# The output of one hard turn. Thinking tokens per effort level are illustrative: Anthropic's pages give
# no counts, and the answer is held at one length so that only the thinking line moves.
ANSWER = 1500
THINKING = {"low": 1000, "medium": 4000, "high": 16000}


def turn_cost(thinking, answer, prefix_mode="read"):
    """Dollar cost of one turn, split into input and output.

    Thinking tokens are billed as output tokens, at the output rate, like the answer.
    prefix_mode: "read" (warm cache) or "write" (the prefix is written again).
    """
    factor = {"read": CACHE_READ, "write": CACHE_WRITE_5M}[prefix_mode]
    cost_in = (PREFIX * factor + REST) * RATE["input"] / 1e6
    cost_out = (thinking + answer) * RATE["output"] / 1e6
    return {"input": cost_in, "output": cost_out, "total": cost_in + cost_out}


def history_after(turns, thinking, answer, keep_thinking=True):
    """Input tokens of turn number `turns` when every earlier turn stays in the history.

    keep_thinking=True: earlier turns' thinking blocks stay in context and count as input
    (the default on Claude Opus 4.6); False: they are omitted, and only the answers remain.
    """
    carried = answer + (thinking if keep_thinking else 0)
    return PREFIX + REST + (turns - 1) * carried


def main():
    print("one hard turn on Claude Opus 4.6, illustrative token counts")
    print(f"input: layers 01-06 = {PREFIX + REST} tokens (prefix 01-02: {PREFIX}, read from the cache)")
    print()
    print("effort  thinking  answer  output  thinking share  input $  output $  total $")
    for level, thinking in THINKING.items():
        c = turn_cost(thinking, ANSWER)
        out = thinking + ANSWER
        print(f"{level:<7}{thinking:>9}{ANSWER:>8}{out:>8}{thinking / out:>15.1%}"
              f"{c['input']:>9.5f}{c['output']:>10.5f}{c['total']:>9.5f}")
    print()
    hi = THINKING["high"]
    lo = turn_cost(THINKING["low"], ANSWER)["total"]
    print(f"high against low effort: {turn_cost(hi, ANSWER)['total'] / lo:.2f} times the cost of the turn")
    print(f"high effort, thinking against the whole input: {hi} against {PREFIX + REST} tokens")
    print()
    print("a top-level effort change between requests restarts the cache (worst case, prefix written again):")
    w = turn_cost(THINKING["medium"], ANSWER, prefix_mode="write")
    r = turn_cost(THINKING["medium"], ANSWER)
    print(f"  medium effort, input with the prefix read: {r['input']:.5f}; written again: {w['input']:.5f}")
    print()
    print("input tokens of turn 5 at high effort, earlier turns kept in the history")
    kept = history_after(5, hi, ANSWER, keep_thinking=True)
    dropped = history_after(5, hi, ANSWER, keep_thinking=False)
    print(f"  thinking blocks kept: {kept}; omitted: {dropped}; difference {kept - dropped}")
    print(f"  at the full input price: {kept * RATE['input'] / 1e6:.5f} against {dropped * RATE['input'] / 1e6:.5f}")


if __name__ == "__main__":
    main()
