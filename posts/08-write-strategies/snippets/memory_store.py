"""Post 08: a memory row with the nine fields, a write gate, and confidence decay.

Run from the series root:  uv run python posts/08-write-strategies/snippets/memory_store.py
Standard library only; no network, no model call. The decay rate, the ask threshold and the
dates are illustrative values chosen for the example, not measured constants.
"""
import json
import re
from dataclasses import asdict, dataclass
from datetime import date

KINDS = ("episodic", "semantic", "procedural")


@dataclass
class MemoryRow:
    id: str                 # stable reference for updates and deletes
    kind: str               # episodic, semantic or procedural
    subject: str            # the entity the memory is about
    content: str            # the fact itself
    source: str             # where the fact came from
    created_at: str         # date of the original write
    last_accessed_at: str   # updated on every read; drives decay
    confidence: float       # 0 to 1; gates assert against ask
    expires_at: str | None  # set only for knowingly short-lived facts


SECRET = re.compile(r"\bsk-[A-Za-z0-9-]{8,}|\b(password|api[_ ]?key)\s*[:=]", re.IGNORECASE)


def check_write(row: MemoryRow, origin: str) -> str | None:
    """Return why the write must be refused, or None when it may go in."""
    if not row.source:
        return "no provenance: the row has no source"
    if SECRET.search(row.content):
        return "secret: it belongs in a secret manager, not a memory store"
    if origin == "tool_result":
        return "transient: a tool result is called again, not remembered"
    if row.kind not in KINDS:
        return f"unknown kind: {row.kind!r}"
    return None


DECAY_PER_IDLE_DAY = 0.01   # illustrative
ASK_BELOW = 0.6             # illustrative


def decayed(row: MemoryRow, today: date) -> float:
    """Confidence after the days since the last read, never below zero."""
    idle = (today - date.fromisoformat(row.last_accessed_at)).days
    return max(0.0, round(row.confidence - DECAY_PER_IDLE_DAY * idle, 2))


def main() -> None:
    row = MemoryRow(
        id="mem-0042", kind="semantic", subject="user:u-17",
        content="Prefers replies in formal English",
        source="conversation:c-311", created_at="2026-09-01",
        last_accessed_at="2026-09-01", confidence=0.9, expires_at=None)
    print(f"{len(asdict(row))} fields")
    print(json.dumps(asdict(row), indent=2))

    print("\nwrite gate:")
    attempts = [
        (row, "user_assertion"),
        (MemoryRow("mem-0043", "semantic", "user:u-17", "Works in the PST time zone", "",
                   "2026-09-02", "2026-09-02", 0.8, None), "session_summary"),
        (MemoryRow("mem-0044", "semantic", "user:u-17", "API key: sk-live-4f9a2b7c1d", "conversation:c-312",
                   "2026-09-03", "2026-09-03", 0.9, None), "user_assertion"),
        (MemoryRow("mem-0045", "semantic", "city:mumbai", "temperature: 32", "tool:get_weather",
                   "2026-09-03", "2026-09-03", 1.0, None), "tool_result"),
    ]
    for candidate, origin in attempts:
        reason = check_write(candidate, origin)
        print(f"  {candidate.id}: {'written' if reason is None else 'refused, ' + reason}")

    print("\ndecay of mem-0042 without a read:")
    for today in (date(2026, 9, 1), date(2026, 9, 21), date(2026, 10, 11)):
        c = decayed(row, today)
        action = "assert" if c >= ASK_BELOW else "ask first"
        print(f"  {today}: {(today - date(2026, 9, 1)).days:>2} idle days, confidence {c:.2f}, {action}")


if __name__ == "__main__":
    main()
