"""Post 25: what one workload costs a day, and how long the first token waits, under long context, RAG and a hybrid.

Run from the series root:  uv run python posts/25-long-context-vs-rag/snippets/cost_latency.py
Standard library only; no network, no model, no API key.

Cited values: Claude Opus 4.6 at 5 dollars per million input tokens and 25 per million output tokens, as of
early 2026, billed at the same per-token rate across its whole 1M-token window; a five-minute cache write at
1.25 times and a cache read at 0.1 times the base input price (Anthropic, "Pricing" and "Prompt caching",
consulted October 2026; post 05). The prefill and decode rates are post 04's illustrative frontier-class rates.
Every value marked ILLUSTRATIVE is a round number chosen for the arithmetic, not a measurement.
"""
IN, OUT = 5.00, 25.00             # dollars per million tokens, Claude Opus 4.6 (cited)
WRITE, READ = 1.25, 0.10          # cache multipliers on the input price (cited)
WINDOW = 1_000_000                # Claude Opus 4.6 context window in tokens (cited, post 04)

RESERVE = 0.30                    # ILLUSTRATIVE: share of the window kept for prompt, history and output
CORPUS = 200_000                  # ILLUSTRATIVE: corpus tokens, loaded whole on the long-context route
QUESTION, ANSWER = 100, 500       # ILLUSTRATIVE: tokens of layer 06 and of the answer, on every route
RAG_IN = 5_000                    # ILLUSTRATIVE: input tokens of a RAG call (system prompt, top-k chunks, question)
RETRIEVAL = 0.001                 # ILLUSTRATIVE: dollars per query for the embedding call and the reranker
QUERIES = 1_000                   # ILLUSTRATIVE: queries a day
WRITES = 10                       # ILLUSTRATIVE: cache writes a day, one after each quiet spell over five minutes
LONG_SHARE = 0.10                 # ILLUSTRATIVE: share of queries the hybrid sends to the long-context route
PREFILL_MS, DECODE_MS = 0.4, 32.0  # ILLUSTRATIVE: post 04's frontier-class milliseconds per token


def dollars(tokens, rate, factor=1.0):
    return tokens * rate * factor / 1e6


def long_call(cache):
    """One long-context call: the corpus sent in full, written to the cache, or read from it."""
    factor = {"none": 1.0, "write": WRITE, "read": READ}[cache]
    corpus = dollars(CORPUS, IN, factor)
    rest = dollars(QUESTION, IN) + dollars(ANSWER, OUT)
    return corpus, rest


def rag_call():
    return dollars(RAG_IN, IN) + dollars(ANSWER, OUT) + RETRIEVAL


def day(queries, writes):
    """Daily cost of the cached long-context route: paid in full (writes and the rest of each call), read."""
    w_corpus, rest = long_call("write")
    r_corpus, _ = long_call("read")
    full = writes * w_corpus + queries * rest
    cached = (queries - writes) * r_corpus
    return full, cached


if __name__ == "__main__":
    print(f"usable corpus room in a {WINDOW:,}-token window with a {RESERVE:.0%} reserve: "
          f"{round(WINDOW * (1 - RESERVE)):,} tokens")
    print(f"one full-window load of input: {dollars(WINDOW, IN):.2f} dollars")
    print()
    print(f"per query, Claude Opus 4.6 (as of early 2026), {CORPUS:,}-token corpus, illustrative sizes")
    for cache in ("none", "write", "read"):
        corpus, rest = long_call(cache)
        print(f"  long context, {cache:<5}  corpus {corpus:.4f} + rest {rest:.4f} = {corpus + rest:.4f}")
    print(f"  RAG                  {RAG_IN:,} in + {ANSWER} out + retrieval {RETRIEVAL} = {rag_call():.4f}")
    print()
    uncached = QUERIES * sum(long_call("none"))
    full, cached = day(QUERIES, WRITES)
    long_n = round(QUERIES * LONG_SHARE)
    h_full, h_cached = day(long_n, WRITES)
    h_rag = (QUERIES - long_n) * rag_call()
    rag = QUERIES * rag_call()
    print(f"per day, {QUERIES:,} queries, {WRITES} cache writes a day")
    print(f"  A  long context, uncached  {uncached:9.2f}")
    print(f"  A  long context, cached    {full + cached:9.2f}   (paid in full {full:.2f}, read from cache {cached:.2f})")
    print(f"  C  hybrid, {LONG_SHARE:.0%} long        {h_full + h_cached + h_rag:9.2f}   "
          f"(long {h_full + h_cached:.2f}: in full {h_full:.2f}, cache {h_cached:.2f}; RAG {h_rag:.2f})")
    print(f"  B  RAG                     {rag:9.2f}")
    print(f"  against RAG: uncached {uncached / rag:.1f} times, cached {(full + cached) / rag:.1f} times, "
          f"hybrid {(h_full + h_cached + h_rag) / rag:.1f} times")
    print()
    print(f"prefill before the first token, uncached, at {PREFILL_MS} ms a token (illustrative)")
    print(f"  long context  {(CORPUS + QUESTION) * PREFILL_MS / 1000:6.2f} s")
    print(f"  RAG           {RAG_IN * PREFILL_MS / 1000:6.2f} s")
    print(f"  decode of the {ANSWER}-token answer, either route: {ANSWER * DECODE_MS / 1000:.2f} s")
