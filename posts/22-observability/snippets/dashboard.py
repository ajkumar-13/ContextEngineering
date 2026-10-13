"""The headline dashboard numbers over two weeks of synthetic sessions, standard library only.

Run from the series root:  uv run python posts/22-observability/snippets/dashboard.py

The traffic is synthetic and illustrative (seeded, so every run prints the same numbers): most sessions take
the normal path, and a share take a slow path, an uncached prefix plus a retry. In week B a deploy sends more
sessions down the slow path. Quality is not simulated: it comes from the evaluation harness of post 20.
"""
import math
import random
import statistics

SESSIONS = 1000
SLOW_SHARE = {"week A": 0.02, "week B": 0.08}       # illustrative
ERROR_RATE = {"tool_error": 0.010, "schema_invalid": 0.004, "refusal": 0.003}  # per session, illustrative
TIMEOUT_IF_SLOW = 0.25                               # a slow session times out a quarter of the time


def p95(values):
    """Nearest-rank 95th percentile: the smallest value at or above 95% of the sample."""
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def week(rng, slow_share):
    latency, cost, errors = [], [], dict.fromkeys([*ERROR_RATE, "timeout"], 0)
    for _ in range(SESSIONS):
        slow = rng.random() < slow_share
        seconds = max(1.0, rng.gauss(4.5, 0.6)) + (7.0 if slow else 0.0)
        dollars = 0.10 * rng.lognormvariate(0.0, 0.3) * (1.8 if slow else 1.0)
        latency.append(seconds)
        cost.append(dollars)
        for kind, rate in ERROR_RATE.items():
            errors[kind] += rng.random() < rate
        errors["timeout"] += slow and rng.random() < TIMEOUT_IF_SLOW
    return latency, cost, errors


def main():
    rng = random.Random(22)
    rows = {name: week(rng, share) for name, share in SLOW_SHARE.items()}
    print(f"{SESSIONS} synthetic sessions per week; slow-path share: "
          + ", ".join(f"{k} {v:.0%}" for k, v in SLOW_SHARE.items()))
    print(f"\n{'':24}{'week A':>10}{'week B':>10}")
    stats = [
        ("latency mean, s", lambda lat, cost: statistics.mean(lat), ".2f"),
        ("latency median, s", lambda lat, cost: statistics.median(lat), ".2f"),
        ("latency p95, s", lambda lat, cost: p95(lat), ".2f"),
        ("cost per session median", lambda lat, cost: statistics.median(cost), ".3f"),
        ("cost per session p95", lambda lat, cost: p95(cost), ".3f"),
    ]
    for label, fn, fmt in stats:
        a, b = (fn(lat, cost) for lat, cost, _ in rows.values())
        print(f"{label:<24}{a:>10{fmt}}{b:>10{fmt}}")
    print("errors per 1000 sessions, by kind:")
    for kind in rows["week A"][2]:
        a, b = (errs[kind] for _, _, errs in rows.values())
        print(f"  {kind:<22}{a:>10}{b:>10}")


if __name__ == "__main__":
    main()
