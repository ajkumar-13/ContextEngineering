# 06 - Five context failure modes

> **TL;DR.** When a large language model (LLM) application starts giving bad answers, the cause is often not the model but the context window it was handed. This series names five recurring ways that window fails: distraction, confusion, conflict, lost-in-the-middle and tool-storm. Each has a symptom a user reports, a mechanism that starts in particular layers of the six, a cheap first fix and a last resort. This post catalogues the five and turns them into a checklist that maps a bug report to one or two of them.
>
> **Prerequisites:** [Post 02](../02-six-layers-of-context/index.md).
> **Safe to skip?** Skip it if a bug report can already be mapped to distraction, confusion, conflict, lost-in-the-middle or tool-storm, with the layers it starts in and its first fix.
>
> **After reading, you will be able to:**
>
> - Name the five context failure modes and the symptom each produces.
> - Trace each failure mode to the layers of the context window it starts in, and explain its mechanism.
> - Map a bug report to one or two of the five modes with the diagnostic checklist, or rule all five out.
> - Choose the first fix for each mode, and the last resort behind it, without a model upgrade or a framework switch.

![A grid of the five failure modes against the six layers, with a first-fix column. Distraction starts in 04, also 01 and 05; confusion starts in 01 and 02; conflict has a side in 01, 03, 04 or 05; lost-in-the-middle starts in 04 and 05, also 06; tool-storm starts in 02, also 01.](diagrams/01-failure-modes-grid.svg)

*Each mode starts in a few layers, and each has a cheap first fix. Conflict is the one mode that needs two parts of the window to disagree.*

---

## 1. The question: which part of the context failed?

In the early months of an LLM project every bug feels unique. Users report that "the bot is dumber today", that "the agent keeps repeating itself", or that "it ignored the policy I told it about an hour ago". The usual responses are to tweak the system prompt or move to a stronger model, and the same complaint often comes back weeks later in another form.

A fix does not stick when each report is treated as a story rather than as an instance of a class. [Post 02](../02-six-layers-of-context/index.md) gave the window a structure, six layers with their own jobs and lifetimes; this post gives its failures names, each with a mechanism, a place to look and a first fix. The question is which mechanical failure of the context lies behind a bad answer, and what the cheapest fix for it is.

The names start from Drew Breunig's essay "How Long Contexts Fail" (June 2025), which describes four failures: poisoning, when "a hallucination or other error makes it into the context, where it is repeatedly referenced"; distraction, when a long context makes the model over-focus on it and neglect what it learned in training; confusion, when superfluous content is used to produce a low-quality response; and clash, when new information or tools conflict with what the context already holds. This series adapts the list rather than copying it:

