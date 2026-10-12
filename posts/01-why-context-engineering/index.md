# 01 - Why context engineering, and why now

> **TL;DR.** "Prompt engineering" described the work well when an engineer's job was to shape the one message a user sent to a large language model (LLM). Tools, retrieval and memory changed that: most of what a model now reads on a call is not the user's sentence but a window of six layers that an engineer assembled. **Context engineering** is the discipline of assembling that window well, so that the model has the right information, in the right place, at the right cost. This post explains why the name changed in 2025, what is new, and how to tell a context problem from a prompt or model problem.
>
> **Prerequisites:** none. This is the first post of the series.
> **Safe to skip?** Skip it if the reader can already say in one sentence how context engineering differs from prompt engineering, name the five jobs of the work, and sort a failing LLM feature into a prompt, context or model problem.
>
> **After reading, you will be able to:**
>
> - State in one sentence what separates context engineering from prompt engineering.
> - Recognise the five recurring jobs of a context engineer in a description of an LLM feature.
> - Decide whether a given problem is a prompt problem, a context problem, or a model problem.
> - Price one uncached call from its input tokens and a per-million-token input rate.

![Two panels of equal height. Left, 2022: one tall purple box, 06 user instruction, is the whole surface of the work. Right, 2025: six bands from 01 system prompt to 06 user instruction, bracketed as stable prefix, per-turn injection, growing tail and trigger, with 02, 03 and 04 labelled as added by tools, memory and retrieval.](diagrams/01-from-message-to-window.svg)

*The user's sentence is still there, as layer 06; it is now one part of six, and the other five are assembled by an engineer.*

---

## 1. The question: why did "prompt engineering" stop describing the work?

In December 2022, "prompt engineering" was an accurate description of the work. A user typed one message into a chat box, and the model read it and answered. If the answer was bad, the user reworded the message. The whole surface of the practice fitted in one text box.

Three changes between then and 2025 broke the name, and each added material to every call that the user never typed.

**First, models gained tools.** OpenAI added function calling to its application programming interface (API) in June 2023 ("Function calling and other API updates"), and within a year the other major providers offered their own tool-use interfaces. The Model Context Protocol (MCP), which Anthropic introduced in November 2024 as an open standard for exposing tools and data to models (post 15 covers it), made those tool definitions portable across applications. On every call the model now reads the JSON (JavaScript Object Notation) schema of every tool it might use, and a large catalogue can run to thousands of tokens (an illustrative size) before the user's message.

**Second, models gained access to outside data.** Retrieval-augmented generation (RAG), named by Lewis et al. in 2020, became a common pattern in production systems. The user asks a one-line question; the system retrieves a handful of relevant chunks from a document index and places them in the request, so the model reads pages of evidence before it reads the user's words.

**Third, models gained memory.** The conversation buffer is the obvious form, but persistent memory (episodic records of past sessions, semantic facts kept in a project memory file, procedural skills stored as reusable instructions) is now common in agent systems. None of it is the user's prompt, and all of it shapes the answer.

Add the system prompt and the conversation history that already existed, and the six layers of a modern call come into view: layer 01, the system prompt; layer 02, tools and MCP descriptions; layer 03, memory and state; layer 04, retrieved chunks; layer 05, conversation history; and layer 06, the user instruction. The figure above draws the change: the user's sentence is one layer of six. A modern call is not a prompt being engineered; it is a **window** being assembled.

---

## 2. Who said what, and when

The work changed before the name did: function calling shipped two years before "context engineering" became the common term. Several writers pushed the term into wide use within a few months of each other in 2025, and the timeline below places them against the changes of section 1.

