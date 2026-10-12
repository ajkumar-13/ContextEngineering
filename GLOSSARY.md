# Glossary

Every term the series uses, one entry each, in alphabetical order. A post that introduces a term in depth names it; this page gives the one-paragraph definition. The fixed vocabulary of the series (the six layers, the four operations, the five failure modes, the retrieval numbers) is defined once in the [notation guide](notation_guide.md), and the entries below agree with it.

---

**Active learning.** In the capstone (post 30), treating every human edit, approval, or rejection of an agent's draft as a training signal, so that the pairs of draft and edited draft can later tune a small model or a routing decision.

**Adaptive thinking.** A reasoning-model mode in which the model decides per request how much internal reasoning to spend, steered by an effort setting rather than a fixed token budget (post 18).

**Agent.** An LLM-driven program that takes several steps, calls tools, and chooses its own next action. Contrast a workflow, whose steps are fixed in code (post 13).

**AGENTS.md.** A repository-level instruction file read by coding agents (Codex, Cursor, and others), written in the five-block form of a system prompt. `CLAUDE.md` is Claude Code's equivalent.

**Approval rate.** The fraction of agent-produced artefacts (drafts, diffs, plans) that a human accepts without editing. A lightweight production signal of quality (posts 20 and 30).

**Attention sink.** A position in the context window, typically the first few tokens, that the model attends to heavily regardless of content (Xiao et al., 2023; post 03).

**Audit log.** An append-only record of every consequential action an agent took, with timestamp, arguments, result, and session id.

**Auto-compaction.** A host policy that summarises older parts of a long conversation when the prompt approaches a token threshold (post 12).

**BABILong.** A long-context benchmark that hides reasoning tasks built from bAbI facts inside long distractor text (Kuratov et al., 2024; post 25).

**BM25.** A lexical ranking function based on term frequency, inverse document frequency, and document length. Combined with dense retrieval in hybrid search.

**Bookend packing.** Placing the highest-ranked retrieved chunk first and the second-highest last, with weaker chunks in the middle, so the strongest evidence avoids the lost-in-the-middle dip (posts 06 and 09).

**Byte-pair encoding (BPE).** A tokeniser built by repeatedly merging the most frequent adjacent pair of symbols, so common words become single tokens and rare strings split into fragments (Sennrich et al., 2016; post 03).

**Cache breakpoint.** A marker in a request that tells the provider where a cacheable prefix ends, so the computed state up to that point is stored and reused by later calls (post 05).

**Cache hit, cache miss.** Whether a request's prefix matches a stored prompt-cache entry. A hit is billed at a fraction of the base input price; a miss bills the prefix at the full price plus, where the prefix is written to the cache, a write premium (post 05).

**Candidate generation.** The second stage of the select pipeline: dense, sparse, or hybrid retrieval that produces a high-recall set of top-N candidates (for example top-50) for the reranker to refine (post 09).

**Causal mask.** The rule in decoder-only models that a token may attend only to itself and the tokens before it; the reason a cached prefix stays valid when later tokens change (post 03).

**Chain of thought (CoT).** A prompting pattern in which the model writes out intermediate reasoning before its answer (Wei et al., 2022).

**Chunking.** Splitting a document into retrieval-sized pieces. The series' default for prose is 400 to 600 tokens with sentence-aware boundaries and 10 to 20 percent overlap (posts 09 and 11).

**Citation accuracy.** The fraction of citations in a generated answer that point to a chunk which supports the cited claim.

**CLAUDE.md.** Claude Code's repository-level instruction file; the equivalent of `AGENTS.md`.

**ColBERT.** A late-interaction retrieval model that keeps one embedding per token and scores a query against a document with MaxSim, trading a larger index for higher accuracy (Khattab and Zaharia, 2020; post 17).

**ColPali.** A late-interaction retrieval model that embeds images of document pages directly, so a page-image corpus can be searched without a separate OCR step (Faysse et al., 2024; post 19).