- **Clash becomes conflict**, with the same meaning: two parts of the window disagree.
- **Distraction and confusion keep their names but are redrawn by layer.** Here distraction is irrelevant material pulling the answer off course (closest to Breunig's confusion), and confusion is the right information handled under unclear rules.
- **Two modes are added:** lost-in-the-middle, for content that is in the window but sits where the model uses it poorly, and tool-storm, for runaway tool calls. Breunig's example of a model given too many tools falls under tool-storm here.
- **Poisoning is split:** the accidental form is handled as conflict, and the deliberate form moves to [post 23](../23-security/index.md), for the reasons section 8 gives.

Every entry below has four parts: the **symptom** a user reports, the **mechanism** in terms of the six layers, the **first fix** (the cheapest change that addresses it) and the **last resort** (the structural change when the first fix is not enough). The grid at the top of the post is the catalogue on one page.

---

## 2. Distraction

**Symptom.** The model latches on to a stray phrase or chunk in the context and gives an answer that is fluent, confident and off topic. A user asks about the cancellation policy and the model explains shipping. A coding agent asked to fix a null check rewrites a different function.

**Mechanism.** Distraction starts in layer 04, retrieved chunks, or in layer 01, the system prompt. Either the retrieval pipeline selects chunks that share surface vocabulary with the question but not its intent, or the system prompt is so broad that it gives the model licence to wander. Layer 05, conversation history, can distract too, when older turns rehearsed a different topic at length.

One way to picture the cause is attention spread thin: the more irrelevant material shares the window, the smaller the share left for the part that matters ([post 03](../03-how-llms-read-context/index.md) gives the account of attention). Measurements point the same way. Chroma's "Context Rot" report (Hong, Troynikov and Huber, July 2025), which tested 18 models, found that adding even a single distractor, a passage close to the answer but not the answer, lowered performance against the baseline without one, and that the damage from distractors grew as the input got longer. A longer window does not cure distraction; it makes room for more of it.

**First fix.** Tighten the select step. Lower top-k, the number of chunks packed into the window. Add a reranker, a second-stage model that re-scores the retrieved candidates so the weakest are dropped. Check that the embedding model suits the domain: a code agent searching with an embedding model trained on general prose is a common trap. If the system prompt is broad ("you are a helpful assistant"), narrow it ("you answer only billing questions; decline other topics in one sentence").

**Last resort.** Replace flat retrieval with a router that classifies the question first and selects from an index scoped to that topic, and add a cheap model check ("is this answer on topic?") before the answer is returned.

---

## 3. Confusion

**Symptom.** The right information is demonstrably in the window and the model still makes the wrong choice. A tool is called with the wrong argument, a date is reformatted incorrectly, a policy is summarised correctly and then broken in the next sentence.

**Mechanism.** Confusion is the failure mode of layer 01, the system prompt, and layer 02, tools and MCP descriptions (MCP is the Model Context Protocol, the open protocol through which external tools reach a host application). The information was there; the rules about what to do with it were not clear. Common shapes:

- A tool description says *"call this when the user asks about orders"* without saying *"and never call it for refunds; for refunds use `issue_refund`"*.
- The system prompt states ten rules as prose paragraphs, and the model follows the easiest and drops the rest.
- Two tools with near-identical names and descriptions compete for the same requests.

When a rule is implicit, ambiguous or buried, the model falls back on whatever its training makes most likely for a request of that surface form. Anthropic's engineering post "Effective context engineering for AI agents" (September 2025) puts the tool case plainly: "If a human engineer can't definitively say which tool should be used in a given situation, an AI agent can't be expected to do better."

Confusion differs from what [post 01](../01-why-context-engineering/index.md) calls a prompt problem in where the fix lands: a prompt problem is fixed by rewording the instruction of one call, confusion in the rules of layers 01 and 02, which every call carries.

**First fix.** Make the rules explicit, motivated and exemplified. Replace prose paragraphs with numbered constraints. Add one example of the mistake each rule prevents. If a rule is about a tool, move it into that tool's description. [Post 14](../14-system-prompt-as-software/index.md) gives six rules for writing rules: one concept per rule, motivated by failure rather than speculation, positive over negative, specific over vague, examples over instructions for complex formats, and reviewed like code.

"Motivated by failure" is the rule most easily skipped. *"Be careful with refunds"*, rewritten from the failure that produced it, becomes *"Never issue a refund above 50 dollars without a manager approval token; in March the bot refunded 4,000 dollars unprompted"* (an illustrative incident), which names the concept, the threshold and the reason.

**Last resort.** Move the constraint out of the prompt and into code. A send gate (as in the capstone of [post 30](../30-capstone-email-reply-agent/index.md)) or a validator on the tool side enforces what the model was only asked to respect.

---

## 4. Conflict

**Symptom.** The answer wavers, contradicts itself, or contradicts an earlier turn. The first paragraph says one thing and the second the opposite, or over a long conversation the agent slowly reverses a position it stated firmly.

**Mechanism.** Conflict is the cross-layer failure mode: two parts of the window disagree, and nothing tells the model which one wins. It takes two layers, or two items in one layer, to happen. Typical shapes:

- A semantic memory in layer 03 says the user prefers Python; a chunk retrieved into layer 04 shows the user writing TypeScript last week.
- Layer 01, the system prompt, forbids an action; an episodic memory note in layer 03 says "the user explicitly approved this last month".
- Two chunks in layer 04 come from different versions of the same document, and both say "current as of 2024".

Faced with a disagreement, the model may follow the later version, the more specific one, or the one repeated more often; none of these is a decision anyone made. The model's own earlier turns in layer 05 can be one side of the disagreement. Breunig's essay cites a Microsoft and Salesforce study that "sharded" the information of benchmark prompts across several turns of a conversation: the sharded prompts scored 39% lower on average than the same information given at once, and the study traced the drop to the model relying on its own early, premature answers in the history.

**First fix.** Stamp every memory and every retrieved chunk with its source and date (a provenance and recency stamp). Add an explicit precedence rule to the system prompt ("when sources disagree, the most recent one wins; when the dates tie, the source with higher confidence wins"). Deduplicate the retrieved set so two near-identical chunks do not vote twice.

**Last resort.** Resolve the conflict before the model sees it. A small resolver step, a separate model call or sub-agent, reads the candidate set, picks the winning version with a reason, and only the winner is packed into the main window.

---

## 5. Lost-in-the-middle

**Symptom.** Quality is fine on short inputs, and fine on long inputs where the relevant content sits at the very start or the very end. When the relevant content lands deep in the middle of a long input, the model behaves as if it were not there.

**Mechanism.** Liu et al. ("Lost in the Middle", arXiv 2023, TACL 2024) placed one relevant document among 10, 20 or 30 documents and moved it from first to last. Accuracy was often highest when the relevant document sat at the start or the end of the input and dropped significantly when it sat in the middle. For GPT-3.5-Turbo with 20 or 30 documents, the worst middle position scored below the model's closed-book accuracy of 56.1%, its accuracy with no documents at all. [Post 03](../03-how-llms-read-context/index.md) draws the measured curve and the mechanisms usually offered for it.

Later benchmarks show that length is a problem as well as the middle. RULER (Hsieh et al., NVIDIA, 2024) scores models on 13 tasks at lengths from 4K to 128K tokens and defines a model's effective length as the longest tested length at which its average score stays above 85.6%, the score of Llama 2 7B at 4K. In its main table (Table 3), 16 of the 17 long-context models reach that threshold only at a length shorter than the window they claim; the seventeenth, Gemini 1.5 Pro, stays above it at 128K, the longest length tested. The figure below draws eight of them. Chroma's "Context Rot" report likewise found performance falling as input grew, even on simple tasks.

![A dumbbell chart cited from RULER Table 3: claimed window against effective length on a log axis. GPT-4 128K and 64K, Llama3.1 (70B) 128K and 64K, GLM4 (9B) 1M and 64K, Qwen2 (72B) 128K and 32K, Yi (34B) 200K and 32K, GradientAI/Llama3 (70B) 1M and 16K, Mistral-v0.2 (7B) 32K and 16K, DBRX (132B) 32K and 8K.](diagrams/03-ruler-effective-length.svg)

*Every model drawn holds its accuracy over a shorter span than its advertised window; the gap runs from a factor of two to more than sixty.*

In practice the failure appears when layer 04, retrieved chunks, or layer 05, conversation history, grows long. Layer 06, the user instruction, is involved too: if it is not placed last, the question itself can end up in the middle, the symptom [post 02](../02-six-layers-of-context/index.md)'s table gives for layer 06 ("It answers a different question than I asked."). RULER's table puts the effective length of 11 of its 17 models between 16K and 64K tokens, for models of 2023 and 2024; how long is too long depends on the model and the task, and is measured, not assumed.

**First fix.** Bookend packing. Place the highest-ranked retrieved chunk first and the second-highest last, with the weaker chunks in the middle, and keep the user instruction as the very last thing the model reads, as the figure below lays out. For history, summarise older turns into a short brief near the start of the message list and keep the recent turns verbatim at the end.

![Five ranked chunks followed by the user instruction, packed in score order 1, 2, 3, 4, 5 and in bookend order 1, 3, 4, 5, 2, over a shaded middle of the input; chunk 2, outlined, moves from the middle to the end.](diagrams/04-bookend-packing.svg)

*The same five chunks, packed two ways. Bookend packing moves the second-best chunk out of the middle without dropping anything.*

**Last resort.** When bookending no longer rescues the middle, the structural fixes are a tighter select step, an aggressive compress step ([post 12](../12-compress-strategies/index.md)), or an isolate step that splits the work across sub-agents with shorter windows ([post 13](../13-isolate-strategies/index.md)).

---

## 6. Tool-storm

**Symptom.** An agent calls the same tool again and again with slightly different arguments and never answers, or calls many tools without using their results. Cost and latency spike, and the trace looks like a panicked search.

**Mechanism.** Tool-storm is the failure mode of layer 02, tools and MCP descriptions, with layer 01, the system prompt, sharing the blame when it sets no limit. Three causes are common:

1. **The catalogue is too large.** Presented with many tools, the model cannot reliably tell the right one apart; it tries several, gets ambiguous results, and tries more. Breunig's essay reports a benchmark run in which a quantised Llama 3.1 8B, given a query with all 46 tools of the GeoEngine benchmark, failed although the context was well within its window, and succeeded when given 19 of them.
2. **The descriptions are too vague.** The right tool is in the catalogue, but its description does not say in which situation to call it, so the model picks the closest-sounding name and gets a result of the wrong shape.
3. **There is no stop condition.** Nothing in the system prompt says when to stop calling tools and answer with what the agent has, so a failed call reads as a reason to try again.

A fourth cause hides in the results rather than the catalogue: a tool that returns enormous payloads. Every result is appended to the window, so a few large results crowd out the task, push the question and the earlier evidence towards the middle, and make every later call of the loop more expensive.

**First fix.** Trim the catalogue to the tools this conversation needs, for example by retrieving tool schemas per query with the same machinery that retrieval-augmented generation (RAG) uses for documents ([post 15](../15-tools-and-mcp/index.md)). Rewrite each tool description to say when not to call it. Add a budget rule to the system prompt ("at most three tool calls per turn; after three, answer with what is known"), and cap the size of a tool result in the wrapper code, not in a prompt instruction. Anthropic's engineering post counts "bloated tool sets" among the most common failures it sees.

**Last resort.** Move tool selection out of the model into a deterministic router. The model never sees the full catalogue, only the two or three tools the router chose for the current question.

---

## 7. A diagnostic checklist

When a bug report arrives, first rule out the faults that the logs show directly: a rate-limit error, a response cut off at its token limit, a malformed tool return. These are systems faults, not context faults. Then walk five questions in order, as the figure below draws them.

![Five numbered questions down a spine, each with a yes arrow to the mode it names and the place to look first: distraction, confusion, conflict, lost-in-the-middle, tool-storm. Every question is asked; a report with no yes reaches a dashed box: none of the five, a model problem.](diagrams/02-diagnostic-walk.svg)

*The questions run from what the answer alone shows to what only the trace shows. A report that earns no yes is a model problem.*

1. **Is the answer fluent but off topic?** Distraction. Look at the retrieved set first and the system prompt second.
2. **Does the answer break a rule, or misuse a tool, that the window states clearly?** Confusion. Audit the system prompt and the tool descriptions for ambiguity.
3. **Do two parts of the window disagree, or does the answer contradict itself or an earlier turn?** Conflict. Look in memory and retrieval for two sources that disagree with no precedence rule.
4. **Does quality drop only when the input is long, although the relevant content is in it?** Lost-in-the-middle. Pack with bookends; otherwise compress.
5. **Is the trace full of tool calls that make no progress?** Tool-storm. Trim the catalogue, or cap the loop.

The order follows the evidence each question needs: the first three need the answer, the window and the conversation; the fourth, the same task at two input lengths; the fifth, the trace of tool calls. A report can earn two yeses: a long history that also holds two disagreeing memories is both conflict and lost-in-the-middle, and gets both first fixes. A report that earns none is, by this series' rule, not a context problem but a model problem ([post 01](../01-why-context-engineering/index.md), section 5, draws that line).

**Detection signals.** Three modes leave numbers an application can alert on before users complain; two do not.

| Mode | Signal to watch | How it shows |
|---|---|---|
| Distraction | precision@k of retrieval: the share of the k packed chunks that were relevant | falls |
| Tool-storm | tool calls per turn, and tokens per turn | jump above their usual band |
| Lost-in-the-middle | accuracy against input length | falls as inputs grow |
| Conflict | no clean counter | an LLM judge on sampled transcripts |
| Confusion | no clean counter | an LLM judge on sampled transcripts |

An LLM judge is a second model call that grades a sampled transcript against the rules and sources the window held. Instrumenting these signals is the subject of [post 22](../22-observability/index.md).

**Fixes map to WSCI.** Every first fix and last resort above is an instance of the four operations of [post 07](../07-write-select-compress-isolate/index.md): write, select, compress, isolate (WSCI, this series' abbreviation for the four strategies of Lance Martin's essay "Context Engineering for Agents").

| Failure mode | Main WSCI operations | Fixes in one line |
|---|---|---|
| Distraction | Select | Lower top-k, add a reranker, scope the index. |
| Confusion | Select (of rules) | Explicit, motivated, exemplified rules; push them into code. |
| Conflict | Select, compress | Provenance and recency stamp with a precedence rule; deduplicate the candidates. |
| Lost-in-the-middle | Compress, isolate | Bookend packing; summarise old history; split across sub-agents. |
| Tool-storm | Select, isolate | Trim the catalogue, add a stop budget, cap the result size. |

Bookend packing is itself the packing step of select ([post 09](../09-select-strategies/index.md)), so lost-in-the-middle touches select as well; compress and isolate are what remain when packing no longer rescues the middle.

---

## 8. The one failure mode that is not on this list

**Memory poisoning** is easy to misdiagnose: a memory written in an earlier session misleads the current one. The symptom looks like confusion or conflict, but the cause is upstream: someone wrote into long-term memory something that should never have been there.

Breunig's context poisoning is the accidental case: a hallucination or other error that enters the context and is then referred to again and again. This series adds the deliberate case and splits the two. The accidental form, an error the agent wrote and keeps citing, is handled here as conflict, with conflict's fix: an entry that carries a source and a date can be checked and overruled. The deliberate form, content planted on purpose, including indirect prompt injection through a document the model reads (Greshake et al., 2023), is an attack, and its defences are architectural, not a better precedence rule. It belongs in [post 23](../23-security/index.md), which treats poisoning as a security term.

---

## 9. What can go wrong?

- **A stronger model for a distraction bug.** The retrieved set is full of near-miss chunks and the team moves to a larger model. The answers stay off topic, now more fluent and more expensive.
- **Fixing conflict by deleting one source.** The stale document that disagreed is removed. The answer is right for a while, then the same contradiction returns from a different pair of sources, because nothing stamps or ranks them.
- **Bookending without measuring.** Packing is switched to the bookend layout and shipped on faith. Where position matters little, nothing improves, and nobody can tell, because no evaluation set compared the layouts ([post 20](../20-evaluation/index.md)).
- **A tool budget that lives only in the prompt.** "At most three tool calls" is written into the system prompt and nowhere else. Traces still show long runs of calls on hard queries: an instruction is a request, not a limit, and only the loop code can enforce the cap.
- **Diagnosing from the complaint instead of the window.** "It forgot what I told it" sounds like lost-in-the-middle, so the team bookends the history. The memory was never written in the first place, and the fix lands on the wrong layer.

---

## Common pitfalls

1. **Treating every bug as a prompt bug.** Rewording the system prompt is the second move, not the first; the first is to look at what the window held.
2. **Answering confusion with more rules.** Six clear rules beat thirty fuzzy ones.
3. **Treating tool-storm as "the model going crazy".** It is a catalogue problem, a description problem or a missing stop condition, and all three are under the engineer's control.
4. **Reading Breunig's names as this series' names.** In the essay, confusion means superfluous content; here it means unclear rules over the right content, and superfluous content is distraction.
5. **Filing memory poisoning under conflict and stopping there.** A planted memory is an attack: a precedence rule will not stop the next one, and the defences of [post 23](../23-security/index.md) apply.

---

## Further reading

- Drew Breunig, ["How Long Contexts Fail"](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html) (June 2025): the four failures this taxonomy starts from.
- Liu, N. F. *et al.*, ["Lost in the Middle: How Language Models Use Long Contexts"](https://arxiv.org/abs/2307.03172) (arXiv 2023, TACL 2024): the position result of section 5.
- Hsieh, C.-P. *et al.*, ["RULER: What's the Real Context Size of Your Long-Context Language Models?"](https://arxiv.org/abs/2404.06654) (NVIDIA, 2024): effective context length.
- Hong, K., Troynikov, A. and Huber, J., ["Context Rot: How Increasing Input Tokens Impacts LLM Performance"](https://www.trychroma.com/research/context-rot) (Chroma, July 2025).
- Anthropic Engineering, ["Effective context engineering for AI agents"](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (September 2025).
- Greshake, K. *et al.*, ["Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection"](https://arxiv.org/abs/2302.12173) (2023): the deliberate relative of these modes, in [post 23](../23-security/index.md).

---

## What to read next

- **[Post 07 - Write, select, compress, isolate](../07-write-select-compress-isolate/index.md):** the four operations behind every first fix in this catalogue.
- **[Post 20 - Evaluation](../20-evaluation/index.md):** how to measure a failure mode before and after its fix, so that a change such as bookend packing ships on evidence.
