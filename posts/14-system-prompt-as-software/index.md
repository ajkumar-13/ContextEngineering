# 14 - The system prompt as software

> **TL;DR.** The system prompt, layer 01, is the standing specification of an agent, and it rots like any specification edited without discipline. This post asks what it means to treat it as software: five named blocks, six rules for writing rules, versioned files such as `AGENTS.md`, a layout that keeps the prefix cached, and a continuous integration (CI) gate that blocks a contradictory rule before it ships. A runnable snippet assembles a five-block prompt from versioned parts and shows the gate passing one version and blocking the next.
>
> **Prerequisites:** [Post 02](../02-six-layers-of-context/index.md).
> **Safe to skip?** Skip it if every system prompt in production is already split into named blocks, kept in version control, reviewed in pull requests and guarded by a regression suite that runs on every change.
>
> **After reading, you will be able to:**
>
> - Decompose a system prompt into the five named blocks (identity, rules, format, knowledge, tool-use guidance) and place a given line in one of them.
> - Apply the six rules for writing rules to rewrite a weak or speculative rule into one a model can follow and a reviewer can audit.
> - Explain how AGENTS.md, CLAUDE.md and SKILL.md files reach the window, and how nested files are resolved.
> - Lay out a prompt so its stable prefix caches, and say which edits invalidate the cached prefix and what that costs.
> - Wire the minimum CI harness for a prompt: a regression set, a scoring rule and a gate that blocks a contradictory rule.
> - Choose the production signals that show a prompt change has gone wrong after it passed the gate.