**Compaction.** Replacing a long conversation history with a shorter summary that keeps the state the task needs. A compress technique (post 12).

**Compress.** The third of the four operations (WSCI): shrinking what is already in the window, by windowing, summarisation, tool-result clearing, priority pruning, semantic chunking, or token-level compression (post 12).

**Confusion.** The failure mode in which the right information is present but the model applies the wrong rule or makes the wrong choice, because the rules about it are implicit, ambiguous or buried. The first fix is explicit, motivated, exemplified rules (post 06).

**Conflict.** The failure mode in which the window holds contradictory information (an old memory and a new document, two retrieved chunks) and the model picks the wrong one. The first fix is a provenance and recency stamp with an explicit precedence rule (post 06).

**Constrained decoding.** Restricting the model's token sampling at generation time to the tokens a grammar or schema allows, so the output is syntactically valid by construction (post 21).

**Context engineering.** The discipline of deciding what enters an LLM's context window on every call, across all six layers, so that the model has the right information, in the right place, at the right cost (post 01).

**Context precision.** A Ragas metric: how much of the retrieved context is relevant to the question, with relevant chunks ranked high.

**Context recall.** A Ragas metric: how much of the information the reference answer needs is present in the retrieved context.

**Context rot.** The degradation of model performance as input length grows, even on simple tasks and well inside the stated window (Hong, Troynikov and Huber, Chroma, 2025; post 06).

**Context window.** The maximum number of tokens a model can take in one call, prompt and output together. A hard ceiling set by the model (post 04).

**Contextual retrieval.** Anthropic's technique of prepending to each chunk a short, model-written context that situates it within its document, before the chunk is embedded and indexed with BM25 (Anthropic, 2024; post 11).

**Conversation buffer.** The recent user and assistant turns held in the prompt for the current session; the near end of layer 05, conversation history.

**Cross-encoder.** A model that reads a query and a document together and outputs one relevance score. Used as the reranker after candidate generation.

**Data residency.** A requirement that data be stored and processed only within a given geographic or legal jurisdiction (post 24).

**Decay.** A periodic job that lowers the confidence of memory cells that have not been confirmed recently, so stale facts stop dominating recall (post 16).

**Decode.** The phase of a call that generates output one token per forward pass, each depending on the previous one (post 05).

**Distraction.** The failure mode in which irrelevant tokens crowd out relevant ones and the model attends to the wrong material. The first fix is a tighter select step (post 06).

**Dual LLM pattern.** A security pattern in which a quarantined model processes untrusted content into structured output and a privileged model, which never sees the raw content, acts on that output (Willison, 2023; post 23).

**Effort (reasoning).** A provider parameter that sets how much reasoning a reasoning model spends, trading answer quality against latency and cost (post 18).

**Embedding.** A dense vector representation of a piece of text or an image, used for similarity search.

**Episodic memory.** Long-term memory of specific past events and interactions, retrieved by reference or by similarity to the current situation (post 16).

**Eval.** A structured test of model or system behaviour on a fixed dataset; the unit of measurement for any context change (post 20).

**Faithfulness.** A Ragas metric: the fraction of claims in a generated answer that the retrieved context supports.

**Fan-out and fan-in.** A sub-agent topology in which the parent dispatches parts of a task to several sub-agents in parallel and merges their results (post 13).

**Few-shot prompting.** Putting example input and output pairs in the prompt so the model infers the pattern. Picking which examples to include is a select operation (post 09).

**Function calling.** A provider feature in which the model receives tool schemas and may answer with a structured call to one of them; the wire format of tool use.

**GraphRAG.** A retrieval pattern that builds a knowledge graph and community summaries from the corpus and answers global or multi-hop questions from them (Edge et al., 2024; post 17).

**Grounding.** Making the model answer from supplied evidence rather than from what it learned in training. The purpose of RAG.

