# 12 - Compress strategies

> **TL;DR.** Compress is the operation that shrinks what is already in the context window. This post covers six techniques (windowing, summarisation, tool-result clearing, priority pruning, semantic chunking and token-level prompt compression), what each removes and what it costs in the facts the next turn needs, measured with the series' information retention ratio. A compression policy pairs the cheap techniques with the lossy ones under two triggers, and a replay set with listed key facts shows whether a change to it lost something.
>
> **Prerequisites:** [Post 07](../07-write-select-compress-isolate/index.md).
> **Safe to skip?** Skip it if a long-running agent's history can already be kept under budget with a stated policy, and the facts that policy drops can be counted on a replay set.
>
> **After reading, you will be able to:**
>
> - Pick the compression technique that fits a given layer and failure mode, from the six this post compares.
> - Set a soft and a hard compaction trigger with the action each one runs, and tell `/compact` apart from `/clear` and from tool-result clearing.
> - Measure a compression policy's information retention ratio and token reduction on a replay set of key facts, and gate a summary change on it.
> - Decide when compression is the wrong answer and a task should be isolated across sub-agents instead.

![Input-budget usage over 110 turns of one simulated session. Without compression it passes the budget at turn 31; summarising alone needs four summaries, at turns 30, 56, 83 and 108; clearing tool results at the 80 percent trigger first postpones the only summary to turn 98.](diagrams/01-usage-and-triggers.svg)

*Clearing the stale tool results at the soft trigger costs no model call and keeps the lossy summary for when nothing cheaper is left.*

---

## 1. The question: what does compression buy, and what does it lose?

Every long-running agent reaches a point where the next call no longer fits the budget. Layer 05, conversation history, is the growing tail of the window (post 02): every turn adds to it, and nothing leaves on its own. There are two kinds of move: drop something, which is cheap and lossy, or replace it with a smaller, denser representation, which costs a model call and loses less. This post asks which technique to use on which content, what each costs in the facts the next turn needs, and when to run it.

Compression is needed before the window is full. Post 04 treats the window as a ceiling rather than a target, and Liu et al. ("Lost in the Middle", arXiv 2023, TACL 2024) found that models used information in the middle of a long input less reliably than at its start or end; a long history can put the turns that matter in that middle.

Compress is one of the four operations of post 07: it moves information out of the window, within one window. Lance Martin's essay "Context Engineering for Agents" (June 2025) names two compress techniques, summarisation and trimming. This post splits them into six, the series' own breakdown: windowing, priority pruning and tool-result clearing are forms of trimming, summarisation and semantic chunking are forms of summarising, and token-level prompt compression works below the level of whole turns.

To compare them, the post uses a teaching construct of its own, the **information retention ratio** (IRR): the fraction of a list of key facts that a later turn could still read after a compression pass. It is not a standard metric; it puts the loss next to the token reduction.

---

## 2. Technique 1: windowing

**Operation.** Drop everything older than the last *N* turns or *M* tokens.

**When it works.** When the task is genuinely local: short tool-use loops, assistants that only need the recent context, latency-sensitive interfaces.

**When it breaks.** Anything with dependencies across turns. The user said "Alice is the project lead" twelve turns ago; a window of eight turns drops it; the agent can no longer say who the lead is, or guesses from the most recent name it saw.

**Token reduction (illustrative).** 50 to 90 percent, depending on the window size. **Retention.** Bimodal: everything inside the window, nothing outside it, which is why pure windowing fails on its own.

**Tuning.** Two refinements lift retention without much extra cost:

- **Pin the first turn.** It often carries the goal, the user's name and the constraints. Layer 01, the system prompt, is never part of the sliding window: it is sent whole on every call.
- **Pin important turns** explicitly: turns the user marked, turns the agent flagged as decisions, turns where a tool wrote to long-term memory.

On the toy replay set of section 10, windowing to the last six entries kept 12 of 22 key facts; pinning the first turn and the decisions kept 20 of 22 for about the same size. Windowing costs no model call, and is rarely the right *only* technique.

---

## 3. Technique 2: summarisation

**Operation.** Replace a span of older context with a summary of that span written by a large language model (LLM).

**When it works.** Long conversations where the gist of the past matters but the exact phrasing does not: project meetings, multi-turn research, customer-support sessions.

