# 24 - Privacy, PII, and data governance

> **TL;DR.** Four of the six layers are not written by the team and can carry regulated personal data (layers 03 to 06: memory and state, retrieved chunks, conversation history with its tool results, and the user instruction), and every assembled prompt is copied whole into the trace store. This post asks where that data enters the context and its copies, and where detection, redaction, retention, consent and tenant isolation must sit to govern it without gutting answer quality. The answer is one detect-and-redact gate at the trust boundary, a redaction policy for each copy, a lifecycle rule on every store, an erasure that reaches all of them, and retrieval that fails closed when the tenant is missing.
>
> **Prerequisites:** [Post 22](../22-observability/index.md), [Post 23](../23-security/index.md).
> **Safe to skip?** Skip it if every store that holds a copy of a prompt already has a retention rule the store enforces and a tested deletion path, and every retrieval and memory read is scoped to one tenant by a filter that fails closed.
>
> **After reading, you will be able to:**
>
> - Trace where personally identifiable information enters the context, layer by layer, and every store that keeps a copy of it, the trace store first.
> - Place a detect-and-redact gate at the trust boundary, and decide separately for the window and the trace store whether a value is redacted or kept.
> - Set retention and residency for logged prompts, and say what a provider's zero-data-retention terms cover and what they leave to the application.
> - Gate memory writes on sensitivity and a recorded lawful basis, and fan one erasure request out to every store that holds the person's data.
> - Enforce tenant isolation in retrieval and memory with a scope filter that fails closed, and test it with a cross-tenant leak test.

![Four channels, the user message, tool results, retrieved chunks and memory rows, cross one detect-and-redact gate into layers 06, 05, 04 and 03 of the window; the assembled prompt goes to the model and, as a copy, to the trace store.](diagrams/01-one-gate-two-copies.svg)

*One gate at the boundary, two copies after it: the window the model reads, and the trace store that keeps every prompt.*

---

## 1. The question: where does regulated data go once it enters the context?

An application that answers support tickets, summarises contracts or remembers its users handles personal data on every call. Personally identifiable information (PII) is information that identifies a person, directly (a name, an email address, a payment card number) or in combination with other data. The question is where such data enters the context a large language model (LLM) receives, and which stores keep copies of it.

The first copy is the easiest to miss. Observability ([post 22](../22-observability/index.md)) keeps a trace store: the store of captured traces, each a copy of the full prompt and response of every model call in it, with the spans around them. That prompt holds everything the context assembler packed into the call, so whatever personal data entered the context also entered the trace store: the medical history a user pasted, the home address in a retrieved chunk, the card number a tool returned. The trace store is not a summary of the prompts; it is a second copy of them, kept longer than the call and read by everyone who debugs.

This is why governance is a different discipline from security. Security ([post 23](../23-security/index.md)) asks what an adversary can do to the context. Governance asks what the application itself does with data that entered legitimately, with the user's cooperation. No attacker is involved: the failure is a well-meaning pipeline that copies personal data into several stores, keeps it indefinitely and cannot delete it when the person asks. Since context is assembled from many sources and copied into several stores, governance is designed into the assembly and logging path, as retrieval and caching are.

**Not legal advice.** This post names the General Data Protection Regulation (GDPR) of the European Union (EU) at a high level, to explain the engineering obligations it and similar regimes create. What a regulation requires of a given product is a question for counsel and the data-protection officer.

---

## 2. Where regulated data enters the context

The first exercise, before any control is written, is a data map: every place personal data can flow into a prompt. In [post 02](../02-six-layers-of-context/index.md)'s six layers, two layers are written by the team and four are not.