**Guardrail.** A check placed around a model call, on the input, the output, or both, that blocks or rewrites unsafe or off-policy content (post 21).

**Hallucination.** A fluent but factually wrong output, often because the needed fact is not in the context.

**Hook.** A script the host runs at a fixed point in the agent loop (before a tool call, after an edit, at session start) to enforce a policy or add behaviour (post 26).

**HyDE (Hypothetical Document Embeddings).** A query-construction technique in which the model first writes a hypothetical answer and that text, rather than the question, is embedded for retrieval (Gao et al., 2022; post 09).

**Hybrid search.** Running dense (vector) and sparse (BM25) retrieval together and merging the ranked lists, usually with reciprocal rank fusion.

**Indirect prompt injection.** An attack in which malicious instructions sit in third-party content (a web page, an email, a retrieved document) that the model later reads (Greshake et al., 2023; post 23).

**Inference cost.** The dollar cost of one model call: input tokens, output tokens, and cache reads and writes, each at its own price (post 05).

**Information retention ratio (IRR).** The series' teaching construct for how much task-relevant information survives a compression step, measured as the fraction of a replay set's key facts still answerable afterwards. It is not a standard metric (post 12).

**Ingestion pipeline.** The offline sequence (source, parse, clean, enrich, chunk, index) that turns raw files into a retrievable corpus (post 10).

**Iron triangle (of tools).** The trade-off between catalogue size, per-tool description quality, and runtime selection: a design can keep any two of the three (post 15).

**Isolate.** The fourth of the four operations (WSCI): splitting work across separate context windows (sub-agents, sandboxes) so that one task's noise, errors, and tool output do not enter another's window (post 13).

**Key-value (KV) cache.** The keys and values already computed for earlier tokens, kept so that each new token attends over them instead of recomputing them; reused across calls for an identical prefix by a prompt cache (post 03).

**Layer.** One of the six parts of the context window, numbered 01 to 06 in the order they are sent: 01 system prompt, 02 tools and MCP descriptions, 03 memory and state, 04 retrieved chunks, 05 conversation history, 06 user instruction. Each has its own lifetime, cost shape, and failure mode (post 02).

**Layout-aware parsing.** Document parsing that keeps visual structure (tables, columns, headings, reading order) instead of flattening a page to a stream of text (post 10).

**LLM-as-judge.** Using a model to score another model's outputs against a rubric. Subject to position bias, length bias, self-preference, and rubric drift (Zheng et al., 2023; post 20).

**Long-context routing.** Deciding per query whether to answer by retrieval or by loading whole documents into the window (posts 17 and 25).

**LongBench.** A bilingual, multitask benchmark of long-context understanding across question answering, summarisation, and code (Bai et al., arXiv 2023, ACL 2024).

**Lost-in-the-middle.** The finding that models use information at the start and the end of a long context better than information in the middle (Liu et al., 2023), and the failure mode named after it (post 06).

**MaxSim.** The late-interaction score of ColBERT: for each query token, the highest similarity to any document token, summed over the query tokens (post 17).

**MCP (Model Context Protocol).** An open protocol, introduced by Anthropic in 2024, through which a host connects to servers that expose tools, resources, and prompts. Its descriptions enter the window as layer 02 (post 15).

**Memory.** Any state that outlives a single model call. Short-term memory lives in the window; long-term memory is stored outside it and is episodic, semantic, or procedural (post 16). Recalled memory enters the window as layer 03, memory and state.

**Memory poisoning.** An attack in which adversarial content is written into an agent's memory store and steers later sessions. A security term, covered in post 23, not one of the five failure modes.

**MRCR (Multi-Round Co-reference Resolution).** A long-context evaluation from the Michelangelo suite in which the model must resolve a reference that depends on a long multi-turn conversation history (Vodrahalli et al., 2024; post 25).

