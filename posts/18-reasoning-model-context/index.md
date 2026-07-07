# 18 · Context for reasoning models

> **TL;DR.** A reasoning model spends **thinking tokens** before it answers, and those tokens are a first-class part of the input you engineer: they consume the same window and the same budget as everything else, and their raw traces must be kept *out* of downstream context, *out* of the cached prefix, and *out* of long-term memory. This post explains what a reasoning model does, how modern Claude replaced the fixed "thinking budget" with an **effort dial** over **adaptive thinking**, how thinking tokens hit the six-layer budget, and the discipline for handling traces so they help the current turn without poisoning the next.
>
> **After reading this you will be able to:**
> - Budget for thinking tokens as a distinct, controllable cost line in your token plan.
> - Set the effort dial per task instead of leaving extended thinking on or off globally.
> - Keep raw reasoning traces out of downstream prompts, the cached prefix, and memory.

![One agent turn drawn as a band: a prompt segment, a wider block of adaptive thinking tokens, then the answer; both thinking and answer are billed as output. An effort dial runs from low to max, biasing how much the model thinks. The raw thinking trace is dropped rather than fed into the next turn and is kept out of the cached prefix and long-term memory, while only the answer and a short distilled note carry forward.](diagrams/00-hero-reasoning-model-context.svg)
*Thinking tokens are part of the input you engineer: they cost budget, and their raw trace must not leak into the next turn.*

---

## 1. A 1M-token model is not a 1M-token reasoner

There is a tempting shortcut in agent design: buy the largest context window available, pour the whole problem in, and assume that a model which can *read* a million tokens can also *reason* over a million tokens. It cannot, at least not for free. Holding text in the window and doing hard multi-step work over that text are different capacities, governed by different limits. The window is a storage question; reasoning is a compute question. [Post 25](../25-long-context-vs-rag/index.md) makes the storage case; this post makes the compute case.

The gap shows up on any task where the answer is not *in* the context but has to be *derived* from it: a multi-constraint scheduling problem, a proof, a refactor that has to preserve a dozen invariants, a diagnosis that rules out competing hypotheses one at a time. A model that emits its answer immediately after reading tends to get the shape right and the details wrong. A model allowed to work through the problem first, generating intermediate steps before committing, does markedly better. That extra work is not free text; it is tokens, and the tokens are where hard tasks are won.

Once a model thinks in tokens, thinking becomes a *surface you engineer*: something to budget for, dial up and down per task, and clean up after. Treat it like any other layer of context, because that is exactly what it is.

---

## 2. What a reasoning model does

A **reasoning model** (also called an extended-thinking model) generates a private stretch of intermediate tokens, its **thinking tokens**, before, and sometimes between, the tokens of its visible answer. The family includes Anthropic's extended-thinking Claude models, OpenAI's o-series, and DeepSeek-R1-style open models. The idea is old (chain-of-thought prompting asked ordinary models to "think step by step"); what is new is that these models are *trained* to produce long, self-correcting reasoning, and the platform bills and manages those tokens explicitly.

Three properties matter for context engineering.

**Thinking is separate from the answer.** The thinking tokens are their own segment of the output. Providers generally do not return the raw chain of thought verbatim; you receive either a *summarised* thinking trace or none at all, alongside the final answer. So you often cannot, and should not, treat the trace as a reliable transcript of the model's logic. It is a by-product, not a contract.

**Modern Claude uses adaptive thinking, not a fixed budget.** Earlier extended-thinking APIs asked you to name a fixed number of thinking tokens ("think for up to 8,000 tokens"). Modern Claude uses **adaptive thinking**: the model itself decides how much to think based on the difficulty of the request, so a trivial question spends little and a hard one spends more (Anthropic, "Extended thinking"). The older fixed thinking-budget parameter is deprecated in favour of this. You no longer hand-tune a token count; you steer the *tendency* to think.

**You steer it with an effort dial.** Instead of a token budget, current Claude exposes an **effort** control with discrete levels, low, medium, high, xhigh, and max, that shifts how readily the model spends thinking tokens on a given request (Anthropic, "Extended thinking"). Low effort keeps latency and cost down for easy work; max effort lets the model grind on genuinely hard problems. The dial is a *policy* over adaptive thinking, not a hard cap: at high effort a simple question still thinks briefly, and at low effort a hard question is not forced to think itself into a corner.

```
       ┌──────────────── effort dial ────────────────┐
 low ──┤ medium ──┤ high ──┤ xhigh ──┤ max            │
       └──────────────────────────────────────────────┘
          more readily spends thinking tokens  ─────▶

 request ─▶ [ thinking tokens (adaptive) ] ─▶ [ answer tokens ]
                    │                                │
              billed as output                 billed as output
              usually not returned raw          returned to you
```
*The effort dial biases how much the model thinks; adaptive thinking decides the actual amount per request; both segments are billed.*

The mental model to carry forward: effort is a *knob on a distribution*, not a fixed allocation. You are telling the model how hard to try, and letting it decide how hard the specific request actually is.

