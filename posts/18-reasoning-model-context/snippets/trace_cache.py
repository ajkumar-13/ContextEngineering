# trace_cache.py: where the thinking text of one turn lands decides what the next call pays
#
# Run from the series root:  uv run python posts/18-reasoning-model-context/snippets/trace_cache.py
# Standard library only; no network call. Token counts are illustrative; the cache is modelled at block
# granularity, as Anthropic's "Prompt caching" page states the rule (consulted October 2026): a hit needs
# the prompt identical up to a cache breakpoint, and the prefix is built in the order tools, system,
# messages. Prices: Claude Opus 4.6 (as of early 2026), Anthropic "Pricing", consulted October 2026.

RATE_IN, RATE_OUT = 5.00, 25.00   # dollars per million tokens
CACHE_READ, CACHE_WRITE = 0.1, 1.25  # multipliers of the base input price (five-minute lifetime)
TRACE = 2000                      # tokens of returned thinking text an application might copy (illustrative)

# Post 04's agent, in the order the API builds the prefix: tools (layer 02), system (layer 01), messages.
BASE = [
    ("02 Tools and MCP descriptions", 1600, "tools"),
    ("01 System prompt", 3000, "system"),
    ("03 Memory and state", 1200, "memory, turn 2"),
    ("04 Retrieved chunks", 2500, "chunks, turn 2"),
    ("05 Conversation history", 2000, "history to turn 1"),
    ("06 User instruction", 200, "question, turn 2"),
]
BREAKPOINTS = 2  # cache breakpoints after the tools and after the system prompt


def with_trace(layer):
    """Turn 2's request with turn 1's thinking text copied into one layer (None: copied nowhere)."""
    out = []
    for name, tokens, content in BASE:
        if name[:2] == layer:
            out.append((name, tokens + TRACE, content + " + turn 1 thinking"))
        else:
            out.append((name, tokens, content))
    return out


def price_prefix(previous, request):
    """Split the request's input tokens into read, written and full-price tokens.

    The first BREAKPOINTS blocks are the cached prefix. A block is read from the cache only if it and
    every block before it are identical to the previous request's; a prefix block after the first
    difference is written to the cache again; the blocks after the prefix pay the base price.
    """
    read = written = full = 0
    same = True
    for i, (block, prev) in enumerate(zip(request, previous)):
        same = same and block == prev
        tokens = block[1]
        if i < BREAKPOINTS:
            if same:
                read += tokens
            else:
                written += tokens
        else:
            full += tokens
    cost = (read * CACHE_READ + written * CACHE_WRITE + full) * RATE_IN / 1e6
    return read, written, full, cost


# One tool-use turn with interleaved thinking: each step returns a thinking block and a tool call, the
# application sends the tool result, and the next request repeats everything before it unchanged.
STEPS = [  # (thinking tokens, tool-call tokens, tool-result tokens); the last step answers instead
    (1200, 100, 800),
    (900, 100, 600),
    (700, 400, 0),  # final step: 700 thinking tokens and a 400-token answer
]


def tool_turn():
    """Input of each request in the turn, with the part a cache breakpoint on the last block can reuse."""
    rows = []
    request = sum(t for _, t, _ in BASE)   # request 1: the turn's input, layers 01 to 06
    reusable = BASE[0][1] + BASE[1][1]     # the stable prefix, cached by earlier turns
    for thinking, call, result in STEPS:
        rows.append((request, reusable, request - reusable))
        reusable = request                 # the whole request is now cached ...
        request += thinking + call + result  # ... and the next one appends to it, blocks unchanged
    return rows


def main():
    print(f"next call's input, Claude Opus 4.6, {TRACE} tokens of turn 1 thinking text, illustrative sizes")
    print("where the thinking text goes          read 0.1x  written 1.25x  full price  input $")
    cases = [
        ("copied nowhere", None),
        ("appended to layer 06", "06"),
        ("saved to memory, back in layer 03", "03"),
        ("spliced into layer 01", "01"),
    ]
    previous = with_trace(None)
    for label, layer in cases:
        read, written, full, cost = price_prefix(previous, with_trace(layer))
        print(f"{label:<37}{read:>10}{written:>15}{full:>12}{cost:>9.5f}")
    print()
    print("one tool-use turn, three requests, thinking blocks passed back unchanged")
    print("request  input tokens  read from cache    new")
    rows = tool_turn()
    for k, (request, reusable, new) in enumerate(rows, 1):
        print(f"{k:>7}{request:>14}{reusable:>17}{new:>7}")
    reads = sum(r for _, r, _ in rows)
    news = sum(n for _, _, n in rows)
    total_in = sum(q for q, _, _ in rows)
    thinking = sum(t for t, _, _ in STEPS)
    output = sum(t + c for t, c, _ in STEPS)
    cached = (reads * CACHE_READ + news * CACHE_WRITE) * RATE_IN / 1e6
    print(f"input over the turn: {total_in} tokens; cached {cached:.5f}, uncached {total_in * RATE_IN / 1e6:.5f}")
    print(f"output over the turn: {output} tokens, of which thinking {thinking} in {len(STEPS)} segments"
          f" ({thinking / output:.1%}); {output * RATE_OUT / 1e6:.5f}")


if __name__ == "__main__":
    main()