- **Layer 01, the system prompt, and layer 02, tools and Model Context Protocol (MCP) descriptions**, are written by the team and reviewed like code. They should hold no personal data; a real customer used as a worked example is removed, since the stable prefix is sent on every call.
- **Layer 03, memory and state.** Long-term memory ([post 16](../16-memory-systems/index.md)) persists facts across sessions, and semantic memory accumulates exactly what privacy regimes care about: "the user's employer is X", "the user mentioned a diagnosis". Section 5 governs it.
- **Layer 04, retrieved chunks.** Retrieval-augmented generation (RAG; [post 11](../11-rag-in-depth/index.md)) pulls from an indexed corpus. If the corpus holds support tickets or customer emails, retrieval brings them into the prompt whenever they match a query, and from there into a trace.
- **Layer 05, conversation history**, holds every earlier message of the session and every tool result. A `lookup_account` tool returns a customer's plan, address and ticket history straight into the window (the same read tool post 23 uses in its exfiltration chain). Tool results come from systems of record, so one result can carry more personal fields than the rest of the prompt.
- **Layer 06, the user instruction.** The hardest channel to bound: users paste contracts, health records and other people's details. After the turn, the message moves into layer 05 and is sent again on every later call.

The figure at the top of the post draws the map: four channels cross one gate at the trust boundary and land in their layers, and the assembled prompt goes to the model and, as a copy, to the trace store. Annotating each channel with the most sensitive class of data it can carry is the input to every later decision.

---

## 3. Detection and redaction at the trust boundary

The place to act is the **trust boundary**: the point where text from outside crosses into the context, and from there into its copies. Post 23 filters content for injected instructions at the same boundary, and both checks can run in one pass: injection filtering looks for adversarial instructions, PII filtering for regulated data.

**Detection** layers three techniques, cheapest first:

- **Patterns with a check** catch structured PII: card numbers confirmed by the Luhn checksum, national identifiers, email addresses, phone numbers. They are fast, deterministic and precise where a checksum exists: a card-shaped order number that fails the check is left alone.
- **Named-entity recognition (NER)** catches the names of people, places and organisations with a small model, far cheaper per call than an LLM. Presidio packages both layers: its recognisers use "Named Entity Recognition, regular expressions, rule based logic and checksum" with context, and it can replace, redact, mask, hash or encrypt what they find (Presidio documentation, consulted October 2026; the project began at Microsoft). The same documentation warns that "there is no guarantee that Presidio will find all sensitive information".
- **An LLM classifier** catches the context-dependent cases ("the patient in bed 4", "her account balance"). It costs a model call per check, so it is a fallback for high-risk paths.

**Redaction** replaces each detected span with a typed placeholder (`<PERSON_1>`, `<EMAIL_1>`) rather than deleting it, so the text still reads and the model can still refer to "the person". The map from placeholder to value goes to a separate vault with tighter access, where an authorised reader can reverse it. This is pseudonymisation: the structure survives, and the raw value does not spread.

**Redaction can destroy the task.** "Email Tom Okafor at tom.okafor@example.org" becomes "Email `<PERSON_1>` at `<EMAIL_1>`", and the model can no longer do the job, because the job was the PII. Debugging pulls the same way: post 22's account of privacy and PII in traces redacts only the fields a rule names, not the whole prompt, because blanket masking removes the debugging value. The two copies therefore get two policies:

- **The window** receives redacted text only when the model does not need the values: a good default for an upload feeding a summary, a bad one when the task is about the person.
- **The trace store** receives redacted text for every field the policy names, so the copy that outlives the call holds placeholders, still readable for debugging and reversible through the vault.

The gate is a few lines of `snippets/pii_gate.py`. Its detectors are the pattern layer plus a list of first names standing in for an NER model. It runs once per prompt, writes the redacted copy to the trace store and the mapping to the vault, and returns what the model receives:

```python
def gate(call_id: str, task: str, text: str, trace_store: list, vault_store: dict) -> str:
    """Run once at the trust boundary. Returns what the model receives; writes the trace and the vault."""
    hits = detect(text)
    redacted, vault = redact(text, hits)
    trace_store.append({"call": call_id, "task": task, "prompt": redacted})   # always the redacted copy
    vault_store[call_id] = vault                                              # kept apart, tighter access
    return redacted if task == "summarise" else text                          # raw only when the task is the PII
```

