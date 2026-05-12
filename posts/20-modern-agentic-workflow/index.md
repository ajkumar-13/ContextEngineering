# 20 · The modern agentic workflow

> **TL;DR.** The 2024–25 generation of coding tools — **Claude Code**, **Cursor**, **Aider**, **Continue**, **Codex CLI**, **Cline**, **Replit Agent** — all converged on the same operating model: a long-running agent inside the editor (or terminal) with file-system tools, repository-aware system prompts, sub-agent orchestration, and per-project skills. Understanding the *shape* of this workflow is now a context-engineering literacy. This post is the practitioner's tour: how the loop works, what `AGENTS.md` / skills actually do for you, and the patterns that make sessions productive.
>
> **Reading time:** ~12 minutes.
>
> **After reading this you will be able to:**
> - Describe the agent loop common to Claude Code, Cursor, Aider, and friends.
> - Configure a project with the `AGENTS.md`, skills, and hooks that make the agent useful.
> - Avoid the four workflow anti-patterns that turn a $20-hour session into a $200-hour one.

---

## 1. What changed

For most of 2023 the standard "AI in the editor" pattern was *autocomplete plus inline chat*: Copilot suggested the next few lines; the user occasionally opened a side panel and asked a question. The model had no persistent context, no tools, no memory of the project.

The current generation is structurally different. The agent **lives in the project**, **reads files itself**, **edits files itself**, **runs commands itself** (with confirmation), **plans across many turns**, and **delegates sub-tasks to other agent instances**. The user moves from *prompting on every line* to *briefing on every task*.

The shift is large enough that the team-level practice changes too. The artefacts the project carries (`AGENTS.md`, skills, prompts, hooks) become first-class citizens of the codebase. The discipline of context engineering moves into the repository.

---

## 2. The agent loop

Reduced to its simplest form, every modern coding agent runs the same loop.

```
load context (AGENTS.md, file tree, skills)
↓
plan task (decompose if needed, sometimes via a sub-agent)
↓
┌─────────────────────────────────────────┐
│  while not done:                        │
│    think (LLM call)                     │
│    decide on next tool call             │
│    execute tool (read, write, run, …)   │
│    observe result                       │
│    update plan / scratchpad             │
└─────────────────────────────────────────┘
↓
summarise + commit / hand back to user
```

Each iteration is one LLM call plus one (or zero) tool call. A typical task takes 5–50 iterations; a complex one can take hundreds. The cost and latency of the loop are dominated by the *iteration count* and the *prompt size at each iteration* — which makes context engineering, again, the lever.

The four context-engineering decisions that shape the loop:

1. **What goes in the system prompt** → set by `AGENTS.md` plus the host's own preamble.
2. **What goes in the tool catalog** → set by the host (file tools, shell tool, MCP servers, custom tools).
3. **How the conversation is compressed as it grows** → set by the host's auto-compaction policy plus per-project hooks.
4. **What sub-agents the planner can delegate to** → set by the host's skill / sub-agent configuration.

A team that consciously sets all four ships materially better sessions than a team that takes the defaults.

---

## 3. `AGENTS.md` (and `CLAUDE.md`)

The repository's per-project system prompt. Every reachable agent in the project loads it. The format is convention; the convention has converged across vendors.

A working skeleton (the same five-block structure as Post 12, §2):

```markdown
# Project: Acme API

## Identity
A Python 3.12 + FastAPI backend for Acme's customer API. SQLAlchemy
2.x against Postgres 16. Tests with pytest + pytest-asyncio.

## Rules
- Every public function has a type annotation.
- Every change with behavioural impact has a test in `tests/`.
- Never commit to `main` directly; open a PR.
- Never edit files in `vendor/` or `legacy/`.
- Use `ruff` for formatting; the CI will reject other formatters.

## Format
- PR titles use Conventional Commits (feat, fix, chore, refactor, …).
- Commit bodies wrap at 72 columns.
- Code uses `from __future__ import annotations`; `from typing import …`.

## Knowledge
- Build: `make build`.
- Test: `make test` (uses Docker for the Postgres dependency).
- Deploy: `make deploy` (requires `STAGING=true` for non-prod).
- The `users` and `orders` tables are joined on `users.id = orders.user_id`.

## Tools
- `make migrate` — generate and apply Alembic migrations.
- `mcp:postgres` — read-only SQL against the local dev DB.
- `slash:run-tests` — runs `make test` and surfaces failing test names.
```

Subdirectory `AGENTS.md` files override or add to the parent. A `frontend/AGENTS.md` with TypeScript rules wins inside the frontend tree. The deepest matching file is the effective prompt for any operation in that subtree.

The discipline that makes this useful: **iterate from minimal**. Start with a near-empty file. Add a rule when a real failure motivates it (the agent removed a critical file; the agent renamed your enums; the agent committed in a style that broke CI). Speculative rules accumulate and contradict.

---

## 4. Skills

A **skill** is a small Markdown file (often called `skill.md`) that packages a single capability — a workflow the agent can invoke when the situation calls for it. A typical skill describes one task: how to draft a PR description in the team's style; how to write a Postgres migration; how to triage a production alert.

Each skill has the same five-block shape as a system prompt, but scoped to one concern. The host loads it *only when relevant*. A skill catalogue is essentially a small library of well-engineered procedural memories ([Post 14](../14-memory-systems/index.md), §4) — searchable by name, retrievable on intent, and version-controlled like code.

Two patterns make skill libraries pay off:

- **One concern per skill.** Like a Unix command. `write-migration.md` is a skill. `do-everything.md` is not.
- **Examples beat instructions.** A skill with two before/after examples is more useful than a skill with five paragraphs of rules. The agent learns from the shape.