![The six-layer stack on the left with layer 01, the system prompt, opened out into five blocks in order: identity, rules, format, knowledge and tool-use guidance, each with its job and one line of the snippet's prompt; the tool schemas sit in layer 02.](diagrams/01-five-blocks.svg)

*Layer 01 is not one paragraph but five named blocks in a fixed order; the tool schemas live next door, in layer 02.*

---

## 1. The question: what does it mean to treat the system prompt as software?

A system prompt often starts as a few lines and grows by accretion: a sentence after each incident, edited in place, with no review and no tests. Months later nobody is willing to touch it, because nobody can say which sentence is still load-bearing, and the model reads every word of it on every call ([post 02](../02-six-layers-of-context/index.md)).

The remedy is to treat the prompt as **code**: versioned in git, reviewed in pull requests, tested in continuous integration (CI, the automated checks that run on every change) and monitored in production.

---

## 2. The five blocks

[Post 02](../02-six-layers-of-context/index.md) lists five blocks that a system prompt typically covers, and this series uses them as its checklist for layer 01. They are a teaching structure, not an industry standard; what they buy is a place for every line and a way to notice what is missing. The figure at the top of the post places the five inside the window.

The snippet of this post, `snippets/prompt_ci.py`, assembles a support agent's system prompt from five parts, each with its own version number, in the fixed order. It prints:

```text
## Identity
You are the support agent for Acme. You help customers with billing, account and
shipping questions, and hand anything else to a human.

## Rules
- [#412] Refunds above 1000 dollars go to a manager for approval.
- [#377] Quote a delivery date only when it is in the order record.
- [#455] Reply in formal British English.

## Format
Answer in plain prose of at most 150 words. Cite the order id in brackets,
as [A-1234], whenever the reply concerns an order.

## Knowledge
Office hours are 9:00 to 18:00 IST, Monday to Saturday; the office is closed on Sunday.

## Tool-use guidance
- lookup_order: questions about where an order is.
- refund_order: refunds the rules let a support agent approve.
- escalate_to_manager: refunds the rules send to a manager.
- handoff_to_human: anything outside billing, account and shipping.
```

**Identity.** One short paragraph: who the agent is, whom it serves, where its scope ends. Anthropic's "Prompting best practices" (Claude documentation, consulted October 2026) states: "Setting a role in the system prompt focuses Claude's behavior and tone for your use case."

**Rules.** Hard constraints: what the agent must or must not do. Each carries the issue id of the incident that motivated it (`[#412]`), so a reader can tell a live constraint from a fossil. Section 3 is about writing them.

**Format.** The shape of every reply: length, structure, citation style. Downstream code depends on this block more than on any other: a parser that extracts `[A-1234]` breaks when the bracket style changes, so a change here is a breaking change.

**Knowledge.** Small, stable facts needed on almost every call: office hours, the fiscal year, the product's name. It is not where the FAQ goes; anything large or rarely needed is retrieved into layer 04, retrieved chunks, when a turn needs it.

**Tool-use guidance.** When to reach for which tool, one line per tool. The schemas themselves are layer 02, tools and MCP descriptions, where MCP is the Model Context Protocol through which external tools reach a host ([post 15](../15-tools-and-mcp/index.md)); this block carries only the judgement the schemas cannot.

A prompt may lack a block, but its authors should be able to say which and why.

**The boundaries are fluid.** "Cite the order id in brackets" is a rule (the agent must cite) and a format (the bracket shape). The blocks are a checklist, not a filing system. A workable test: a line that constrains what the agent may do is a rule; a line that constrains what the reply looks like is format; a line that states a fact is knowledge. A line that is genuinely both goes where a reader will look first, and only there: a rule stated twice can drift out of step with itself.

---

## 3. The six rules

The blocks say where a line goes; the six rules say how to write one. They are the first fix [post 06](../06-context-failure-modes/index.md) gives for confusion, the right information handled under unclear rules, the failure mode of layers 01 and 02 (its section 3).

1. **One concept per rule.** "Never refund over 1,000 dollars without manager approval and always cite sources" is two rules, and a model that follows one half has partly complied in a way nobody can see. Split them.
2. **Motivated by failure, not by speculation.** A rule is added when a real interaction went wrong, not because a future one might; speculative rules accumulate and start to contradict each other. The issue id records the failure, and Anthropic's "Prompting best practices" adds that explaining why an instruction matters helps the model understand the goal.
3. **Positive over negative.** "Reply in formal English" beats "do not be casual": the positive form names a target, while the negative form leaves a wide space of acceptable replies. Anthropic's page says the same: "Tell Claude what to do instead of what not to do". The snippet's rule `[#377]` reads "Quote a delivery date only when it is in the order record", not "never speculate about delivery dates".
4. **Specific over vague.** "At most 150 words" beats "be concise". Both nudge the model; only the first can be checked by a reviewer or a test.
5. **Examples beat instructions for complex format.** One good example, and where useful one bad one, often replaces a paragraph of format rules; Anthropic's page calls examples "one of the most reliable ways to steer Claude's output format, tone, and structure."
6. **Reviewed like code.** Every change is a diff, every diff has a reviewer, and every diff carries a one-sentence justification in its commit message.

Four of the six substitute one wording for another; the second and the sixth are habits of process.

---

## 4. Versioning, `AGENTS.md`, `CLAUDE.md` and `SKILL.md`

The system prompt belongs in version control, in one of two layouts. **One file**: `prompts/system.md`, read at start-up, every change a pull request. **Composed from blocks**: each block its own file with its own version, concatenated in the fixed order, which suits a team where different people own different blocks (support policy owns the rules, product the identity). The snippet works the second way, and its first line names the version of every part:

```text
prompt v1 (identity 1.0.0, rules 1.2.0, format 1.1.0, knowledge 1.0.0, tool-use guidance 1.0.0)
```

For an agent that works on a repository, the same idea ships as files checked in beside the code. [Post 08](../08-write-strategies/index.md) treats them as a write destination (its section 4); here the question is how each reaches the window and how nested files resolve.

| File | Read by | How it reaches the window | Nested files |
|---|---|---|---|
| `AGENTS.md` | agents that support the open format (Codex, Cursor, Gemini CLI and others) | standing instructions for the session | the closest file to the edited file wins |
| `CLAUDE.md` | Claude Code | a user message after the system prompt | files from the root down to the working directory are concatenated at launch; a subdirectory's file loads when work reaches it |
| `SKILL.md` | agents that support Agent Skills | name and description pre-loaded; the body read only when a task needs it | one file per skill directory |

The agents.md site (consulted October 2026) gives the nesting rule in its FAQ: "The closest AGENTS.md to the edited file wins; explicit user chat prompts override everything." Claude Code resolves `CLAUDE.md` differently. Its documentation ("How Claude remembers your project", consulted October 2026) says that the files from the working directory up to the root are concatenated, not overridden, root first, so the closest is read last; that a subdirectory's file loads once Claude reads, writes or edits a file there; and that `CLAUDE.md` content "is delivered as a user message after the system prompt, not as part of the system prompt itself." It still does the job of layer 01, standing instructions for the session, wherever the host places it ([post 02](../02-six-layers-of-context/index.md)). The same page says Claude Code reads a repository's `AGENTS.md` when there is no `CLAUDE.md`, and that a `CLAUDE.md` can import it with an `@AGENTS.md` line, so one shared file serves every tool.

A minimal `AGENTS.md` for a coding agent, in the five-block form:

```markdown
# AGENTS.md for payments-service

## Identity
This is payments-service. Agents implement changes, write tests and open
pull requests here. They do not deploy.

## Rules
- Change `migrations/` only when the task asks for it. [#212]
- Every new endpoint ships with a test. [#218]
- Use British spelling in prose and comments. [#231]

## Format
- Cite files as `path:line`. Keep pull-request descriptions under 200 words.

## Knowledge
- Build: `pnpm build`. Test: `pnpm test`. Deploy is handled by CI.
- Money is stored in integer minor units, never floats.

## Tools and commands
- Run `pnpm lint` before opening a pull request.
```

The rules carry their issues (rule 2) and the first is positive (rule 3). Two rules of thumb follow from how such files load. **Keep them short**: Claude Code's documentation targets under 200 lines per `CLAUDE.md` and says "Longer files consume more context and reduce adherence." **Iterate from minimal**: start almost empty and add a rule only when a real failure motivates it.

**Loading only the relevant part.** In Anthropic's Agent Skills format (Anthropic Engineering, "Equipping agents for the real world with Agent Skills", 16 October 2025), a skill is a directory with a `SKILL.md` whose front matter gives a `name` and a `description`; the agent pre-loads both for every installed skill and reads the full file only when a task matches. Nested `AGENTS.md` and `CLAUDE.md` files do the same for a monorepo: a call carries the slice its task needs, not the union of every slice.

**Who outranks whom.** OpenAI's "Model Spec" (version of 18 August 2026, consulted October 2026) orders instructions by levels of authority: root, system, developer, user and guideline, with assistant and tool messages and quoted or untrusted text carrying none. The developer's instructions outrank the user's message, which is why a rule belongs in layer 01 and why text arriving in a tool result or a retrieved chunk should never act as a rule ([post 23](../23-security/index.md) takes up the attack).

---

## 5. Caching and the prompt's cost

A production prompt is resent on every call. **Prompt caching** removes most of that cost: the provider stores the processed state of a prefix, in effect its KV cache ([post 03](../03-how-llms-read-context/index.md), section 7), and reuses it when a later request starts with the same prefix. [Post 05](../05-economics-of-context/index.md) works through the rules and the arithmetic (its section 4); this section applies them to a prompt that changes by release.

The rules, from Anthropic's "Prompt caching" documentation as consulted in October 2026 and as post 05 states them: a hit needs a prefix identical up to a cache breakpoint (a `cache_control` marker, at most four per request); the prefix is built in the order `tools`, `system`, `messages`; a cache write costs 1.25 times the base input price for the default five-minute lifetime and 2 times for the one-hour lifetime; a cache read costs 0.1 times the base input price on most models, with lower multipliers on some newer ones; and a prefix shorter than the model's minimum (1,024 tokens for Claude Sonnet 4.5, 4,096 for Claude Opus 4.6 and Claude Haiku 4.5) is not cached, with no error returned. OpenAI's "Prompt caching" guide (consulted October 2026) describes caching on by default for supported models, with cached input discounted by up to 95%, depending on the model.

Two consequences follow for a system prompt:

- **Stable content first, per-turn content last.** The five blocks and the tool schemas, layers 01 and 02, form the stable prefix; layers 03 to 06 follow. A per-call value (a timestamp, the user's name, this turn's chunks) inside the system prompt ends the reusable prefix there on every call.
- **Every edit is a cache event.** An edit to any block changes the bytes of the system prompt, so its cached entry no longer matches. The next call writes the new prefix at the write premium; only an earlier part written under its own breakpoint can still be read.

![Three rows of one request in Anthropic's cache order, tools, system prompt, then layers 03 to 06, with breakpoints after the tools and the system prompt: the first call with prompt v1 writes both, a later call reads both, and the first call after the rules edit reads the tools and writes the system prompt again.](diagrams/02-rule-edit-cache.svg)

*A one-line rule edit costs one rewrite of the system prompt's cache entry; a breakpoint after the tools keeps the schemas reusable.*

The figure above draws the second consequence for the snippet's change from rules 1.2.0 to 1.3.0, with post 05's multipliers. The practical rule is post 05's: batch prompt changes into deliberate releases, because each edit pays the write premium again and dents the cache-hit rate that monitoring watches (section 7).

---

## 6. Testing: the harness without which prompts rot

The minimum harness for a prompt change has three parts:

- **A regression set.** Each case is an input and the behaviour the team has decided is right, taken from production interactions, edge cases caught in review, and the incidents behind each rule. An illustrative starting size is a few dozen to a couple of hundred cases; the snippet uses ten.
- **A scoring rule.** Exact match for cases with one correct answer (a tool name, a number, a JSON shape); for a behaviour (tone, a citation, a due refusal), a model used as a judge with a written rubric ([post 20](../20-evaluation/index.md) covers judges and their failure modes).
- **A gate in CI.** Every pull request that touches the prompt runs the set, and a drop greater than the noise floor (the run-to-run variation of the unchanged prompt) blocks the merge. A failing case names exactly which behaviour broke.

Some checks need no model. A linter over the prompt can confirm that every block is present, that every rule carries an issue id, and that no two rules contradict each other where the contradiction is mechanical. The last check of the snippet's `lint` turns the refund rules into ranges of amounts and reports any two that overlap with different actions:

```python
    # Refund rules as ranges of amounts: "above L" is (L, inf), "up to L" is [0, L].
    ranges = [(rid, (int(limit), float("inf")) if kind == "above" else (0, int(limit)), action)
              for rid, kind, limit, action in REFUND_RULE.findall(parts["Rules"][1])]
    for i, (id_a, (lo_a, hi_a), act_a) in enumerate(ranges):
        for id_b, (lo_b, hi_b), act_b in ranges[i + 1:]:
            lo, hi = max(lo_a, lo_b), min(hi_a, hi_b)
            if act_a != act_b and lo < hi:
                findings.append(f"rules #{id_a} and #{id_b} disagree on refunds above {lo} dollars up to {hi} dollars")
    return findings
```

The ten cases pair a request with the one tool the prompt says it should lead to: refunds of 40, 999, 1,000, 1,001, 1,500 and 2,500 dollars, two questions about where an order is, a question the knowledge block answers directly, and a request outside the agent's scope. With no model offline, the snippet scores them against a stand-in that reads the rules block literally and follows the last rule that matches, one arbitrary way to settle two rules that disagree; Claude Code's documentation warns that with contradictory instructions the model "may pick one arbitrarily". A real suite sends each case to the model.

Running `uv run python posts/14-system-prompt-as-software/snippets/prompt_ci.py` from the series root prints, for the prompt of section 2:

```text
sha256 of the prompt: 721901ca86e1
lint: no findings
regression: 10/10 cases pass
gate: pass
```

Version 1.3.0 of the rules block then adds one rule, the kind a well-meant edit introduces to speed up mid-sized refunds:

```text
prompt v2 (identity 1.0.0, rules 1.3.0, format 1.1.0, knowledge 1.0.0, tool-use guidance 1.0.0); changed blocks: Rules
rules 1.3.0 adds: - [#481] Refunds up to 2000 dollars may be approved without a manager.
sha256 of the prompt: a041327e5751
lint: rules #412 and #481 disagree on refunds above 1000 dollars up to 2000 dollars
regression: 8/10 cases pass
  case 04 "Refund 1001 dollars for order A-1004.": expected escalate_to_manager, got refund_order
  case 05 "I need a refund of 1500 dollars for order A-1005.": expected escalate_to_manager, got refund_order
gate: blocked (1 lint finding, 2 failing cases)
```

![Two rows of the same CI pipeline, pull request, lint, ten regression cases and gate: with rules 1.2.0 lint finds nothing, ten of ten cases pass and the gate passes; with rules 1.3.0 lint reports rules 412 and 481 in conflict, eight of ten pass and the gate blocks the merge.](diagrams/03-ci-gate.svg)

*The same gate, two versions of the rules block. The contradiction is caught twice: by the linter, statically, and by the two cases inside the disputed range.*

The figure above lays the two runs side by side; the changed hash is the cache event of section 5. The 2,500-dollar case still passes, because only `[#412]` covers it, and the case of exactly 1,000 dollars passes in both versions, because "above 1000" excludes it. Without the two cases inside the disputed range, the regression set alone would not have seen the contradiction: cases belong at the boundaries of each rule, with a static check beside them. The stand-in has no run-to-run noise, so its gate blocks on any failing case; with a real model, the threshold is the measured noise floor.

The harness composes with the retrieval evaluation of [post 11](../11-rag-in-depth/index.md) (its section 6) and the retention measurement of [post 12](../12-compress-strategies/index.md) (its section 10): it can be the same harness with different fixtures.

---

## 7. Production monitoring

A regression set only tests what someone thought to write down. The minimum monitoring, each signal a chart segmented by prompt version:

- **Refusal rate.** A jump after a release points at a rule that fires too often.
- **Tool-call distribution.** A tool whose share falls to zero points at an edit to the tool-use guidance or the tool's description.
- **Reply length**, average and 99th percentile: a direct test of a format rule such as "at most 150 words".
- **Citation rate**, for agents that must cite. A drop means the format block is being ignored.
- **Cache-hit rate**, the share of input tokens read from the cache ([post 05](../05-economics-of-context/index.md), section 7). A drop after a release is the fingerprint of a changed prefix.
- **User-reported quality**: ratings and complaints, segmented by release.

None is sufficient alone; together they are a smoke alarm for changes that slipped past the regression set. [Post 22](../22-observability/index.md) instruments them.

---

## 8. The payoff

Edits become reviewable changes; a reviewer sees which cases moved, not only which words did; and an incident such as "an edit shipped and the refund rate halved" becomes a failing case in a pull request instead of a discovery in production. The cost is the discipline of writing each rule with its motivation and each behaviour as a case.

---

## 9. What can go wrong?

- **A contradictory rule passes because no case sits in its range.** The suite covers 40 and 2,500 dollars but nothing between 1,000 and 2,000; rule `[#481]` merges with every case green, and mid-sized refunds go through without a manager. Cases at each rule's boundary, and a static check for overlapping rules, catch it.
- **A per-call value is formatted into the system prompt.** A timestamp sits in the identity block. Every reply looks fine, but the usage block reports few or no cache-read tokens and the cost per call never drops. The value belongs in layer 03, 04 or 06.
- **One fact is stated in two blocks.** The refund limit appears in the rules and again in the tool-use guidance; a later edit changes one copy, and the model now sees two limits.
- **A nested file is assumed to override.** A team expects a subdirectory's `CLAUDE.md` to replace the root one, as the closest `AGENTS.md` does. Claude Code concatenates both, so the rule meant to be replaced is still read, and the two conflict.
- **A format change ships as a wording tweak.** The citation style moves from `[A-1234]` to `(A-1234)`; the downstream parser silently stops extracting order ids, and the citation-rate chart is the first sign.

---

## Common pitfalls

1. **One giant unstructured prompt.** Nobody dares to touch it; refactoring it into the five blocks is the first step.
2. **Speculative rules.** A rule added "in case" answers no observed failure, and such rules soon contradict each other.
3. **Edits without review or a regression set.** A change with no diff, no reviewer and no suite is a silent regression waiting to surface.
4. **Per-turn content at the top of the prompt.** Retrieved chunks or a timestamp in front of the stable blocks invalidate the cached prefix on every call; they belong after layers 01 and 02.
5. **Editing the prompt on every deploy.** Each edit pays the cache write again; prompt changes go out as deliberate, versioned releases.

---

## Further reading

- Anthropic, "Prompting best practices" (Claude documentation, consulted October 2026): roles, motivated instructions, positive phrasing and examples.
- OpenAI, "Model Spec" (version of 18 August 2026, consulted October 2026): the levels of authority between system, developer and user instructions.
- agents.md project, "AGENTS.md" (consulted October 2026): the open format and its nesting rule.
- Anthropic, "How Claude remembers your project" (Claude Code documentation, consulted October 2026): how `CLAUDE.md` files load, where they are delivered, and the size guidance.
- Anthropic Engineering, "Equipping agents for the real world with Agent Skills" (16 October 2025): the `SKILL.md` format and loading on demand.
- Anthropic, "Prompt caching" documentation, and OpenAI, "Prompt caching" guide (both consulted October 2026): breakpoints, cache order, multipliers and minimum lengths.
- DAIR.AI, "Prompt Engineering Guide" (2024 edition): the broader field and its vocabulary.

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 15 - Tools and MCP](../15-tools-and-mcp/index.md):** layer 02, where the schemas that the tool-use guidance block points at are designed and budgeted.
- **[Post 20 - Evaluation](../20-evaluation/index.md):** the regression set and gate of section 6 grown into a full evaluation harness.
