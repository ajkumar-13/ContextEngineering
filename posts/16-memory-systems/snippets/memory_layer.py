"""Post 16: a minimal memory layer. Three kinds in one row schema, three retrieval paths, decay on read.

Run from the series root:  uv run python posts/16-memory-systems/snippets/memory_layer.py
Standard library only; no network, no model call. Ten rows of mixed kind are written, three turns are
answered by the orchestrator, the layer 03 block of the second turn is printed, and the post's gate is
checked. Retrieval is read-only here, so every turn sees the rows as written. The decay rate, the two
thresholds, the dates and the word-overlap search (a stand-in for an embedding search) are illustrative
choices for the example, not measured or tuned values.
"""
import re
from dataclasses import dataclass, field
from datetime import date

KINDS = ("episodic", "semantic", "procedural")
DECAY_PER_IDLE_DAY = 0.01   # illustrative, the rate of post 08
ASK_BELOW = 0.6             # illustrative, post 08's cutoff: assert at or above, ask first below
COLD_BELOW = 0.4            # illustrative: below this a row leaves the live store (kept, never deleted)
TODAY = date(2026, 10, 12)


@dataclass
class MemoryRow:
    id: str
    kind: str                     # episodic, semantic or procedural
    subject: str                  # who the row is about; for a procedural row, the scope of the rule
    content: str                  # the event, the fact, or the rule
    source: str
    created_at: str
    last_accessed_at: str
    confidence: float
    expires_at: str | None = None
    trigger: str | None = None    # procedural only: the condition that fires the rule, "key=value"


def confidence_on(row: MemoryRow, today: date) -> float:
    """Decay on read: computed from the stored row, never written back."""
    if row.kind == "procedural":
        return row.confidence          # a rule does not decay; a person removes it
    if row.expires_at and today > date.fromisoformat(row.expires_at):
        return 0.0
    idle = (today - date.fromisoformat(row.last_accessed_at)).days
    return max(0.0, round(row.confidence - DECAY_PER_IDLE_DAY * idle, 2))


@dataclass
class MemoryContext:
    procedural: list = field(default_factory=list)
    semantic: list = field(default_factory=list)
    episodic: list = field(default_factory=list)


PAST = re.compile(r"\b(last|again|before|earlier|ago|previous|back)\b", re.IGNORECASE)


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower())) - {"the", "a", "to", "on", "by", "for", "is", "it", "from"}


class MemoryLayer:
    def __init__(self, today: date):
        self.rows: list[MemoryRow] = []
        self.today = today

    def write(self, row: MemoryRow) -> str | None:
        """Append-only: a contradiction is a new row, never an edit of the old one."""
        if not row.source:
            return "no provenance"
        if row.kind not in KINDS:
            return f"unknown kind {row.kind!r}"
        if (row.kind == "procedural") != (row.trigger is not None):
            return "a trigger belongs on a procedural row, and only there"
        self.rows.append(row)
        return None

    def live(self, subject: str, kind: str) -> list[MemoryRow]:
        return [r for r in self.rows if r.subject == subject and r.kind == kind
                and confidence_on(r, self.today) >= COLD_BELOW]

    def retrieve(self, turn: dict, k: int = 3) -> MemoryContext:
        """Read-only: the application updates last_accessed_at for the rows the answer relied on."""
        subject, text, facts = turn["subject"], turn["text"], turn["facts"]
        # 1. procedural first: every rule whose trigger is true now, unranked
        fired = [r for r in self.live(subject, "procedural")
                 if facts.get(r.trigger.split("=")[0]) == r.trigger.split("=")[1]]
        # 2. semantic second: background grounding, ranked by confidence, then by the last read
        facts_now = sorted(self.live(subject, "semantic"),
                           key=lambda r: (confidence_on(r, self.today), r.last_accessed_at), reverse=True)[:k]
        # 3. episodic last, and only when the turn refers to the past
        events = []
        if PAST.search(text):
            scored = [(len(words(text) & words(r.content)), r) for r in self.live(subject, "episodic")]
            events = [r for s, r in sorted(scored, key=lambda p: -p[0]) if s > 0][:k]
        return MemoryContext(fired, facts_now, events)


def render(ctx: MemoryContext, today: date) -> str:
    """The layer 03 block, in the orchestrator's order, each item with its source and date."""
    out = ["[memory: rules that apply to this turn]"]
    out += [f"- {r.content} ({r.source})" for r in ctx.procedural] or ["- none"]
    out.append("[memory: facts about this user]")
    for r in ctx.semantic:
        c = confidence_on(r, today)
        note = f"last read {r.last_accessed_at}" if c >= ASK_BELOW else "unconfirmed: ask before relying on it"
        out.append(f"- {r.content} ({r.source}, {note})")
    out.append("[memory: past events this turn refers to]")
    out += [f"- {r.content} ({r.source}, {r.created_at})" for r in ctx.episodic] or ["- none"]
    return "\n".join(out)


