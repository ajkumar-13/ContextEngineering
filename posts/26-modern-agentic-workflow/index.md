# 26 - The modern agentic workflow

> **TL;DR.** Coding agents such as Claude Code, Cursor, Aider and Codex share one operating model: a long-running loop in the editor or terminal that reads files, edits them and runs commands, configured by files the repository carries. This post asks what that model is and which of those files make a session productive: `AGENTS.md` (or `CLAUDE.md`) in the five-block form, skills loaded on demand, hooks that enforce in code, and sub-agents that keep noise out of the main window. It closes with the four anti-patterns that multiply what a session costs.
>
> **Prerequisites:** [Post 13](../13-isolate-strategies/index.md), [Post 14](../14-system-prompt-as-software/index.md).
> **Safe to skip?** Skip it if a repository already carries a reviewed `AGENTS.md`, its own skills and hooks, sub-agents with turn caps and a compaction habit, and a session transcript can already be read as write, select, compress and isolate events.
>
> **After reading, you will be able to:**
>
> - Describe the agent loop that coding hosts share, and say which decisions the host makes and which the model makes.
> - Write a project's AGENTS.md in the five-block form, and explain how it, CLAUDE.md and a skill's SKILL.md reach the window.
> - Configure a hook that blocks or reports an edit, and say which hook events can stop the action.
> - Delegate a scoped task to a sub-agent with a contract and a turn cap, and say which work stays in the main agent.
> - Recognise the four workflow anti-patterns, and work out what an uncompacted session costs against a compacted one.

![Repository files on the left feed the six-layer window on the right: the rules file and skill descriptions into layer 01, MCP servers into layer 02, sub-agent summaries and hook messages into layer 05. Sub-agents run in windows of their own; hooks run as code outside the window.](diagrams/00-hero-modern-agentic-workflow.svg)

*The repository is the agent's configuration: each file feeds one layer of the window, by one of the four operations.*

---

## 1. The question: what did the coding tools converge on?

The first editor assistants were autocomplete plus a chat panel: the model suggested the next lines of the open file, with no tools and no view of the project. The current hosts work in the project: the agent reads files, edits them, runs commands (with confirmation where the host asks for it), plans across many turns and hands sub-tasks to other agent instances. Anthropic's "How Claude Code works" (Claude Code documentation, consulted October 2026) puts the contrast in one line: "This is different from inline code assistants that only see the current file." The person's job moves from prompting line by line to briefing task by task.

That shift moves context engineering into the repository: the files a project carries decide what the model reads on every call, so they are reviewed like code ([post 14](../14-system-prompt-as-software/index.md)), and the figure at the top maps each to the layer it feeds. The patterns are vendor-neutral; each example names the host whose documentation it follows, mostly Claude Code's, the most explicit about the mechanics.

---

## 2. The agent loop

Reduced to its simplest form, every coding host runs the same loop:

```text
load context: the rules file, skill descriptions, tool schemas
while the task is not done:
    model call: read the window, decide the next step
    tool calls: read, search, edit, run (zero, one or several)
    append the calls and their results to the window
    compact the window when it nears its limit
hand back: a summary of what changed, for review
```

Claude Code's documentation describes three phases, "gather context, take action, and verify results", and the division of labour: the model reasons and picks the tools, and "Claude Code is the layer around the model that provides the tools and manages the context the model sees." Every model call re-reads the whole window, so a session's cost and latency are set by how many calls it makes and how large the window is at each.

The host, configured by the repository, takes four context decisions, each one of the operations of [post 07](../07-write-select-compress-isolate/index.md):

1. **The standing instructions.** `AGENTS.md` or `CLAUDE.md` on top of the host's preamble, selected into layer 01, the system prompt, every session (section 3).
2. **The tool catalogue.** File, search and shell tools plus MCP servers (the Model Context Protocol, through which external tools reach a host; [post 15](../15-tools-and-mcp/index.md)) fill layer 02, tools and MCP descriptions. It is a select: in Claude Code, "MCP tool definitions are deferred by default and loaded on demand via tool search".
3. **Compression.** Automatic compaction of layer 05, conversation history, which in Claude Code "clears older tool outputs first, then summarizes the conversation if needed", and `/compact` ([post 12](../12-compress-strategies/index.md), section 8).
4. **Delegation.** Sub-agents with windows of their own: isolate (section 5).

