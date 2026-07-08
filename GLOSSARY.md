# Glossary

One-line definitions for every term used in this series. Sorted alphabetically. When a post introduces a term in depth, it links here.

---

**Active learning.** Using human feedback (edits, accepts, rejects) on agent outputs as training signal for a future fine-tune or routing decision.

**Adaptive thinking.** A reasoning-model mode where the model decides on its own how much internal reasoning to spend per request, rather than using a fixed budget.

**Agent.** An LLM-driven program that can take multiple steps, call tools, and decide its own next action.

**AGENTS.md.** A repository-level system prompt convention used by Codex, Cursor, and other coding agents — equivalent to `CLAUDE.md`.

**Approval rate.** The fraction of agent-produced artefacts (drafts, diffs, plans) that the human accepts without edit. A lightweight quality proxy in production.

**Attention sink.** A position in the context window (typically the first few tokens) that the model attends to disproportionately, regardless of content.

**Audit log.** A structured, append-only record of every consequential action an agent took, with timestamp, args, result, and session id.

**Auto-compaction.** A host policy that summarises older portions of a long conversation when the prompt approaches a token threshold.

**BABILong.** A long-context benchmark testing multi-hop reasoning over distractor-filled long passages.

**BM25.** A classical lexical retrieval algorithm based on term frequency and document length. Often combined with vector search for hybrid retrieval.

**Bookend packing.** Placing the most relevant retrieved chunk first and the second-most relevant last, with weaker chunks in the middle, to mitigate the lost-in-the-middle effect.

**Cache breakpoint.** An explicit marker in the prompt telling the provider where a cacheable prefix ends, so the KV-cache up to that point can be stored and re-used.

**Cache hit / cache miss.** Whether a request's prefix matches a previously stored prompt cache entry. Hits are billed at a fraction of the input rate.

**Candidate generation.** The first stage of retrieval — producing a high-recall set (often ~50 items) that a reranker will refine.

**Chain of Thought (CoT).** A prompting pattern where the model is asked to reason step-by-step before answering.

**Chunking.** Splitting a document into retrieval-sized pieces, typically 400–600 tokens, sentence-aware, with overlap.

**Citation accuracy.** The fraction of citations in a generated answer that actually point to a chunk supporting the cited claim.

**CLAUDE.md.** Anthropic's repository-level system prompt convention for Claude Code; analogous to `AGENTS.md`.

**ColBERT.** A late-interaction retrieval model that scores query–document similarity per-token, achieving high accuracy at a higher index cost.

**ColPali.** A multimodal late-interaction retrieval model that embeds document page images directly, retrieving over visual layout without a separate OCR step.

**Compaction.** The act of summarising a long conversation history into a shorter representation that preserves the essential state.

**Compression.** The "C" in WSCI — reducing the size of items already in context (windowing, summarisation, pruning, tool-result clearing).

**Constrained decoding.** Restricting the model's token sampling at generation time to only those tokens allowed by a grammar or schema, guaranteeing syntactically valid output.

**Context engineering.** The discipline of deciding what enters an LLM's context window on every call — across all six layers — so that the model has the right information, in the right place, at the right cost.

**Context precision.** Ragas metric: the fraction of retrieved chunks that were actually relevant to the question.

**Context recall.** Ragas metric: the fraction of ground-truth-relevant chunks that the retriever surfaced.

**Context rot.** The gradual degradation of model behaviour as the context window fills with stale, redundant, or low-signal tokens.

**Context window.** The maximum number of tokens an LLM can attend to in a single call. Hard upper bound set by the model.

**Contextual retrieval.** Anthropic's technique of prepending an LLM-generated one-sentence header to each chunk to capture document-level context for embedding.

**Conversation buffer.** The recent user/assistant turns held in the prompt for the current session.

**Cross-encoder.** A model that takes a (query, document) pair and produces a relevance score. Used as a reranker after first-pass retrieval.

**Data residency.** A requirement that data be stored and processed only within a specified geographic or legal jurisdiction.

**Decay.** A periodic job that lowers the confidence of memory cells not recently confirmed, preventing stale facts from dominating recall.

**Distraction.** A context-failure mode where irrelevant tokens crowd out relevant ones and the model attends to the wrong material.

**Dual-LLM pattern.** A security pattern where one LLM processes untrusted content into structured output, and a second LLM (with no tools) acts on that output.

**Effort (reasoning).** A provider parameter that sets how much reasoning a reasoning model should spend, trading answer quality against latency and cost.

