"""Post 27: what a remote agent costs a month, server against model.

Run from the series root:  uv run python posts/27-remote-agentic-workflow/snippets/remote_costs.py
Standard library only; no network, no model, no API key.

Cited values, all consulted October 2026:
- EC2 On-Demand hourly rates, Linux, US East (N. Virginia): AWS, "Amazon EC2 On-Demand Pricing".
- Data transfer out of EC2 to the internet: the first 100 GB a month free (aggregated across services and
  Regions), then 0.09 dollars per GB for the first 10 TB in US East (N. Virginia): the same AWS page.
- Hetzner CPX31 (4 shared vCPUs, 8 GB, US locations Ashburn and Hillsboro): 73.49 dollars a month, excluding
  VAT and the IPv4 address, for orders from 15 June 2026: Hetzner, "Price adjustment".
- Claude Opus 4.6: 5 dollars per million input tokens and 25 per million output tokens, as of early 2026; a
  five-minute cache write at 1.25 times and a cache read at 0.1 times the base input price, the rate for most
  models: Anthropic, "Pricing" and "Prompt caching" (post 05).
Every value marked ILLUSTRATIVE is a round number chosen for the arithmetic, not a measurement.
"""
EC2 = {                          # instance: (vCPUs, GiB of memory, dollars per hour), cited
    "c6i.large": (2, 4, 0.085),
    "c6i.xlarge": (4, 8, 0.17),
    "c6i.2xlarge": (8, 16, 0.34),
    "c6i.4xlarge": (16, 32, 0.68),
}
MONTH_H = 24 * 365 / 12          # 730 hours: a server left running all month
WORK_H = 8 * 22                  # ILLUSTRATIVE: 8 hours a day on 22 working days, stopped otherwise
HETZNER_CPX31 = 73.49            # dollars a month, cited
EGRESS_FREE_GB, EGRESS_RATE = 100, 0.09   # cited
EGRESS_GB = 20                   # ILLUSTRATIVE: a month of agent traffic out to the internet

IN, OUT = 5.00, 25.00            # dollars per million tokens, Claude Opus 4.6 (cited)
WRITE, READ = 1.25, 0.10         # cache multipliers on the input price (cited)
CALLS = 64                       # ILLUSTRATIVE: model calls in one thirty-minute agent task
CALL_IN, CALL_OUT = 50_000, 1_000  # ILLUSTRATIVE: input and output tokens of one call
CACHED = 0.90                    # ILLUSTRATIVE: share of each call's input read from the cache
TASK_H = 0.5                     # the task's thirty minutes
TASKS = 4 * 22                   # ILLUSTRATIVE: four such tasks a day on 22 working days


def dollars(tokens, rate, factor=1.0):
    return tokens * rate * factor / 1e6


def task_cost(cache):
    """The model bill of one task: input uncached, or 90% read from the cache and the rest written to it."""
    out = CALLS * dollars(CALL_OUT, OUT)
    if not cache:
        return CALLS * dollars(CALL_IN, IN), 0.0, out
    read = CALLS * dollars(CALL_IN * CACHED, IN, READ)
    write = CALLS * dollars(CALL_IN * (1 - CACHED), IN, WRITE)
    return read, write, out


def egress(gb):
    return max(0, gb - EGRESS_FREE_GB) * EGRESS_RATE


if __name__ == "__main__":
    print("EC2 On-Demand, Linux, US East (N. Virginia), consulted October 2026")
    for name, (cpu, mem, rate) in EC2.items():
        print(f"  {name:<12} {cpu:>2} vCPU {mem:>3} GiB  {rate:.3f} $/h  {rate * MONTH_H:7.2f} $ a {MONTH_H:.0f}-hour month")
    xl = EC2["c6i.xlarge"][2]
    print(f"  c6i.xlarge stopped outside working hours, {WORK_H} h a month: {xl * WORK_H:.2f} $")
    print(f"Hetzner CPX31, 4 vCPU, 8 GB, US, from 15 June 2026: {HETZNER_CPX31:.2f} $ a month "
          f"(c6i.xlarge all month: {xl * MONTH_H:.2f})")
    print(f"egress: {EGRESS_GB} GB a month costs {egress(EGRESS_GB):.2f} $; 150 GB would cost {egress(150):.2f} $")
    print()
    print(f"one thirty-minute task, Claude Opus 4.6: {CALLS} calls of {CALL_IN:,} tokens in and {CALL_OUT:,} out")
    i, _, o = task_cost(cache=False)
    print(f"  {'uncached':<24} input {i:.2f} + output {o:.2f} = {i + o:.2f} $")
    r, w, o = task_cost(cache=True)
    task = r + w + o
    print(f"  {f'{CACHED:.0%} read from the cache':<24} read {r:.2f} + write {w:.2f} + output {o:.2f} = {task:.2f} $")
    server = xl * TASK_H
    print(f"  c6i.xlarge for the same half hour: {server:.3f} $; the model costs {task / server:.0f} times as much")
    print()
    print(f"a month of {TASKS} such tasks: model {TASKS * task:.2f} $, against the server "
          f"{xl * MONTH_H:.2f} (all month) or {xl * WORK_H:.2f} (working hours)")
