"""Post 24: the stores behind the window, governed. A memory write gate, tenant-scoped retrieval with a
cross-tenant leak test, a retention lifecycle for the trace store, and one erasure request fanned out to
every store.

Run from the series root:  uv run python posts/24-privacy-and-governance/snippets/governed_stores.py
Standard library only; no network, no model call. Two tenants share one chunk store, one memory store and one
trace store. A word-overlap score stands in for an embedding search. Every person, address and date is
synthetic, and the retention windows (30 days at full fidelity, 180 days in all) are illustrative policy
values: no regulation names them.
"""
import re
from datetime import date, timedelta

TODAY = date(2026, 10, 13)
FULL_DAYS, KEEP_DAYS = 30, 180          # illustrative retention policy for the trace store


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower())) - {"the", "a", "an", "of", "for", "to", "on", "in", "is", "and", "what", "her", "his"}


# ---------------------------------------------------------------- memory: a write gate on sensitivity and consent
CONSENT = {("u-017", "health"): False, ("u-104", "health"): True}     # recorded opt-ins, by subject and category


def check_memory_write(row: dict) -> str | None:
    """Return why the write is refused, or None. Runs after post 08's gate (source, secrets, tool results)."""
    if row["sensitivity"] == "special" and not CONSENT.get((row["subject"], row["category"]), False):
        return f"special-category ({row['category']}) with no recorded opt-in"
    if not row.get("basis"):
        return "no lawful basis recorded"
    return None


CANDIDATES = [
    dict(id="mem-01", tenant="tenant-a", subject="u-017", kind="semantic", category="preference",
         sensitivity="personal", basis="contract", source="conversation:c-311",
         content="Priya Raman prefers replies in formal English"),
    dict(id="mem-02", tenant="tenant-a", subject="u-017", kind="episodic", category="account",
         sensitivity="personal", basis="contract", source="ticket:4410",
         content="Priya Raman (priya.raman@example.com) reported a double charge on 2 October"),
    dict(id="mem-03", tenant="tenant-a", subject="u-017", kind="semantic", category="health",
         sensitivity="special", basis="consent", source="conversation:c-312",
         content="Priya Raman mentioned a diabetes diagnosis"),
    dict(id="mem-04", tenant="tenant-b", subject="u-104", kind="semantic", category="health",
         sensitivity="special", basis="consent", source="conversation:c-907",
         content="Lucy Hart asked for large-print documents after an eye operation"),
    dict(id="mem-05", tenant="tenant-a", subject="u-023", kind="semantic", category="preference",
         sensitivity="personal", basis="", source="conversation:c-402",
         content="Tom Okafor prefers a call to an email"),
]

# ---------------------------------------------------------------- documents: chunks, a manifest, an index
DOCS = [
    dict(id="doc-a1", tenant="tenant-a", about=[], text="Refund policy: refunds above 500 pounds need approval from finance. "
         "Duplicate card charges are refunded within five working days."),
    dict(id="doc-a2", tenant="tenant-a", about=["u-017"], text="Ticket 4410: Priya Raman reported a duplicate card charge "
         "and asked for a refund to her card. Contact priya.raman@example.com."),
    dict(id="doc-a3", tenant="tenant-a", about=["u-017"], text="Call note: Priya Raman asked to close her account "
         "after the duplicate charge refund."),
    dict(id="doc-a4", tenant="tenant-a", about=["u-023"], text="Ticket 4417: Tom Okafor asked for a refund of a late "
         "delivery charge."),
    dict(id="doc-b1", tenant="tenant-b", about=[], text="Returns: items can be returned within 30 days for a refund "
         "to the original payment method."),
    dict(id="doc-b2", tenant="tenant-b", about=["u-104"], text="Ticket 88: Lucy Hart asked how to close her account."),
]


def build(docs: list[dict]) -> tuple[list[dict], dict[str, list[str]], dict[str, set[str]]]:
    """Chunk by sentence; the manifest maps each document to its chunks; the index maps words to chunks."""
    chunks, manifest, index = [], {}, {}
    for d in docs:
        manifest[d["id"]] = []
        for j, sentence in enumerate(re.split(r"(?<=\.) ", d["text"]), 1):
            c = dict(id=f"{d['id']}-c{j}", doc=d["id"], tenant=d["tenant"], text=sentence)
            chunks.append(c)
            manifest[d["id"]].append(c["id"])
            for w in words(sentence):
                index.setdefault(w, set()).add(c["id"])
    return chunks, manifest, index