**Embedding.** A dense vector representation of a piece of text, used for similarity search.

**Episodic memory.** Long-term memory of specific past interactions, retrieved by similarity to the current situation.

**Eval.** A structured test of model behaviour on a fixed dataset. The unit of measurement for any context change.

**Faithfulness.** Ragas metric: the fraction of claims in the generated answer that are supported by the retrieved context.

**Fan-out / fan-in.** Sub-agent topology where the parent dispatches the same task to N parallel sub-agents and merges their results.

**Few-shot prompting.** Providing example input/output pairs in the prompt so the model infers the desired pattern.

**Function calling.** A provider feature where the model is given tool schemas and may emit structured calls to them. The provider-side wire format for tool use.

**GraphRAG.** A retrieval pattern that builds a knowledge graph from the corpus and uses graph queries to assemble context.

**Grounding.** Forcing the model to answer from supplied evidence rather than parametric knowledge. The point of RAG.

**Guardrail.** A deterministic check placed around a model call — on the input, the output, or both — that blocks or rewrites unsafe or off-policy content.

**Hallucination.** A model output that is fluent but factually wrong, typically because the relevant fact is not in the context.

**Hook.** A script that runs at a specific point in the agent loop (pre-tool-call, post-edit, pre-commit, session-start, etc.) to enforce policy or augment behaviour.

**HyDE — Hypothetical Document Embeddings.** A query-construction technique where the model first writes a hypothetical answer and that text is embedded for retrieval.

**Hybrid search.** Combining vector (semantic) and lexical (BM25) retrieval, then merging or reranking the results.

**Indirect prompt injection.** An attack where malicious instructions are placed in a third-party document that the model later retrieves or reads.

**Inference cost.** The dollar cost of one model call, dominated by input tokens at long context lengths.

**Information retention ratio (IRR).** A measurement of how much task-relevant information survives a compression step, measured against a replay set.

**Ingestion pipeline.** The offline sequence — parse, clean, chunk, embed, index — that turns raw source documents into a retrievable corpus.

**Inter-agent bus.** A shared substrate (filesystem, message queue, database) through which isolated sub-agents communicate.

**Iron triangle (of tools).** The trade-off between catalog size, per-tool description quality, and runtime selection cost — pick at most two.

**Isolation.** The "I" in WSCI — running sub-tasks in their own context windows so noise, errors, and tool storms do not contaminate the parent.

**Layout-aware parsing.** Document parsing that preserves visual structure — tables, columns, headings, reading order — instead of flattening a page to a raw text stream.

**LLM-as-judge.** Using a model to score another model's outputs against a rubric. Subject to position bias, length bias, self-preference, and rubric drift.

**Long-context routing.** A router that decides per-query between RAG and "load the whole document into context".

**LongBench.** A benchmark suite of long-context tasks across reasoning, summarisation, and question answering.

**Lost in the middle.** The empirical finding (Liu et al., 2023) that LLMs attend better to the start and end of long contexts than to the middle.

**MCP — Model Context Protocol.** Anthropic-led open protocol for connecting LLM hosts to external tools, resources, and prompts.

**Memory.** Any persistent state that survives a single LLM call. Subdivided into short-term, long-term, episodic, semantic, and procedural.

**Memory poisoning.** An attack class where adversarial content is written into the agent's memory store and influences future sessions.

**MRCR — Multi-Round Coreference Resolution.** A long-context eval that tests pronoun and entity resolution across long passages.

**Multimodal context.** Context that mixes text with other modalities — images, document page scans, audio — passed to a model that can attend across all of them.

**Needle in a haystack (NIAH).** A class of long-context evals where a single fact is hidden in a long document and the model must retrieve it.

**Observability.** The discipline of inspecting agent behaviour through traces, spans, and metrics so failures can be diagnosed.

**OCR (optical character recognition).** Converting text embedded in images or scanned pages into machine-readable characters during document ingestion.

**OWASP LLM Top 10.** OWASP's prioritised list of the most common security risks in LLM applications.

**Prefix caching.** Synonym for prompt caching.

**Priority pruning.** A compression technique that drops items in priority bands (P0 keep, P1 keep if room, P2 summarise, P3 drop) instead of by recency.

**Procedural memory.** Long-term memory of how to do things — skills, routines, slash commands, hook scripts.

**Prompt cache.** A provider-side cache that stores the KV-cache for a stable prompt prefix and re-uses it on subsequent calls.

