# 14 · Memory systems

> **TL;DR.** Memory is the layer that lets an agent remember what it learned yesterday without paying token cost for it today. The framework worth memorising is the **three-kind taxonomy** — **episodic** (events), **semantic** (facts and preferences), **procedural** (rules and how-tos) — each with its own write trigger, retrieval strategy, decay policy, and access pattern. This post is the engineering account: what each kind contains, what schema each needs, how to retrieve from each, and how to keep them all from poisoning each other.
>
> **Reading time:** ~12 minutes.
>
> **After reading this you will be able to:**
> - Distinguish episodic, semantic, and procedural memory and route data to the right one.
> - Specify the minimum metadata each memory cell needs.
> - Avoid the four classes of bug that turn a memory store into an active liability.

![Memory taxonomy](../../assets/diagrams/exports/08-memory-taxonomy.svg)

---

## 1. Why three kinds

The temptation is to call the whole thing "memory" and store everything in one table. Production teams that have done this all run into the same wall: the access patterns are different. A user-stated preference ("I prefer markdown") is small, durable, and asserted on most turns. An event ("user resolved ticket #4321 last Tuesday") is medium-sized, time-anchored, and only relevant when the user references that ticket. A rule ("refunds over $1 000 require manager approval") is large-impact, near-permanent, and gets retrieved by *intent* rather than *content*.

Trying to cover all three with one schema, one retrieval strategy, and one decay policy means each is served badly.

The taxonomy used here — episodic / semantic / procedural — comes from cognitive science (Tulving, 1972) by way of the agent-memory papers of 2023 (Generative Agents, MemGPT) and the framework rebrandings since. It is small enough to memorise and large enough to cover what production systems need.

---

## 2. Episodic memory

**What it stores.** Events. Things that happened, with a *when* and a *who*. *"On 14 March, the user reported a billing error and resolved it by escalating to the billing team."* *"Three sessions ago, the agent recommended Postgres; the user adopted it."*

**When it gets written.** At the end of an interaction, when something noteworthy happened. The decision of "noteworthy" is itself a small LLM judgement: did the user state a preference, take an action, react strongly, hit an error, achieve a goal? If yes, write an episode.

**The minimum schema.**

| Field | Notes |
|---|---|
| `id` | Stable reference |
| `subject` | Who the episode is about (user id, project id) |
| `event_type` | `decision` / `error` / `preference` / `action` — drives downstream filtering |
| `summary` | One sentence. The retrievable form. |
| `details` | Optional longer narrative. Not retrieved on the fast path. |
| `source` | Conversation id, ticket id, transcript URL |
| `timestamp` | When the event happened |
| `confidence` | 0–1; lowers as the episode ages without confirmation |

**How it gets retrieved.** Two access patterns. (a) *Reference recall* — the user mentions an entity ("the issue we had last week"), retrieval pulls episodes mentioning that entity. (b) *Background grounding* — the agent fetches the *N* most recent episodes about this subject as soft context for any turn. Both retrieve through the standard Select pipeline ([Post 08](../08-select-strategies/index.md)) over `summary` text plus metadata filters on `subject` and time range.

**Decay.** Episodic facts age. A 6-month-old preference may have changed; a 6-month-old project decision is probably still valid. The simplest workable policy: drop `confidence` by a small amount every quarter without re-confirmation; demote below threshold to a colder tier (still searchable, less prominent) instead of deleting.

---

## 3. Semantic memory

**What it stores.** Facts and preferences. Things the agent should treat as currently true. *"The user prefers replies in formal English."* *"This customer is on the enterprise tier."* *"The team uses Postgres in production and DuckDB for analytics."*

