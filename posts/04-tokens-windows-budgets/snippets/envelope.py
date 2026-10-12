# envelope.py: size the customer-support agent of post 04 on an envelope
#
# Token counts per layer are illustrative. Rates are Anthropic's published prices as of early
# 2026 (Anthropic, "Pricing"): Claude Sonnet 4.5 at $3 / $15 and Claude Haiku 4.5 at $1 / $5
# per million input / output tokens, with a cache read at 0.1 times the base input price.
# The latency rates further down are illustrative, not measured.

LAYERS = {
    "01 System prompt": 3000,
    "02 Tools and MCP descriptions": 1600,
    "03 Memory and state": 1200,
    "04 Retrieved chunks": 2500,
    "05 Conversation history": 2000,
    "06 User instruction": 200,
}
OUT_TOKENS = 400
PREFIX = 3000 + 1600  # layers 01 and 02, identical on every call

SONNET = {"price_in": 3.00, "price_out": 15.00}  # $ per 1M tokens, as of early 2026
HAIKU = {"price_in": 1.00, "price_out": 5.00}

CALLS_PER_DAY = 10_000 * 4 * 5  # conversations x turns x calls per turn (illustrative)
CHEAP_SHARE = 0.60  # share of calls simple enough for the cheap tier (illustrative)

# Starting shares of the input budget per layer, in percent (section 6; illustrative defaults).
DEFAULT_SHARES = {
    "01 System prompt": (5, 15),
    "02 Tools and MCP descriptions": (5, 15),
    "03 Memory and state": (5, 10),
    "04 Retrieved chunks": (20, 40),
    "05 Conversation history": (10, 30),
    "06 User instruction": (1, 5),
}

# Illustrative latency rates in milliseconds per token: (prefill, decode).
LATENCY_MS = {"cheap": (0.1, 8.0), "mid": (0.2, 16.0), "frontier": (0.4, 32.0)}


def call_cost(layers, price_in, price_out, out_tokens,
              cached_prefix=0, cache_read=0.10):
    """Cost of one LLM call in dollars.
    layers: {name: input_tokens}; price_* in $ per 1M tokens;
    cached_prefix: leading tokens billed at cache_read x price_in."""
    total_in = sum(layers.values())
    billable_in = total_in - cached_prefix
    return (cached_prefix / 1e6 * price_in * cache_read
            + billable_in / 1e6 * price_in
            + out_tokens / 1e6 * price_out)


def wall_time(in_tokens, out_tokens, prefill_ms, decode_ms):
    """Seconds for one call: prefill of the whole prompt, then one decode step per output token."""
    return (in_tokens * prefill_ms + out_tokens * decode_ms) / 1000


def main() -> None:
    total_in = sum(LAYERS.values())
    print("layer                            tokens  share  default")
    for name, n in LAYERS.items():
        lo, hi = DEFAULT_SHARES[name]
        share = 100 * n / total_in
        flag = "" if lo <= share <= hi else "  outside"
        print(f"  {name:30} {n:6d}  {share:4.1f}%  {lo}-{hi}%{flag}")
    print(f"  {'input total':30} {total_in:6d}")
    print(f"  {'output':30} {OUT_TOKENS:6d}")

    per_call = call_cost(LAYERS, **SONNET, out_tokens=OUT_TOKENS)
    cached = call_cost(LAYERS, **SONNET, out_tokens=OUT_TOKENS, cached_prefix=PREFIX)
    cheap = call_cost(LAYERS, **HAIKU, out_tokens=OUT_TOKENS, cached_prefix=PREFIX)
    routed = (1 - CHEAP_SHARE) * cached + CHEAP_SHARE * cheap

    print(f"\ncalls per day: {CALLS_PER_DAY}")
    print("                         per call    per day   per 30 days")
    for label, c in [("uncached, Sonnet 4.5", per_call), ("cached prefix", cached),
                     ("cached, Haiku 4.5", cheap), ("routed 60% to Haiku", routed)]:
        print(f"  {label:22} {c:9.5f} {c * CALLS_PER_DAY:10.2f} {c * CALLS_PER_DAY * 30:12.2f}")
    print(f"\ncaching saves {100 * (1 - cached / per_call):.1f}% of the uncached bill")
    print(f"caching plus routing is {per_call / routed:.2f} times cheaper than the uncached bill")

    print(f"\nlatency of one call ({total_in} in, {OUT_TOKENS} out), illustrative rates:")
    print("  class      prefill ms/tok  decode ms/tok  prefill s  decode s  total s")
    for cls, (p, d) in LATENCY_MS.items():
        t_pre, t_dec = total_in * p / 1000, OUT_TOKENS * d / 1000
        print(f"  {cls:9} {p:14.1f} {d:14.1f} {t_pre:10.2f} {t_dec:9.2f} {wall_time(total_in, OUT_TOKENS, p, d):8.2f}")
    p, d = LATENCY_MS["mid"]
    print(f"  prefill and decode take equal time when the prompt is {d / p:.0f} times the output")


if __name__ == "__main__":
    main()