def retrieve(chunks, index, query: str, *, tenant_id: str, k: int = 3) -> list[dict]:
    """Filter by tenant first, then rank. tenant_id has no default, so a call without it fails closed."""
    by_id = {c["id"]: c for c in chunks if c["tenant"] == tenant_id}          # 1. the scope filter
    scores = {}
    for w in words(query):
        for cid in index.get(w, ()):
            if cid in by_id:
                scores[cid] = scores.get(cid, 0) + 1
    ranked = sorted(scores, key=lambda cid: (-scores[cid], cid))[:k]         # 2. rank only what is in scope
    return [by_id[cid] for cid in ranked]


def retrieve_unscoped(chunks, index, query: str, k: int = 3) -> list[dict]:
    """The bug: rank the whole shared store, nearest first, whoever owns the chunk."""
    by_id = {c["id"]: c for c in chunks}
    scores = {}
    for w in words(query):
        for cid in index.get(w, ()):
            scores[cid] = scores.get(cid, 0) + 1
    return [by_id[cid] for cid in sorted(scores, key=lambda cid: (-scores[cid], cid))[:k]]


B_QUERIES = ["How do I get a refund for a duplicate card charge?", "How long does a refund take?",
             "How do I close my account?", "Who approves a large refund?", "Can I return an item for a refund?"]

# ---------------------------------------------------------------- the trace store
TRACES = [
    dict(call="t-01", tenant="tenant-a", user="u-017", day=TODAY - timedelta(days=2),
         prompt="Priya Raman: please refund the duplicate charge to my card. Reply to priya.raman@example.com."),
    dict(call="t-02", tenant="tenant-a", user="u-017", day=TODAY - timedelta(days=45),
         prompt="Priya Raman asked whether formal English replies can be the default."),
    dict(call="t-03", tenant="tenant-a", user="u-023", day=TODAY - timedelta(days=5),
         prompt="Tom Okafor asked about a late delivery charge."),
    dict(call="t-04", tenant="tenant-b", user="u-104", day=TODAY - timedelta(days=12),
         prompt="Lucy Hart asked how to close her account."),
    dict(call="t-05", tenant="tenant-a", user="u-023", day=TODAY - timedelta(days=95),
         prompt="Tom Okafor asked for a call instead of an email."),
    dict(call="t-06", tenant="tenant-b", user="u-104", day=TODAY - timedelta(days=200),
         prompt="Lucy Hart asked for large-print documents."),
]


def apply_retention(traces: list[dict], audit: list[str]) -> list[dict]:
    """The lifecycle rule: full text for FULL_DAYS, then the prompt is dropped, deleted after KEEP_DAYS."""
    kept = []
    for t in traces:
        age = (TODAY - t["day"]).days
        if age > KEEP_DAYS:
            audit.append(f"{TODAY} retention: deleted {t['call']} (age {age} days)")
            continue
        if age > FULL_DAYS and t["prompt"] is not None:
            t = dict(t, prompt=None)
            audit.append(f"{TODAY} retention: dropped the prompt of {t['call']} (age {age} days)")
        kept.append(t)
    return kept


def erase(subject: str, memory, docs, chunks, manifest, index, traces, audit):
    """One erasure request, fanned out: memory rows, source documents and their chunks, traces."""
    memory2 = [r for r in memory if r["subject"] != subject]
    gone_docs = [d["id"] for d in docs if subject in d["about"]]
    docs2 = [d for d in docs if d["id"] not in gone_docs]
    gone_chunks = {cid for doc in gone_docs for cid in manifest.pop(doc)}   # the manifest names every chunk
    chunks2 = [c for c in chunks if c["id"] not in gone_chunks]
    for ids in index.values():
        ids -= gone_chunks                                                 # and every index entry goes with them
    traces2 = [t for t in traces if t["user"] != subject]
    audit.append(f"{TODAY} erasure {subject}: {len(memory) - len(memory2)} memory rows")
    audit.append(f"{TODAY} erasure {subject}: {', '.join(gone_docs)} and chunks {', '.join(sorted(gone_chunks))}")
    audit.append(f"{TODAY} erasure {subject}: {len(traces) - len(traces2)} traces")
    return memory2, docs2, chunks2, traces2