U = "user:u-17"
ROWS = [
    MemoryRow("mem-01", "semantic", U, "Prefers replies in formal English", "conversation:c-311",
              "2026-06-02", "2026-10-09", 0.9),
    MemoryRow("mem-02", "semantic", U, "Is on the enterprise tier", "billing:acct-17",
              "2026-03-15", "2026-10-10", 1.0),
    MemoryRow("mem-03", "semantic", U, "Works in the Pacific time zone", "conversation:c-298",
              "2026-05-11", "2026-09-12", 0.8),
    MemoryRow("mem-04", "semantic", U, "Uses Postgres in production", "conversation:c-140",
              "2026-02-20", "2026-07-01", 0.9),
    MemoryRow("mem-05", "episodic", U, "Resolved ticket 4321 on 14 September by escalating the billing error",
              "ticket:4321", "2026-09-14", "2026-09-14", 1.0),
    MemoryRow("mem-06", "episodic", U, "Reported a failed CSV export on 2 October", "conversation:c-402",
              "2026-10-02", "2026-10-02", 1.0),
    MemoryRow("mem-07", "episodic", U, "Asked for a refund on invoice 88 on 3 June", "conversation:c-215",
              "2026-06-03", "2026-06-03", 1.0),
    MemoryRow("mem-08", "procedural", U, "Export this client's reports as CSV first; their system rejects a PDF on its own",
              "conversation:c-187", "2026-05-20", "2026-05-20", 1.0, trigger="intent=export"),
    MemoryRow("mem-09", "procedural", U, "Copy every escalation to the account's named technical contact",
              "conversation:c-233", "2026-06-18", "2026-06-18", 1.0, trigger="intent=escalate"),
    MemoryRow("mem-10", "procedural", U, "Ask for the purchase-order number before discussing a refund",
              "conversation:c-190", "2026-05-20", "2026-05-20", 1.0, trigger="intent=refund"),
]
TURNS = [
    {"subject": U, "text": "Please send this month's usage report.", "facts": {"intent": "export"}},
    {"subject": U, "text": "The billing error from ticket 4321 is back; please escalate it.",
     "facts": {"intent": "escalate"}},
    {"subject": U, "text": "Last time I asked about a refund on invoice 88. Where is it?",
     "facts": {"intent": "refund"}},
]


def main() -> None:
    layer = MemoryLayer(TODAY)
    refused = [r.id for r in ROWS if layer.write(r)]
    counts = {k: sum(r.kind == k for r in layer.rows) for k in KINDS}
    print(f"wrote {len(layer.rows)} rows: {counts['semantic']} semantic, {counts['episodic']} episodic, "
          f"{counts['procedural']} procedural; refused {len(refused)}")

    print(f"\nconfidence on {TODAY} ({DECAY_PER_IDLE_DAY} per idle day; procedural rows do not decay):")
    for r in layer.rows:
        c = confidence_on(r, TODAY)
        state = "cold" if c < COLD_BELOW else "ask" if c < ASK_BELOW and r.kind == "semantic" else "live"
        print(f"  {r.id}  {r.kind:<10}  idle {(TODAY - date.fromisoformat(r.last_accessed_at)).days:>3} days  "
              f"{c:.2f}  {state}")

    ctxs = []
    for n, turn in enumerate(TURNS, 1):
        ctx = layer.retrieve(turn)
        ctxs.append(ctx)
        print(f"\nturn {n}: \"{turn['text']}\" ({', '.join(f'{a}={b}' for a, b in turn['facts'].items())})")
        print(f"  1 procedural, trigger match: {', '.join(r.id for r in ctx.procedural) or 'none'}")
        print(f"  2 semantic, background top-3: {', '.join(r.id for r in ctx.semantic)}")
        if not PAST.search(turn["text"]):
            print("  3 episodic, reference recall: skipped, the turn refers to no past event")
        else:
            cold = [r.id for r in layer.rows if r.kind == "episodic" and confidence_on(r, TODAY) < COLD_BELOW
                    and words(turn["text"]) & words(r.content)]
            line = ", ".join(r.id for r in ctx.episodic) or "none live"
            print(f"  3 episodic, reference recall: {line}" + (f"; {', '.join(cold)} matches but is cold" if cold else ""))
        if n == 2:
            block = render(ctx, TODAY)

    print("\nlayer 03 block for turn 2:")
    print(block)

    ids = [{k: [r.id for r in getattr(c, k)] for k in ("procedural", "semantic", "episodic")} for c in ctxs]
    checks = {
        "preference mem-01 by background grounding": all("mem-01" in i["semantic"] for i in ids),
        "event mem-05 by reference recall": ids[1]["episodic"] == ["mem-05"],
        "rule mem-08 by trigger match": ids[0]["procedural"] == ["mem-08"],
        "stale event mem-07 decayed": ids[2]["episodic"] == [] and confidence_on(ROWS[6], TODAY) < COLD_BELOW,
        "rule mem-10 did not": ids[2]["procedural"] == ["mem-10"] and confidence_on(ROWS[9], TODAY) == 1.0,
    }
    print(f"\ngate: {sum(checks.values())} of {len(checks)} checks pass")
    for name, ok in checks.items():
        print(f"  {'pass' if ok else 'FAIL'}  {name}")


if __name__ == "__main__":
    main()