The model's own choices are mostly selects: a coding agent does not load the repository but searches and reads the few files a step needs, the decision of [post 25](../25-long-context-vs-rag/index.md) taken on every turn.

---

## 3. `AGENTS.md` and `CLAUDE.md`

The standing instructions live in a file checked in beside the code: `AGENTS.md`, the open format read by Codex, Cursor and other agents, or `CLAUDE.md`, Claude Code's. [Post 14](../14-system-prompt-as-software/index.md), section 4, gives how each reaches the window. For nested files the agents.md site's rule is "The closest AGENTS.md to the edited file wins", and Cursor's "Rules" documentation (consulted October 2026) supports `AGENTS.md` "in the project root and subdirectories"; Claude Code instead concatenates the `CLAUDE.md` files from the root down and delivers them as a user message after the system prompt. Both do the job of layer 01, and one file can serve every host: Claude Code reads `AGENTS.md` when there is no `CLAUDE.md`, and a `CLAUDE.md` can import it with an `@AGENTS.md` line. Aider loads a conventions file when told to: its "Specifying coding conventions" page (consulted October 2026) recommends `aider --read CONVENTIONS.md`, which marks the file "read-only, and cached if prompt caching is enabled".

A skeleton in [post 14](../14-system-prompt-as-software/index.md)'s five blocks (identity, rules, format, knowledge, tool-use guidance), each rule carrying the issue that motivated it:

```markdown
# AGENTS.md for acme-api

## Identity
A Python 3.12 and FastAPI backend for Acme's customer API, on PostgreSQL 16.
Agents implement changes and open pull requests here; they do not deploy.

## Rules
- Every change in behaviour ships with a test in `tests/`. [#117]
- Never edit `vendor/` or `legacy/`; a hook enforces this. [#142]
- Open a pull request for every change; never commit to `main`. [#150]

## Format
- Pull-request titles use Conventional Commits (feat, fix, chore, refactor).

## Knowledge
- Build: `make build`. Test: `make test` (starts PostgreSQL in Docker).

## Tool-use guidance
- `make migrate`: generate and apply Alembic migrations.
- `/run-tests` (a project skill): runs `make test`, lists the failures.
```

A `frontend/CLAUDE.md` is read in addition to the root file, so it can add a rule but not replace one. The discipline is [post 14](../14-system-prompt-as-software/index.md)'s: **iterate from minimal**, adding a rule only when a real failure motivates it (the agent deleted a needed file, or committed in a style continuous integration (CI) rejected). Every line is read on every call; Claude Code's documentation targets under 200 lines per `CLAUDE.md`.

---

## 4. Skills

A **skill** packages one capability the agent loads when a task calls for it: a pull-request description in the team's style, a migration, an alert triage. In Anthropic's Agent Skills format ("Equipping agents for the real world with Agent Skills", 16 October 2025), a skill is a directory holding a `SKILL.md`, whose front matter gives a `name` and a `description`, and any scripts it uses ([post 08](../08-write-strategies/index.md), section 4). Claude Code's "Extend Claude with skills" page (consulted October 2026) reads project skills from `.claude/skills/<skill-name>/SKILL.md`, committed for the team, and a person's own from `~/.claude/skills/`. A minimal project skill, `.claude/skills/write-migration/SKILL.md`:

```markdown
---
name: write-migration
description: Draft an Alembic migration for a schema change to the Acme database. Use when a task adds, drops or alters a table or a column.
---

## Steps
1. Read the current model in `app/models/`.
2. Generate the migration with `make migrate`.
3. Check that the generated file touches only the intended tables.

## Example
Before: add a `deleted_at` column to `orders`.
After: a migration that adds the nullable column and a matching index.
```

