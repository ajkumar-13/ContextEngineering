# 16 - Memory systems

> **TL;DR.** An agent remembers across sessions only what the application writes to a store and selects back into layer 03, memory and state. This post asks why that store needs three kinds of memory, episodic (events), semantic (facts and preferences) and procedural (learned rules), and how each is written, retrieved, decayed and kept from corrupting the others. The three share post 08's nine-field row plus a trigger for rules, each has its own retrieval path in a fixed order, and four classes of bug, post 08's three plus the wrong kind, turn the store into a liability.
>
> **Prerequisites:** [Post 08](../08-write-strategies/index.md).
> **Safe to skip?** Skip it if every memory an agent keeps already has a kind, a source, a retrieval path suited to that kind and a decay rule, and learned rules are kept apart from preferences and events.
>
> **After reading, you will be able to:**
>
> - Distinguish episodic, semantic and procedural memory, and route a piece of information to the right kind, or to no memory store at all.
> - Specify the metadata each memory row needs: post 08's nine fields, how each kind uses them, and the trigger a procedural row adds.
> - Retrieve from each kind by its own path (trigger match, background ranking, reference recall) in the orchestrator's order, with decay applied on read.
> - Recognise the four classes of bug that turn a memory store into a liability, and the guard against each.
> - Choose between a vector store, a temporal knowledge graph and tiered paging (Mem0, Zep, Letta) for a workload, or decide that no memory store is wanted.

![Three memory stores in the order they are read: procedural holds learned rules, retrieved by trigger match, no decay; semantic holds facts and preferences, retrieved as background top-k, decays; episodic holds events, retrieved by reference recall, decays. Each feeds 03 Memory and state in the six-layer window.](diagrams/01-three-kinds.svg)

*Three stores, three write triggers, three retrieval paths and two decay policies, all feeding one layer. One table with one policy serves each of them badly.*

---

## 1. The question: what does an agent remember, and where?

A large language model (LLM) is stateless. The model weights do not change between calls, and the model retains nothing from one request to the next: every turn, whatever the model should know has to be supplied in the request or it is gone. What feels like a chatbot "remembering" the earlier part of a conversation is the host replaying the transcript on each call. Nothing is stored in the model.

That gives two distinct problems:

- **Short-term memory** is the working set of the current task. The conversation history is layer 05: it sits in the window and costs tokens on every call. A scratchpad is a file outside the window that the agent writes between iterations and reads back by select ([post 08](../08-write-strategies/index.md), section 3); only the part read back costs tokens. Both end with the task.
- **Long-term memory** is what survives across sessions: preferences, past events, learned rules. It lives in a store outside the window, and it costs tokens only for the slice selected into layer 03, memory and state, on a given turn.

This post is about the long-term store; short-term memory belongs to post 08 (write) and [post 12](../12-compress-strategies/index.md) (compress). The question is why an agent that remembers needs three different memories, and how each is written, retrieved, decayed and kept from corrupting the others. The figure at the top of the post is the answer in outline.

---

## 2. Why three kinds

The temptation is to call the whole thing "memory" and keep it in one table. The trouble with a single store is that the access patterns differ. A stated preference ("prefers replies in formal English") is small, durable and relevant on most turns. An event ("resolved ticket 4321 on 14 September by escalating the billing error") is time-anchored and relevant only when the user refers to it. A learned rule ("ask for the purchase-order number before discussing a refund") is obeyed rather than weighed, and it is relevant when a condition holds, whatever the words of the turn.

Covering all three with one schema, one retrieval strategy and one decay policy serves each badly: the preference is buried under events, the event is treated as a standing fact, and the rule scores below an episode in a similarity search and never fires.

The names come from cognitive psychology. Tulving (1972) separated episodic memory, of personally experienced events placed in time, from semantic memory, of general knowledge held without a record of when it was learned. Procedural memory, of how to do things, joined them later: Tulving's "How many memory systems are there?" (1985) arranged procedural, semantic and episodic memory as three systems. The three kinds reached language agents through the Cognitive Architectures for Language Agents framework (CoALA; Sumers et al., 2023), which gives an agent a working memory and three long-term memories: episodic, for experience from earlier decision cycles; semantic, for knowledge about the world and itself; procedural, held in the model's weights and the agent's code. Harrison Chase's "Memory for Agents" (LangChain, October 2024), which post 08 cites for the three kinds, takes them from CoALA. This series' procedural kind is narrower than CoALA's: it holds rules and how-tos written as text, not weights or code.

