# retention.py: token reduction and information retention ratio (IRR) of five compress techniques
#
# Run from the series root:  uv run python posts/12-compress-strategies/snippets/retention.py
# Needs tiktoken (in the root environment, encodings cached); no network call, no model call.
#
# A toy replay set: three conversations (layer 05, conversation history), each with the key facts the next
# turns need. A fact survives a technique when every one of its words is still in the compressed history.
# The summariser is a rule-based stand-in for a model: it keeps what the section 3 prompt asks a summary to
# keep (decisions, open questions, user-stated facts, tool conclusions) and drops the rest.
import tiktoken

ENC = tiktoken.get_encoding("o200k_base")


def tool(name, conclusion, rows):
    """A tool result: the line the agent needed, inside `rows` lines of payload it did not."""
    payload = [f"{name} row {i}: status=ok latency_ms={100 + 7 * i} region=eu-west-1" for i in range(rows)]
    payload.insert(rows // 2, conclusion)
    return {"role": "tool", "text": "\n".join(payload), "note": f"[{name}: {conclusion}]", "tag": "tool"}


def msg(role, text, tag=None):
    """tag: "pin" (the first turn), "decision", "fact", "open", or None for everything else."""
    return {"role": role, "text": text, "tag": tag}


REPLAY = {
    "export-job": (
        [msg("user", "I am Priya; the project lead is Alice Moreno and we run Postgres 16.", "pin"),
         msg("assistant", "Understood. What should I look at first?"),
         msg("user", "Find out why the nightly export job fails."),
         tool("search_logs", "ERROR export: disk quota exceeded on /var/exports", 120),
         msg("assistant", "The export fails because the disk quota on /var/exports is exceeded.", "fact"),
         msg("user", "Decision: move the exports to the bucket acme-exports instead of a bigger disk.", "decision"),
         msg("assistant", "Agreed; I will change the export path."),
         tool("read_config", "export_path = /var/exports", 80),
         msg("user", "Thanks. Unrelated, but the coffee machine on floor 3 is broken again."),
         msg("assistant", "Noted, though I cannot fix the coffee machine."),
         msg("user", "Open question: does our retention policy allow 90 days in the bucket?", "open"),
         tool("web_search", "2 URLs selected: storage-lifecycle and retention-faq", 150),
         msg("user", "Schedule the export at 02:30 UTC from now on.", "decision"),
         tool("run_tests", "42 tests passed", 60),
         msg("assistant", "All 42 tests pass with the new path and schedule.")],
        [("Alice", "Moreno"), ("Postgres", "16"), ("disk", "quota"), ("acme-exports",), ("90", "days"),
         ("02:30", "UTC"), ("42", "tests")]),
    "refund-case": (
        [msg("user", "Order 48213, placed by Rahul Mehta; he wants a refund, not a replacement.", "pin"),
         msg("assistant", "I will check the order."),
         tool("get_order", "order 48213: 2 items, paid 3,398 rupees, shipped 5 March", 90),
         msg("assistant", "The order shipped on 5 March and was paid in full.", "fact"),
         msg("user", "He says the parcel arrived damaged; he sent photos yesterday.", "fact"),
         tool("get_tracking", "delivered 9 March, signed by R. Mehta", 110),
         msg("user", "Policy reminder: refunds above 3,000 rupees need a manager's approval.", "decision"),
         msg("assistant", "Then this refund needs approval."),
         msg("user", "By the way, he mentioned he prefers WhatsApp to email."),
         msg("assistant", "I will keep that in mind."),
         tool("lookup_manager", "on-call manager: Dana Okafor", 40),
         msg("user", "Open question: can we refund the courier fee as well?", "open"),
         msg("assistant", "I will ask Dana Okafor for approval and about the courier fee.")],
        [("48213",), ("refund",), ("damaged",), ("3,000",), ("approval",), ("WhatsApp",), ("Dana", "Okafor")]),
    "trip-plan": (
        [msg("user", "Plan a team offsite in Lisbon for 12 people in the week of 14 September.", "pin"),
         msg("assistant", "I will look at venues and flights."),
         tool("search_venues", "3 venues fit 12 people; Casa Azul is the only one with a projector", 140),
         msg("assistant", "Casa Azul is the only venue with a projector.", "fact"),
         msg("user", "Decision: book Casa Azul for 15 and 16 September.", "decision"),
         msg("user", "Two of the team are vegetarian and one is allergic to nuts.", "fact"),
         tool("search_flights", "cheapest direct flights land 14 September 10:05", 160),
         msg("assistant", "Flights landing on 14 September at 10:05 are the cheapest direct option."),
         msg("user", "Keep the total under 18,000 euros.", "decision"),
         msg("user", "Open question: should we add a half-day sailing trip?", "open"),
         msg("assistant", "I will price the sailing trip separately.")],
        [("Lisbon",), ("12", "people"), ("Casa", "Azul"), ("vegetarian",), ("nuts",), ("18,000",),
         ("sailing",), ("10:05",)]),
}

RECENT = 3          # turns every technique keeps verbatim at the end
WINDOW_TURNS = 6    # windowing keeps the last six entries


def tokens(history):
    return sum(len(ENC.encode(f"{e['role']}: {e['text']}\n")) for e in history)


def windowing(h):
    return h[-WINDOW_TURNS:]


def windowing_pinned(h):
    pinned = [e for e in h[:-WINDOW_TURNS] if e["tag"] in ("pin", "decision")]
    return pinned + h[-WINDOW_TURNS:]


def clear_tool_results(h):
    old = [dict(e, text=e["note"]) if e["tag"] == "tool" else e for e in h[:-RECENT]]
    return old + h[-RECENT:]


def priority_pruning(h, share=0.15):
    """Classes P1 (the recent turns and the pinned first turn), P2 (older messages), P3 (older tool results).
    Drop P3, then P2 oldest first, until the history fits `share` of its original size."""
    budget = share * tokens(h)
    keep = list(h)
    p3 = [e for e in h[:-RECENT] if e["tag"] == "tool"]
    p2 = [e for e in h[:-RECENT] if e["tag"] not in ("tool", "pin")]
    for e in p3 + p2:
        if tokens(keep) <= budget:
            break
        keep.remove(e)
    return keep


def summarise(h):
    """Rule-based stand-in for the section 3 summary: keep the tagged lines and the tool conclusions."""
    kept = [e["note"] if e["tag"] == "tool" else e["text"] for e in h[:-RECENT] if e["tag"]]
    summary = {"role": "summary", "text": "\n".join("- " + line for line in kept), "tag": "summary"}
    return [summary] + h[-RECENT:]


TECHNIQUES = [("windowing", windowing), ("windowing, pinned", windowing_pinned),
              ("tool-result clearing", clear_tool_results), ("priority pruning", priority_pruning),
              ("summarisation", summarise)]


def survives(fact, history):
    text = " ".join(e["text"] for e in history).lower()
    return all(word.lower() in text for word in fact)


def measure(technique):
    """Token reduction and IRR of one technique, pooled over the replay set."""
    before = after = kept = total = 0
    for history, facts in REPLAY.values():
        out = technique(history)
        before, after = before + tokens(history), after + tokens(out)
        kept, total = kept + sum(survives(f, out) for f in facts), total + len(facts)
    return before, after, kept, total


def main():
    n_facts = sum(len(f) for _, f in REPLAY.values())
    print(f"replay set: {len(REPLAY)} conversations, {n_facts} key facts, encoding o200k_base")
    print(f"{'technique':<22} {'tokens':>7} {'after':>6} {'reduction':>9} {'facts kept':>10} {'IRR':>5}")
    for name, technique in TECHNIQUES:
        before, after, kept, total = measure(technique)
        print(f"{name:<22} {before:>7} {after:>6} {1 - after / before:>9.1%} {kept:>5} of {total:<2} "
              f"{kept / total:>5.0%}")
    print()
    for name, technique in TECHNIQUES:
        lost = [" ".join(f) for history, facts in REPLAY.values() for f in facts
                if not survives(f, technique(history))]
        print(f"{name:<22} lost: {', '.join(lost) if lost else 'nothing'}")

if __name__ == "__main__":
    main()
