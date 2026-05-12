# 12 · The system prompt as software

> **TL;DR.** The system prompt is not "the magic words at the top of the chat". It is the **executable specification** of the agent: identity, rules, format, knowledge, tools. Treating it like software — versioned, reviewed, tested, monitored — is the single largest discipline change that distinguishes prototype agents from production ones. This post lays out the **five-block structure**, the **six rules** that keep prompts from rotting, and the **CI gates** that let a team change them safely.
>
> **Reading time:** ~12 minutes.
>
> **After reading this you will be able to:**
> - Decompose any system prompt into five named blocks.
> - Apply six rules that keep a prompt from accumulating contradictions.
> - Wire the minimum CI harness that lets you change prompts without praying.

---

## 1. The thesis

Most teams write a system prompt the way teams used to write SQL queries in the 1990s: by accretion, in a single file, edited live, with no review and no tests. Both situations end the same way — a critical artefact that nobody is willing to touch because nobody fully understands it any more.

The fix is the same as it was for SQL. Treat the prompt as **code** — versioned in git, reviewed in pull requests, tested in CI, monitored in production. That single shift unlocks every other practice in this post.

---

## 2. The five-block structure

Every well-engineered system prompt the author has seen — across Anthropic, OpenAI, Cursor, Cognition, Replit, internal enterprise systems — decomposes into the same five blocks, in the same order. Other vocabularies exist; the underlying structure is invariant.

```
┌──────────────────────────────────────────────────────────┐
│ 1. IDENTITY      Who the agent is, in one paragraph      │
│ 2. RULES         Hard constraints the agent must follow  │
│ 3. FORMAT        How outputs should be shaped            │
│ 4. KNOWLEDGE     Facts the agent needs that won't fit    │
│                  via retrieval (small, stable, vital)    │
│ 5. TOOLS         Tool catalog with usage guidance        │
└──────────────────────────────────────────────────────────┘
```

**Identity.** One paragraph. *"You are a customer-support agent for Acme. You help users with billing, account, and shipping questions. You escalate anything else to a human."* The identity sets defaults for tone, scope, and posture. Skipping it leaves the model to default to "helpful generic assistant", which is rarely what was wanted.

**Rules.** Hard constraints. *"Refunds over $1 000 require manager approval. Never reveal internal SKU numbers. Never speculate about delivery dates that are not in the order record."* Rules are imperative; they say what the agent **must** or **must not** do. Each rule should be motivated by a real failure that occurred — speculative rules accumulate and contradict each other.

**Format.** Output shape. *"Respond in plain prose, no headings unless the user explicitly asks. Cite sources in [brackets]. End every interaction with 'Anything else I can help with?'."* Format is the block that downstream code most often depends on. Changes here break parsers; treat as breaking changes.

**Knowledge.** Small, stable, vital facts. *"Acme is headquartered in Mumbai. Office hours are 9:00–18:00 IST. The fiscal year starts April 1."* Knowledge is *not* where the entire FAQ goes — that goes in retrieval. Knowledge is the ten facts the agent will refer to so often that retrieval would be wasteful.

**Tools.** The tool catalog with one-line usage guidance per tool. *"`refund_order(order_id, amount)` — issue a refund. Confirm with the user before calling. Maximum $1 000 without escalation."* The schemas themselves come from the tool layer; this block carries the *meta-guidance* — when to reach for which tool.

A prompt missing one of these blocks is not necessarily wrong, but the team should be able to say *which block they intentionally left out and why*.

---

## 3. The six rules

A small set of practices that, applied consistently, prevent the most common failure modes.

**1. One concept per rule.** "Never refund over $1 000 without manager approval and always cite sources" is two rules. Split them. Rules joined by "and" hide partial compliance.

**2. Motivated by failure, not by speculation.** Add a rule when a real interaction went wrong; do not add a rule because a hypothetical future interaction might. Speculative rules accumulate and contradict. A useful trick: every rule carries a comment with the date and the issue id that motivated it.

**3. Positive over negative.** "Reply in formal English" beats "do not be casual". The positive form gives the model a target; the negative form gives it a wide space of acceptable behaviours, only one of which is the one you wanted.

**4. Specific over vague.** "Limit replies to 200 words" beats "be concise". The model has internalised statistical priors for both, but only the first one is auditable.

**5. Examples beat instructions for complex format.** A two-line "good example" + "bad example" pair often eliminates a paragraph of rules. The format block is where examples earn their keep.

**6. Reviewed like code.** Every change is a diff. Every diff has a reviewer. Every diff has a justification. The justification is one sentence and lives in the commit message.

These six rules will not write the prompt for you. They will keep the prompt you wrote from rotting.

---

## 4. Versioning and `AGENTS.md`

The system prompt belongs in version control. The two patterns that work:

**Pattern A — single file.** The prompt is `prompts/system.md` in the repository. The application reads it at startup. Every change is a PR.

**Pattern B — composed from blocks.** Each block is its own file (`prompts/identity.md`, `prompts/rules.md`, etc.). The application concatenates them at startup. Useful when different teams own different blocks (security owns rules; product owns identity; platform owns tools).