**Multimodal context.** Context that mixes text with images, rendered pages, screenshots, or audio, all of which occupy the same window and budget (post 19).

**Needle in a haystack (NIAH).** A long-context test that hides one fact in a long document and asks the model to retrieve it. It measures recall of a single fact, not reasoning over many (post 03).

**Observability.** Inspecting an LLM system's behaviour through traces, spans, and metrics so that failures can be diagnosed and costed (post 22).

**OCR (optical character recognition).** Converting text in images or scanned pages into machine-readable characters during ingestion (post 10).

**OWASP Top 10 for LLM Applications.** OWASP's ranked list of the most common security risks in LLM applications; prompt injection is first (post 23).

**Precision@k.** The fraction of the top-k packed items that are relevant. The series' measure of the rerank and pack stages (post 09).

**Prefill.** The phase of a call in which the model processes all input tokens in parallel before producing the first output token (post 05).

**Prefix caching.** Another name for prompt caching.

**Priority pruning.** A compress technique that drops entries by priority class (P0 never trimmed to P3 trimmed first), lowest class first, rather than by age (post 12).

**Procedural memory.** Long-term memory of how to do things: rules, skills, and routines, each with a trigger, the rule it injects, and its scope (post 16).

**Prompt cache.** A provider-side cache that stores the computed state of a stable prompt prefix and reuses it on later calls with the same prefix; the reason the stable prefix (layers 01 and 02) comes first (post 05).

**Prompt engineering.** The narrower practice of choosing the wording, structure, and examples of a single message, which context engineering extends to the whole window (post 01).

**Prompt injection.** An attack in which adversarial text in the input makes the model ignore its instructions or take unintended actions. Direct injection comes from the user; indirect injection comes from content the model reads (post 23).

**Provenance.** The recorded source of a memory cell or a retrieved chunk: who or what put it there, and when (posts 08 and 10).

**Query rewriting.** Reformulating the user's question into one or more retrieval-friendly queries before search; the first stage of the select pipeline (post 09).

**RAG (retrieval-augmented generation).** A pattern in which relevant chunks are retrieved at query time and placed in the prompt, as layer 04, before generation (post 11).

**Ragas.** An open-source evaluation library for RAG systems that provides faithfulness, answer relevancy, context precision, and context recall (Es et al., 2023).

**Reasoning model.** A model trained to generate thinking tokens before its final answer, spending extra compute to improve accuracy on hard problems (post 18).

**Recall@N.** The fraction of the relevant items that appear in the top-N candidate set. The series' measure of the candidate-generation stage (post 09).

**Reciprocal rank fusion (RRF).** A parameter-light method for merging ranked lists: each item scores $\sum_i 1/(k + r_i)$ over the lists it appears in, where $r_i$ is its rank in list $i$ and $k$ is a damping constant, often 60, unrelated to top-k (Cormack et al., 2009; posts 09 and 11).

**Regression suite.** A fixed set of inputs and expected outputs run on every prompt or pipeline change to detect quality drops (posts 14 and 20).

**Reranker.** A second-pass model, usually a cross-encoder, that re-scores the top-N candidates and keeps the top-k for packing (post 09).

**Resource (MCP).** Read-only data an MCP server exposes, which the host application can fetch without a tool call (post 15).

**RULER.** A long-context benchmark from NVIDIA that extends needle tests with multi-needle retrieval, multi-hop tracing, aggregation, and question answering, and reports an effective context length (Hsieh et al., 2024).

**Sandboxing.** In post 13's sense, output-scoping: running a tool so that its full output goes to a file and only the fields the model needs enter the window; the security sense, containment of side effects and privileges, is post 23's (posts 13, 15, and 23).

**Scratchpad.** A working area the agent writes to and reads from during a task, outside the window, such as a plan file (post 08).

**Select.** The second of the four operations (WSCI): choosing which items enter the window for this call. RAG, tool selection, memory recall, and few-shot picking are all select (post 09).