The snippet passes twenty synthetic prompts through the gate, ten summaries and ten actions, with reserved email domains, phone ranges reserved for drama and published test card numbers:

```text
detect-and-redact gate: 20 prompts, 42 seeded values
  CARD      4 caught
  NINO      2 caught
  EMAIL     9 caught
  PHONE     7 caught
  PERSON   20 caught
  missed    0
card-shaped order number 1234 5678 9012 3456: Luhn fail, left in the text
context-dependent health detail: not caught (a case for the classifier layer)
to the model: 10 summarise prompts redacted, 10 act prompts sent with the values
to the trace store: 20 records, 0 seeded values found
example, call-01:
  trace: Summarise this ticket: <PERSON_1> (<EMAIL_1>) says her card <CARD_1> was charged twice.
  vault: <CARD_1> = 4111 1111 1111 1111, <EMAIL_1> = priya.raman@example.com, <PERSON_1> = Priya Raman
gate: pass
```

All 42 seeded values were caught and none reached the trace store, while the ten action prompts went to the model with their values. The prompts were written for these detectors, so zero misses tests the plumbing, not the detection rate, which has to be measured on the application's own data. And "the patient in bed 4 has a penicillin allergy" passed every pattern and the name list: the classifier layer's case. The figure below follows `call-01` through the gate.

![The prompt of call-01 passes the detectors in order: patterns find a card and an email, the name list a person, and the classifier is not run. Placeholders go to the trace store and the window, the values to a vault.](diagrams/02-redaction-gate.svg)

*The trace store and the window get placeholders; the values go to a vault with its own access rule.*

---

## 4. Retention and residency of logged prompts

**Retention.** A trace store without a retention rule grows without bound, and every extra day is extra exposure and extra scope for an erasure request. The GDPR's storage-limitation principle (Article 5(1)(e)) requires personal data to be kept in a form that identifies the person for no longer than the purposes of the processing need. It names no number, so every window is a policy choice made with counsel. One workable shape has three tiers: the full prompt and response for a short debugging window; then the record without the prompt (tokens, cost, latency, outcome) for a longer analytics window; then deletion, with an audit record. `snippets/governed_stores.py` implements it with illustrative windows of 30 days in full and 180 days in all. Of six traces aged from 2 to 200 days on 13 October 2026, it keeps three whole, drops the prompt of two and deletes one, writing an audit line for each change:

```text
retention on 2026-10-13 (illustrative: full text 30 days, 180 days in all):
  6 traces -> 3 with the prompt, 2 without, 1 deleted
```

The point is that the store enforces the rule, by a scheduled job or the storage system's lifecycle policy, not by someone remembering a cleanup script.

**Residency.** Some regimes constrain where personal data is processed and stored, and the model provider processes every prompt. Both providers document controls:

- Anthropic's "Data residency" page (consulted October 2026) separates the inference geography, set per request with `inference_geo` (`"global"`, the default, or `"us"`), from the workspace geography where data is stored at rest (`"us"` is the only option listed). US-only inference costs 1.1 times the standard rate on Claude 4.6 and later models.
- OpenAI's "Data controls in the OpenAI platform" (consulted October 2026) lists regional endpoints, `eu.api.openai.com` among them, and requires a Modified Retention amendment, with approved modified abuse monitoring or zero data retention, for regions outside the United States.

A region setting is a contract term to check against the provider's data-processing addendum, not an assumption.

**Zero data retention (ZDR)** is an arrangement in which the provider keeps no prompts or outputs after the response. Without one, Anthropic deletes application programming interface (API) inputs and outputs on its backend within 30 days ("How long do you store my organization's data?", Anthropic Privacy Center, consulted October 2026); under ZDR, it "does not store customer prompts or responses at rest after the API response is returned" ("API and data retention", consulted October 2026). OpenAI keeps abuse-monitoring logs for up to 30 days by default ("Data controls", consulted October 2026) and, under ZDR, excludes customer content from them. Both say API data is not used for training by default. Three limits matter:

- ZDR is granted per organisation, on request, not by default.
- It covers some features and not others. Anthropic lists the Batch API (29-day retention) and the Files API among the features it does not cover; OpenAI lists `/v1/files`, `/v1/batches` and `/v1/vector_stores` among the endpoints that are not eligible. Documents uploaded through a files endpoint are outside the arrangement.
- Both keep data where the law requires it, and Anthropic may keep flagged content for up to 2 years even under ZDR.

ZDR does nothing for the application's own copies. Enabling it while logging the full prompt in the trace store moves the regulated copy from the provider's systems to the application's; governance is about the whole set of copies.

---

## 5. Memory governance: consent, persistence, and the right to be forgotten

**What may persist.** Some facts fall into the GDPR's special categories (Article 9, among them health, ethnic origin, political opinions, religious beliefs and sexual orientation), which it protects more strictly. A sound default is an allow-list: operational preferences may be written, and special-category content is refused unless the person has opted in. [Post 16](../16-memory-systems/index.md)'s rows carry [post 08](../08-write-strategies/index.md)'s nine fields, with `source` for provenance, and post 23 adds a trust tag to every row, naming whether system, user or external content wrote it. This post adds a sensitivity label, an extra field that post 16, section 3 already allows, so that a write gate can act on it.

**Consent and lawful basis.** Persisting a fact about a person is a processing decision that needs a lawful basis; consent is one of the six that GDPR Article 6 lists. A memory write of personal data records its basis, so the store can answer "why is this row held?"; a row whose basis cannot be named is not held. The snippet's gate runs after post 08's write gate, which already refuses missing sources, secrets and tool results:

```python
CONSENT = {("u-017", "health"): False, ("u-104", "health"): True}     # recorded opt-ins, by subject and category


def check_memory_write(row: dict) -> str | None:
    """Return why the write is refused, or None. Runs after post 08's gate (source, secrets, tool results)."""
    if row["sensitivity"] == "special" and not CONSENT.get((row["subject"], row["category"]), False):
        return f"special-category ({row['category']}) with no recorded opt-in"
    if not row.get("basis"):
        return "no lawful basis recorded"
    return None
```

Offered five candidate rows, it writes three:

```text
memory write gate:
  mem-01 u-017 preference written
  mem-02 u-017 account    written
  mem-03 u-017 health     refused, special-category (health) with no recorded opt-in
  mem-04 u-104 health     written
  mem-05 u-023 preference refused, no lawful basis recorded
```

**The right to erasure.** Article 17 of the GDPR gives a person the right to have their personal data erased without undue delay where one of its grounds applies (consent withdrawn, or the data no longer needed, among others). In an LLM stack that is a fan-out to every store holding a copy: the memory rows about the person; the source documents about them, with every chunk and index entry they produced (the manifest of post 08, section 5 names them); the traces of their calls; and the provider's copy, which the application cannot delete itself and governs through the terms of section 4. The snippet sends one request for user `u-017`:

```text
erasure request for u-017 (Priya Raman), tenant-a:
  store         before  memory only  fan-out
  memory rows       2            0        0
  documents         2            2        0
  chunks            3            3        0
  traces            2            2        0
  provider      outside this process: the provider's retention terms apply
  query "Priya Raman duplicate card charge refund":
    before: doc-a2-c1, doc-a3-c1, doc-a1-c2
    after:  doc-a1-c2, doc-a4-c1, doc-a1-c1
```

The middle column is a deletion that stops at the memory store: the person is still in two documents, three chunks and two traces, and a query still retrieves their ticket. After the fan-out every count is zero, the same query returns the general refund policy and another customer's ticket, and the audit log records each removal. The figure below draws the fan-out with these counts.

