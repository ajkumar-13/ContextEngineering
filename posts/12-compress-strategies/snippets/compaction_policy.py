# compaction_policy.py: replay one long agent session against a two-trigger compression policy
#
# Run from the series root:  uv run python posts/12-compress-strategies/snippets/compaction_policy.py
# Standard library only; no network call, no model call. Every size below is a constant with its source.

WINDOW = 200_000           # Claude Sonnet 4.5, Anthropic "Context windows" (consulted October 2026), as post 04 cites it
OUTPUT_RESERVE = 20_000    # tokens kept free for the answer through max_tokens (post 04's illustrative reserve)
BUDGET = WINDOW - OUTPUT_RESERVE   # the input budget the triggers are measured against

SOFT, HARD, SOFT_TARGET = 0.80, 0.95, 0.60   # the policy of section 9: illustrative values, not measured ones

# The session (illustrative sizes). Layers 01 and 02 and layers 03 and 04 are the support agent of post 04;
# every turn appends a user message, a reply and one tool result to layer 05, conversation history.
PREFIX = 4_600             # layers 01 and 02, sent unchanged on every call
INJECTION = 3_700          # layers 03 and 04, replaced on every call, so they do not accumulate
MESSAGES = 1_400           # one user message and the agent's reply, per turn
TOOL_SIZES = [6_000, 1_500, 9_000, 800, 3_500]   # tool results, repeating in this order
TURNS = 110

STUB = 60                  # a cleared tool result keeps a one-line note of what it found
KEEP_RECENT = 3            # the last three turns are never cleared or summarised
SUMMARY = 3_000            # the running summary that replaces the older turns at the hard trigger


def run(policy, trace=None):
    """Replay the session. policy is "none", "summarise-only" or "two-trigger".

    Returns one row per turn: (turn, usage before compression, usage after, event). A list passed as trace
    receives (turn, split before, split after) for every turn with an event; a split is the input in tokens as
    (layers 01-02, layers 03-04, layer 05 messages, summary and notes, layer 05 tool results kept verbatim).
    """
    turns, summary, rows = [], 0, []
    for t in range(1, TURNS + 1):
        turns.append({"messages": MESSAGES, "tool": TOOL_SIZES[(t - 1) % len(TOOL_SIZES)]})

        def usage():
            history = summary + sum(x["messages"] + x["tool"] for x in turns)
            return (PREFIX + INJECTION + history) / BUDGET

        def split():
            tools = sum(x["tool"] for x in turns if x["tool"] > STUB)
            rest = summary + sum(x["messages"] + x["tool"] for x in turns) - tools
            return (PREFIX, INJECTION, rest, tools)

        before, event, split_before = usage(), "", split()
        if policy != "none" and before >= HARD:
            # hard trigger: fold everything but the recent turns into the summary (one model call)
            turns, summary, event = turns[-KEEP_RECENT:], SUMMARY, "hard"
        elif policy == "two-trigger" and before >= SOFT:
            # soft trigger: clear the stale tool results, oldest first, until usage is under the target
            for x in turns[:-KEEP_RECENT]:
                if usage() < SOFT_TARGET:
                    break
                if x["tool"] > STUB:
                    x["tool"], event = STUB, "soft"
        rows.append((t, before, usage(), event))
        if event and trace is not None:
            trace.append((t, split_before, split()))
    return rows


def main():
    print(f"window {WINDOW}, output reserve {OUTPUT_RESERVE}, input budget {BUDGET}")
    print(f"triggers: soft {SOFT:.0%}, hard {HARD:.0%}, soft target {SOFT_TARGET:.0%}; {TURNS} turns")
    print()
    for policy in ("none", "summarise-only", "two-trigger"):
        rows = run(policy)
        over = [t for t, before, after, e in rows if after > 1.0]
        soft = [t for t, *_, e in rows if e == "soft"]
        hard = [t for t, *_, e in rows if e == "hard"]
        print(f"{policy:<15} first over budget: {over[0] if over else '-':>3}   "
              f"soft passes: {len(soft):>2}   summaries: {len(hard)} at turns {hard}")
    print()
    rows = run("two-trigger")
    reached = [t for t, _, after, e in rows if e == "soft" and after < SOFT_TARGET]
    missed = [(t, b, a) for t, b, a, e in rows if e == "soft" and a >= SOFT_TARGET]
    print("two-trigger policy, usage of the input budget before -> after")
    print(f"  soft passes that reached {SOFT_TARGET:.0%}: turns {reached}")
    t, b, a = missed[0]
    print(f"  first soft pass that did not: turn {t} ({b:.1%} -> {a:.1%})")
    for t, b, a, e in rows:
        if e == "hard":
            print(f"  summary: turn {t} ({b:.1%} -> {a:.1%})")


if __name__ == "__main__":
    main()