**How the host decides to load it.** By the description. The page states that "skill descriptions are loaded into context so Claude knows what's available, but full skill content only loads when invoked", and the `description` field's entry reads "Claude uses this to decide when to apply the skill." No keyword list fires it: the model judges the match from the description (an optional `when_to_use` field is appended), so the description says what the skill does and when to use it. An unused skill costs only its description per call.

**Which copy wins.** When a personal and a project skill share a name, the page's order is "Enterprise over personal, and personal over project". Sub-agent definitions resolve the other way (section 5).

Skills are the packaged-capability home of [post 16](../16-memory-systems/index.md), section 6: team rules in `AGENTS.md`, packaged capabilities in a `SKILL.md`, a how-to learned about one user as a procedural memory row. Two habits pay off: **one concern per skill**, and **examples over instructions**, since one before-and-after pair often steers better than a paragraph of rules (rule 5 of [post 14](../14-system-prompt-as-software/index.md), section 3).

---

## 5. Sub-agents and the orchestrator pattern

Hosts let the main agent hand a scoped task to a **sub-agent**. Claude Code's "Create custom subagents" page (consulted October 2026) says that "each subagent runs in its own context window with a custom system prompt, specific tool access, and independent permissions" and "returns only the summary". The patterns are [post 13](../13-isolate-strategies/index.md)'s: a **research** sub-agent reads a module and reports how it is wired (Claude Code's built-in Explore sub-agent, read-only by design); a **test-and-fix** sub-agent keeps the test logs in its own window. Definitions are files too: Markdown with YAML front matter (`name`, `description`, optionally `tools`, `model`, `maxTurns`) in `.claude/agents/`, where a project definition outranks a personal one in `~/.claude/agents/`.

Delegation is a four-step handshake, drawn below. The parent (1) frames a scoped task and names the result it expects; (2) spawns the sub-agent with a fresh window, only the tools the task needs and a turn cap; the sub-agent (3) runs its own loop of reads, tool calls and retries in isolation; the parent (4) folds only the returned summary into its window. It never sees the child's intermediate calls, so its window stays small and on task.

![Two lanes, the parent's window above and the sub-agent's below, across four steps: frame the task and the result expected; spawn with a fresh window, scoped tools and a turn cap; the sub-agent's own loop, which never reaches the parent; fold in the summary only.](diagrams/02-orchestrator-handshake.svg)

*The summary is what keeps the parent's window small, and also what hides the child's mistakes from it.*

- **Cap the turns.** Claude Code's `maxTurns` is the "maximum number of agentic turns before the subagent stops"; the output then comes back marked as partial. Nesting is capped too: by default a sub-agent can spawn its own, "up to three layers below the main conversation".
- **Make the contract explicit.** The sub-agent returns a structured result (what it found, what it changed, which tests pass), and the parent checks it before acting ([post 13](../13-isolate-strategies/index.md), section 5).
- **Review transcripts on a sample.** A summary can hide a skipped test, a hard-coded value or an edit the child should not have made.

**The steelman against all this.** Walden Yan's "Don't Build Multi-Agents" (Cognition, June 2025) argues that splitting work fragments the context: each agent holds a slice of the reasoning behind the others' outputs, and parallel agents make conflicting implicit decisions. It recommends a single-threaded, linear agent, and describes Claude Code's sub-agents of the time as consistent with that view, since a sub-agent was usually given a question to answer rather than code to write and never ran in parallel with the main agent ([post 13](../13-isolate-strategies/index.md), section 9). The reconciling rule is [post 13](../13-isolate-strategies/index.md)'s contract test: delegate a task whose input is fully specified, whose output is structured and finite, and which needs none of the parent's evolving state; keep in the main agent anything whose reasoning must stay coherent across steps.

---

## 6. Hooks

A **hook** is a command the host runs at a fixed point of the loop, a pattern borrowed from git hooks: a small program fires on an event and can inspect what is about to happen, block it or report back. The model sees only what the hook chooses to say.

Claude Code's "Hooks reference" (consulted October 2026) gives the protocol. Hooks are registered in a settings file such as `.claude/settings.json`, by event name and a matcher on the tool name. The host passes the event as JavaScript Object Notation (JSON) on standard input, with fields such as `cwd`, `tool_name` and `tool_input`, and the exit code is the answer. Exit 0 lets the action proceed. "Exit with code 2 to block the action": the hook's standard error becomes the message, which before a tool call blocks it and tells the model why, and after a tool call (the tool has already run) is shown to the model. Any other non-zero code is "a non-blocking error", so a hook that enforces a policy exits 2.

`snippets/edit_hooks.py` implements two hooks in that protocol, registered under `PreToolUse` and `PostToolUse` with the matcher `Edit|Write`. The guard runs before every edit:

```python
def guard(event):
    """PreToolUse on Edit|Write: block an edit outside the project or inside a protected directory."""
    root = Path(event["cwd"]).resolve()
    target = (root / event["tool_input"]["file_path"]).resolve()
    if not target.is_relative_to(root):
        return 2, "blocked: the file is outside the project."
    top = target.relative_to(root).parts[0]
    if top in PROTECTED:
        return 2, f"blocked: {top}/ is read-only here; change the code that calls it."
    return 0, ""
```

The second, `compile_check`, runs after each edit and reports a Python file that no longer parses. With no argument, the script builds a throwaway project in a temporary directory and calls itself five times as the host would. `uv run python posts/26-modern-agentic-workflow/snippets/edit_hooks.py` from the series root prints:

```text
PreToolUse   Edit   app/orders.py       exit 0  allowed
PreToolUse   Edit   vendor/payments.py  exit 2  blocked: vendor/ is read-only here; change the code that calls it.
PreToolUse   Write  ../.env             exit 2  blocked: the file is outside the project.
PostToolUse  Edit   app/orders.py       exit 0  passed
PostToolUse  Edit   app/refunds.py      exit 2  refunds.py line 1: expected ':'.
```

The last line is the loop correcting itself: the syntax error reaches the model as the hook's message, and the next call fixes it. The figure below places the hook events on the loop.

![The agent loop from session start through the user's prompt, model calls and tool calls to session end, with hook events at their points: PreToolUse, UserPromptSubmit and PreCompact can block; PostToolUse reports after the tool has run; SessionStart adds its output to the context; SessionEnd cannot block.](diagrams/01-hook-points.svg)

*Only a hook in front of an action can stop it; the hook after a tool call can only report, because the tool has already run.*

The points teams attach to, in Claude Code's event names:

- **`PreToolUse`.** Block dangerous arguments: an edit in `vendor/`, a delete outside the project, a force push. A pre-commit check is this event on the shell tool, or git's own pre-commit hook.
- **`PostToolUse`.** Run the formatter or the relevant test after an edit and report a failure; record a trace span ([post 22](../22-observability/index.md)). Trimming a noisy tool result is the tool wrapper's job ([post 13](../13-isolate-strategies/index.md), section 6).
- **`SessionStart`.** Claude Code adds such a hook's plain-text output "to Claude's context", so a hook that prints the branch's open issue is a select into the window.
- **`PreCompact` and `SessionEnd`.** Both suit housekeeping, such as archiving the transcript outside every prompt; `SessionEnd` cannot block, while `PreCompact` exiting 2 blocks compaction.

Local security controls belong here: "do not overwrite production configuration" is a hook, not a line in `AGENTS.md`, because a rule in the prompt is followed most of the time and code that intercepts the call every time (D1 of [post 23](../23-security/index.md), section 5).

---

## 7. The four workflow anti-patterns

**Anti-pattern 1: letting the history grow without compaction.** Every call re-reads the whole window, so a session's input grows with the square of its length when nothing is removed. `snippets/session_cost.py` replays one session with illustrative sizes: an 18,000-token stable prefix (layers 01 and 02) and 120 model calls, each appending a 300-token tool call and a 2,200-token tool result to layer 05, at Claude Opus 4.6's rates as of early 2026 (5 dollars per million input tokens, 25 per million output, a cache write at 1.25 times and a cache read at 0.1 times the input price; Anthropic, "Pricing" and "Prompt caching", consulted October 2026, as [post 05](../05-economics-of-context/index.md) states them). The second run compacts whenever the window would pass 100,000 tokens, an illustrative policy, into a 5,000-token summary. Running `uv run python posts/26-modern-agentic-workflow/snippets/session_cost.py` prints:

```text
illustrative session: 120 calls, prefix 18000 tokens, +2500 tokens per call
prices: Claude Opus 4.6, 5 and 25 dollars per million, cache write 1.25x, cache read 0.1x
                        input tokens  peak window  compactions  uncached $  cached $
no compaction               20010000       315500            0      100.95     12.72
compact at 100000            7254000        95500            3       37.55      6.80
no compaction reads 2.8 times the input tokens and costs 1.9 times as much with caching
```

Without compaction the last call reads $18{,}000 + 119 \times 2{,}500 = 315{,}500$ tokens and the session $120 \times 18{,}000 + 2{,}500 \times (0 + 1 + \dots + 119) = 20{,}010{,}000$. Three compactions keep every call under 100,000 tokens and cut the input to 7,254,000. Caching narrows the dollar gap (12.72 against 6.80 dollars) but does not shrink what the model reads, and a long window is where distraction ([post 06](../06-context-failure-modes/index.md), section 2) and lost-in-the-middle ([post 06](../06-context-failure-modes/index.md), section 5) set in. The figure below draws the window call by call. The fix is automatic compaction left on, and `/compact` (or `/clear` at a real task boundary) when quality drifts ([post 12](../12-compress-strategies/index.md), sections 8 and 9).

![A line chart of the window in tokens over 120 model calls: without compaction a straight climb from 18,000 to 315,500; with compaction a sawtooth up to 95,500 and back to 23,000, three times, under a dotted 100,000-token limit. Illustrative sizes.](diagrams/03-session-window.svg)

*Every call pays for the whole window, so the area under each line is the session's input.*

**Anti-pattern 2: over-broad task framing.** "Refactor the codebase" is a research project, not a task, and the agent spends its budget exploring. The fix is scoped tasks with a clear definition of done; a rule of thumb from practice, not measurement, is the scope a person would finish in one focused sitting.

**Anti-pattern 3: letting the agent edit and run everything unasked.** Confirmation prompts catch real mistakes. Claude Code's checkpoints undo file edits only: "Actions that affect remote systems (databases, APIs, deployments) can't be checkpointed." Deleting files, force-pushing, dropping tables and deploying need confirmation enforced by the host (a permission rule or a hook), not a sentence in the prompt: D1 and D2 of [post 23](../23-security/index.md), section 5, on the development machine, with the confirmation flow of [post 15](../15-tools-and-mcp/index.md), section 6.

**Anti-pattern 4: no skills, no hooks, a default `AGENTS.md`.** Every session starts cold and the same mistakes recur. The fix is the setup of sections 3 to 6, grown from real failures.

---

## 8. The session as a unit of work

A useful mental model: **treat each agent session like a focused session with a human collaborator**: brief it, check in at boundaries, review the diff.

A transcript can be read in the vocabulary of [post 07](../07-write-select-compress-isolate/index.md), section 9, each event a write, select, compress or isolate on one layer. One illustrative session on the repository of section 3, adding a `deleted_at` column to `orders`:

| # | Event | Op | Layer |
|---|---|---|---|
| 1 | Before the session, a reviewed rule is added to `AGENTS.md`. | W | 01 System prompt |
| 2 | At start, the host loads `AGENTS.md` and every skill's description. | S | 01 System prompt |
| 3 | A `SessionStart` hook prints the branch's open issue. | S | 05 Conversation history |
| 4 | The task matches `write-migration`; its `SKILL.md` loads. | S | 01 System prompt |
| 5 | A research sub-agent reads the order module and returns a summary. | I | 05 Conversation history |
| 6 | The agent writes its plan to a notes file outside the window. | W | none |
| 7 | Near the limit, old tool outputs are cleared and the history summarised. | C | 05 Conversation history |
| 8 | After compaction, the agent reads its notes file back. | S | 05 Conversation history |
| 9 | A `SessionEnd` hook archives the transcript outside every prompt. | W | none |

The rules file and the skill are placed by their job, standing instructions, as [post 14](../14-system-prompt-as-software/index.md) places `CLAUDE.md` in layer 01; hooks that only block or report are code and appear only where they write or select.

---

## 9. What can go wrong?

- **A hook that exits 1.** It means to block an edit; Claude Code treats code 1 as a non-blocking error, and the protected file changes.
- **A hook trusted unread.** The reference warns that "Command hooks execute shell commands with your full user permissions." Claude Code holds hooks back until a folder is trusted, so a cloned repository's `.claude/` settings are read first.
- **A nested file expected to replace its parent.** A `frontend/CLAUDE.md` is written to override a root rule; Claude Code reads both, and the agent follows either.
- **A skill that never loads.** Its description says "Database helper"; nothing in it matches a migration task, so the agent writes the migration from scratch and skips the team's checks.
- **A sub-agent's summary taken on trust.** The child reports "all tests pass" after running a subset; CI fails on the tests it never ran.
- **A session that runs all day.** Quality drops by the afternoon: the morning's instructions sit mid-history.

---

## Common pitfalls

1. **No `AGENTS.md`, or a bloated one.** Without it every session rediscovers the conventions; bloated, it costs tokens on every call and its rules contradict each other.
2. **Rules where hooks belong.** "Never edit `vendor/`" in the prompt is followed most of the time; a `PreToolUse` hook that exits 2 every time.
3. **No compaction habit.** The window grows until quality and the bill both suffer; compact or clear at task boundaries.
4. **Sub-agents without turn caps or contracts.** A stuck child burns tokens, and an unchecked summary hides its mistakes.
5. **Treating the agent as autocomplete.** The leverage comes from delegating scoped, reviewed tasks, not from faster typing.

---

## Further reading

- Anthropic, ["How Claude Code works"](https://code.claude.com/docs/en/how-claude-code-works), ["Hooks reference"](https://code.claude.com/docs/en/hooks), ["Extend Claude with skills"](https://code.claude.com/docs/en/skills), ["Create custom subagents"](https://code.claude.com/docs/en/sub-agents) and ["How Claude remembers your project"](https://code.claude.com/docs/en/memory) (Claude Code documentation, consulted October 2026).
- agents.md project, ["AGENTS.md"](https://agents.md/) (consulted October 2026).
- Cursor, ["Rules"](https://cursor.com/docs/context/rules) (documentation, consulted October 2026).
- Aider, ["Specifying coding conventions"](https://aider.chat/docs/usage/conventions.html) (documentation, consulted October 2026).
- Anthropic Engineering, ["Equipping agents for the real world with Agent Skills"](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) (16 October 2025).
- Cognition (Walden Yan), ["Don't Build Multi-Agents"](https://cognition.com/blog/dont-build-multi-agents) (June 2025): the counter-argument of section 5.
- Anthropic, ["Pricing"](https://platform.claude.com/docs/en/about-claude/pricing) and ["Prompt caching"](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) (consulted October 2026): the rates of section 7.

---

## What to read next

- **[Post 27 - Remote agentic workflow](../27-remote-agentic-workflow/index.md):** the same workflow on a remote machine, reachable from any device.
- **[Post 28 - Build #1: RAG chatbot from scratch](../28-build-rag-chatbot/index.md):** the first build, where an `AGENTS.md`, a five-block prompt and an eval gate meet in one repository.
