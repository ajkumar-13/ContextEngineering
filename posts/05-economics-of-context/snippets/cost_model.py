# cost_model.py: price one agent turn at three tiers, with and without prompt caching
#
# Run from the series root:  uv run python posts/05-economics-of-context/snippets/cost_model.py
# Standard library only; no network call. Every price is a constant below with its source.

# Dollars per million tokens. Anthropic, "Pricing" (platform.claude.com/docs/en/about-claude/pricing),
# consulted 12 October 2026. These are the series' running models as of early 2026.
RATES = {
    "Claude Opus 4.6": {"input": 5.00, "output": 25.00},
    "Claude Sonnet 4.5": {"input": 3.00, "output": 15.00},
    "Claude Haiku 4.5": {"input": 1.00, "output": 5.00},
}

# Multipliers of the base input price. Anthropic, "Prompt caching", consulted 12 October 2026:
# writes are 1.25x (five-minute lifetime) or 2x (one-hour); a cache read is 0.1x for these three
# models (the page lists lower read multipliers for some newer models).
CACHE_WRITE_5M = 1.25
CACHE_WRITE_1H = 2.0
CACHE_READ = 0.1

# One turn of the customer-support agent sized in post 04 (illustrative token counts).
LAYERS = [
    (1, "System prompt", 3000),
    (2, "Tools and MCP descriptions", 1600),
    (3, "Memory and state", 1200),
    (4, "Retrieved chunks", 2500),
    (5, "Conversation history", 2000),
    (6, "User instruction", 200),
]
OUTPUT_TOKENS = 400
PREFIX = sum(t for n, _, t in LAYERS if n <= 2)  # layers 01 and 02: identical on every call
REST = sum(t for n, _, t in LAYERS if n >= 3)  # layers 03 to 06: new on every call


def call_cost(rate, prefix, rest, output, prefix_mode="none"):
    """Dollar cost of one call, split into its parts.

    rate: {"input": $/M, "output": $/M}; prefix: tokens of the cacheable prefix;
    rest: input tokens after it; prefix_mode: "none" (no caching), "write" (a
    five-minute cache write) or "read" (a cache hit).
    """
    factor = {"none": 1.0, "write": CACHE_WRITE_5M, "read": CACHE_READ}[prefix_mode]
    parts = {
        "prefix": prefix * rate["input"] * factor / 1e6,
        "rest": rest * rate["input"] / 1e6,
        "output": output * rate["output"] / 1e6,
    }
    parts["total"] = sum(parts.values())
    return parts


def prefix_cost_over_calls(rate, prefix, calls, write, lapsed=False):
    """Cumulative cost of the prefix alone over a run of calls: one write, then reads.

    write is the write multiplier (CACHE_WRITE_5M or CACHE_WRITE_1H), or None for no caching;
    lapsed=True means the cache expires between calls, so every call writes it again.
    """
    full = prefix * rate["input"] / 1e6
    if write is None:
        return [full * n for n in range(1, calls + 1)]
    if lapsed:
        return [full * write * n for n in range(1, calls + 1)]
    return [full * (write + CACHE_READ * (n - 1)) for n in range(1, calls + 1)]


def main():
    print(f"input per call: {PREFIX + REST} tokens "
          f"(prefix 01-02: {PREFIX}, layers 03-06: {REST}); output: {OUTPUT_TOKENS}")
    print()
    print("cost of one call, dollars")
    print(f"{'model':<18} {'no caching':>11} {'cache write':>12} {'cache read':>11} {'saving':>7}")
    for model, rate in RATES.items():
        none, write, read = (call_cost(rate, PREFIX, REST, OUTPUT_TOKENS, m)["total"]
                             for m in ("none", "write", "read"))
        print(f"{model:<18} {none:>11.5f} {write:>12.5f} {read:>11.5f} {1 - read / none:>7.1%}")
    print()

    sonnet = RATES["Claude Sonnet 4.5"]
    for mode in ("none", "write", "read"):
        p = call_cost(sonnet, PREFIX, REST, OUTPUT_TOKENS, mode)
        print(f"Sonnet 4.5, {mode:<5}: prefix {p['prefix']:.5f} + layers 03-06 {p['rest']:.5f}"
              f" + output {p['output']:.5f} = {p['total']:.5f}")
    print(f"cache-hit rate of a warm call: {PREFIX} / {PREFIX + REST} = {PREFIX / (PREFIX + REST):.1%}")
    print()

    calls = 10_000 * 4 * 5  # conversations a day x turns each x model calls per turn
    none = call_cost(sonnet, PREFIX, REST, OUTPUT_TOKENS, "none")["total"]
    first = call_cost(sonnet, PREFIX, REST, OUTPUT_TOKENS, "write")["total"]
    read = call_cost(sonnet, PREFIX, REST, OUTPUT_TOKENS, "read")["total"]
    cached_day = first + (calls - 1) * read  # one write, then every call reads the warm prefix
    print(f"Sonnet 4.5, {calls} calls a day: no caching {none * calls:.2f}, "
          f"cached {cached_day:.2f}, difference {none * calls - cached_day:.2f}")
    print()

    print("Sonnet 4.5, cumulative prefix cost over calls 1 to 5, dollars")
    for label, write, lapsed in (("no caching", None, False), ("5-minute", CACHE_WRITE_5M, False),
                                 ("1-hour", CACHE_WRITE_1H, False), ("lapsed", CACHE_WRITE_5M, True)):
        run = prefix_cost_over_calls(sonnet, PREFIX, 5, write, lapsed)
        print(f"  {label:<10} " + "  ".join(f"{v:.5f}" for v in run))
    print()

    for tokens_in, tokens_out in ((2000, 2500), (12000, 200)):
        p = call_cost(sonnet, 0, tokens_in, tokens_out)
        print(f"Sonnet 4.5, {tokens_in} in + {tokens_out} out: "
              f"{p['rest']:.5f} + {p['output']:.5f} = {p['total']:.5f}")


if __name__ == "__main__":
    main()