Both compose with the **`AGENTS.md` / `CLAUDE.md` convention** ([Post 07](../07-write-strategies/index.md), §4) for repository-aware agents. The repository file extends or overrides the global system prompt for a specific codebase. The rule is recursive: a top-level `AGENTS.md` describes the project, subdirectory files refine, the deepest matching file wins. This is the most disciplined way the field has found to ship behaviour-shaping configuration alongside the code it shapes.

Two rules of thumb for `AGENTS.md` files:

- **Keep them under ~500 lines.** They load on every relevant call.
- **Iterate from minimal.** Start almost empty; add only when a real failure motivates it. (Identical to rule #2 above; the `AGENTS.md` has the same failure modes as the global prompt.)

---

## 5. Caching and the prompt's cost

A typical production prompt is large — 4 k–20 k tokens before any conversation begins. Naïvely, every call pays for it. **Prompt caching** removes that cost: the host stores the KV-cache of the prefix and reuses it for subsequent calls that share the same prefix.

This makes the *order* of the prompt operationally important:

- **Stable content goes first** — system prompt blocks (identity, rules, format, knowledge), tool catalog, long-lived examples.
- **Dynamic content goes last** — retrieved RAG chunks, conversation history, the user's current turn.

A cache hit on the prefix typically reduces input cost by 10× and latency by 2–4× ([Post 04](../04-tokens-windows-budgets/index.md), §3). A single change to the system prompt invalidates the cache for every active session — *which is one more reason to stop changing the prompt casually*.

A pattern that pays back: **explicit cache markers**. Anthropic's API (`cache_control`) and similar features in OpenAI / Google APIs let you mark exactly where the cacheable prefix ends. Use them. Without them, the cache boundary depends on heuristics and may move under you.

---

## 6. Testing — the harness without which prompts rot

A prompt change is a software change. Software changes are tested. The minimum harness:

- **A regression suite of 30–100 prompt/response pairs.** Each pair captures a behaviour the team has decided is right. They come from real production interactions, edge cases caught in review, and cases that motivated rule additions.
- **A scoring function.** For pairs with a single correct answer (a tool name, a number, a JSON shape), exact match. For pairs whose value is a behaviour (tone, citation present, refusal correct), an LLM-as-judge with a rubric.
- **A CI gate.** Every PR that touches the prompt runs the suite. A drop greater than the noise floor blocks the merge. A regression on a *specific* pair lights up exactly which behaviour broke.

This harness is the single most important discipline change in agent development. A team that ships prompt edits without it is shipping silent regressions; it is just a matter of time before one of them surfaces in production at the worst moment.

The harness composes with the RAG eval ([Post 09](../09-rag-in-depth/index.md), §6) and the compression eval ([Post 10](../10-compress-strategies/index.md), §8); often it is the same harness with different fixtures.

---

## 7. Production monitoring

The prompt does not exist in isolation; it interacts with everything else in the system, including changes in user behaviour and silent shifts in upstream model versions. The minimum monitoring:

- **Refusal rate.** Sudden jumps usually mean a recent rule change is over-firing.
- **Tool-call distribution.** A tool's frequency falling to zero often means a recent edit broke its description.
- **Average and p99 reply length.** Drift in either direction is a signal worth investigating before a user complains.
- **Citation rate** (for retrieval-grounded agents). A drop usually means the format block is being ignored.
- **User-reported quality.** Thumbs / stars / explicit complaints, segmented by deploy.

Each of these is one chart. None of them are sufficient alone; together they form a smoke alarm for prompt changes that slipped through the regression suite.

---

## 8. The "treat the prompt as software" payoff

A team that adopts the practices in this post — five blocks, six rules, versioned files, prompt caching with explicit markers, regression suite in CI, four monitoring charts — gets three things at once.

- **Confidence to change the prompt.** Edits feel like edits, not like surgery on a black box.
- **Faster iteration.** A change goes from idea to production in hours, not days.
- **Fewer fires.** The kind of bug where "we shipped a prompt edit and our refund rate halved" stops happening.

The cost is the modest discipline of writing rules with motivations and pairs with scores. The payoff compounds over the lifetime of the agent.

---

## Common pitfalls

- **One giant unstructured prompt.** Everyone is afraid to touch it. Refactor into the five blocks.
- **Speculative rules.** Each one was added "in case", and they now contradict each other.
- **Negative phrasing.** "Don't be too long" is unverifiable.
- **Edits without review.** The prompt was the spec, and the spec changed at midnight without a diff.
- **No regression suite.** The next edit will silently regress something.
- **No cache markers.** The cache boundary moves; cost forecasts are wrong by 5×.
- **Putting retrieved chunks at the top of the prompt.** They invalidate the cache prefix; lift them to the bottom.

---

## Further reading

- Anthropic Engineering, *"Crafting effective system prompts"* (2024).
- OpenAI, *"Model Spec"* (2024) — a public artefact that *is* a system prompt at scale.
- agents.md project, *"AGENTS.md spec"* (2025).
- DAIR.ai, *"Prompt Engineering Guide"* (2024 ed.) — the broad field, useful for vocabulary.
- Anthropic, *"Prompt caching"* docs — the operational details of cache markers.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 13 — Tools and MCP](../13-tools-and-mcp/index.md)** — the tools block, in depth.
- **[Post 14 — Memory systems](../14-memory-systems/index.md)** — the persistent counterpart.
- **[Post 17 — Observability](../17-observability/index.md)** — the monitoring and CI harness, productionised.