---

## 3. One row for all three kinds

[Post 08](../08-write-strategies/index.md), section 2, fixes the row every memory store carries: `id`, `kind`, `subject`, `content`, `source`, `created_at`, `last_accessed_at`, `confidence` and `expires_at`. Episodic and semantic rows use the nine fields as they stand; a procedural row adds one field, `trigger`, keeps the rule in `content`, and uses `subject` as the rule's scope:

| Field | Episodic | Semantic | Procedural |
|---|---|---|---|
| `id`, `kind`, `source` | as post 08 | as post 08 | as post 08 |
| `subject` | who the event is about | who the fact is about | the scope: the user, account or project the rule applies to |
| `content` | the event, one sentence | the fact or preference | the rule |
| `created_at` | when the event was written | when the fact was first asserted | when the rule was learned |
| `last_accessed_at` | drives decay | drives decay | kept for audit; drives nothing |
| `confidence` | decays | decays; below a cutoff, ask before asserting | fixed at 1.0 |
| `expires_at` | rarely set | for knowingly short-lived facts | not used: a person removes a rule |
| `trigger` (added) | none | none | the condition that fires the rule |

A store may add fields (a sensitivity label for the governance filter of [post 24](../24-privacy-and-governance/index.md)); it never drops one of the nine. One use changes: post 08 updates `last_accessed_at` on every read, while this post updates it only for the rows an answer relied on, for the reason section 15 gives. The post's snippet, `snippets/memory_layer.py`, declares the row this way:

```python
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
```

Its write method refuses a row with no `source`, an unknown `kind`, or a `trigger` on anything but a procedural row, and it only appends: a contradiction becomes a new row, never an edit of the old one.

---

## 4. Episodic memory

**What it stores.** Events: things that happened, with a when and a who. *"Resolved ticket 4321 on 14 September by escalating the billing error."* *"Three sessions ago, the agent recommended Postgres and the user adopted it."*

**When it is written.** At the end of an interaction, when something noteworthy happened. Deciding what is noteworthy is itself a small model judgement: did the user state a preference, take an action, react strongly, hit an error, reach a goal? If so, write an episode.

**How it is retrieved.** Two access patterns. *Reference recall*: the user mentions an entity or a past exchange ("the issue from last week"), and retrieval pulls the episodes that mention it. *Background grounding*: the agent fetches the few most recent episodes about the subject as soft context for any turn. Both are the select pipeline of [post 09](../09-select-strategies/index.md) over `content`, with filters on `subject` and a `created_at` range. The snippet implements reference recall only, and only when the turn refers to the past; a word-overlap score stands in for an embedding search.

**Decay.** Episodes age: last spring's complaint rarely matters to this week's question. The snippet uses post 08's illustrative scheme, confidence lowered by 0.01 for every day without a read, and treats a row below an illustrative 0.4 as cold: kept in the store, never packed by default. A production cold tier stays searchable on an explicit request. Decay is a schedule the team chooses, not something that happens by itself.

---

## 5. Semantic memory

**What it stores.** Facts and preferences the agent should treat as currently true. *"Prefers replies in formal English."* *"Is on the enterprise tier."* *"The team uses Postgres in production and DuckDB for analytics."*