**When it gets written.** On explicit assertion ("remember that I work in PST") or on observed pattern (the user has corrected the agent's tone twice in the same direction). The threshold for "observed pattern" is the source of most semantic-memory bugs — too low and the store fills with noise; too high and obvious preferences never get captured.

**The minimum schema.** Mostly the same fields as episodic, with two differences: `event_type` becomes `kind` (`preference`, `fact`, `relationship`); `timestamp` is the most-recent-confirmation time, not the original observation time.

**How it gets retrieved.** Almost always *background*. On every turn (or every *N* turns), pull the top-*k* semantic facts about the current subject; pack them into the memory layer of the prompt. Because the layer is small (Post 04, §6: 5–10 % of budget), the *ranking* matters: most-recently-confirmed first, then most-frequently-relevant.

**Conflict.** Semantic memory has the hardest write semantics of the three. The user said "use formal English" three months ago; today they used a casual greeting; should the preference change? The pattern that works:

- **Never silently overwrite.** Two contradicting cells coexist for a while; the older one's `confidence` decays; eventually it falls below threshold.
- **Surface the conflict on relevant turns.** "I have you down as preferring formal replies — should I keep using that style?" One round-trip per conflict; cheap insurance.

---

## 4. Procedural memory

**What it stores.** How-tos and rules. Reusable patterns. *"To deploy a hotfix, run `make hotfix && git push origin hotfix/<id>`."* *"Refunds over $1 000 require manager approval."* *"When the user says 'urgent', skip the standard intake form."*

**When it gets written.** Rarely. Procedural memory is the most-edited *manually* — it tends to live in `AGENTS.md` files ([Post 07](../07-write-strategies/index.md), §4) rather than in a vector store. New rules get added in a PR by a human, with review.

**Schema and retrieval.** Procedural memory blurs into the system-prompt rules block ([Post 12](../12-system-prompt-as-software/index.md), §2). The pragmatic split:

- Rules that apply to *every* turn → live in the system prompt.
- Rules that apply *conditionally* (only for this customer, only for this project, only when this tool is being called) → live in a procedural store and get retrieved by trigger.

The retrieval pattern for the conditional case is **trigger matching**, not semantic search. *"User is on the enterprise tier"* triggers a known set of procedural cells. The store is essentially a small rules engine; the LLM is the executor.

**Decay.** Procedural memory does *not* decay. Stale rules are removed by humans, not by time. A confidence score is meaningless here.

---

## 5. The retrieval orchestrator

A live agent with all three memories needs to answer, on every turn, three questions:

1. Which **semantic** facts about this subject should I include? (Background grounding.)
2. Are any of the user's words **referring** to a past episode I should retrieve? (Reference recall.)
3. Do any **procedural** rules trigger for this turn? (Rule matching.)

The order matters. Procedural rules first (they may rule out the turn entirely — "do not respond to this user, escalate"). Semantic facts second (they shape tone and assumptions for the rest of the turn). Episodic recall last and conditionally (only if the user's turn references something specific).

A useful pattern is to **wrap the three retrievals in a single "context assembler" call** that the rest of the agent code does not have to know about. The call returns a `MemoryContext` object that the prompt assembler stitches into the right layers.

---

## 6. The four bugs

Almost every memory-related production incident reduces to one of four bugs.

**Bug 1 — undifferentiated store.** Episodic, semantic, and procedural data in one table. Symptom: agent over-anchors to a stale event, or treats a one-time tool result as a persistent fact, or refuses to act on a procedural rule because it scored below an episode for retrieval. Fix: three tables, three policies, three retrieval strategies.

**Bug 2 — no provenance.** A memory cell asserts a fact; the cell has no `source`; the user disputes it; nobody can find where the agent learned it. Fix: every cell carries `source` and `created_at` and (for semantic) `last_confirmed_at`. Recovery: bulk re-validation pass.

**Bug 3 — no decay.** Memories never expire. Old preferences override new ones. The agent insists the user uses Vim despite the last six sessions being in VS Code. Fix: confidence decay schedule; periodic "is this still true?" prompts on aging cells.

**Bug 4 — silent overwrite.** Conflicting facts overwrite each other; history is lost. The agent has no way to detect that the user changed their mind. Fix: append-only writes; conflict resolution at retrieval, not write, time.

These are small disciplines. They are also the difference between memory that helps and memory that quietly degrades quality.

---

## 7. Memory in the prompt

How the retrieved memory actually appears in the prompt matters. A skeleton that travels well:

```
[memory: facts you have stored about this user]
- Prefers formal English replies. (last confirmed 14 days ago)
- On the enterprise tier. (verified from billing system)
- Resolved ticket #4321 by escalating to billing on 14 March.

[memory: rules that apply to this conversation]
- Enterprise tier customers may exceed standard rate limits.
- Always offer the call-back option after the second message.
```

Notice the structure: three labelled sub-sections (semantic / procedural / episodic, in the retrieval-orchestrator order from §5), each with the source or date in parentheses, each item one line. The model uses the structure as a hint — it treats the procedural items as imperatives, the semantic items as defaults, the episodic items as background.

---

## 8. When *not* to use a memory store

A short tour of cases where the right answer is "no memory".

- **Stateless tools.** A pure function (a calculator, a unit converter, a regex tester) does not need memory. Adding it adds bugs.
- **Single-turn use.** A search box is not an agent; do not bolt a memory store onto it.
- **Sensitive interactions.** Health, financial, legal advice in some jurisdictions: persisting user statements across sessions is a regulatory liability. Either store nothing or store with explicit consent and clear deletion.
- **Where humans expect amnesia.** Some user experiences are *better* without memory. A mood-journal agent that forgets between entries respects the user's privacy in a way one that "remembers" might not.

The strongest agent designs are explicit about what they do and do not remember, and tell the user.

---

## Common pitfalls

- **One table for all three kinds.** The single largest design mistake in this area.
- **Writing tool results to long-term memory.** Tool results are transient. Re-call, do not remember.
- **No `source`.** The cell that turned out to be wrong is unrecoverable.
- **No decay.** Old facts compete with new ones forever.
- **Silent overwrite on conflict.** History is lost; the agent cannot explain itself.
- **Storing secrets.** Secrets belong in a secret manager; never in a memory store.
- **Background-grounding the entire memory store.** The memory layer is small; rank, do not pack everything.

---

## Further reading

- Tulving, E., *"Episodic and semantic memory"* (1972) — the source of the three-kind taxonomy.
- Park, J. *et al.*, *"Generative Agents: Interactive Simulacra of Human Behavior"* (2023).
- Packer, C. *et al.*, *"MemGPT: Towards LLMs as Operating Systems"* (2023) — tiered memory with explicit eviction.
- LangChain Blog, *"The state of AI agents — memory"* (2024).
- Letta (formerly MemGPT), *"Building Agents with Long-Term Memory"* (2024 docs).

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 15 — Advanced retrieval](../15-advanced-retrieval/index.md)** — the techniques that power memory retrieval.
- **[Post 07 — Write strategies](../07-write-strategies/index.md)** — the persistence side, in depth.
- **[Post 18 — Security](../18-security/index.md)** — what an attacker can do once they can write to memory.