**When it breaks.** Anywhere the exact wording matters: code, legal text, tool outputs that will be quoted again. A summary of a stack trace is useless if the agent needed the line numbers.

**Token reduction (illustrative).** 80 to 95 percent. **Retention.** Depends on the summary prompt more than on anything else: a prompt that names what to keep keeps it, and a prompt that says only "summarise" keeps whatever the model finds salient.

**The summarisation prompt matters as much as the model.** A skeleton that names what to keep, in priority order, and bans filler:

```text
Summarise the conversation below for the agent that will continue it.
Preserve, in this order:
1. Decisions made, with the reasoning given.
2. Open questions and unresolved items.
3. User-stated facts and preferences.
4. Tool calls and their key results (only the conclusion, not the verbatim output).
Do NOT include politeness, recap, or filler.
Output as bullet points, <= {target_tokens} tokens.
```

The four categories give the summariser a checklist, and the cap keeps the summary from growing back into the history it replaced. What the summariser fails to file under one of them is lost first: a preference mentioned in passing (section 10 shows one).

**Rolling summarisation** keeps one running summary and folds each new batch of turns into it. **Hierarchical summarisation** summarises turns 1 to 20, then compresses that summary together with turns 21 to 40, and so on; it stays coherent over very long sessions but multiplies the model calls. **Structured summarisation**, one digest per topic, is semantic chunking (section 6).

`snippets/rolling_summary.py` holds the rolling variant's fold step, with the model call passed in as a function, so the step runs offline and any provider can be plugged in:

```python
def fold_prompt(summary: str, new_turns: list[str], target_tokens: int = 300) -> str:
    """The prompt that folds new turns into a running summary, preserving decisions and facts."""
    prior = f"Existing summary:\n{summary}\n\n" if summary else ""
    convo = "\n".join(new_turns)
    return (
        f"{prior}New turns to fold in:\n{convo}\n\n"
        "Rewrite the summary for the agent that will continue this conversation. "
        "Preserve, in order: decisions and their reasoning; open questions; "
        "user-stated facts and preferences; tool conclusions (not verbatim output). "
        f"No politeness or filler. Bullet points, <= {target_tokens} tokens."
    )


def fold(summary, new_turns, complete, target_tokens=300):
    """complete(prompt, max_tokens) -> text is any model call; the summary it returns replaces the old one."""
    return complete(fold_prompt(summary, new_turns, target_tokens), target_tokens + 100)
```

Run as `uv run python posts/12-compress-strategies/snippets/rolling_summary.py` from the series root, it prints the prompt the first fold of a four-turn batch would send and makes no model call. The same file holds `anthropic_complete`, which sends the prompt through the Anthropic Messages API (application programming interface) to Claude Sonnet 4.5, a running model of the series as of early 2026; it needs the Anthropic software development kit (SDK) and an API key.

---

## 4. Technique 3: tool-result clearing

**Operation.** After a tool call, keep the part of the result the agent used and drop the verbatim body.

**When it works.** Whenever a tool result has been read and acted on.

A web-search tool returns, say, 8 KB of result snippets (an illustrative size). The agent reads them, picks two URLs to fetch, and moves on, but the 8 KB stays in layer 05 for the rest of the session, paid for on every later call. Replacing the body with a note such as `[search results: 2 URLs selected, see fetch outputs]` costs the answer nothing, and if the original results are needed again, the call can be repeated.

**Token reduction (illustrative).** 70 to 95 percent of the tool-result tokens, which can be the largest share of a long agent run's history. **Retention.** Close to complete when the note records what the agent took from the result and the call can be repeated.

**The principle.** Deterministic results that are cheap to fetch again are safe to clear. Expensive, non-deterministic or stateful results (a payment, a write, a call billed per request) are summarised instead, so the record of what happened survives.

Claude Code works this way when its window fills: its documentation ("How Claude Code works", consulted 12 October 2026) says that it "clears older tool outputs first, then summarizes the conversation if needed". The simulation of section 9 shows why that order pays.

---

## 5. Technique 4: priority pruning

**Operation.** Give every entry in the window (or every chunk within a layer) a priority class. When over budget, trim from the lowest class first.

**When it works.** Requests whose parts differ clearly in importance: the system prompt matters more than a stale tool result.

