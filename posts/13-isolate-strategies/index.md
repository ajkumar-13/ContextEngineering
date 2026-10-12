# 13 - Isolate strategies

> **TL;DR.** Isolate is the operation of write, select, compress, isolate (WSCI) that stops using a single context window and uses several. Its two recurring patterns are sub-agents, where a parent hands a scoped task to a child with a clean window of its own and gets back only a structured result, and sandboxing, where a tool runs in a process whose noisy output never enters the model's window. Isolation pays when a sub-task has a clean input and output contract, and costs more than it saves when it does not; this post gives the test, the topologies, the contract, the cost arithmetic and the case against splitting at all.
>
> **Prerequisites:** [Post 07](../07-write-select-compress-isolate/index.md).
> **Safe to skip?** Skip it if a sub-agent's input and output contract can already be written, a sandbox wrapper can already be built, and the token cost of a fan-out can already be set against that of a single agent.
>
> **After reading, you will be able to:**
>
> - Decide whether a task should be isolated by testing its input contract, its output contract and its independence from the parent's state.
> - Specify the input and output contracts of a sub-agent, and validate its result against the output contract before the parent uses it.
> - Choose among sequential, fan-out and fan-in, and supervisor topologies, and say which of them leave the next step to the model.
> - Keep noisy tool output out of the window with a sandbox that returns only the fields the model needs.
> - Work out the token cost of an isolated design against a single agent, and say when isolation lowers the bill and when it raises it.

![A parent window of 26 tokens sends a typed task to a worker window, which fills with three test-runner calls and their logs, 9 messages and 1,418 tokens. Only a validated result returns, and the parent grows by 33 tokens; none of the 85 log lines reaches it.](diagrams/01-subagent-isolation.svg)

*The worker's window holds the noise; the parent's window holds the answer. Counts printed by snippets/orchestrator.py.*

---

## 1. The question: when is one window not enough?

A single context window comes under strain when the conversation is long, the toolbox large, several sub-tasks compete for attention, and at least one produces noisy output (logs, search results, file dumps). The other operations of [post 07](../07-write-select-compress-isolate/index.md) (tighter writing, harder selection, heavier compression) then give less and less, because all the work still shares one window; [post 06](../06-context-failure-modes/index.md) lists isolate among the fixes for lost-in-the-middle and tool-storm, two failures of one overloaded window. Isolation changes the structure instead: each piece of work runs in its own window, with its own tools and budget. The question of this post is when that split is worth what it costs.

Anthropic's account of its Research feature ("How we built our multi-agent research system", June 2025) gives one measured answer for research tasks. A system with Claude Opus 4 as the lead agent and Claude Sonnet 4 sub-agents outperformed a single Claude Opus 4 agent by 90.2% on Anthropic's internal research evaluation; the same post reports that, in Anthropic's data, agents use about 4 times more tokens than chat interactions and multi-agent systems about 15 times more. Better answers and a larger bill arrive together.

**Workflow versus agent.** A multi-call system takes one of two shapes. Anthropic's "Building Effective AI Agents" (December 2024) defines workflows as systems where models and tools are orchestrated through predefined code paths, and agents as systems where the model directs its own process and tool use. A workflow is predictable and cheaper to reason about; an agent is flexible and harder to bound. The same post recommends the simplest solution possible, adding complexity only when needed, and this post does the same.

---

## 2. The pattern: sub-agents

A sub-agent is a model call, or a loop of calls, launched by a parent agent with three things scoped: an **input** (a focused task description and the data it needs), a **toolkit** (only the tools this sub-task uses) and an **output contract** (the shape of the result the parent expects).

The parent sees the input it sent and the output it received, and nothing in between: the tool calls, retries, scratchpad notes and full document reads live and die inside the sub-agent's window.

That property is the point. A research sub-agent that reads ten long documents adds one short answer to the parent's window, not the documents; a debugging sub-agent that tries seven hypotheses adds the one that worked, not the six that failed.

The snippet `snippets/orchestrator.py` shows the property without a framework. A release agent delegates a test run to a worker, the worker calls a test-runner tool on three files whose verbose logs fill its own window, and the parent appends only the worker's validated result to its own message list. The worker's model is a scripted stand-in that makes the tool calls a model would make, so the script runs offline with no application programming interface (API) key; it shows which tokens land in which window, counted with the `o200k_base` encoding of `tiktoken`. Running `uv run python posts/13-isolate-strategies/snippets/orchestrator.py` from the series root prints:

```text
worker window: 9 messages, 1418 tokens (3 test logs, 85 log lines)
parent window: 26 tokens before the call, 59 after (+33)
returned to the parent: {"passed": 73, "failed": ["tests/test_db.py::test_migration_rollback", "tests/test_auth.py::test_token_expiry"]}
log lines in the parent window: 0
a prose reply is rejected by the contract check: JSONDecodeError
```

The worker's window held 1,418 tokens; the parent's grew by 33, and the script asserts that none of the 85 log lines reached it. The figure at the top of the post draws the two windows side by side.

---

## 3. When to isolate (and when not to)

The rule:

> **Isolate when the sub-task has a clean input contract and a clean output contract. Do not isolate otherwise.**

A clean contract means three things, all at once:

1. **The input is fully specified.** The sub-agent does not need to ask the parent clarifying questions. If it does, the round trips cost more than the split saves.
2. **The output is structured and finite.** The parent knows what shape of result to expect (a JavaScript Object Notation (JSON) object, a list of titles, a single number). A sub-agent cannot return "a conversation".
3. **The work is self-contained.** The sub-agent does not need ongoing access to the parent's evolving state.

Five example tasks calibrate the rule:

| Task | Isolate? | Why |
|---|---|---|
| "Find the three most relevant papers and return their titles and digital object identifiers" | **Yes** | Input clear; output structured; self-contained |
| "Read this 200-page contract and return a summary" | **Yes** | Input clear; output bounded; the source never needs to enter the parent's window |
| "Run the test suite and return pass or fail and the failing tests' names" | **Yes** | The tool output is large; the structured result is small |
| "Help me think through the architecture of this feature" | **No** | No clean output contract; the value is the conversation |
| "Decide whether to escalate this ticket" | **Borderline** | Yes if the escalation rules are written down; no if the decision needs context only the parent holds |

Isolating a sub-task that fails this test gives the worst of both designs: a chatty sub-agent that needs context the parent has to reload, paying twice for a worse answer.

---

## 4. The three topologies

Three wirings cover the designs this series uses, drawn side by side below.

![Three panels: a sequential chain of workers A, B and C; a parent fanning out to N parallel workers whose results a merge step combines; and a supervisor exchanging calls with three workers in a loop. The first two are marked as workflows with the flow in code; under the third, the model picks the next step.](diagrams/02-three-topologies.svg)

*In the first two the engineer writes the control flow; only the supervisor hands the next step to the model.*

**Sequential pipeline.** Sub-agent A's output is sub-agent B's input, and B's output is C's. Each sub-agent has one job, and the pattern fits clear hand-offs: parse, then analyse, then format. The risk is latency, because every step waits for the one before; the strength is auditability, because each stage's input and output can be logged on its own. "Building Effective AI Agents" calls this prompt chaining.

**Fan-out and fan-in (map-reduce).** A parent issues *N* sub-tasks of the same kind in parallel, and the parent or a final reducer call merges their partial results. The pattern fits "do this for each of these items": research three competitors, summarise each chapter, review ten files. The latency is that of the slowest worker, the token cost grows linearly with *N* (section 8), and the merge step is where the bugs collect, because it is the one place the partial results meet. The same post calls it parallelisation by sectioning.

**Supervisor and workers.** A supervisor model decides, call by call, which worker to call next and how to combine the results. The pattern fits open-ended problems where the decomposition is itself part of the work: agentic research, complex coding tasks, long support sessions. Its prompt needs the most care; without it, the supervisor becomes a generalist that does every worker's job itself: told to delegate a patch, it writes the patch in its own window, and the worker's clean window buys nothing.

The first two are workflows in Anthropic's sense. The supervisor is where the model starts choosing the next step. Anthropic's nearest pattern, orchestrator-workers (a central model breaks a task down, delegates the parts and synthesises the results), is still listed among its workflows; a supervisor that also loops until it judges the task finished sits on the agent side of the line. The practical rule: **start with a sequential or fan-out design**, and reach for a supervisor only when the decomposition cannot be planned ahead of time.

---

## 5. Designing the contract

A sub-agent's prompt is half specification and half guard-rail. A skeleton that travels well:

```text
You are the {role} sub-agent.

Your task: {one paragraph, no ambiguity}.

Inputs you will receive:
- {input 1}: {type, format, example}
- {input 2}: {type, format, example}

You have access to the following tools:
- {tool 1}: {when to use}
- {tool 2}: {when to use}

You MUST return a JSON object of the form:
{ "key1": <type>, "key2": <type>, "confidence": <0..1> }

Constraints:
- Do not ask clarifying questions; if the input is insufficient, return
  { "error": "<what is missing>" }.
- Do not return prose outside the JSON object.
- If you cannot complete the task within {budget} tool calls, return
  { "error": "budget_exhausted", "partial": <best effort> }.
```

The constraints are where first designs are weakest. A sub-agent allowed to return prose will sometimes return prose; one allowed to exceed its budget will sometimes exceed it.

A prompt asks; code enforces. The other half of the contract is a check of the reply against the output schema at the boundary, before the parent uses it, so that a malformed reply fails loudly instead of propagating. In `snippets/orchestrator.py` both halves are a few lines of the standard library:

```python
@dataclass(frozen=True)
class TestTask:  # the input contract: everything the worker needs, and nothing else
    paths: list[str]


@dataclass(frozen=True)
class TestReport:  # the output contract: structured and finite
    passed: int
    failed: list[str]


def validate(raw: str) -> TestReport:
    """Check the worker's reply against the output contract before the parent uses it."""
    data = json.loads(raw)  # a prose reply fails here
    ok = (isinstance(data, dict) and set(data) == {"passed", "failed"}
          and isinstance(data["passed"], int) and isinstance(data["failed"], list)
          and all(isinstance(name, str) for name in data["failed"]))
    if not ok:
        raise ValueError("the reply does not match the output contract")
    return TestReport(data["passed"], data["failed"])
```

The last line of the output in section 2 is this check at work: a prose reply ("All tests passed except two, see above.") is rejected before the parent reads it. A schema library (Pydantic, Zod, JSON Schema) does the same job at scale.

---

## 6. The pattern: sandboxing

Sandboxing is the second species of isolation, and it is structural rather than agentic. The principle: **run the tool somewhere whose noisy output never enters the model's window.** Sandboxing here means output-scoping, deciding what a tool result contributes to the window, not the security sense of containment and privilege separation, which [post 23](../23-security/index.md) covers.

The motivating example is `npm install`. A coding agent runs it to set up a project; it prints pages of progress lines, deprecation warnings and peer-dependency complaints, of which the model needs one fact (it succeeded) or three (it failed, the failing package, the failing line). Pasting the whole output into the next call is wasteful and distracting.

The mechanism:

- The agent calls a tool that runs the command in a child process.
- The child process's standard output and error are captured to a file, kept for debugging (the snippet's lives in a temporary directory).
- A small wrapper extracts the fields the model needs.
- Only those fields return to the model.

`snippets/sandbox.py` does exactly this with a stand-in install command (a child process that prints a package-manager-style log; nothing is installed). Its wrapper is one function, and `uv run python posts/13-isolate-strategies/snippets/sandbox.py` prints:

```text
full log: 133 lines, 2385 tokens (kept in install.log)
returned to the model: {"ok": true, "exit_code": 0, "warnings": 12, "summary": "added 120 packages in 8s", "log": "install.log"}
38 tokens, 63 times fewer than the full log
```