![A timeline from 2020 to 2026. Below the axis: the RAG paper in 2020, OpenAI function calling in June 2023 and the Model Context Protocol in November 2024. Above it: Martin's essay and Karpathy's post in June 2025 and Anthropic Engineering's article in September 2025.](diagrams/02-timeline.svg)

*The changes to the work sit below the axis and the naming above it; every date is one this section cites.*

**Andrej Karpathy** popularised the term in a post on X on 25 June 2025, responding to Shopify's chief executive Tobi Lütke, and gave the short definition most often quoted:

> *"+1 for 'context engineering' over 'prompt engineering'. People associate prompts with short task descriptions you'd give an LLM in your day-to-day use. When in every industrial-strength LLM app, context engineering is the delicate art and science of filling the context window with just the right information for the next step."*

**Lance Martin** published "Context Engineering for Agents" on his own blog in June 2025, and the LangChain blog ran a version in July 2025. It groups the strategies into four buckets that this series uses throughout: **write, select, compress, isolate** (WSCI, in that order).

**Anthropic Engineering** published "Effective context engineering for AI agents" in September 2025. It calls context engineering "the natural progression of prompt engineering" and treats context as "a finite resource with diminishing marginal returns", to be filled with "the smallest possible set of high-signal tokens" that does the job.

**IBM Think** published the explainer "What is context engineering?" in 2025, defining it as "the practice of deliberately designing, structuring and optimizing the context provided to a large language model (LLM) to produce more accurate, relevant and reliable outputs".

**Dex Horthy's** "12-Factor Agents" (2025) argued, from conversations with founders building agents, that most products sold as AI agents are mostly deterministic code with model calls placed at chosen points, and made "own your context window" one of its twelve factors.

The phrasing varies; the substance does not. Each of them points at the same shift: the work is no longer about the one sentence a user sends to the model.

---

## 3. What is genuinely new, and what is not

Is the rename hype? Most of the techniques are old: few-shot examples, system prompts, retrieval and summarisation were all in use before 2025. Two things changed, and both are large.

**The interface is no longer a single string.** A modern API call is a structured object with a system prompt, a list of tool definitions and a list of messages, often carrying retrieved documents and cache markers. The unit of work is a layered data structure, not a phrase.

**The window is finite, and the cost is real.** A window of a million tokens (an illustrative size; window sizes differ by model and change often) sounds endless until tools, retrieved documents and history start to fill it. Anthropic's "Pricing" page listed Claude Sonnet 4.5 input at 3 US dollars per million tokens as of early 2026. One uncached call with 100,000 input tokens therefore costs 100,000 times 3 dollars divided by 1,000,000, which is 0.30 dollars, roughly thirty cents, before any output tokens. Ten thousand such calls a day (an illustrative workload) cost 3,000 dollars a day in input alone. What to include, compress or write out now shows up directly in latency and money. Post 04 sizes a call on an envelope, and post 05 prices it in full, caching included.

In short, prompt engineering was a craft. Context engineering is the same craft, applied to a larger surface, under hard budgets.

---

## 4. The five jobs of a context engineer

Whatever the application (a coding agent, a support bot, a research assistant), the work decomposes into the same five jobs, and the figure below places each where it acts on the window.

![The six layers sent as one stack into a model box and on to an answer, with the five jobs placed where they act: tool schemas, memories and documents enter layers 02 to 04; an unused tool and a stale chunk stay out in a red dashed box; the order of the stack is labelled; layer 05 is marked for refresh; the answer is marked for measurement.](diagrams/03-five-jobs.svg)

*Every job acts on the same window: two choose its contents, one orders them, one keeps the growing tail in check, and one checks the result.*

**1. Decide what goes in.** Which layers are populated, which tools are exposed, which memories are replayed, which documents are retrieved. It is the most visible decision and often where teams start.

**2. Decide what stays out.** The harder and more important sibling of the first job. Every token that does not need to be in the window competes with the tokens that do. Pruning is not optimisation; it is correctness work, and post 06 shows the failures that follow when it is skipped.

**3. Decide where each piece sits.** Position matters. Liu et al. ("Lost in the Middle", 2023) measured multi-document question answering and found that models used a relevant passage more reliably when it sat at the start or the end of a long input than when it sat in the middle; post 03 explains the mechanism. Provider prompt caches match on a prefix of the request, so the layers meant to be cached go first (post 05). This series places the user instruction last, on purpose (post 02).

**4. Decide when to refresh, compress, or write out.** A long-running session accumulates context, and left alone it degrades as stale and redundant tokens pile up. Engineers schedule compaction, summarisation and the writing of state out of the window to files or memory stores (posts 08, 12 and 16).

**5. Decide how to measure whether it worked.** Without traces, evaluations and cost dashboards, every change is a guess: the same change that improves answers on one slice of traffic can quietly degrade another (posts 20 and 22).

Anyone doing one of these five jobs is doing context engineering, whatever the job title says.

---

## 5. When is a problem not a context problem?

Not every LLM bug is a context bug. Before reaching for a retrieval pipeline or a memory system, it is worth ruling out two simpler possibilities, and the order of the two questions matters, as the chart below shows.

![A decision chart. Question 1 asks whether the right information is in the window, in a sensible place and amount; no leads to a context problem. Yes leads to question 2, whether rewording the instruction fixes the answer; yes leads to a prompt problem and no to a model problem.](diagrams/04-which-problem.svg)

*A context problem is the large middle between the other two, and the subject of this series.*

**It might be a prompt problem.** If the information the model needs is all in the window and rewording the instruction fixes the answer, the problem was the wording. Prompt problems still exist; they just cover less ground than they used to.

**It might be a model problem.** If the right information is demonstrably in the window, in a sensible position and in a sensible amount, and the model still fails however the instruction is worded (for example, on a task that needs deeper reasoning than the model can do), the problem is the model. The fix is a stronger model, not more context.

What is left is the large middle: cases where the model is capable in principle but is being given the wrong information, in the wrong place, or in the wrong amount. Those are context problems, and they are the subject of this series. The first question can only be answered by looking at the request the application actually sent, which is why post 02 prints one and labels every part of it.

---

## 6. What this series will and will not cover

This series is **framework-agnostic** by design. The examples use plain Python, the providers' official software development kits (SDKs) for Anthropic, OpenAI and Google, and the MCP reference SDK. Frameworks (LangChain, LlamaIndex, LangGraph and others) are named where a pattern originates and are never the protagonist: the series teaches the underlying shapes first, so that a reader can choose tools later with open eyes.

The series goes deep on:

- The **six layers** of a context window and how they interact, with their costs and failure modes (Part I).
- The **four operations**, write, select, compress, isolate, that organise every context decision (Part II).
- **RAG** done properly: ingestion, chunking, hybrid search, reranking, and where plain RAG breaks (Parts II and III).
- **Memory systems**, with the episodic, semantic and procedural kinds (post 16), and **tools and MCP** (post 15).
- **Production practice**: evaluation, structured output, observability, security, privacy, and long context against RAG (Part IV).
- Three **builds from scratch**: a RAG chatbot (post 28), an MCP server (post 29) and an email-reply agent (post 30).

It is not a survey of every framework, vector database or paper; it is a tutorial.

---

## 7. The plan from here

The next post, [post 02](../02-six-layers-of-context/index.md), finds each of the six layers in a real API request, so that the rest of the series has a concrete spine. Post 03 explains how the model reads what it is sent: tokens, attention, positions and the cache of past computation. Post 04 introduces the token budget and how to size a call on an envelope. Post 05 prices calls, shows what prompt caching saves, and budgets latency. Post 06 names the five failure modes (distraction, confusion, conflict, lost-in-the-middle, tool-storm) that a badly assembled window produces.

By the end of Part I a reader can name the six layers in a raw API request, estimate the tokens, latency and dollars of a prompt without running it, lay out a prefix so that it caches, and map a production bug report to one of the five failure modes. Everything in Parts II to V is a deeper look at one piece of that picture.

---

## 8. What can go wrong?

These are the mistakes that applying this post's ideas actually produces.

- **A stronger model for a context problem.** The needed fact never reached the window, so the team upgrades the model. The symptom is the same wrong answer from the new model, at a higher price per call.
- **Rewording for a context problem.** A stale chunk in layer 04 carries an old fact, and the team rewrites the instruction. The answer changes its wording and keeps the old fact.
- **Diagnosing from the symptom, not the request.** The team guesses what the window held instead of logging the assembled request. Fixes land on the wrong layer, and the bug comes back on the next release.
- **Pricing only the user's message.** A cost estimate counts the user's sentence and forgets the tool schemas, retrieved chunks and history sent with it. The bill comes in many times the estimate.
- **Quoting a price without its date.** A per-million-token rate copied from an old note is used as if it were current. Providers change prices and models, and the estimate is wrong without anyone noticing.

---

## Common pitfalls

1. **Treating "context engineering" as a synonym for "RAG".** RAG fills one of the six layers, layer 04, the retrieved chunks; it is not the whole job.
2. **Confusing the context window with the context.** The window is a hard limit set by the model; the context is what the engineer chooses to put in it. The window is the budget and the context is the spending plan.
3. **Adding context to fix a bad answer when the right move was to remove some.** More tokens are not more signal, and several of the failure modes in post 06 come from too much.
4. **Optimising one layer in isolation.** The layers share one window and one budget, so a longer system prompt or a larger tool catalogue leaves less room, and less money, for everything else.
5. **Skipping evaluation because the answers look better.** They look better on the handful of examples tried by hand; an evaluation set decides whether a change ships (post 20).

---

## Further reading

- Andrej Karpathy, post on X endorsing "context engineering" over "prompt engineering" (25 June 2025). The definition quoted in section 2.
- Lance Martin, "Context Engineering for Agents" (June 2025; LangChain blog version, July 2025). The source of the write, select, compress, isolate vocabulary.
- Anthropic Engineering, "Effective context engineering for AI agents" (September 2025). Context as a finite resource; quoted in section 2.
- IBM Think, "What is context engineering?" (2025). The definition quoted in section 2.
- Dex Horthy, "12-Factor Agents" (2025). Practitioner patterns, including "own your context window".
- OpenAI, "Function calling and other API updates" (June 2023), and Anthropic, "Introducing the Model Context Protocol" (November 2024). The tool changes of section 1.
- Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (2020). The paper that named RAG.
- Liu et al., "Lost in the Middle: How Language Models Use Long Contexts" (2023). The position finding of section 4.
- Anthropic, "Pricing" (per-million-token rates, as of early 2026). The source of the cost figure in section 3.

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 02 - The six layers of context](../02-six-layers-of-context/index.md):** the structural view, with every layer found in a real API request.
- **[Post 07 - Write, select, compress, isolate](../07-write-select-compress-isolate/index.md):** the four operations that act on the layers, for a reader who prefers to start with the verbs instead of the nouns.
