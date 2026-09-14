# 24 · Privacy, PII, and data governance

> **TL;DR.** Every layer that feeds the model can carry regulated data: RAG chunks, long-term memory, conversation history, and (most easily overlooked) the trace store, which is a copy of every prompt you ever sent. That makes privacy a **cross-cutting context-assembly concern**, distinct from security ([Post 23](../23-security/index.md), which is about adversaries): here the risk is your own pipeline mishandling data that entered it legitimately. This post maps where regulated data enters the context, where to detect and redact it, how long to keep logged prompts and where, how to govern what memory persists, and how to keep one tenant's data out of another's context.
>
> **After reading this you will be able to:**
> - Trace where personally identifiable information (PII) enters the context pipeline and the trace store.
> - Place PII detection, redaction, retention, and residency controls at the right boundary without gutting answer quality.
> - Enforce memory consent, deletion, and multi-tenant isolation across a RAG and memory stack.

![Data-flow diagram: user input, RAG chunks, memory cells, and tool results converge on a detect-and-redact gate at the trust boundary, then fan out to the context window and the trace store, with retention and tenant-isolation notes downstream.](diagrams/00-hero-privacy-and-governance.svg)
*Redact at the boundary: regulated data should be caught before it reaches either the context or the trace store.*

> **Not legal advice.** This post frames GDPR, CCPA, and similar regimes at a high level to explain the *engineering* obligations they create. It is not legal advice, and the specifics of what a given regulation requires of your product are a question for your counsel and your data-protection officer, not for a blog post.

---

## 1. The trace store is a copy of every prompt

Start with the observation that surprises most teams the first time they draw the data-flow diagram: the observability layer ([Post 22](../22-observability/index.md)) records the full prompt and the full response for every call, because that artefact is the one most worth keeping for debugging. A span captures `model`, `prompt`, `response`, token counts, cost, and latency (Post 22, §2). The prompt field is, by construction, a verbatim copy of everything the context assembler packed into that call.

So whatever regulated data entered the context also entered the trace store. If a user pasted their medical history into the chat, it is in the trace. If a RAG chunk contained a customer's home address, it is in the trace. If a tool result returned a payment card number, it is in the trace. The trace store is not a summary of your prompts; it is a second, long-lived, widely-readable copy of them.

This is the crux of why governance is distinct from security. Security ([Post 23](../23-security/index.md)) asks what an *adversary* can do to your context: inject instructions, exfiltrate data, poison memory. Governance asks what *you* are doing with data that entered your context legitimately, through the front door, with the user's cooperation. No attacker is involved. The failure mode is a well-meaning pipeline that copies regulated data into several stores, keeps it indefinitely, replicates it across regions, and has no procedure to delete it when the user asks.

The practical consequence: you cannot govern data at a single choke point, because context is *assembled* from many sources and *copied* into several stores. Governance has to be designed into the assembly and logging path, the same way retrieval and caching are.

---

## 2. Where regulated data enters the context

A useful exercise before writing any control: enumerate every place regulated data can flow into a prompt. For a typical agent the list is short and the same every time.

```
                          ┌──────────────────────┐
   user message  ───────► │                      │
   RAG chunks    ───────► │  context assembler   │ ──► prompt ──► model
   memory cells  ───────► │  (packs the prompt)  │        │
   tool results  ───────► │                      │        └──► TRACE STORE
                          └──────────────────────┘             (verbatim copy)
```

*Four inbound channels feed the context assembler; the assembled prompt then fans out to the model and, verbatim, to the trace store.*

- **User input.** The most obvious channel and the hardest to bound. Users paste anything: contracts, health records, screenshots of bank statements, other people's PII. You control the schema of everything else in the prompt; you do not control this.
- **RAG chunks.** Retrieval ([Post 11](../11-rag-in-depth/index.md)) pulls from a corpus you indexed. If that corpus contains regulated data (support tickets, HR documents, customer emails), retrieval will surface it into the prompt whenever it is relevant to a query. The chunk was compliant sitting in the store; it becomes a governance event when it is copied into a prompt and then into a trace.
- **Memory cells.** Long-term memory ([Post 16](../16-memory-systems/index.md)) persists facts and preferences across sessions. Semantic memory in particular tends to accumulate exactly the data privacy regimes care about: "the user's employer is X", "the user's diagnosis is Y". Memory is a governed store by nature, covered in §5.
- **Tool results.** A `lookup_account` tool returns a customer's plan, address, and ticket history straight into context (the same read tool that Post 23 §2 uses in its exfiltration chain). Tool outputs are frequently the highest-density source of regulated data in the whole prompt, because they come from systems of record.