**Token reduction (illustrative).** 20 to 60 percent, depending on how far down the classes the trimming goes. **Retention.** Everything in the classes kept, nothing in the classes trimmed.

**A practical four-class scheme**, a starting default rather than a standard:

| Class | Contents | Trim policy |
|---|---|---|
| **P0** | System prompt, identity, hard rules | Never trim |
| **P1** | Last three user turns, the current goal | Never trim until the budget cannot be met otherwise |
| **P2** | Older history; retrieved chunks beyond the top three | Trim first |
| **P3** | Stale tool results, expired memory entries | Trim eagerly; clear by default |

"Top three" means the three highest-scoring chunks in layer 04, retrieved chunks, which retrieval-augmented generation (RAG) fills (posts 09 to 11). Tag every entry with its class as it lands in the budget, sort by class and then by age, and drop from the bottom until the budget fits.

Pruning is blind inside a class. On the toy replay set of section 10, pruning to 15 percent of the original size dropped older P2 messages oldest first, decisions included, and kept 16 of 22 key facts; promoting decisions to P1 keeps them. Pruning composes well with the other techniques, as a default trim mechanism with summarisation kept for when even P2 trimming cannot meet the budget.

---

## 6. Technique 5: semantic chunking

**Operation.** Group the history by topic, summarise each topic on its own, and put the topic summaries in place of the turns.

**When it works.** Sessions that have moved across distinct sub-topics. A coding session that touched authentication, then billing, then an interface bug is better served by three topic summaries than by one chronological one.

**When it breaks.** Sessions whose topics are tightly intertwined, and sessions short enough for simpler techniques.

**Token reduction (illustrative).** 80 to 95 percent. **Retention.** Facts stay next to the other facts about the same subject, which a chronological summary can split.

**Cost.** The highest on this list: a clustering pass, then one summary call per topic. It is reserved for long-lived sessions where the cost is spread over many later turns.

A simple implementation: every *N* turns, embed each turn, cluster the embeddings (HDBSCAN, agglomerative clustering, or k-means with a sensible number of clusters *k*), summarise each cluster with the prompt of section 3, and replace the turns with the summaries. The name is shared with an ingestion technique that splits documents at topic boundaries before indexing (post 10); here it is applied to the history.

---

## 7. Technique 6: token-level prompt compression (LLMLingua, RECOMP)

The five techniques above work on whole turns, tool results or topics. Token-level compression deletes the individual words a downstream model can do without, leaving a prompt that is shorter and still usable by a model, though no longer fluent for a human.

**LLMLingua** (Jiang et al., EMNLP 2023) uses a small language model to score tokens by perplexity, roughly how surprising each one is, and drops the predictable ones. Its abstract reports "up to 20x compression with little performance loss" on the authors' benchmarks. **LLMLingua-2** (Pan et al., Findings of ACL 2024) recasts the task as token classification, keep or drop, with a small encoder trained on data distilled from a larger LLM; the authors report it runs 3 to 6 times faster than earlier prompt compressors and cuts end-to-end latency by 1.6 to 2.9 times at compression ratios of 2 to 5 times.

**RECOMP** (Xu, Shi and Choi, arXiv 2023) is the retrieval-specific relative: an *extractive* compressor selects the most useful sentences of the retrieved documents and an *abstractive* one writes a short synthesis of them, before the answering model sees them. The authors report compression to as little as 6 percent of the original length with minimal loss on their tasks. Its aim is that of tool-result clearing, applied to layer 04: fewer tokens for the same evidence.

**When it works.** Fixed, verbose context sent many times: long retrieved contexts, blocks of few-shot examples, long static instructions.

**When it breaks.** Anything a human reads or quotes verbatim, and short prompts where the compressor's own call costs more than it saves. It also interacts badly with prompt caching: a prefix rewritten on every call never matches the cached one and loses the cache-read discount (post 05, section 4), so the stable part is compressed once, reviewed, and then cached as it is.

**Token reduction.** The figures above are the papers' own, on their benchmarks; other traffic is measured before the technique is trusted, with the compressor's latency and cost added to the budget.

---

## 8. Two Claude Code commands: `/compact` and `/clear`