![One erasure request for u-017 fans out: memory rows 2 to 0, documents 2 to 0, chunks 3 to 0, traces 2 to 0, and the provider's copy follows its retention terms. A memory-only deletion leaves 7 copies.](diagrams/03-erasure-fan-out.svg)

*An erasure that stops at the memory store leaves the person in every other copy.*

The procedure extends post 23's memory revocation for poisoned rows (find rows by subject, source and content pattern, delete with an audit record) by re-validating what depended on them, such as an index or a cache. It reaches every tier, including a cold tier kept "never deleted" (post 16, section 15). It is built before it is needed, because an erasure request arrives with a deadline.

---

## 6. Tenant isolation in multi-tenant RAG and memory

The most damaging governance bug in a multi-tenant product is one tenant's data in another tenant's context. It is a context-assembly failure: a retriever or memory reader returned another tenant's chunk or row. [Post 25](../25-long-context-vs-rag/index.md), section 5 (when RAG wins), counts per-tenant data as a reason to retrieve rather than load a whole corpus; the other side of that argument is that retrieval is where cross-tenant leakage happens.

A shared store returns whatever is nearest to the query, whoever owns it. The snippet's store holds two tenants' refund policies and tickets, and five ordinary questions from tenant B, ranked over the whole store, all come back with tenant A's chunks in their top 3:

```text
cross-tenant leak test: 5 tenant-b queries, top 3, store shared with tenant-a
  rank, no tenant filter:  5 of 5 packs hold tenant-a chunks
  filter, then rank:       0 of 5 packs hold tenant-a chunks
  first query, unscoped, rank 1: doc-a2-c1 (tenant-a), "Ticket 4410: Priya Raman reported a dupl..."
  retrieve() with no tenant_id: refused (TypeError), the call fails closed
```

The defences are structural, not instructions to the model:

- **Filter, then rank.** Every retrieval carries a mandatory tenant filter applied before ranking, so another tenant's chunk is never a candidate, however similar. With the tenant as a required argument with no default, a call that forgets it fails closed instead of searching everything:

```python
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
```

- **Hard isolation for high-sensitivity tenants.** A separate index or namespace per tenant removes the class of bug, at the cost of more infrastructure. A shared index with a metadata filter is cheaper, but fails open if the filter is ever dropped, so the filter is a security control and is tested like one.
- **Memory scoped by tenant and subject.** A memory row is retrievable only within the tenant that wrote it, and within the user where memory is kept per user. A memory store shared across users is where post 23's memory poisoning and cross-tenant leakage meet.
- **A test of the boundary.** A leak test like the snippet's seeds tenant A with distinctive data, runs tenant B's queries and asserts that none of A's data appears in B's packs. It belongs in the evaluation suite of [post 20](../20-evaluation/index.md), beside post 23's injection lab.

The figure below draws the snippet's first tenant B query both ways.

![A tenant B question ranked over the whole shared store packs tenant A's chunks first; filtered to tenant B before ranking, the pack holds only tenant B's own chunks.](diagrams/04-filter-then-rank.svg)

*Ranking cannot keep a secret: only a filter applied before it keeps another tenant's data out of the candidates.*

Tenant isolation is enforced by retrieval and memory reads that fail closed on a missing scope, never by asking the model to ignore what it should not have been shown.

---

## 7. A governance checklist

Run it before shipping and on a schedule; a line with no owner is the next fix.

- **Data map.** Every inbound channel annotated with the most sensitive class of data it can carry (section 2).
- **Boundary detection.** PII detection at the trust boundary, in the same pass as injection filtering (section 3).
- **Redaction policy.** A written rule for what is redacted into the window and what into the trace store (section 3).
- **Retention.** A lifecycle rule on every store, set with counsel, with an audit record of each deletion (section 4).
- **Residency and ZDR.** Region and retention terms checked against the data-processing addendum, and the features outside ZDR listed (section 4).
- **Memory consent.** Personal-data writes tied to a recorded lawful basis; special-category content refused without an opt-in (section 5).
- **Erasure fan-out.** A tested procedure that reaches memory, documents, chunks, traces and the provider (section 5).
- **Tenant isolation.** A mandatory scope filter that fails closed, and a cross-tenant leak test (section 6).
- **Access control.** The trace store readable only by those allowed to read the underlying transcripts (post 22's privacy controls), and the vault on its own, stricter rule.

---

## 8. Make it run

Both snippets are standard-library Python, run from the series root in well under a second, with no network and no model call:

```text
uv run python posts/24-privacy-and-governance/snippets/pii_gate.py
uv run python posts/24-privacy-and-governance/snippets/governed_stores.py
```

Each ends with `gate: pass`. Three changes show the moving parts. Setting the `CARD` detector's check to `None` redacts the order number as a card, and the first gate fails. Changing a `"summarise"` task to `"act"` sends that prompt's values to the model while the trace store stays clean. Using `retrieve_unscoped` in the leak test makes it report leaks for tenant B.

---

## 9. What can go wrong?

- **The logger runs before the gate.** The logging middleware captures the request before the gate rewrites it: the window gets placeholders and the trace store the raw prompt. A search of the traces for a customer's email finds calls whose model input was redacted.
- **Placeholders compared across calls.** `<PERSON_1>` is numbered per call, so it names a different person in each trace; grouping traces by placeholder merges strangers.
- **The vault beside the traces.** Same access, same retention: whoever reads the traces can reverse them, and pseudonymisation protects nothing.
- **A summary policy applied to an action.** The window is redacted for a task about the person, and the model answers "I will email `<PERSON_1>`" or asks for the address it was given.
- **An erasure that misses derived copies.** An answer cache, a cold tier or a test set harvested from traces keeps the person's details, and the name reappears in a replayed test.
- **The tenant filter applied after ranking.** The pack is ranked over the whole store and then filtered: nothing foreign is packed, but tenant B's pack comes back short or empty whenever tenant A's chunks rank higher.

---

## Common pitfalls

1. **Forgetting the trace store.** Redacting the window while logging the raw prompt leaves the regulated copy in the store kept longest and read most widely.
2. **Blanket redaction.** Masking every value everywhere breaks tasks whose subject is the PII and strips traces of their debugging value.
3. **Retention by neglect.** With no lifecycle rule, traces accumulate for years, and every one is in scope for an erasure request.
4. **Provider ZDR treated as total coverage.** It does nothing for the application's own memory, index and trace stores, nor for the provider features it excludes.
5. **Trusting ranking for tenant isolation.** A shared index with no mandatory tenant filter returns the nearest chunk whoever owns it.
6. **Confusing governance with security.** Defences against an attacker do not stop the application's own pipeline from mishandling data it holds legitimately.

---

## Further reading

- NIST (National Institute of Standards and Technology), "AI 600-1: Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile" (July 2024): data privacy among the generative-AI risks it lists.
- OWASP (Open Worldwide Application Security Project), "Top 10 for Large Language Model Applications" (2025): LLM02:2025 Sensitive Information Disclosure.
- European Union, "General Data Protection Regulation" (Regulation (EU) 2016/679): Articles 5(1)(e), 6, 9 and 17, read at a high level, not as legal advice.
- Presidio documentation, including "Supported entities" (consulted October 2026).
- Anthropic, "API and data retention" and "Data residency" (Claude Platform documentation), and "How long do you store my organization's data?" (Anthropic Privacy Center), consulted October 2026.
- OpenAI, "Data controls in the OpenAI platform" (API documentation, consulted October 2026).

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 25 - Long context vs. RAG: a decision framework](../25-long-context-vs-rag/index.md):** the choice between loading a corpus and retrieving from it, where per-tenant data weighs on the side of retrieval.
- **[Post 16 - Memory systems](../16-memory-systems/index.md):** the store whose rows this post labels, gates and erases.
