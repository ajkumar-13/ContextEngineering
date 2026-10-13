"""A minimal tracer and trace store for one agent turn, standard library only.

Run from the series root:  uv run python posts/22-observability/snippets/trace_store.py

Offline: the turn is simulated with a fake clock and illustrative token counts, so the run makes no model call
and prints the same numbers every time. Rates are Anthropic's "Pricing" page as of early 2026, as post 05
quotes them; the cache multipliers are Anthropic's "Prompt caching" page (consulted October 2026). The
attribute names follow the OpenTelemetry GenAI semantic conventions (status: Development, consulted October 2026).
"""
import json
from contextlib import contextmanager

RATES = {  # dollars per million tokens, as of early 2026
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
}
CACHE_WRITE_5M = 1.25  # a five-minute cache write costs 1.25 times the base input price
CACHE_READ = 0.1       # a cache read costs 0.1 times the base input price (most models)


class Clock:
    """A fake clock in milliseconds, so the run is deterministic."""

    def __init__(self):
        self.now = 0

    def advance(self, ms):
        self.now += ms


class Tracer:
    """Records nested spans; every finished trace goes into the trace store."""

    def __init__(self, clock):
        self.clock = clock
        self.stack = []
        self.store = []  # the trace store: one record per finished trace

    @contextmanager
    def span(self, name, **attrs):
        record = {"name": name, "start_ms": self.clock.now, "attrs": dict(attrs), "children": []}
        if self.stack:
            self.stack[-1]["children"].append(record)
        self.stack.append(record)
        try:
            yield record
        finally:
            record["end_ms"] = self.clock.now
            self.stack.pop()
            if not self.stack:
                self.store.append(record)


def record_usage(span, model, usage):
    """Copy a provider usage block onto an LLM span, and price the call.

    usage holds Anthropic's fields. Its input_tokens counts only the tokens after the
    last cache breakpoint, so the total input is the sum of three fields.
    """
    fresh = usage["input_tokens"]
    read = usage.get("cache_read_input_tokens", 0)
    write = usage.get("cache_creation_input_tokens", 0)
    out = usage["output_tokens"]
    rate = RATES[model]
    a = span["attrs"]
    a["gen_ai.request.model"] = model
    a["gen_ai.usage.input_tokens"] = fresh + read + write
    a["gen_ai.usage.cache_read.input_tokens"] = read
    a["gen_ai.usage.cache_write.input_tokens"] = write
    a["gen_ai.usage.output_tokens"] = out
    a["cost_usd"] = (
        fresh * rate["input"]
        + write * rate["input"] * CACHE_WRITE_5M
        + read * rate["input"] * CACHE_READ
        + out * rate["output"]
    ) / 1e6


def traced_anthropic_call(tracer, model, system, messages, max_tokens=512):
    """The live version: one Messages API call inside a span. Needs the anthropic SDK and a key."""
    from anthropic import Anthropic  # imported here so that the offline run needs no SDK

    with tracer.span("llm_call") as s:
        resp = Anthropic().messages.create(
            model=model, max_tokens=max_tokens, system=system, messages=messages,
        )
        u = resp.usage
        record_usage(s, model, {
            "input_tokens": u.input_tokens,
            "cache_read_input_tokens": u.cache_read_input_tokens or 0,
            "cache_creation_input_tokens": u.cache_creation_input_tokens or 0,
            "output_tokens": u.output_tokens,
        })
        s["attrs"]["gen_ai.input.messages"] = messages  # opt-in content capture
        s["attrs"]["gen_ai.output.messages"] = [b.text for b in resp.content if b.type == "text"]
        return resp


# The simulated turn: span name -> milliseconds of its own work (illustrative).
WORK_MS = {
    "load_memory": 30, "select_tools": 10, "query_rewrite": 350, "hybrid_search": 90,
    "rerank": 120, "llm_call": 3800, "issue_refund": 40, "db_query": 60,
}
REWRITE_USAGE = {"input_tokens": 300, "output_tokens": 40}
MAIN_USAGE = {"input_tokens": 5900, "cache_read_input_tokens": 4600,
              "cache_creation_input_tokens": 0, "output_tokens": 400}


def simulate_turn(tracer, clock):
    """One support-agent turn, with the spans section 3 asks for."""
    work = lambda name: clock.advance(WORK_MS[name])  # noqa: E731
    with tracer.span("turn", session_id="session-A1B2", turn=7, release="r42"):
        with tracer.span("assemble_context"):
            with tracer.span("load_memory", rows=3):
                work("load_memory")
            with tracer.span("select_tools", tools=4):
                work("select_tools")
        with tracer.span("retrieve"):
            with tracer.span("query_rewrite") as s:
                work("query_rewrite")
                record_usage(s, "claude-haiku-4-5", REWRITE_USAGE)
            with tracer.span("hybrid_search", top_n=50):
                work("hybrid_search")
            with tracer.span("rerank", top_k=5):
                work("rerank")
        with tracer.span("llm_call") as s:
            work("llm_call")
            record_usage(s, "claude-sonnet-4-5", MAIN_USAGE)
            s["attrs"]["gen_ai.input.messages"] = "[the full prompt: layers 01 to 06]"
            s["attrs"]["gen_ai.output.messages"] = "[the full response]"
        with tracer.span("tool_call", tool="issue_refund"):
            work("issue_refund")
            with tracer.span("db_query"):
                work("db_query")


def walk(record, depth=0):
    yield depth, record
    for child in record["children"]:
        yield from walk(child, depth + 1)


def total_cost(record):
    return sum(r["attrs"].get("cost_usd", 0.0) for _, r in walk(record))


def print_trace(record):
    for depth, r in walk(record):
        a = r["attrs"]
        name = r["name"] if "tool" not in a else f"{r['name']} {a['tool']}"
        ms = r["end_ms"] - r["start_ms"]
        line = f"{'  ' * depth + name:<24}{ms:>6} ms"
        cost = total_cost(r) if depth == 0 else a.get("cost_usd")
        if cost is not None:
            line += f"  ${cost:.5f}"
        if "gen_ai.request.model" in a:
            line += (f"  {a['gen_ai.request.model']}: in {a['gen_ai.usage.input_tokens']}"
                     f" (cache read {a['gen_ai.usage.cache_read.input_tokens']})"
                     f" out {a['gen_ai.usage.output_tokens']}")
        print(line)


def main():
    clock = Clock()
    tracer = Tracer(clock)
    simulate_turn(tracer, clock)
    trace = tracer.store[0]
    spans = sum(1 for _ in walk(trace))
    print(f"trace store: {len(tracer.store)} trace, {spans} spans")
    print_trace(trace)

    llm = trace["children"][2]
    a = llm["attrs"]
    total, read = a["gen_ai.usage.input_tokens"], a["gen_ai.usage.cache_read.input_tokens"]
    print(f"\ncache-hit rate of llm_call: {read} / {total} = {read / total:.1%}")
    print(f"same rate over Anthropic's input_tokens alone: {read} / {MAIN_USAGE['input_tokens']}"
          f" = {read / MAIN_USAGE['input_tokens']:.1%} (wrong denominator)")
    print("\nllm_call as stored:")
    print(json.dumps({k: v for k, v in a.items()}, indent=1))


if __name__ == "__main__":
    main()