**When it is written.** On explicit assertion ("remember that I work in Pacific time") or on an observed pattern (the user has corrected the agent's tone twice in the same direction). Set the pattern threshold too low and the store fills with noise; too high, and obvious preferences are never captured.

**How it is retrieved.** In the background: on every turn, or every few turns, the top-k semantic rows about the current subject are packed into layer 03. The layer is small, 5 to 10 percent of the input budget in [post 04](../04-tokens-windows-budgets/index.md)'s illustrative defaults (its section 6), so the ranking matters. The snippet ranks by decayed confidence and then by the last read, and packs the top 3. Generative Agents (Park et al., 2023) ranked its memory stream by a richer score: recency, an exponential decay over the sandbox game hours since a memory was last retrieved (decay factor 0.995), plus importance and relevance, each normalised and summed with equal weights.

**Conflict.** Semantic memory has the hardest write semantics of the three. Three months ago the user asked for formal English; today they opened with a casual greeting. Two rules hold up:

- **Never overwrite in place.** The new fact is a new row with its own source; the old row keeps its source and decays. Which one is packed is decided by the precedence rule of [post 06](../06-context-failure-modes/index.md), section 4 (the most recent wins; on a tie, the higher confidence), and the history of the change survives.
- **Surface a doubtful fact instead of asserting it.** Below post 08's illustrative cutoff of 0.6, the snippet still packs the fact but marks it "unconfirmed: ask before relying on it". One question to the user costs one round trip; a wrong assertion costs trust.

---

## 6. Procedural memory

**What it stores.** How-tos and rules learned about one user, account or project: for a client whose system needs comma-separated values (CSV) and rejects a Portable Document Format (PDF) file on its own, *"Export this client's reports as CSV first; their system rejects a PDF on its own."*

**Where a rule lives.** Not every rule is procedural memory. [Post 08](../08-write-strategies/index.md) gives rules three homes, and this post keeps them apart:

- A rule for every user and every turn, written by the team ("refunds above $1,000 go to the manager queue"), belongs in the rules block of layer 01, the system prompt ([post 14](../14-system-prompt-as-software/index.md)), or in the repository's `AGENTS.md` (post 08, section 4). People write it and review it like code.
- A packaged capability with its own instructions belongs in a skill's `SKILL.md`, loaded only when a task needs it (post 08, section 4).
- A rule learned from one user or account, which applies only when a condition holds, is a procedural row in the memory store. That is the procedural kind of this post.

**When it is written.** Rarely: on an explicit instruction ("always send this client CSV"), or when the same correction recurs. Because a rule is obeyed rather than weighed, a new procedural row deserves a confirmation step before it is written: the agent repeats the rule back to the user, or a person approves it.

**How it is retrieved.** By **trigger matching**, not by similarity search. The turn's facts (its intent, the account's tier, the tool about to be called) are checked against each row's `trigger`, and every rule whose trigger is true fires, unranked. The snippet's three procedural rows read like a lookup table:

| `trigger` | `content` (the rule) | `subject` (the scope) |
|---|---|---|
| `intent=export` | Export this client's reports as CSV first; their system rejects a PDF on its own | `user:u-17` |
| `intent=escalate` | Copy every escalation to the account's named technical contact | `user:u-17` |
| `intent=refund` | Ask for the purchase-order number before discussing a refund | `user:u-17` |

The contrast with semantic memory is exact: semantic retrieval asks "which facts are most worth packing for this turn?" and ranks; procedural retrieval asks "which triggers are true right now?" and returns every match.

**Decay.** None. A rule is not less true for being unused for five months; it is removed by a person when it stops applying. Its `confidence` stays at 1.0 and its `last_accessed_at` drives nothing.

---

## 7. The retrieval orchestrator

A live agent with all three memories answers three questions on every turn:

1. Do any **procedural** rules trigger for this turn? (Trigger match.)
2. Which **semantic** facts about this subject should be packed? (Background grounding.)
3. Does the turn **refer** to a past episode that should be recalled? (Reference recall.)

The order matters. Procedural rules come first, because a rule can change what the turn is ("escalate this account's billing complaints to a person" may end it). Semantic facts come second, because they shape tone and assumptions for the rest of the turn. Episodic recall comes last and only when the turn refers to something specific, so most turns never pay for it.

The three retrievals sit behind one call that returns a `MemoryContext`, a record with one list per kind, which the prompt assembler turns into layer 03; the rest of the agent never needs to know there are three stores. The snippet's `retrieve` method is the whole orchestrator:

```python
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
```

The figure below follows the snippet's second turn through the three paths. Each path is a select in [post 09](../09-select-strategies/index.md)'s sense over its own corpus, with its own query and its own ranking signal.

![One turn about ticket 4321 runs down three paths in order: the procedural path fires mem-09; the semantic path packs mem-02, mem-01 and mem-03, the last marked ask, and leaves mem-04 cold; the episodic path, run because the turn says back, recalls mem-05. The lists merge into one MemoryContext for 03 Memory and state.](diagrams/02-orchestrator.svg)

*Rules first, because a rule can change what the turn is; episodes last, and only when the turn points at the past.*

---

## 8. Decay on read