Every one of these four channels is also, downstream, a write into the trace store. Annotate each arrow with the *most sensitive* class of data it can carry; that annotation is the input to every decision in the rest of this post.

---

## 3. Detection and redaction at the trust boundary

The place to act on regulated data is the **trust boundary**: the point where external text crosses into your context (or into your trace store). This is the same boundary Post 23 §3 uses for injection filtering, and it is efficient to run both checks in the same pass. The difference is intent: injection filtering looks for adversarial *instructions*; PII filtering looks for regulated *data*.

![Three PII-detection layers in increasing cost, the tradeoff that redaction can destroy the task, and the three places redaction applies differently](diagrams/01-detect-and-redact.svg)

*Detection layers cheapest first. Redaction is a scalpel, and where it is applied matters more than whether it is.*

**Detection** typically layers three techniques, cheapest first:

- **Regex and format rules** catch structured PII: card numbers (with a Luhn check), national identifiers, email addresses, phone numbers. Fast, deterministic, and high-precision on formats that have a checksum.
- **Named-entity recognition (NER)** catches unstructured PII: person names, locations, organisations. A small model does this well and cheaply. Open tooling such as Microsoft Presidio packages both regex recognisers and NER for exactly this job (Microsoft, "Presidio," ongoing).
- **An LLM classifier** catches the context-dependent cases the first two miss ("the patient", "her account balance"). Slower and costlier, so it is usually a fallback for high-risk paths, not the default.

**Redaction** then replaces detected spans with typed placeholders (`<PERSON_1>`, `<EMAIL_1>`) rather than deleting them, so the surrounding text still parses and, where you need it, the mapping can be reversed inside the trust boundary.

The hard tradeoff is that **redaction can hurt answer quality.** If you redact "email John Smith at john@acme.com" down to "email `<PERSON_1>` at `<EMAIL_1>`", the model can no longer complete the task, because the task *was* the PII. This is why Post 22 (§2) makes the deliberate call to **not redact the prompt in the trace unless there is a hard regulatory reason**: the prompt is the artefact most worth keeping for debugging, and blanket redaction destroys it. Reconcile the two positions like this:

- Redact into the **context** only when the model genuinely does not need the PII to do the job (a good default for free-text uploads feeding a summarisation task; a bad default for a task whose subject is the PII).
- Redact into the **trace store** as a compliance layer, applied *selectively* to the fields a regulation actually names, accepting that you trade some debugging value for it (Post 22, §7).
- Prefer **tokenisation over deletion**: swap the real value for a reversible token, keep the mapping in a separate, tightly-access-controlled vault, and let authorised debugging reverse it. This preserves referential structure without spreading the raw value.

Redaction is a scalpel, not a firehose: run detection at the boundary once, redact into the trace by policy, and redact into the live context only when quality allows.

---

## 4. Retention and residency of logged prompts

Once you accept that traces are copies of prompts, two questions follow immediately: how long do you keep them, and where do they physically live.

![Three retention tiers along a time axis — full fidelity, redacted, hard deletion — beside residency and the zero-retention trap](diagrams/02-retention-tiers.svg)

*The regulation sets the shape, not the number. The engineering point is that a lifecycle rule enforces it, not a remembered script.*

**Retention.** A trace store without a retention policy grows without bound, and every day of extra retention is extra exposure and extra scope for a subject-access or deletion request. The policy is set by the regulatory environment, not by disk being cheap (Post 22, §7). GDPR's storage-limitation principle requires that personal data be kept no longer than necessary for the purpose it was collected for (EU, "GDPR" Art. 5(1)(e), 2016); it does not name a number, so any specific window is your policy choice. Common practice is a short, tiered scheme, offered here as an illustrative shape rather than a mandated figure:

- Full-fidelity traces (prompt and response verbatim) for a short debugging window.
- Redacted or aggregated traces for a longer analytics window.
- Hard deletion, with an audit record that the deletion happened, after that.

Set the number to what your regulatory environment and counsel require; the engineering point is that the store enforces the policy automatically, by lifecycle rule, not by someone remembering to run a cleanup script.