![A child process prints a 133-line install log of 2,385 tokens to a file on disk; a wrapper passes a five-field result of 38 tokens, 63 times fewer, into the model's window.](diagrams/03-sandbox-wrapper.svg)

*The model's window receives the five fields; the log stays on disk. Counts printed by snippets/sandbox.py.*

As the figure shows, for the model the rest of the output does not exist; for a human debugging the run, it is one file read away. The pattern generalises: a code interpreter can return the value, not the print stream; a web fetch, the cleaned text, not the raw markup; a database query, the rows, not the connection chatter. Any tool whose signal is small next to its noise is a candidate.

---

## 7. Memory across isolated agents

A sub-agent cut off from the parent's window still needs what earlier calls learned. Two patterns:

- **Shared external memory.** The sub-agent has read access to the same memory store as the parent ([post 16](../16-memory-systems/index.md)) and writes its findings there with provenance, naming itself as the source. Best for episodic and semantic facts that later calls, by the parent or by other sub-agents, should benefit from.
- **Hand-back summary.** The sub-agent's output contract includes a field of two or three sentences on what it learned, and the parent appends that to its own memory or scratchpad. Best for facts specific to this parent task.

The wrong pattern is to pass the parent's full window into the sub-agent, which brings back every problem isolation was meant to remove.

---

## 8. The cost arithmetic

Whether isolation lowers or raises the bill depends on one thing: whether the single agent would have re-read tokens that a worker can keep to itself. `snippets/isolation_cost.py` writes the arithmetic out for two cases with illustrative sizes: five independent pieces of work, a 2,000-token preamble (system prompt and tools) at the start of every window, and prices at Claude Sonnet 4.5's rates as of early 2026, 3 dollars per million input tokens and 15 dollars per million output tokens (Anthropic, "Pricing", consulted October 2026). One function prices any agent loop that re-reads its whole window on every call:

```python
def loop(prefix, steps, step_out, result, final_out):
    """Input and output tokens of one agent loop that re-reads its whole window on every call.

    The window starts at prefix tokens. Each of the steps is a model call that writes a step_out-token
    tool call and gets back a result-token tool result; one last call writes final_out tokens.
    """
    calls = steps + 1
    tokens_in = sum(prefix + c * (step_out + result) for c in range(calls))
    tokens_out = steps * step_out + final_out
    return tokens_in, tokens_out
```

**One shot.** Each piece is an 8,000-token document pasted into the prompt, with no tool calls. One agent reads the preamble and all five documents, $2{,}000 + 5 \times 8{,}000 = 42{,}000$ input tokens, and writes a 1,000-token answer. Five workers each read the preamble and one document, $5 \times 10{,}000 = 50{,}000$ tokens, and write 1,000 tokens each; a merge call reads the preamble and the five answers, 7,000 tokens, and writes the final 1,000.

**Agent loop.** Each piece needs four tool calls of 100 tokens that return 2,000 tokens each. One agent makes all twenty in one window, so every call re-reads every earlier result. Each worker makes its four in its own window and returns a 300-token result, and the orchestrator's own loop makes five delegate calls and reads five results. The script prints:

```text
one shot
  one agent                  42000 in  1000 out  0.1410 dollars
  orchestrator and workers   57000 in  6000 out  0.2610 dollars
agent loop
  one agent                 483000 in  3000 out  1.4940 dollars
  orchestrator and workers  173000 in  5000 out  0.5940 dollars
```

![Bars of input tokens. One shot: one agent 42,000; orchestrator and workers 57,000, the workers 50,000 and the merge 7,000. Agent loop: one agent 483,000; orchestrator and workers 173,000, the workers 155,000 and the orchestrator 18,000. Illustrative sizes.](diagrams/04-isolation-cost.svg)

*Fanning out a one-shot job only adds preambles and a merge; fanning out a loop stops every call re-reading every other piece's tool results.*

In the one-shot case isolation costs more: the preamble is paid five times instead of once, five answers are written instead of one, and the merge call is extra, so the bill is 0.2610 dollars against 0.1410. In the loop case it costs less, 0.5940 dollars against 1.4940: every call the single agent makes on the fifth piece re-reads the sixteen tool results of the four pieces already finished, while a worker's calls read only its own results. The figure sets the two cases side by side. Prompt caching ([post 05](../05-economics-of-context/index.md)) bills a re-read prefix at a fraction of the input rate and so narrows the dollar gap of the loop case, but it does not shrink the window the model has to read.

The arithmetic holds the amount of work fixed, and real systems do not: in Anthropic's figures of section 1, multi-agent systems use about 15 times the tokens of a chat against about 4 for a single agent, so the saving here is a property of input scoping, not a forecast of a bill. That is the useful corollary: **good sub-agent design is largely good input scoping.** A design that stuffs the whole conversation into every sub-agent's prompt pays the single agent's re-reads once per worker, and is a sign that the problem cannot be cleanly isolated.

---

## 9. The steelman: "Don't Build Multi-Agents"

Everything so far argues for isolation; the strongest argument against it deserves equal room.

Walden Yan of Cognition, the team behind the Devin coding agent, published "Don't Build Multi-Agents" (June 2025). It rests on two principles, stated in the essay as "Share context, and share full agent traces, not just individual messages" and "Actions carry implicit decisions, and conflicting decisions carry bad results":

- **Context does not share cleanly.** When work is split across agents, each holds only a slice of the reasoning behind the others' outputs. In the essay's example, a task to build a Flappy Bird clone is split in two: one sub-agent builds a background in the style of a different game, the other a bird that looks and moves nothing like the original, and the agent that combines them inherits both misunderstandings.
- **Parallel actions conflict.** Two sub-agents working at once each make assumptions the other cannot see; when their outputs are merged, the assumptions collide, and the essay concludes that "running multiple agents in collaboration only results in fragile systems."

The essay's recommendation is a single-threaded, linear agent, in which every action sees the full trace of the decisions before it, and, for tasks too long for one window, a model whose job is to compress the history of actions and conversation into its key details. It describes Claude Code's sub-agents, as of June 2025, as a design that respects the principles: the sub-agent is usually given a question to answer rather than code to write, and never works in parallel with the main agent. Anthropic's research post makes the same point from the other side: domains that need all agents to share the same context, or that involve many dependencies between agents, are a poor fit for multi-agent systems today, and most coding tasks offer fewer truly parallel sub-tasks than research does.

The two positions agree more than they conflict. Every failure Cognition describes traces to what the rule of section 3 guards against: a sub-task isolated without a fully specified input and a structured, finite output. The rule is the reconciliation: isolate only where the contract is clean (a document summary, a test run, a scoped search), and keep everything whose value is the shared, evolving reasoning inside one agent. The steelman is a warning against the "team of personalities" of section 10, not against sandboxing a noisy tool or fanning out ten independent file reviews. The default is one agent; a multi-agent design needs a reason, and a clean contract is that reason.

---

## 10. What can go wrong?

- **Splitting for the diagram.** A task is cut into three sub-agents because the architecture drawing looks better. The bill grows with every preamble and merge call, and quality does not move.
- **The team of personalities.** A "critic", a "writer" and a "researcher" with no contracts between them. It demos well and fails on the second real task, the critic and the writer undoing each other's changes.
- **The parent's full window as the sub-agent's input.** The sub-agent receives the whole conversation "to be safe"; its answers are no better than the parent's, and every delegation costs more as the conversation grows.
- **No output schema.** The parent receives free-form prose and parses it with a regular expression. It works until a sub-agent phrases its answer differently, and then the parent acts on a half-parsed result without any error.
- **Unbounded recursion.** A sub-agent calls a sub-sub-agent, which calls another. Each level adds a full loop, and a run that should take minutes runs for an hour; a depth cap and a per-task budget in the orchestrator's code stop it.
- **Sandboxing forgotten on the noisy tools.** `git log`, `npm install`, `pytest -v` and `kubectl logs` are passed to the model whole. The window fills after a few tool calls, and the question and the earlier evidence drift towards the middle of the input.

---

## Common pitfalls

1. **Isolating a task without clean contracts.** It is worse than not isolating: the sub-agent asks for context the parent has to resend.
2. **Skipping the check of the sub-agent's output.** A malformed result propagates quietly; validate it against the schema at the boundary.
3. **A supervisor where a sequential pipeline would do.** It costs more, is harder to test, and adds the model's choices to the list of things that can go wrong.
4. **Re-passing the parent's context.** The cost arithmetic of section 8 stops working, and the sub-agent inherits the parent's clutter.
5. **No depth or budget cap on sub-agent chains.** A delegation loop can burn a day's budget unnoticed; enforce the cap in code, not in a prompt.

---

## Further reading

- Anthropic Engineering, "Building Effective AI Agents" (December 2024): workflows against agents, prompt chaining, parallelisation and orchestrator-workers.
- Anthropic Engineering, "How we built our multi-agent research system" (June 2025): sub-agents in production, the 90.2% result and the token multipliers of section 1, and where multi-agent designs fit poorly.
- Cognition (Walden Yan), "Don't Build Multi-Agents" (June 2025): the counter-argument of section 9.
- Anthropic, "Pricing" (consulted October 2026): the rates of section 8.
- LangChain, LangGraph documentation (2024 to 2025): supervisor and swarm topologies as library patterns.
- Wu, Q. *et al.*, "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation" (2023).
- OpenAI, "Swarm" (GitHub repository, 2024): an experimental, educational library of hand-offs between agents, since replaced by the OpenAI Agents SDK.

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 14 - The system prompt as software](../14-system-prompt-as-software/index.md):** opens Part III with layer 01, where a sub-agent's contract is written.
- **[Post 26 - The modern agentic workflow](../26-modern-agentic-workflow/index.md):** sub-agents and the orchestrator pattern as coding hosts ship them.