Decay is applied when a row is read, from the stored values, and never written back:

```python
def confidence_on(row: MemoryRow, today: date) -> float:
    """Decay on read: computed from the stored row, never written back."""
    if row.kind == "procedural":
        return row.confidence          # a rule does not decay; a person removes it
    if row.expires_at and today > date.fromisoformat(row.expires_at):
        return 0.0
    idle = (today - date.fromisoformat(row.last_accessed_at)).days
    return max(0.0, round(row.confidence - DECAY_PER_IDLE_DAY * idle, 2))
```

The store keeps its history, because nothing is edited, and the schedule can change without a migration. On 12 October the snippet prints this table for its ten rows:

```text
confidence on 2026-10-12 (0.01 per idle day; procedural rows do not decay):
  mem-01  semantic    idle   3 days  0.87  live
  mem-02  semantic    idle   2 days  0.98  live
  mem-03  semantic    idle  30 days  0.50  ask
  mem-04  semantic    idle 103 days  0.00  cold
  mem-05  episodic    idle  28 days  0.72  live
  mem-06  episodic    idle  10 days  0.90  live
  mem-07  episodic    idle 131 days  0.00  cold
  mem-08  procedural  idle 145 days  1.00  live
  mem-09  procedural  idle 116 days  1.00  live
  mem-10  procedural  idle 145 days  1.00  live
```

The event mem-07, a refund request written on 3 June and never read again, is cold; the rule mem-10, written two weeks earlier on 20 May and never read either, still stands at 1.00. The figure below draws the same function over the months for one rule, two events and one fact.

![Confidence from 20 May to 12 October for four rows. The rule mem-10 stays at 1.00. The event mem-07 falls from 1.00 on 3 June, is cold from 3 August and falls to 0.00 by 11 September. The event mem-05 ends at 0.72; the fact mem-03 ends at 0.50, between the ask line at 0.6 and the cold line at 0.4.](diagrams/03-decay.svg)

*Events and facts lose confidence with every idle day; a rule does not. The two lines are post 08's ask cutoff and this post's cold threshold, both illustrative.*

---

## 9. Memory in the prompt

The snippet renders the `MemoryContext` of its second turn as one block of layer 03:

```text
[memory: rules that apply to this turn]
- Copy every escalation to the account's named technical contact (conversation:c-233)
[memory: facts about this user]
- Is on the enterprise tier (billing:acct-17, last read 2026-10-10)
- Prefers replies in formal English (conversation:c-311, last read 2026-10-09)
- Works in the Pacific time zone (conversation:c-298, unconfirmed: ask before relying on it)
[memory: past events this turn refers to]
- Resolved ticket 4321 on 14 September by escalating the billing error (ticket:4321, 2026-09-14)
```

The structure is deliberate: three labelled parts in the orchestrator's order, one line per item, each with its source and a date, and a doubtful fact marked as doubtful. The labels let the system prompt say how to treat each part: rules as instructions, facts as defaults the user may correct, events as background.

The block is a per-turn injection: it follows the stable prefix of layer 01, the system prompt, and layer 02, tools and Model Context Protocol (MCP) descriptions, so changing it on every turn leaves the cached prefix intact ([post 05](../05-economics-of-context/index.md)). Of the carriers [post 02](../02-six-layers-of-context/index.md) names, two keep it there: a synthetic exchange at the start of the message list, or a block of the first user message; a block of the system prompt would change the cached prefix on every turn.

---

## 10. The four classes of bug

[Post 08](../08-write-strategies/index.md) names three classes of bug; a store with three kinds adds a fourth.

1. **No provenance** (post 08). The user disputes a fact and nobody can find where the agent learned it. Its quieter form is the silent overwrite: a new fact replaces the old row in place, and the agent's behaviour changes with no record of why. Guard: a `source` and `created_at` on every row, and append-only writes.
2. **The wrong content** (post 08). A tool result, a turn of the live conversation, a secret, or a raw reasoning trace ([post 18](../18-reasoning-model-context/index.md)) is written into a long-lived store and read back as if it were still true, or leaked. Guard: a write gate, as post 08's `check_write`.
3. **No expiry** (post 08). Nothing decays, so old preferences override new ones: the agent insists the user works in Vim although the last six sessions were in VS Code. Guard: decay on read, a cold tier, and `expires_at` for facts known to be short-lived.
4. **The wrong kind** (this post). All three kinds share one table and one policy. A learned rule decays like a passing preference and disappears; a one-off event is packed every turn as a standing fact; a rule scores below an episode in a similarity search and never fires. Guard: a `kind` on every row, and a retrieval path and a decay policy per kind.

