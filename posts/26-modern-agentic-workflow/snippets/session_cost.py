"""The cost of one long agent session, with and without compaction (post 26, section 7).

Run from the series root:  uv run python posts/26-modern-agentic-workflow/snippets/session_cost.py

Every size is illustrative: a stable prefix (layers 01 and 02: the host's preamble, AGENTS.md, the tool
schemas and the skill descriptions), and a loop in which each model call writes a tool call and gets back a
tool result, both appended to layer 05. Every call re-reads the whole window. Prices are Claude Opus 4.6's as
of early 2026 (Anthropic, "Pricing", consulted October 2026, as post 05 states them): 5 dollars per million
input tokens, 25 per million output tokens, a cache write at 1.25 times the input price and a cache read at
0.1 times. The cached columns assume every call arrives within the cache lifetime.
"""

PREFIX = 18_000       # layers 01 and 02, tokens
TOOL_CALL = 300       # tokens the model writes per call (appended to the history)
RESULT = 2_200        # tokens of tool result per call (appended to the history)
CALLS = 120           # model calls in the session
LIMIT = 100_000       # compact when the window would pass this many tokens
SUMMARY = 5_000       # tokens of the summary that replaces the history

IN, OUT = 5 / 1e6, 25 / 1e6          # dollars per token, Claude Opus 4.6
WRITE, READ = 1.25 * IN, 0.1 * IN    # cache write (five-minute lifetime) and cache read


def run(limit=None):
    """Replay the session. Return the window at each call and the totals."""
    windows, tokens_in, tokens_out = [], 0, 0
    uncached = cached = 0.0
    window, cached_part, compactions = PREFIX, 0, 0
    for _ in range(CALLS):
        if limit is not None and window + TOOL_CALL + RESULT > limit:
            # One compaction call reads the window and writes the summary, which replaces the history.
            tokens_in += window
            tokens_out += SUMMARY
            uncached += window * IN + SUMMARY * OUT
            cached += cached_part * READ + (window - cached_part) * WRITE + SUMMARY * OUT
            window, cached_part, compactions = PREFIX + SUMMARY, PREFIX, compactions + 1
        windows.append(window)
        tokens_in += window
        tokens_out += TOOL_CALL
        uncached += window * IN + TOOL_CALL * OUT
        cached += cached_part * READ + (window - cached_part) * WRITE + TOOL_CALL * OUT
        cached_part = window                    # this call's prompt is now cached
        window += TOOL_CALL + RESULT            # the next call re-reads all of it
    return dict(windows=windows, tokens_in=tokens_in, tokens_out=tokens_out, peak=max(windows),
                compactions=compactions, uncached=uncached, cached=cached)


def main():
    plain, compact = run(), run(LIMIT)
    print(f"illustrative session: {CALLS} calls, prefix {PREFIX} tokens, +{TOOL_CALL + RESULT} tokens per call")
    print("prices: Claude Opus 4.6, 5 and 25 dollars per million, cache write 1.25x, cache read 0.1x")
    print(f"{'':22}{'input tokens':>14}{'peak window':>13}{'compactions':>13}{'uncached $':>12}{'cached $':>10}")
    for name, r in (("no compaction", plain), (f"compact at {LIMIT}", compact)):
        print(f"{name:22}{r['tokens_in']:>14}{r['peak']:>13}{r['compactions']:>13}"
              f"{r['uncached']:>12.2f}{r['cached']:>10.2f}")
    print(f"no compaction reads {plain['tokens_in'] / compact['tokens_in']:.1f} times the input tokens "
          f"and costs {plain['cached'] / compact['cached']:.1f} times as much with caching")


if __name__ == "__main__":
    main()