**Residency.** Some regimes constrain *where* personal data may be processed and stored, which has a direct architectural consequence, because your model provider is a data processor in another region. Two levers matter:

- **Regional endpoints and processing.** Major providers offer region-pinned inference and documented sub-processor lists so that data does not leave a jurisdiction. Treat the region guarantee as a contract to check, not an assumption.
- **Zero-data-retention (ZDR) options.** Several providers offer a mode in which prompts and completions are not retained on their side beyond the request, or are exempt from human review and training use. Anthropic, for example, documents that API inputs and outputs are not used to train its models by default and offers zero-retention arrangements for eligible customers (Anthropic, "Privacy and data usage," 2024–25); OpenAI documents a comparable API default and zero-retention options (OpenAI, "Enterprise privacy," 2024–25). Terms and eligibility differ by provider and change often, so verify against the current data-processing addendum rather than a blog summary.

ZDR on the provider side does not absolve *your* trace store. If you enable zero retention with the provider but log the full prompt in your own observability stack, you have simply moved the regulated copy from their systems to yours. Governance is about the whole set of copies, not the provider's copy alone.

---

## 5. Memory governance: consent, persistence, and the right to be forgotten

Memory ([Post 16](../16-memory-systems/index.md)) is the layer where governance stops being about transient copies and becomes about a durable store that speaks for the user across sessions. It deserves its own controls.

**What may persist.** Not everything the model learns should be written to long-term memory. Semantic memory accumulates preferences and facts, and some of those facts are special-category data (health, ethnicity, sexual orientation, political views) that many regimes protect more strictly. A sound default is an allow-list: memory writes are permitted for operational preferences and denied for special-category content unless the user has explicitly opted in. Post 16's memory cells already carry a `source` and a trust tag (Post 23, §3, Defence 4); add a `sensitivity` field so a governance filter can act on it at write time.

**Consent.** Persisting a fact about a person is a processing decision, and several regimes require a lawful basis for it. In practice this means memory writes of personal data should be tied to a recorded consent state, and the store should be able to answer "why is this cell held" with a pointer to that basis. A cell whose lawful basis you cannot name is a cell you should not be holding.

**Right to be forgotten and deletion.** GDPR's right to erasure (EU, "GDPR" Art. 17, 2016) obliges you, on request, to delete a subject's personal data. For an LLM stack this is not one delete; it is a fan-out across every store that holds a copy:

```
deletion request (user_id = U)
  ├─ memory store    → delete/soft-delete all cells where subject = U
  ├─ RAG corpus      → remove source docs about U; re-index
  ├─ trace store     → purge or redact traces where user_id = U
  └─ provider side   → invoke provider deletion / rely on ZDR
```

*A single erasure request fans out to every store that holds a copy of the subject's data.*

The design lesson mirrors Post 23's memory-revocation procedure (Post 23, §6): query by subject, source, and content pattern, soft-delete with an audit trail, and re-validate anything (a cache, a retrieval index) that depended on the deleted data. A deletion that only clears the memory store, leaving the same PII in the trace store and the RAG index, does not satisfy the request. Build the fan-out before you need it, because you will be asked to run it under a clock.

---

## 6. Tenant isolation in multi-tenant RAG and memory

The single most damaging governance bug in a multi-tenant product is leaking tenant A's data into tenant B's context. It is a context-assembly failure: the retriever or the memory reader returned a chunk or a cell belonging to the wrong tenant, and it was packed into a prompt where it never belonged. Post 25 (§5) lists multi-tenant data as a reason RAG beats loading everything; the flip side is that RAG's retrieval step is exactly where cross-tenant leakage happens.

The failure is easy to introduce and hard to see, because a shared vector store returns whatever is nearest in embedding space regardless of ownership. The defences are structural, not prompt-level:

- **Filter, do not trust ranking.** Every retrieval query carries a mandatory `tenant_id` filter applied *before* similarity ranking, so a chunk from another tenant is never a candidate, however similar it is. Making the filter a required argument (so a query without it fails closed) is stronger than remembering to add it.
- **Prefer hard isolation for high-sensitivity tenants.** A per-tenant index or namespace removes the class of bug entirely, at the cost of more infrastructure. A shared index with a metadata filter is cheaper and adequate for many workloads, but it fails *open* if the filter is ever dropped, so treat the filter as a security control and test it.
- **Scope memory by subject and tenant.** A memory cell is retrievable only within the tenant (and usually the user) that wrote it. Cross-user memory in a shared store is where Post 23's memory-poisoning risk and the cross-tenant-leak risk overlap.
- **Test the boundary directly.** Add an eval ([Post 20](../20-evaluation/index.md)) that issues tenant B's queries against a store seeded with tenant A's distinctive data and asserts that none of A's data appears in B's retrieved pack. It belongs in the same suite as your security tests.

The principle: tenant isolation is enforced by the retrieval and memory layers failing *closed* on a missing scope, never by the model being asked politely to ignore data it should not have been shown.

---

## 7. A governance checklist

A one-page checklist to run before shipping, and quarterly after. If a line has no owner, that is the next thing to fix.

- **Data map.** Every inbound channel (user, RAG, memory, tools) annotated with the most sensitive data class it can carry (§2).
- **Boundary detection.** PII detection runs at the trust boundary, in the same pass as injection filtering (§3).
- **Redaction policy.** Explicit rule for what is redacted into context vs. into the trace, with the quality tradeoff acknowledged (§3).
- **Retention.** Automated lifecycle deletion of traces, set by regulation, not convenience, with an audit record of deletion (§4).
- **Residency and ZDR.** Provider region and retention terms verified against the current data-processing addendum, not assumed (§4).
- **Memory consent.** Personal-data memory writes tied to a recorded lawful basis; special-category content gated (§5).
- **Deletion fan-out.** A tested erasure procedure that reaches memory, RAG, traces, and the provider (§5).
- **Tenant isolation.** Mandatory scope filter that fails closed, plus a cross-tenant leak eval (§6).
- **Access control.** The trace store is readable only by those allowed to read the underlying transcripts (Post 22, §7).

The checklist is deliberately mechanical. Governance failures are rarely exotic; they are almost always a missing lifecycle rule, a dropped filter, or a deletion that reached three stores out of four.

---

## Common pitfalls

- **Forgetting the trace store.** Redacting the live context but logging the raw prompt verbatim leaves the regulated copy in the most widely-read store you own.
- **Blanket redaction.** Masking all PII everywhere guts answer quality on tasks whose subject *is* the PII, and destroys the debugging value of traces (Post 22, §2).
- **Retention by neglect.** No lifecycle rule, so traces accumulate for years and every one is deletion-request scope.
- **Provider ZDR treated as total coverage.** Zero retention on the provider side does nothing for the copies in your own memory, RAG, and trace stores.
- **Deletion that reaches only one store.** An erasure that clears memory but leaves the same PII in the trace store and the RAG index does not satisfy the request.
- **Trusting ranking for tenant isolation.** A shared index with no mandatory `tenant_id` filter returns the nearest chunk regardless of owner; the filter must fail closed.
- **Confusing governance with security.** Assuming Post 23's adversary defences cover privacy; they address a different failure mode (an attacker), not your own pipeline mishandling data it holds legitimately.

---

## Further reading

- NIST, *"AI 600-1: AI Risk Management Framework — Generative AI Profile"* (2024): the data-privacy and data-governance subcategories that this post operationalises.
- OWASP, *"Top 10 for LLM Applications"* (2025 edition): LLM02 Sensitive Information Disclosure is the security-side complement to this post.
- EU, *"General Data Protection Regulation (GDPR)"* (2016): storage limitation (Art. 5), right to erasure (Art. 17), read at a high level, not as legal advice.
- Microsoft, *"Presidio"* (ongoing): open-source PII detection and anonymisation tooling for the §3 boundary.
- Anthropic, *"Privacy and data usage"* and OpenAI, *"Enterprise privacy"* (2024–25): the provider data-retention and zero-retention terms referenced in §4; verify against the live pages.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 25 — Long context vs. RAG](../25-long-context-vs-rag/index.md)**: the retrieval-vs-loading decision, including why per-tenant data pushes you toward RAG (§6 here is its governance flip side).
- **[Post 23 — Security and prompt injection](../23-security/index.md)**: the adversary-facing companion to this post; same trust boundaries, different threat model.
- **[Post 16 — Memory systems](../16-memory-systems/index.md)**: the store whose consent, persistence, and deletion this post governs.