The skill marketplaces (Claude Skills, Cursor MCP marketplace, community skill repos) are early but growing. The *discipline* of writing your own skills is more valuable than the catalogue size — every team accumulates a small library specific to its codebase that no public skill could match.

---

## 5. Sub-agents and the orchestrator pattern

Modern hosts let the main agent spawn sub-agents for scoped tasks. The patterns the field has converged on (Post 11, §3):

- **Research sub-agent.** "Read these three files and tell me how `process_order` is wired." The sub-agent does the reads; the parent gets a summary and keeps its context clean.
- **Test-and-fix sub-agent.** "Run the failing test, find the root cause, propose a fix." The sub-agent has shell + file tools; the parent stays at the planning level.
- **Migration sub-agent.** "Generate the Alembic migration for this schema change." The sub-agent has migration tools; the parent does not need to know the details.

Two tactical points:

- **Set the budget.** Each sub-agent has a maximum number of tool calls. Without this, a stuck sub-agent burns the day's tokens.
- **Make the contract explicit.** The sub-agent returns a structured summary (problem found, fix applied, tests passing). Free-form prose loses across the boundary.

A useful organisational habit: **review sub-agent transcripts on a sample**. The summaries the parent received can hide problems (the sub-agent skipped a test, hard-coded a value, edited a file it should not have). Periodic spot-checks keep the trust calibrated.

---

## 6. Hooks

Most modern hosts allow **hooks** — scripts that run at specific points in the agent loop. The pattern is borrowed from git hooks and is roughly as useful.

Common hook points and what teams use them for:

- **Pre-tool-call.** Validate the tool args; reject dangerous combinations (e.g., a `delete` on a path outside the project).
- **Post-tool-call.** Format the output; clip noisy logs (Post 11, §6); record a structured trace span.
- **Pre-edit.** Check the target file is not in a generated/vendored directory.
- **Post-edit.** Run the formatter; run the relevant test; if either fails, surface back to the agent.
- **Pre-commit.** Run linter / typecheck; block if either fails.
- **Session-start.** Print a one-line reminder of the day's task; load the project status; pin a "today's goal" cell into memory.
- **Session-end.** Compress the conversation; write a summary to a daily journal; archive the trace.

Hooks are how a team encodes its culture into the agent without bloating the system prompt. They are also where security controls (Post 18) actually enforce — *do not let the agent overwrite production config* is a hook, not a rule in `AGENTS.md`.

---

## 7. The four workflow anti-patterns

Each of these turns a productive session into an expensive one.

**Anti-pattern 1 — letting context grow without compaction.** The session has been running for four hours. The conversation is 180 k tokens. Every new turn pays for all of it. The agent's quality has been silently degrading for the last hour because of distraction (Post 05, §3) and lost-in-the-middle (Post 03, §3). The fix is hosted auto-compaction with sensible thresholds and the discipline of `/compact` (or equivalent) when the user notices quality drift.

**Anti-pattern 2 — over-broad task framing.** "Refactor the codebase" is not a task; it is a research project. The agent will burn the budget exploring. The fix is to break the work into 30-minute scoped tasks with clear definition of done. The agent works best at the same scope a human contributor does in a focused hour.

**Anti-pattern 3 — letting the agent autonomously edit everything.** Confirmation prompts feel like friction; they catch a lot. Tools that can do destructive things (delete files, force-push, drop database tables, run `rm -rf`) need confirmation in the host, not just in the prompt. The fix is the security defences from Post 18, applied locally to the dev environment.

**Anti-pattern 4 — no skills, no hooks, default `AGENTS.md`.** The team is using the agent on hard mode. Every session starts cold; the same instructions are typed for the dozenth time; the same defaults trip the agent up. The fix is investing one hour to set up the project-level customisations; it pays back within the first week.

---

## 8. The session as a unit of work

A useful mental model: **treat each agent session like a focused human-collaborator session**. Brief on the goal. Give it the relevant context. Check in at meaningful boundaries. Review the diff. Pair on the hard parts.

The teams getting the most leverage from these tools are the ones that have moved decisively from "the agent autocompletes my code" to "the agent does scoped tasks I assign and review". The shift is cultural as much as technical, and it is the largest practical productivity change the tools deliver.

---

## Common pitfalls

- **No `AGENTS.md`.** Every session re-discovers the project conventions.
- **Bloated `AGENTS.md`.** Every call pays for it; humans stop reading it; rules contradict.
- **No auto-compaction policy.** The session degrades silently after a few hours.
- **Sub-agents without budget caps.** A stuck sub-agent burns the day's tokens.
- **No hooks for dangerous commands.** Eventually the agent runs the wrong destructive command.
- **Treating agents as autocomplete.** The leverage of the new tools comes from delegating tasks, not from typing assistance.

---

## Further reading

- Anthropic, *"Claude Code"* docs (2024–25) — the canonical reference.
- agents.md project, *"AGENTS.md spec"* (2025).
- Cursor docs, *"Composer and AI rules"* (2025).
- Aider docs, *"Architect mode and conventions"* (2024–25).
- Anthropic Engineering, *"Claude Skills"* (2024).
- Cognition, *"Don't build multi-agents"* (2024) — the contrarian take, sharpens the discipline.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 21 — Remote agentic workflow](../21-remote-agentic-workflow/index.md)** — the same workflow, on a remote machine.
- **[Post 22 — Build a RAG chatbot](../22-build-rag-chatbot/index.md)** — the first capstone build.
- **[Post 18 — Security and prompt injection](../18-security/index.md)** — the local-dev variant of the security story.