**Prompt engineering.** The narrower practice of choosing the wording, structure, and few-shots of a single message. A subset of context engineering.

**Prompt injection.** An attack where adversarial text in the input causes the model to ignore its system prompt or take unintended actions.

**Provenance.** The recorded source of a memory cell or a retrieved chunk — who or what put it there, and when.

**Query rewriting.** Reformulating the user's query into one or more retrieval-friendly variants before search.

**RAG — Retrieval-Augmented Generation.** A pattern where relevant chunks are retrieved at query time and stuffed into the prompt before generation.

**Ragas.** An open-source evaluation library for RAG systems; provides faithfulness, answer relevancy, context precision, and context recall.

**Recall@N.** The fraction of relevant items present in the top-N retrieved set.

**ReAct.** A prompting pattern interleaving Reason–Act–Observe steps for tool-using agents.

**Reasoning model.** A model trained to produce an internal chain of thinking tokens before its final answer, spending extra compute to improve hard-problem accuracy.

**Reciprocal Rank Fusion (RRF).** A simple, parameter-light algorithm for merging multiple ranked lists into one.

**Regression suite.** A small set of fixed input/output pairs run on every prompt change to detect quality drops.

**Reranker.** A second-pass model (usually a cross-encoder) that re-scores the top-k from a first-pass retriever.

**Resource (MCP).** A read-only document an MCP server exposes; the host can fetch it on demand without invoking a tool.

**RULER.** A long-context benchmark from NVIDIA covering retrieval, multi-hop, aggregation, and CWE tasks.

**Sandboxing.** Running a sub-agent in a confined process / container so its noisy or risky tool output cannot harm the parent.

**Scratchpad.** A short-term memory area the model writes to and reads from during a single task to externalise reasoning.

**Select.** The "S" in WSCI — choosing which items to bring into context (RAG, tool selection, memory recall, few-shot selection).

**Semantic chunking.** Chunking by topic boundary rather than fixed token count, often via embedding similarity between adjacent sentences.

**Semantic memory.** Long-term memory of distilled facts and preferences; slowly changing, often hand-curated.

**Send-gate.** A deterministic post-draft check that runs before any outbound action (e.g. sending an email), enforcing rules in code that the model is only asked to respect.

**Sequential topology.** Sub-agent pattern where each child runs after the previous, with output piped forward.

**Skill.** A re-usable, model-readable workflow definition (e.g. Anthropic's `.skills/` files).

**Span.** A timed unit of work inside a trace; spans nest to form a tree of operations.

**Structured output.** A provider feature that forces the model's response to conform to a supplied JSON schema, returning parseable data rather than free text.

**Sub-agent.** A child LLM call invoked by a parent agent, running in its own isolated context window.

**Supervisor topology.** Sub-agent pattern where one agent decomposes a task and delegates to specialised workers, then synthesises.

**System prompt.** The first message in an LLM call; sets identity, rules, format, and available tools.

**Tenant isolation.** Keeping each customer's data, indexes, and memory strictly partitioned so one tenant can never retrieve or influence another's context.

**Text-to-SQL.** A retrieval pattern where the model generates a SQL query against a structured database instead of fetching unstructured chunks.

**Thinking tokens.** The intermediate reasoning tokens a reasoning model generates before its answer — billed as output, and usually hidden or summarised in the response.

**Token.** The unit the model reads and bills on. Roughly 0.75 English words per token.

**Tool.** A callable function exposed to the model via a JSON schema.

**Tool selection.** The runtime act of choosing which subset of an available tool catalog to expose to the model on a given call.

**Tool-result clearing.** A compression step that drops or truncates large prior tool outputs once they are no longer needed.

**Trace.** The full record of one agent session — every model call, every tool call, every span — used for debugging and audit.

**Triager.** A small sub-agent whose only job is to classify a request and route it.

**Trust boundary.** A line in the system across which input is treated as untrusted; filtering, validation, or sandboxing happens at the boundary.

**Validate-and-retry.** A loop that parses or schema-checks a model's output and, on failure, re-prompts the model with the error until it produces valid output or a retry cap is hit.

**Vector database.** A datastore optimised for nearest-neighbour search over embeddings.

**Windowing.** A compression technique that keeps only the most recent N turns / tokens of a conversation.

**Write.** The "W" in WSCI — externalising state out of the context window into memory, files, scratchpads, or indexes.

**WSCI.** Write, Select, Compress, Isolate — the four primitive operations on context, popularised by Lance Martin (2025).