Claude Code, Anthropic's coding agent, exposes two of these techniques as slash commands, described in its "Commands" reference and "How Claude Code works" page (both consulted 12 October 2026).

- **`/compact [instructions]`** is summarisation (section 3) of the conversation so far: the reference describes it as freeing context "by summarizing the conversation so far", with optional focus instructions (`/compact focus on the API changes` is the documentation's example). Claude Code also compacts automatically as the window approaches its limit, clearing older tool outputs before it summarises, and a "Compact Instructions" section in the project's `CLAUDE.md` steers what the summary keeps. The documentation gives the automatic trigger as a window size in tokens, adjustable with `/autocompact`, and states no default percentage, so the thresholds of section 9 are this series' policy values, not Claude Code's.
- **`/clear`** starts "a new conversation with empty context" (aliases `/reset` and `/new`); the commands page notes that it keeps project memory. It is windowing (section 2) with a window of zero, for a genuine task boundary.

Neither is this post's tool-result clearing (section 4), which drops one verbose tool body and leaves the rest of the conversation in place. The rule of thumb: `/compact` to keep the thread but shrink it, `/clear` when the thread is done, tool-result clearing continuously.

---

## 9. The two triggers: 80 and 95 percent

A compression policy is two thresholds and an action at each, measured against the input budget: the context window minus the output reserve that `max_tokens` holds back (post 04). The two numbers are illustrative defaults, a starting point and not a measured law.

- **At 80 percent of the budget, the soft trigger.** Run the cheap operations, tool-result clearing and P3 pruning, oldest first, until the input is under 60 percent. No model is called.
- **At 95 percent, the hard trigger.** Summarise, or semantically chunk, the older part of the conversation, keeping the most recent turns verbatim. The agent tells the user it is compressing earlier conversation, and the original turns go to a separate log for debugging.

Both move down when token usage varies a lot from turn to turn (long tool outputs, deep retrieval) and up when it varies little.

`snippets/compaction_policy.py` replays one illustrative session against this policy. The window is Claude Sonnet 4.5's 200,000 tokens (Anthropic, "Context windows", consulted October 2026, as post 04 cites it), less post 04's illustrative output reserve of 20,000, an input budget of 180,000 tokens. Layers 01 to 04 take 8,300 tokens on every call (post 04's support agent), and every turn appends 1,400 tokens of messages and one tool result of 800 to 9,000 tokens to layer 05, all illustrative sizes. It prints:

```text
window 200000, output reserve 20000, input budget 180000
triggers: soft 80%, hard 95%, soft target 60%; 110 turns

none            first over budget:  31   soft passes:  0   summaries: 0 at turns []
summarise-only  first over budget:   -   soft passes:  0   summaries: 4 at turns [30, 56, 83, 108]
two-trigger     first over budget:   -   soft passes: 26   summaries: 1 at turns [98]

two-trigger policy, usage of the input budget before -> after
  soft passes that reached 60%: turns [25, 32, 38, 46, 53, 61]
  first soft pass that did not: turn 68 (82.5% -> 68.8%)
  summary: turn 98 (95.1% -> 17.8%)
```

The hero figure draws the three runs. Without compression the input passes the budget at turn 31. Summarising alone holds it, at the price of four lossy summaries in 110 turns. With the soft trigger in front, the first six clearing passes each bring the input back under 60 percent; from turn 68 the clearable tool results run out, the passes stop reaching the target, and the one summary comes at turn 98. A soft pass that misses its target is the signal that the hard trigger is near. The figure below shows what each pass removes.

![Four stacked bars of the input, split into layers 01 and 02, layers 03 and 04, the messages, notes and summary of layer 05, and its verbatim tool results. At turn 25 the soft pass cuts the input from 81.8 to 59.1 percent. At turn 98 the summary cuts it from 95.1 to 17.8 percent.](diagrams/02-what-each-pass-removes.svg)

*The soft pass removes tool bodies and nothing else; the summary is the only pass that rewrites what was said.*

**Anti-pattern: summarising on every turn.** Each summary is a model call that reads the whole span it replaces, and each rewrites the history, so a prompt cache over the earlier conversation stops matching. Compress on triggers, not on a schedule.

---

## 10. Measuring information retention

A summary that drops the fact the next turn needed is a regression. The way to catch it before it ships:

- **A small replay set.** Real conversations, each with the key facts a later turn needs listed beside it, or with the next turn's correct answer recorded.
- **The metric.** Run each conversation through the policy, then check which key facts the compressed history still holds, or ask the next turn's question and score the answer. The IRR is the fraction that survive, reported beside the token reduction.
- **The gate.** A new summary prompt or policy whose IRR falls by more than the run-to-run noise of the measurement blocks the merge.

`snippets/retention.py` runs the first two steps on a toy replay set of three conversations with 22 key facts, counting tokens with tiktoken's `o200k_base` encoding. A fact survives when every word of it is still in the compressed history. The summariser is a rule-based stand-in for a model: it keeps what the section 3 prompt asks for (decisions, open questions, stated facts, tool conclusions), so its row measures the prompt's checklist, not a model. It prints:

```text
replay set: 3 conversations, 22 key facts, encoding o200k_base
technique               tokens  after reduction facts kept   IRR
windowing                19931   8650     56.6%    12 of 22   55%
windowing, pinned        19931   8768     56.0%    20 of 22   91%
tool-result clearing     19931   2598     87.0%    22 of 22  100%
priority pruning         19931   2248     88.7%    16 of 22   73%
summarisation            19931   2449     87.7%    21 of 22   95%

windowing              lost: Alice Moreno, Postgres 16, disk quota, acme-exports, 48213, damaged, 3,000, Lisbon, 12 people, Casa Azul
windowing, pinned      lost: disk quota, damaged
tool-result clearing   lost: nothing
priority pruning       lost: disk quota, acme-exports, 90 days, damaged, 3,000, WhatsApp
summarisation          lost: WhatsApp
```

Two lessons hold beyond the toy. The token reduction says nothing about the loss: windowing and pinned windowing remove about the same 56 percent and keep 12 and 20 of the 22 facts. And the losses are specific: the summary lost a customer's preference for WhatsApp, mentioned "by the way" and never picked out as a stated preference; the fix is a line in the prompt, and the replay set is what shows it is needed. The figure below lines up the six techniques by what each removes, with these numbers beside the five the snippet runs.

![Eight strips of the same ten-entry history, oldest left: the original, then what windowing, pinned windowing, tool-result clearing, priority pruning, summarisation, semantic chunking and token-level compression keep, removed parts dashed in red. Beside the first five, reduction and IRR: 56.6 and 55, 56.0 and 91, 87.0 and 100, 88.7 and 73, 87.7 and 95 percent.](diagrams/03-six-techniques.svg)

*Each technique removes a different part of the history. The reduction column cannot rank them; the IRR column can.*

For a public check, long-context benchmarks such as LongBench (Bai et al., arXiv 2023, ACL 2024), with question answering, summarisation and code tasks in English and Chinese, are where prompt compressors such as LLMLingua-2 report results. This is the same kind of gate as the evaluation of a retrieval pipeline ([post 11](../11-rag-in-depth/index.md)) and of a whole system ([post 20](../20-evaluation/index.md)).

---

## 11. Picking among the six

- **Default: priority pruning and tool-result clearing.** Cheap, predictable and composable; both can be on from the first release.
- **Add summarisation** when the length of the conversation is the bottleneck and the gist is enough.
- **Add semantic chunking** when several long-running threads would lose their structure in one chronological summary.
- **Add token-level compression** only for large, fixed context sent many times, and only where it can coexist with caching.
- **Use windowing alone** only when the task is genuinely local; otherwise with pinned turns.

The order matters: clearing and pruning give the headroom that lets the expensive techniques run rarely, as section 9 shows. The technique also follows from the layer that is over budget and the failure mode it feeds, in post 06's names:

| What is too large | Layer | Failure mode it feeds | Technique to try first |
|---|---|---|---|
| Tool results already read | 05 Conversation history | tool-storm (oversized results) | tool-result clearing |
| A long history, key turns in the middle | 05 Conversation history | lost-in-the-middle | summarise older turns into a brief near the start |
| Old turns on a topic the session has left | 05 Conversation history | distraction | semantic chunking, or windowing with pins |
| Two versions of one fact | 05, or 03 Memory and state | conflict | a summary that keeps only the latest decision |
| A long retrieved payload on every turn | 04 Retrieved chunks | lost-in-the-middle | RECOMP-style extraction, or pruning past the top three |
| Few-shot examples, static instructions | 01 System prompt | none; a cost problem | token-level compression, once, then cached |

Layer 06, the user instruction, is never compressed: it is the trigger of the call, small and last. Post 06's first fix for distraction remains a tighter select step; compression is the fix only when the distracting material is the session's own history.

---

## 12. When compression is the wrong answer

Compression is lossy by construction, so sometimes the right move is to keep the material out of the window in the first place. That is the isolate operation ([post 13](../13-isolate-strategies/index.md)), the better answer whenever compression would throw away something the task cannot lose.

Isolate rather than compress when:

- **The material is exact and irreplaceable.** Code, legal text, financial figures, tool outputs that will be quoted verbatim. Any lossy pass corrupts them; a sub-agent whose own window holds the full text does the work and returns only the conclusion.
- **The context is really several unrelated jobs.** Compressing the combined history of three loosely related threads treats the distraction each causes the others (post 06) without curing it; separate windows remove those tokens from each other's context entirely.
- **Auditability is required.** A summariser that drops a fact leaves no trace; a sub-agent boundary makes the hand-off explicit and inspectable.

The two are complementary: compress within a window, isolate across windows. A policy that keeps losing facts on the replay set however its prompt is tuned is the signal to isolate rather than compress harder.

---

## 13. What can go wrong?

- **The summary drops the one fact the next turn needs.** A preference stated in passing slips past the summary prompt's checklist, and three turns later the agent contradicts it. The trace shows a summary event just before the regression; a replay set listing that preference fails the change before it ships.
- **A summariser rewrites the rules.** The compaction span includes the system prompt or the first turn, and "refunds above 3,000 rupees need approval" becomes "large refunds are reviewed". The rule is broken only after the first compaction.
- **A non-repeatable tool result is cleared.** A payment confirmation is cleared like a search result; later the agent cannot tell whether the payment went through, and calls the tool again.
- **The soft pass stops reaching its target unnoticed.** Usage then creeps towards the hard trigger, as in section 9 from turn 68 to turn 98, and every call pays for a fuller window. Logging whether each soft pass reached its target turns this into an alert.
- **Token-level compression on a cached prefix.** A compressor rewrites the system prompt on every call; the cache-read tokens in the usage block fall to zero, and the input bill rises although the prompt got shorter.

---

## Common pitfalls

1. **Skipping tool-result clearing.** Tool results can be the largest share of a long run's history, and clearing them costs no model call.
2. **Summarising what could be cleared.** A deterministic result that can be fetched again is cleared, not summarised.
3. **No replay set.** Without one, the next "improvement" to the summary prompt regresses silently.
4. **Compressing on every turn.** Every summary is a second model bill and a broken cache; compression runs on triggers.
5. **Treating windowing as a complete strategy.** It loses everything outside the window, however important; pins are the minimum.
6. **Letting a summariser see P0.** The system prompt and the pinned turns stay out of every compaction span.

---

## Further reading

- Anthropic, "How Claude Code works" and "Commands" (Claude Code documentation, consulted 12 October 2026): automatic compaction, `/compact` and `/clear`.
- Martin, L., "Context Engineering for Agents" (June 2025): summarisation and trimming, the compress techniques this post splits into six.
- Jiang, H. *et al.*, "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models" (EMNLP 2023).
- Pan, Z. *et al.*, "LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression" (Findings of ACL 2024).
- Xu, F., Shi, W. and Choi, E., "RECOMP: Improving Retrieval-Augmented LMs with Compression and Selective Augmentation" (arXiv 2023).
- Bai, Y. *et al.*, "LongBench: A Bilingual, Multitask Benchmark for Long Context Understanding" (arXiv 2023, ACL 2024).
- Liu, N. F. *et al.*, "Lost in the Middle: How Language Models Use Long Contexts" (arXiv 2023, TACL 2024).

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 13 - Isolate strategies](../13-isolate-strategies/index.md):** the operation to reach for when compression would lose what the task needs.
- **[Post 30 - Capstone: email reply agent](../30-capstone-email-reply-agent/index.md):** the two-trigger policy and the structured summary prompt applied to long email threads.