---

## 3. Thinking tokens hit the six-layer budget

Thinking tokens are not a special free resource. They land in the same two accounts every other token does: the **window** and the **bill**. Both accounts were set up in [Post 04](../04-tokens-windows-budgets/index.md), and reasoning models spend from them in ways that surprise teams who budgeted only for the prompt and the answer.

**The window.** Thinking tokens occupy space in the context window while they are being generated. On a model with a 200k-token window, a long thinking pass on a hard problem eats into the same ceiling as your system prompt, your retrieved context, and your tool results. Provision the window as prompt *plus* expected thinking *plus* answer, not prompt plus answer. If you have packed the context to 95 % of the window and then ask for max-effort thinking, you can run out of room mid-reasoning.

**The bill.** Thinking tokens are billed as **output tokens**, at the output rate, which for the running examples in this series is several times the input rate (roughly $15 per million output against roughly $3 per million input for a Sonnet-tier model; prices are illustrative and current as of early 2026, so check the provider's pricing page, per [Post 04](../04-tokens-windows-budgets/index.md)). High effort means more thinking tokens, more output tokens, more cost and more latency. This is the central trade the effort dial exposes: **more thinking buys quality at the price of cost and latency.** A max-effort answer to a hard question can cost and take several times what a low-effort answer to the same question does; the multiple is workload-dependent, so measure it rather than assume it.

Two practical consequences follow. First, **effort is a per-task decision, not a global switch.** Leaving extended thinking on max for an entire agent is the reasoning-era version of loading every document into every prompt: it works, and it is wasteful. Route easy turns (a greeting, a lookup, a format conversion) to low effort and reserve high and above for the turns that actually need derivation. Second, **thinking tokens interact with caching** (§4), because the one thing you can cache is your prefix, and thinking is not part of it.

A back-of-the-envelope worth internalising: if a hard agentic turn spends, illustratively, 3,000 thinking tokens on top of a 1,500-token answer, then 60 % of the *output* bill for that turn is invisible in the final message. Budgeting only for the answer you can see undercounts the true cost of a reasoning agent, sometimes by a large margin.

---

## 4. Keep traces out of downstream context

This is the rule that separates a well-engineered reasoning agent from a leaky one. **A raw reasoning trace is a working note, not a durable artefact.** It exists to help the model produce *this* turn's answer, and its job ends there. Three places it must not end up.

**Not in the next turn's prompt.** The strong temptation, especially in agent loops, is to append the full thinking trace to the conversation history so the next turn "remembers how it reasoned". Resist it. Raw traces are long, bloating the window and the bill on every subsequent turn, and they are noisy, full of discarded hypotheses, false starts, and self-corrections that read, out of context, like conclusions. Re-feeding them can actively mislead the next turn into treating a rejected branch as an accepted fact. The correct move is to carry forward the *answer* (and any decisions or facts it produced), and either **summarise the reasoning to a short note** or **drop it entirely**. This is precisely the compress operation from [Post 12](../12-compress-strategies/index.md): a trace is the highest-volume, lowest-durability content in the whole context, so it is the first thing to shrink or clear.

**Not in the cached prefix.** Prompt caching earns its discount only on a *stable prefix* that repeats across calls (an Anthropic cache read bills at roughly 10 % of the base input price on a hit; [Post 04](../04-tokens-windows-budgets/index.md), Anthropic, "Prompt caching"). Thinking tokens are, by construction, freshly generated on every call and different every time. If a trace lands inside what you were treating as the cacheable prefix, it breaks the prefix, and every downstream call reverts to a full-price cache miss. Keep the reasoning segment strictly *after* the stable, cacheable material (system prompt, tools, pinned context), never woven into it.

**Not in long-term memory.** [Post 16](../16-memory-systems/index.md) draws a hard line between what deserves to outlive a session and what does not. A raw reasoning trace almost never deserves to. Writing traces into episodic or semantic memory pollutes the store with verbose, low-signal content and, worse, risks persisting a *discarded* line of reasoning as if it were a learned fact, a durable version of the same "rejected branch reads as conclusion" failure. Persist the *outcome* (the decision, the preference, the corrected rule), never the deliberation that produced it.

The unifying principle: **traces are ephemeral by default.** Design the loop so the trace is used, summarised or dropped, and forgotten, unless you have a specific, audited reason to keep a distilled version (debugging and evaluation are legitimate reasons; see [Post 22](../22-observability/index.md) for how to log traces to a side channel rather than the live context).

---

## 5. Interleaved thinking and tool calls

The single most useful capability the reasoning models added for agents is **interleaved thinking**: the model can think, call a tool, see the result, think again about that result, and then call the next tool or answer. Reasoning is no longer a single block at the front; it is woven between tool results (Anthropic, "Extended thinking").

This changes agent design in a concrete way. In a classic tool-use loop, the model decides its next action from the raw tool output with no room to deliberate; complex plans have to be forced into an explicit scaffold of prompt-engineered planning steps. With interleaved thinking, the deliberation happens *inside* the model between observations: it can notice that a search result contradicts an earlier one, reconsider its plan, and adjust, all without a separate planning node.

Two engineering notes follow from §3 and §4. First, **each thinking segment between tool calls costs output tokens**, so a long interleaved loop on max effort can quietly run up a large bill; the per-turn budgeting from [Post 04](../04-tokens-windows-budgets/index.md) has to account for *N* thinking segments, not one. Second, **the interleaved traces are still ephemeral.** When you compact the tool-use history ([Post 12](../12-compress-strategies/index.md)), the thinking segments are prime candidates to drop; keep the tool calls and their results (the durable record of what happened), summarise or discard the deliberation between them.

A useful default for interleaved agents: preserve the *observation-action* trail (what the agent did and saw) at full fidelity, and treat the *thinking* between those steps as compressible working memory.

---

## 6. When reasoning replaces scaffolding, and when not to reach for it

Extended thinking changes the build-versus-buy calculus for parts of an agent you may currently hand-build.

**Where it replaces scaffolding.** A capable reasoning model can absorb work that older pipelines did with explicit, prompt-engineered steps: query decomposition, multi-hop planning, self-critique, chain-of-verification. If the model can decompose a multi-hop question internally, you may not need the separate decomposition prompt from [Post 17](../17-advanced-retrieval/index.md); if it can self-check its arithmetic during thinking, you may not need a separate verification pass. The general pattern: *lean on thinking for reasoning-shaped subtasks, and keep hand-built scaffolding for the parts that need determinism, tool access, or auditability the model's internal reasoning cannot provide.* Fewer hand-built steps means fewer places for the pipeline to break, but it also moves logic from code you can test into a trace you mostly cannot see, so the trade is real.

**Where not to reach for it.** Extended thinking is the wrong default for at least three kinds of work:

- **Simple, deterministic tasks.** Format conversion, classification into known buckets, a lookup, a templated reply. There is nothing to derive; thinking tokens buy nothing and cost latency and money. Use low effort or a non-reasoning model.
- **Latency-sensitive paths.** Anything a user waits on interactively (autocomplete, a fast chat reply, a UI action) pays the thinking cost as visible delay. Reserve high effort for background or clearly "hard" requests where the user expects to wait.
- **Tasks bounded by missing information, not missing reasoning.** If the answer requires a fact the model does not have, more thinking will not conjure it; it will confabulate more elaborately. The fix is retrieval or a tool call ([Post 17](../17-advanced-retrieval/index.md)), not a higher effort setting.

The honest framing: extended thinking is a powerful and *expensive* tool. Turn it up where the bottleneck is genuinely reasoning depth, and leave it low everywhere else. A system that thinks hard on every turn is not a smart system; it is an untuned one.

---

## Common pitfalls

- **Budgeting for the answer, not the thinking.** Sizing a reasoning agent on prompt-plus-answer tokens undercounts the bill and can overflow the window; thinking tokens are billed output and must be provisioned.
- **Leaving effort on max globally.** The reasoning-era version of loading every document into every prompt: correct, and wasteful. Route effort per task.
- **Re-feeding raw traces into the next turn.** Bloats context and can mislead the model into treating a discarded branch as an accepted fact. Summarise or drop.
- **Letting a trace break the cached prefix.** A freshly-generated thinking segment inside your stable prefix turns every cache hit into a full-price miss. Keep thinking after the cacheable material.
- **Writing traces to long-term memory.** Persist the *outcome*, never the deliberation; a stored trace risks preserving a rejected line of reasoning as a durable "fact".
- **Treating the summarised trace as the model's real logic.** The returned trace is a by-product, not a faithful transcript; do not build control flow that depends on parsing it.
- **Reaching for thinking to fix a missing-information problem.** More reasoning cannot supply a fact the model lacks; it confabulates. Retrieve or call a tool instead.

---

## Further reading

- Anthropic, *"Extended thinking"* (documentation, 2024–25): adaptive thinking, the effort dial, interleaved thinking, and how thinking tokens are billed and returned.
- Anthropic, *"Building effective agents"* (Anthropic Engineering, 2024): where model reasoning replaces hand-built orchestration and where scaffolding still earns its place.
- Wei, J. *et al.*, *"Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"* (2022): the antecedent that showed intermediate steps improve reasoning.
- DeepSeek-AI, *"DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning"* (2025): an open reasoning-model account of training for long self-correcting chains of thought.
- Anthropic, *"Prompt caching"* (documentation, 2024–25): the cache-read discount that a stray trace destroys.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 19 — Multimodal context](../19-multimodal-context/index.md)**: the next context surface, images, audio, and documents in the window, and how they hit the same budget thinking tokens do.
- **[Post 17 — Advanced retrieval](../17-advanced-retrieval/index.md)** (back): the hand-built retrieval scaffolding that extended thinking sometimes replaces, and often still needs.