---

## 11. What Mem0, Letta and Zep do

Few teams build the store from scratch. Three production designs show three storage shapes.

**An extracted fact store (Mem0).** The Mem0 paper (Chhikara et al., April 2025) describes two phases. When a new pair of messages arrives, a model extracts candidate facts. For each candidate, the system retrieves the most similar stored memories by embedding (ten in the paper's experiments), and a model chooses one of four operations: ADD a new memory, UPDATE an existing one with complementary information, DELETE a memory the new information contradicts, or NOOP. In this post's terms it is mostly semantic memory with an automated write gate. Its DELETE is an overwrite policy: the store stays small and current, at the price of the history that section 5 keeps.

**A temporal knowledge graph (Zep).** Zep's engine, Graphiti (Rasmussen et al., January 2025), stores memory as a knowledge graph whose edges are facts. Each edge carries four timestamps: when it was created and invalidated in the system, and when the fact held in the world. When a new edge contradicts an old one, the old edge is marked invalid from the time the new one became valid, not deleted, so the graph can say what was true then and what is true now. Retrieval combines embedding similarity, keyword search and a walk outward from the matched nodes. Strength: questions about relationships and change over time. Weakness: more machinery, and overkill for independent facts.

**Tiered memory paged by the agent (Letta, formerly MemGPT).** MemGPT (Packer et al., October 2023) treats the window as main memory and external storage as disk, after an operating system's memory hierarchy, and lets the model move information between them with function calls. Letta's documentation (consulted October 2026) describes memory blocks pinned to the context window, which the agent edits through memory tools, and an archival memory, a searchable database outside the window that the agent queries through tools. Strength: the agent manages its own working set over very long sessions. Weakness: memory decisions sit inside the model's loop, which costs calls and is harder to audit than a store driven from application code.

**ChatGPT's memory.** OpenAI's "Memory and new controls for ChatGPT" (13 February 2024, in its update of 10 April 2025) describes saved memories, which the user asks it to keep, and references to past conversations; either can be turned off. In this post's terms these are semantic rows written on explicit assertion and a form of episodic recall. OpenAI does not publish the storage design.

---

## 12. How to choose

The storage shape follows from the questions the agent must answer:

- **Independent facts and preferences, "what does this user want?"**: an extracted fact store over a vector index, as in Mem0. The default; reach for it first.
- **Relationships and change over time, "what changed, and what caused it?"**: a temporal knowledge graph, as in Zep.
- **Very long single sessions where the agent must manage its own working set**: tiered memory paged by the agent, as in Letta.
- **Rules written by people that change by review, not by observation**: not a memory store at all. They belong in the system prompt's rules block or in `AGENTS.md` (post 08, section 4).

A sensible path starts with the first and the three-kind discipline of sections 3 to 6, and adds a graph only once the relationship question a flat store cannot answer can be named.

---

## 13. When not to use a memory store

Some agents are better with no long-term memory at all:

- **Stateless tools and single-turn use.** A calculator or a search box needs no memory; adding one adds bugs.
- **Sensitive interactions.** Health, financial and legal conversations carry data that privacy regimes protect strictly. Store nothing, or store with explicit consent and a working deletion path ([post 24](../24-privacy-and-governance/index.md)).
- **Where people expect forgetting.** A journaling agent that forgets between entries can respect its user's privacy in a way that one that "remembers" does not.

The strongest designs are explicit about what they remember and what they do not, and they tell the user.

---

## 14. Make it run: a minimal memory layer

The memory layer of sections 3 to 9 is one standard-library file. From the series root:

```text
uv run python posts/16-memory-systems/snippets/memory_layer.py
```

It runs in well under a second, with no network and no model call. It writes ten rows (four semantic, three episodic, three procedural), prints the decay table of section 8, answers three turns, prints the block of section 9, and checks this post's gate: a preference, an event and a rule each retrieved by its own path, and a stale event decayed while a rule did not. The first turn asks for a report: mem-08 fires and no episode is recalled. The second is the turn of section 7. The third asks about a refund on invoice 88: mem-10 fires, and the only matching episode, mem-07, is cold. The run ends:

```text
gate: 5 of 5 checks pass
  pass  preference mem-01 by background grounding
  pass  event mem-05 by reference recall
  pass  rule mem-08 by trigger match
  pass  stale event mem-07 decayed
  pass  rule mem-10 did not
```

Three changes show the moving parts. Moving `TODAY` to 12 November drops mem-01 under the ask cutoff (0.56) and mem-03 into the cold tier (0.19), so background grounding packs two facts instead of three, while the three rules still stand at 1.00. Setting mem-10's `kind` to `"semantic"` makes the write method refuse it, because it carries a `trigger`; removing the trigger as well lets it in, where it decays to 0.00 and the last check of the gate fails: the fourth class of bug of section 10. An empty `source` is refused as having no provenance.

---

## 15. What can go wrong?

- **Background reads counted as confirmations.** Post 08 updates `last_accessed_at` on every read, so a fact packed as background on every turn never decays, however wrong it has become. The snippet's retrieval is read-only for this reason: count only the reads an answer relied on, or a confirmation by the user.
- **A trigger on words instead of intent.** A rule fires on the word "refund", so "I do not want a refund, just the invoice" starts the refund procedure. A trigger tests a classified fact of the turn (its intent, the account's tier, the tool about to run), not a substring.
- **Episodic recall on every turn.** Old events are packed into turns that never referred to them, and the answer drifts toward a ticket closed in September: distraction, in [post 06](../06-context-failure-modes/index.md)'s terms.
- **A learned rule against a team rule.** A procedural row says "skip the approval step for this account"; layer 01 says every refund above $1,000 needs approval. That is conflict (post 06, section 4) inside one window. The write step checks a new rule against the system prompt, and the system prompt states that its rules win.
- **A cold tier forgotten at deletion time.** A user asks for their data to be erased; the live rows go, and the cold rows, kept "never deleted", stay. Deletion has to reach every tier ([post 24](../24-privacy-and-governance/index.md)).

---

## Common pitfalls

1. **One table and one policy for all three kinds.** Rules decay with preferences and events pose as standing facts.
2. **Writing tool results to long-term memory.** A tool result describes the moment of the call; when it is needed again, the tool is called again.
3. **Packing the whole store as background.** Layer 03 is small; rank and pack the top few, and leave the rest in the store.
4. **Overwriting a fact on contradiction.** Write the new fact as a new row and let the old one decay, so the change can be explained.
5. **Writing a learned rule without confirmation.** A procedural row is obeyed on every matching turn; one mistaken rule misleads them all.

---

## Further reading

- Tulving, E., "Episodic and semantic memory" (1972): the episodic and semantic distinction.
- Tulving, E., "How many memory systems are there?" (*American Psychologist*, 1985): procedural, semantic and episodic memory as three systems.
- Sumers, T. R., Yao, S., Narasimhan, K. and Griffiths, T. L., "Cognitive Architectures for Language Agents" (2023): working, episodic, semantic and procedural memory for language agents.
- Harrison Chase, "Memory for Agents" (LangChain blog, October 2024): the three kinds for agent builders, after CoALA.
- Park, J. S. *et al.*, "Generative Agents: Interactive Simulacra of Human Behavior" (2023): a memory stream ranked by recency, importance and relevance.
- Packer, C. *et al.*, "MemGPT: Towards LLMs as Operating Systems" (2023): tiered memory paged by the agent.
- Chhikara, P. *et al.*, "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory" (2025): extraction and the ADD, UPDATE, DELETE and NOOP update phase.
- Rasmussen, P. *et al.*, "Zep: A Temporal Knowledge Graph Architecture for Agent Memory" (2025): Graphiti and its time-stamped edges.
- Letta, "Introduction to stateful agents" and "Archival memory" (Letta documentation, consulted October 2026).
- OpenAI, "Memory and new controls for ChatGPT" (13 February 2024; update of 10 April 2025).

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 17 - Advanced retrieval](../17-advanced-retrieval/index.md):** graph retrieval and the other techniques for questions a flat similarity search cannot answer.
- **[Post 23 - Security and prompt injection](../23-security/index.md):** what changes when someone writes to the memory store on purpose: memory poisoning.