**Semantic chunking.** Splitting text at topic boundaries rather than at a fixed token count, often by comparing the embeddings of adjacent sentences.

**Semantic memory.** Long-term memory of distilled facts and preferences, slowly changing and confirmed or decayed over time (post 16).

**Send gate.** A deterministic check that runs before any outbound action (sending an email, issuing a refund) and enforces in code the rules the model is only asked to respect (post 30).

**Sequential topology.** A sub-agent pattern in which each child runs after the previous one and receives its output (post 13).

**Skill.** A reusable workflow the host loads into the window only when a task matches its description. In Anthropic's Agent Skills format each skill is a directory with a `SKILL.md` file (posts 08 and 26).

**Span.** A timed unit of work inside a trace; spans nest into a tree of operations (post 22).

**Structured output.** A provider feature that constrains the model's response to a supplied JSON Schema, so it returns parseable data rather than free text (post 21).

**Sub-agent.** A child model call invoked by a parent agent, running in its own isolated context window and returning only a structured result (post 13).

**Supervisor topology.** A sub-agent pattern in which a supervisor model decides, call by call, which worker to call next and how to combine the results; of the three topologies, the only one that leaves the next step to the model (post 13).

**System prompt.** Layer 01: the instructions sent first on every call. In the five-block form it carries identity, rules, format, knowledge, and tool-use guidance; the tool schemas themselves are layer 02 (post 14).

**Tenant isolation.** Keeping each customer's data, indexes, and memory partitioned so that no tenant can retrieve or influence another's context (post 24).

**Text-to-SQL.** A retrieval pattern in which the model writes a SQL query against a structured database instead of fetching unstructured chunks (post 17).

**Thinking tokens.** The intermediate reasoning tokens a reasoning model generates before its answer. They are billed as output and are usually hidden or summarised in the response (post 18).

**Time to first token (TTFT).** The wait before the first output token appears; it is set mainly by prefill, which streaming cannot hide (post 05).

**Token.** The unit a model reads and bills by. In English prose one token is roughly three quarters of a word (OpenAI, "Tokenizer"; post 04).

**Tool.** A callable function exposed to the model through a name, a description, and a JSON Schema for its arguments.

**Tool-result clearing.** A compress technique that drops or truncates large earlier tool outputs once they are no longer needed (post 12).

**Tool selection.** Choosing at run time which subset of the tool catalogue to expose to the model on a given call. A select operation over tool descriptions (posts 09 and 15).

**Tool-storm.** The failure mode in which the model makes repeated, redundant, or useless tool calls, from a catalogue that is too large, descriptions that do not say when to call a tool, or no stop condition. The first fix is a trimmed catalogue with a stop budget (post 06).

**Top-k.** The number of items kept after reranking and packed into the window (post 09).

**Top-N.** The size of the candidate set that candidate generation passes to the reranker (post 09).

**Trace.** The full record of one agent run: every model call, every tool call, every span, with tokens, latency, and cost (post 22).

**Triager.** A small sub-agent whose only job is to classify an input and route it (post 30).

**Trust boundary.** A line in a system across which input is treated as untrusted; filtering, validation, or sandboxing happens at the boundary (post 23).

**Validate-and-retry.** A loop that parses or schema-checks a model's output and, on failure, re-prompts with the error until the output is valid or a retry cap is reached (post 21).

**Vector database.** A datastore built for nearest-neighbour search over embeddings.

**Windowing.** A compress technique that keeps only the most recent turns or tokens of a conversation (post 12).

**Write.** The first of the four operations (WSCI): moving information out of the window into a store (memory, a scratchpad, repository documentation, an index) so that it can be selected later (post 08).

**WSCI.** The series' abbreviation for write, select, compress, isolate, always in that order: the four operations on context named by Lance Martin ("Context Engineering for Agents", 2025). Every technique is placed in exactly one of the four (post 07).