def mentions(identifiers: set[str], memory, docs, chunks, traces) -> dict[str, int]:
    hit = lambda text: text is not None and any(i in text for i in identifiers)  # noqa: E731
    return {"memory rows": sum(hit(r["content"]) or r["subject"] in identifiers for r in memory),
            "documents": sum(hit(d["text"]) or bool(identifiers & set(d["about"])) for d in docs),
            "chunks": sum(hit(c["text"]) for c in chunks),
            "traces": sum(hit(t["prompt"]) or t["user"] in identifiers for t in traces)}


def main() -> None:
    audit: list[str] = []
    print("memory write gate:")
    memory = []
    for row in CANDIDATES:
        why = check_memory_write(row)
        print(f"  {row['id']} {row['subject']} {row['category']:<10} {'refused, ' + why if why else 'written'}")
        if why is None:
            memory.append(row)

    chunks, manifest, index = build(DOCS)
    print(f"\ncross-tenant leak test: {len(B_QUERIES)} tenant-b queries, top 3, store shared with tenant-a")
    leaks_unscoped = sum(any(c["tenant"] != "tenant-b" for c in retrieve_unscoped(chunks, index, q)) for q in B_QUERIES)
    leaks_scoped = sum(any(c["tenant"] != "tenant-b" for c in retrieve(chunks, index, q, tenant_id="tenant-b"))
                       for q in B_QUERIES)
    print(f"  rank, no tenant filter:  {leaks_unscoped} of {len(B_QUERIES)} packs hold tenant-a chunks")
    print(f"  filter, then rank:       {leaks_scoped} of {len(B_QUERIES)} packs hold tenant-a chunks")
    first = retrieve_unscoped(chunks, index, B_QUERIES[0])[0]
    print(f"  first query, unscoped, rank 1: {first['id']} ({first['tenant']}), \"{first['text'][:40]}...\"")
    try:
        retrieve(chunks, index, B_QUERIES[0])
        print("  retrieve() with no tenant_id: answered")
    except TypeError:
        print("  retrieve() with no tenant_id: refused (TypeError), the call fails closed")

    traces = apply_retention(TRACES, audit)
    full = sum(t["prompt"] is not None for t in traces)
    print(f"\nretention on {TODAY} (illustrative: full text {FULL_DAYS} days, {KEEP_DAYS} days in all):")
    print(f"  {len(TRACES)} traces -> {full} with the prompt, {len(traces) - full} without, {len(TRACES) - len(traces)} deleted")

    who = {"u-017", "Priya Raman", "priya.raman@example.com"}
    q = "Priya Raman duplicate card charge refund"
    before_pack = [c["id"] for c in retrieve(chunks, index, q, tenant_id="tenant-a")]
    before = mentions(who, memory, DOCS, chunks, traces)
    partial = mentions(who, [r for r in memory if r["subject"] != "u-017"], DOCS, chunks, traces)
    memory, docs, chunks, traces = erase("u-017", memory, DOCS, chunks, manifest, index, traces, audit)
    after = mentions(who, memory, docs, chunks, traces)
    after_pack = [c["id"] for c in retrieve(chunks, index, q, tenant_id="tenant-a")]
    print("\nerasure request for u-017 (Priya Raman), tenant-a:")
    print("  store         before  memory only  fan-out")
    for store in before:
        print(f"  {store:<12} {before[store]:>6} {partial[store]:>12} {after[store]:>8}")
    print("  provider      outside this process: the provider's retention terms apply")
    print(f"  query \"{q}\":")
    print(f"    before: {', '.join(before_pack)}")
    print(f"    after:  {', '.join(after_pack)}")
    print("audit log:")
    for line in audit:
        print(f"  {line}")
    ok = (leaks_scoped == 0 and leaks_unscoped > 0 and not any(after.values())
          and any(partial.values()) and not any(c.startswith(("doc-a2", "doc-a3")) for c in after_pack))
    print(f"gate: {'pass' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
