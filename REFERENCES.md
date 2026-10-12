# References

The bibliography of the series, grouped by post. A source cited by several posts is listed once, under the first post that cites it, and later posts point back to that entry. URLs are given where a stable canonical URL exists; living vendor documentation is cited at its documentation page, with the years it was read.

Citation style: author or organisation, title in quotation marks, venue or publisher in italics, year, then the URL, and where the point a source supports is not obvious, a short note after a colon.

---

## Post 01 - Why context engineering, and why now

- **Karpathy, A.** "+1 for 'context engineering' over 'prompt engineering'." *Post on X*, 25 June 2025: popularised the term and gave the definition quoted in post 01.
- **Martin, L.** "Context Engineering for Agents." *Personal blog*, 23 June 2025, https://rlancemartin.github.io/2025/06/23/context_engineering/; adapted on the *LangChain blog* as "Context Engineering" (The LangChain Team), 2 July 2025, https://www.langchain.com/blog/context-engineering-for-agents: the source of the write, select, compress, isolate operations this series abbreviates as WSCI.
- **Anthropic Engineering.** "Effective context engineering for AI agents." *Anthropic blog*, 29 September 2025. https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- **IBM Think.** "What is context engineering?" *IBM Think*, 2025. https://www.ibm.com/think/topics/context-engineering
- **Horthy, D.** "12-Factor Agents." *humanlayer/12-factor-agents*, GitHub, 2025. https://github.com/humanlayer/12-factor-agents
- **OpenAI.** "Function calling and other API updates." *OpenAI blog*, June 2023. https://openai.com/index/function-calling-and-other-api-updates/
- **Anthropic.** "Introducing the Model Context Protocol." *Anthropic blog*, November 2024. https://www.anthropic.com/news/model-context-protocol
- **Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., Liang, P.** "Lost in the Middle: How Language Models Use Long Contexts." *TACL*, 2024 (arXiv:2307.03172, 2023). https://arxiv.org/abs/2307.03172
- **Anthropic.** "Pricing." *Claude API documentation*, per-million-token rates as of early 2026, consulted October 2026. https://platform.claude.com/docs/en/about-claude/pricing
- **Lewis, P. *et al.*** "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." *NeurIPS 2020* (arXiv:2005.11401). https://arxiv.org/abs/2005.11401: the paper that named retrieval-augmented generation (RAG), cited by post 01 for the date.

## Post 02 - The six layers of context

- **Anthropic.** "Prompt caching." *Claude API documentation*, consulted October 2026. https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- **Anthropic.** "Introducing Contextual Retrieval." *Anthropic blog*, September 2024. https://www.anthropic.com/news/contextual-retrieval
- **OpenAI.** "Function calling." *OpenAI documentation*. https://platform.openai.com/docs/guides/function-calling
- **OpenAI.** "API reference" (Chat Completions and Responses). *OpenAI documentation*. https://developers.openai.com/api/reference/
- **Google.** "Generating content" (`generateContent`). *Gemini API documentation*. https://ai.google.dev/api/generate-content
- Effective context engineering for AI agents, What is context engineering?, Lost in the Middle: see Post 01.

## Post 03 - How LLMs actually read context

- **Xiao, G., Tian, Y., Chen, B., Han, S., Lewis, M.** "Efficient Streaming Language Models with Attention Sinks." *ICLR 2024* (arXiv:2309.17453, 2023). https://arxiv.org/abs/2309.17453
- **Su, J. *et al.*** "RoFormer: Enhanced Transformer with Rotary Position Embedding." *arXiv:2104.09864*, 2021. https://arxiv.org/abs/2104.09864
- **Hsieh, C.-P. *et al.*** "RULER: What's the Real Context Size of Your Long-Context Language Models?" *NVIDIA, arXiv:2404.06654*, 2024. https://arxiv.org/abs/2404.06654
- **Press, O., Smith, N. A., Lewis, M.** "Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation." *ICLR 2022* (arXiv:2108.12409). https://arxiv.org/abs/2108.12409
- **OpenAI.** "Tokenizer" (interactive). https://platform.openai.com/tokenizer; and the `tiktoken` library, https://github.com/openai/tiktoken
- **Sennrich, R., Haddow, B., Birch, A.** "Neural Machine Translation of Rare Words with Subword Units." *ACL 2016* (arXiv:1508.07909). https://arxiv.org/abs/1508.07909: byte-pair encoding adapted to sub-word segmentation for neural machine translation (the algorithm itself is Gage, 1994).
- **Kamradt, G.** "Needle In A Haystack: Pressure Testing LLMs." *GitHub repository*, 2023. https://github.com/gkamradt/LLMTest_NeedleInAHaystack
- **Hong, K., Troynikov, A., Huber, J.** "Context Rot: How Increasing Input Tokens Impacts LLM Performance." *Chroma Research*, 14 July 2025. https://www.trychroma.com/research/context-rot
- Lost in the Middle, Pricing: see Post 01. Prompt caching: see Post 02.

## Post 04 - Tokens, windows, and budgets

- **Anthropic.** "Token counting." *Anthropic documentation*, 2024 to 2026. https://docs.anthropic.com/en/docs/build-with-claude/token-counting
- **Google.** "Long context." *Gemini API documentation*, page updated 22 June 2026, consulted October 2026. https://ai.google.dev/gemini-api/docs/long-context
- **Anthropic.** "Context windows." *Claude API documentation*, consulted October 2026. https://platform.claude.com/docs/en/build-with-claude/context-windows: what counts toward the window, the overflow behaviour, and the window sizes by model.
- **Ji, Y. (Manus).** "Context Engineering for AI Agents: Lessons from Building Manus." *Manus blog*, 18 July 2025. https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus: the KV cache hit rate as the metric to watch for a production agent; timestamps in the prefix.
- **Pope, R. *et al.*** "Efficiently Scaling Transformer Inference." *MLSys 2023* (arXiv:2211.05102, 2022). https://arxiv.org/abs/2211.05102: prefill and decode mechanics.
- Tokenizer and `tiktoken`, Neural Machine Translation of Rare Words with Subword Units: see Post 03. Pricing: see Post 01. Prompt caching: see Post 02.

## Post 05 - The economics of context: pricing, caching, and latency

- **OpenAI.** "Prompt caching." *OpenAI API documentation*, consulted 12 October 2026. https://developers.openai.com/api/docs/guides/prompt-caching
- **Google.** "Context caching." *Gemini API documentation*, consulted 12 October 2026. https://ai.google.dev/gemini-api/docs/caching
- Pricing (Anthropic): see Post 01. Prompt caching (Anthropic): see Post 02. Context Engineering for AI Agents (Ji, Manus), Efficiently Scaling Transformer Inference (Pope et al.): see Post 04.

## Post 06 - Five context failure modes

- **Breunig, D.** "How Long Contexts Fail." *Personal blog*, 22 June 2025. https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html: the essay the failure-mode taxonomy starts from.
- **Laban, P., Hayashi, H., Zhou, Y., Neville, J.** "LLMs Get Lost In Multi-Turn Conversation." *arXiv:2505.06120*, 2025. https://arxiv.org/abs/2505.06120: the 39 percent drop on sharded prompts that Breunig quotes.
- **Greshake, K. *et al.*** "Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection." *arXiv:2302.12173*, 2023. https://arxiv.org/abs/2302.12173
- **LangChain.** "LangGraph documentation." 2024 to 2025. https://langchain-ai.github.io/langgraph/
- Lost in the Middle, Effective context engineering for AI agents: see Post 01. RULER, Context Rot: see Post 03.

## Post 07 - Write, select, compress, isolate

- **Anthropic.** "Manage costs effectively." *Claude Code documentation*, consulted 12 October 2026. https://code.claude.com/docs/en/costs: automatic compaction, `/compact` instructions, and the token cost of agent teams.
- Context Engineering for Agents (Martin), Effective context engineering for AI agents, What is context engineering?: see Post 01. Introducing Contextual Retrieval: see Post 02. Agent Skills: see Post 15. Claude Code documentation (compaction commands): see Post 12.

## Post 08 - Write strategies

- **Anthropic Engineering.** "Building Effective AI Agents." *Anthropic blog*, December 2024. https://www.anthropic.com/engineering/building-effective-agents
- **Chase, H.** "Memory for Agents." *LangChain blog*, 19 October 2024. https://www.langchain.com/blog/memory-for-agents
- **Anthropic.** "How Claude remembers your project." *Claude Code documentation*, consulted 12 October 2026. https://code.claude.com/docs/en/memory
- **agents.md project.** "AGENTS.md: a simple, open format for guiding coding agents." Stewarded by the Agentic AI Foundation under the Linux Foundation; consulted October 2026. https://agents.md/
- **Park, J. S. *et al.*** "Generative Agents: Interactive Simulacra of Human Behavior." *UIST 2023* (arXiv:2304.03442). https://arxiv.org/abs/2304.03442
- Context Engineering for Agents (Martin), Effective context engineering for AI agents: see Post 01. Introducing Contextual Retrieval: see Post 02. Agent Skills: see Post 15.

## Post 09 - Select strategies

- **Karpukhin, V. *et al.*** "Dense Passage Retrieval for Open-Domain Question Answering." *EMNLP 2020* (arXiv:2004.04906). https://arxiv.org/abs/2004.04906
- **Robertson, S., Zaragoza, H.** "The Probabilistic Relevance Framework: BM25 and Beyond." *Foundations and Trends in Information Retrieval*, 2009.
- **Cormack, G. V., Clarke, C. L. A., Büttcher, S.** "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods." *SIGIR 2009*: the reciprocal rank fusion paper.
- **Gao, L., Ma, X., Lin, J., Callan, J.** "Precise Zero-Shot Dense Retrieval without Relevance Labels." *ACL 2023* (arXiv:2212.10496, 2022). https://arxiv.org/abs/2212.10496: HyDE.
- **Cohere.** "Rerank." *Cohere documentation*. https://docs.cohere.com/
- **Voyage AI.** "Rerankers." *Voyage AI documentation*. https://docs.voyageai.com/
- **BAAI.** "bge-reranker-v2" model cards. https://huggingface.co/BAAI/bge-reranker-v2-m3
- **Carbonell, J., Goldstein, J.** "The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries." *SIGIR 1998*: maximal marginal relevance.
- Introducing Contextual Retrieval: see Post 02. Lost in the Middle (Liu et al.): see Post 01.

## Post 10 - Data ingestion and document pipelines

- **Smith, R.** "An Overview of the Tesseract OCR Engine." *ICDAR 2007*.
- **Barbaresi, A.** "Trafilatura: A Web Scraping Library and Command-Line Tool for Text Discovery and Extraction." *ACL 2021 (system demonstrations)*. https://trafilatura.readthedocs.io/
- **Mozilla.** "Readability." *GitHub*. https://github.com/mozilla/readability: main-content extraction.
- **Docling, Unstructured, LlamaParse.** Layout-aware document-parsing toolkits, cited as a class; documentation consulted October 2026. https://github.com/docling-project/docling, https://unstructured.io/, https://developers.llamaindex.ai/python/cloud/llamaparse/
- **pdfminer.six, pdfplumber, PyMuPDF.** Text-layer extraction libraries for born-digital PDFs, cited as a class; documentation consulted October 2026. https://github.com/pdfminer/pdfminer.six, https://github.com/jsvine/pdfplumber, https://pymupdf.readthedocs.io/
- **Smock, B., Pesala, R., Abraham, R.** "PubTables-1M: Towards Comprehensive Table Extraction from Unstructured Documents." *CVPR 2022* (arXiv:2110.00061). https://arxiv.org/abs/2110.00061
- Introducing Contextual Retrieval: see Post 02.

## Post 11 - RAG in depth

- Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (Lewis et al.): see Post 01.
- **Khattab, O., Zaharia, M.** "ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT." *SIGIR 2020* (arXiv:2004.12832). https://arxiv.org/abs/2004.12832
- **Saad-Falcon, J. *et al.*** "ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems." *NAACL 2024* (arXiv:2311.09476, 2023). https://arxiv.org/abs/2311.09476
- **Günther, M., Mohr, I., Williams, D. J., Wang, B., Xiao, H.** "Late Chunking: Contextual Chunk Embeddings Using Long-Context Embedding Models." *arXiv:2409.04701*, 2024. https://arxiv.org/abs/2409.04701
- **Muennighoff, N., Tazi, N., Magne, L., Reimers, N.** "MTEB: Massive Text Embedding Benchmark." *EACL 2023* (arXiv:2210.07316, 2022). https://arxiv.org/abs/2210.07316
- **Voyage AI.** "Text embeddings" (model list). *Voyage AI documentation*, consulted October 2026. https://docs.voyageai.com/docs/embeddings
- **LlamaIndex.** "SentenceSplitter." *LlamaIndex documentation*, consulted October 2026. https://docs.llamaindex.ai/
- Introducing Contextual Retrieval: see Post 02. Reciprocal rank fusion, BM25 and Beyond (Robertson and Zaragoza), HyDE, rerankers: see Post 09.

## Post 12 - Compress strategies

- **Anthropic.** "How Claude Code works" and "Commands." *Claude Code documentation*, consulted 12 October 2026. https://code.claude.com/docs/en/how-claude-code-works, https://code.claude.com/docs/en/commands: automatic compaction (older tool outputs cleared first, then a summary), `/compact [instructions]`, `/clear`.
- **Jiang, H., Wu, Q., Lin, C.-Y., Yang, Y., Qiu, L.** "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models." *EMNLP 2023* (arXiv:2310.05736). https://arxiv.org/abs/2310.05736
- **Pan, Z. *et al.*** "LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression." *Findings of ACL 2024* (arXiv:2403.12968). https://arxiv.org/abs/2403.12968
- **Xu, F., Shi, W., Choi, E.** "RECOMP: Improving Retrieval-Augmented LMs with Compression and Selective Augmentation." *arXiv:2310.04408*, 2023. https://arxiv.org/abs/2310.04408
- **Bai, Y. *et al.*** "LongBench: A Bilingual, Multitask Benchmark for Long Context Understanding." *ACL 2024* (arXiv:2308.14508, 2023). https://arxiv.org/abs/2308.14508
- Context Engineering for Agents (Martin), Lost in the Middle: see Post 01. Context windows: see Post 04.

## Post 13 - Isolate strategies

- **Anthropic Engineering.** "How we built our multi-agent research system." *Anthropic blog*, 13 June 2025. https://www.anthropic.com/engineering/built-multi-agent-research-system
- **Wu, Q. *et al.*** "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation." *arXiv:2308.08155*, 2023. https://arxiv.org/abs/2308.08155
- **OpenAI.** "Swarm" (experimental, educational; since replaced by the OpenAI Agents SDK). *GitHub repository*, 2024. https://github.com/openai/swarm
- **Yan, W. (Cognition).** "Don't Build Multi-Agents." *Cognition blog*, 12 June 2025. https://cognition.ai/blog/dont-build-multi-agents (now served at https://cognition.com/blog/dont-build-multi-agents): the counter-argument of post 13, section 9.
- Building Effective AI Agents: see Post 08. LangGraph: see Post 06. Pricing (Anthropic): see Post 01.

## Post 14 - The system prompt as software

- **Anthropic.** "Giving Claude a role with a system prompt." *Anthropic documentation*, 2024 to 2025. https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts
- **OpenAI.** "Model Spec." May 2024 (living document). https://model-spec.openai.com/
- **DAIR.AI.** "Prompt Engineering Guide." 2024 edition. https://www.promptingguide.ai/
- AGENTS.md: see Post 08. Prompt caching: see Post 02.

## Post 15 - Tools and MCP

- **Model Context Protocol.** "Specification" (current revision). https://modelcontextprotocol.io/
- **Anthropic Engineering.** "Equipping agents for the real world with Agent Skills." *Anthropic blog*, 16 October 2025. https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- **Anthropic Engineering.** "Code execution with MCP: building more efficient agents." *Anthropic blog*, November 2025. https://www.anthropic.com/engineering/code-execution-with-mcp
- Don't Build Multi-Agents (Yan, Cognition): see Post 13.
- Introducing the Model Context Protocol: see Post 01. Function calling (OpenAI): see Post 02.

## Post 16 - Memory systems

- **Tulving, E.** "Episodic and semantic memory." In Tulving, E. and Donaldson, W. (eds.), *Organization of Memory*, Academic Press, 1972: the source of the episodic and semantic distinction.
- **Packer, C. *et al.*** "MemGPT: Towards LLMs as Operating Systems." *arXiv:2310.08560*, 2023. https://arxiv.org/abs/2310.08560
- **Rasmussen, P. *et al.*** "Zep: A Temporal Knowledge Graph Architecture for Agent Memory." *arXiv:2501.13956*, 2025. https://arxiv.org/abs/2501.13956: the Graphiti engine behind graph-based memory.
- **Letta (formerly MemGPT).** "Building Agents with Long-Term Memory." *Letta documentation*, 2024 to 2025. https://docs.letta.com/
- **Mem0.** "Long-term memory for AI agents." *Mem0 documentation*, 2024 to 2025. https://mem0.ai/
- **OpenAI.** "Memory and new controls for ChatGPT." *OpenAI blog*, 2024. https://openai.com/index/memory-and-new-controls-for-chatgpt/
- **LangChain Blog.** "The state of AI agents: memory." 2024.
- Generative Agents (Park et al.): see Post 08.

## Post 17 - Advanced retrieval

- **Edge, D. *et al.*** "From Local to Global: A Graph RAG Approach to Query-Focused Summarization." *Microsoft Research, arXiv:2404.16130*, 2024. https://arxiv.org/abs/2404.16130
- **Santhanam, K. *et al.*** "ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction." *NAACL 2022* (arXiv:2112.01488). https://arxiv.org/abs/2112.01488
- **Clavié, B.** "JaColBERT and Hard Negatives, Towards Better Japanese-First Embeddings for Retrieval." *arXiv:2312.16144*, 2023. https://arxiv.org/abs/2312.16144
- **Pourreza, M., Rafiei, D.** "DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction." *NeurIPS 2023* (arXiv:2304.11015). https://arxiv.org/abs/2304.11015
- **Anthropic.** "Long context prompting for Claude 2.1." *Anthropic blog*, December 2023. https://www.anthropic.com/news/claude-2-1-prompting
- ColBERT: see Post 11. Prompt caching: see Post 02.

## Post 18 - Context for reasoning models

- **Anthropic.** "Extended thinking" and "Adaptive thinking." *Anthropic documentation*, 2024 to 2025. https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking
- **Wei, J. *et al.*** "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models." *NeurIPS 2022* (arXiv:2201.11903). https://arxiv.org/abs/2201.11903
- **DeepSeek-AI.** "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning." *arXiv:2501.12948*, 2025. https://arxiv.org/abs/2501.12948
- Prompt caching: see Post 02. Building Effective AI Agents: see Post 08.

## Post 19 - Multimodal context: images, PDF pages, and audio

- **Faysse, M. *et al.*** "ColPali: Efficient Document Retrieval with Vision Language Models." *arXiv:2407.01449*, 2024. https://arxiv.org/abs/2407.01449: and the ViDoRe benchmark.
- **OpenAI.** "Vision" and "Computer use." *OpenAI documentation*, 2024 to 2025. https://platform.openai.com/docs/guides/vision
- **Anthropic.** "Vision" and "Computer use." *Anthropic documentation*, 2024 to 2025. https://docs.anthropic.com/en/docs/build-with-claude/vision
- ColBERT (late interaction): see Post 11.

## Post 20 - Evaluation

- **Zheng, L. *et al.*** "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena." *NeurIPS 2023 Datasets and Benchmarks* (arXiv:2306.05685). https://arxiv.org/abs/2306.05685: the source for position, length, and self-preference bias.
- **Chiang, W.-L. *et al.*** "Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference." *LMSYS, ICML 2024* (arXiv:2403.04132). https://arxiv.org/abs/2403.04132
- **Es, S., James, J., Espinosa-Anke, L., Schockaert, S.** "RAGAS: Automated Evaluation of Retrieval Augmented Generation." *EACL 2024 demo* (arXiv:2309.15217, 2023). https://arxiv.org/abs/2309.15217
- **Liu, Y. *et al.*** "G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment." *EMNLP 2023* (arXiv:2303.16634). https://arxiv.org/abs/2303.16634
- **Anthropic.** "Create strong empirical evaluations." *Anthropic documentation*, 2024 to 2025. https://docs.anthropic.com/en/docs/test-and-evaluate
- **promptfoo.** Documentation. https://www.promptfoo.dev/docs/
- **DeepEval (Confident AI).** Documentation. https://docs.confident-ai.com/
- **OpenAI Evals.** GitHub. https://github.com/openai/evals
- ARES: see Post 11. LangSmith: see Post 22.

## Post 21 - Structured output and guardrails

- **OpenAI.** "Structured Outputs." *OpenAI documentation*. https://platform.openai.com/docs/guides/structured-outputs
- **Anthropic.** "Tool use." *Anthropic documentation*, 2024 to 2025. https://docs.anthropic.com/en/docs/build-with-claude/tool-use
- **Pydantic**, **Instructor**, **Outlines.** Structured-output libraries. https://docs.pydantic.dev/, https://python.useinstructor.com/, https://dottxt-ai.github.io/outlines/
- **Guardrails AI** and **NVIDIA NeMo Guardrails.** Output-guardrail frameworks. https://www.guardrailsai.com/, https://github.com/NVIDIA/NeMo-Guardrails

## Post 22 - Observability, tracing, and cost

- **LangSmith.** "Tracing and evaluation." *Documentation*, 2024 to 2025. https://docs.smith.langchain.com/
- **Langfuse.** "Open source LLM observability." *Documentation*, 2025. https://langfuse.com/docs
- **Arize.** "Phoenix." *Documentation*, 2024 to 2025. https://docs.arize.com/phoenix
- **Helicone.** "Proxy-based LLM observability." *Documentation*, 2025. https://docs.helicone.ai/
- **OpenTelemetry.** "Semantic conventions for generative AI systems." In development, 2025. https://opentelemetry.io/docs/specs/semconv/gen-ai/

## Post 23 - Security and prompt injection

- **OWASP.** "Top 10 for Large Language Model Applications." 2025 edition. https://owasp.org/www-project-top-10-for-large-language-model-applications/
- **Willison, S.** "Prompt injection" essay series, 2022 to 2025. https://simonwillison.net/series/prompt-injection/
- **Willison, S.** "The Dual LLM pattern for building AI assistants that can resist prompt injection." *Personal blog*, April 2023. https://simonwillison.net/2023/Apr/25/dual-llm-pattern/
- **Bai, Y. *et al.*** "Constitutional AI: Harmlessness from AI Feedback." *Anthropic, arXiv:2212.08073*, 2022. https://arxiv.org/abs/2212.08073
- **Anthropic.** "Responsible Scaling Policy." Ongoing. https://www.anthropic.com/news/anthropics-responsible-scaling-policy
- **NIST.** "AI 600-1: Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile." July 2024. https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
- Greshake et al.: see Post 06.

## Post 24 - Privacy, PII, and data governance

- **European Union.** "General Data Protection Regulation (GDPR)," Articles 5(1)(e) and 17. 2016. https://gdpr-info.eu/
- **Microsoft.** "Presidio" (PII detection and anonymisation). https://github.com/microsoft/presidio
- **Anthropic**, "Privacy and data usage"; **OpenAI**, "Enterprise privacy." *Vendor documentation*, 2024 to 2025.
- NIST AI 600-1, OWASP Top 10 for Large Language Model Applications: see Post 23.

## Post 25 - Long context vs. RAG: a decision framework

- **Kuratov, Y. *et al.*** "In Search of Needles in a 11M Haystack: Recurrent Memory Finds What LLMs Miss." *arXiv:2402.10790*, 2024. https://arxiv.org/abs/2402.10790: BABILong.
- **Vodrahalli, K. *et al.*** "Michelangelo: Long Context Evaluations Beyond Haystacks via Latent Structure Queries." *Google DeepMind, arXiv:2409.12640*, 2024. https://arxiv.org/abs/2409.12640
- **Gemini Team, Google.** "Gemini 1.5: Unlocking multimodal understanding across millions of tokens of context." *arXiv:2403.05530*, 2024. https://arxiv.org/abs/2403.05530
- Pricing (Anthropic, the per-token rates for the cost arithmetic of section 7; prices change often): see Post 01. RULER: see Post 03. LongBench: see Post 12. Long context prompting for Claude 2.1: see Post 17. Prompt caching: see Post 02. Long context (Gemini API): see Post 04.

## Post 26 - The modern agentic workflow

- **Cursor.** "Rules and Composer." *Documentation*, 2025. https://docs.cursor.com/
- **Aider.** "Architect mode and conventions." *Documentation*, 2024 to 2025. https://aider.chat/docs/
- Claude Code documentation: see Post 12. AGENTS.md: see Post 08. Agent Skills: see Post 15. Don't Build Multi-Agents: see Post 13.

## Post 27 - Remote agentic workflow

- **AWS.** "Connect using EC2 Instance Connect." *EC2 documentation*, 2024 to 2025. https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-connect-methods.html
- **VS Code.** "Remote Development using SSH." *Documentation* (latest). https://code.visualstudio.com/docs/remote/ssh
- ***OpenClaude*, *claude-code-remote*** and similar community projects (Telegram and web bridges). GitHub, 2024 to 2025: cited as a class; there is no single canonical repository.
- Aider documentation: see Post 26.

## Post 28 - Build #1: RAG chatbot from scratch

- **LangChain.** "RAG from scratch" cookbook. GitHub, 2024. https://github.com/langchain-ai/rag-from-scratch
- **Voyage AI.** "voyage-3" model cards. https://docs.voyageai.com/
- Introducing Contextual Retrieval: see Post 02. Cohere Rerank: see Post 09. RAGAS: see Post 20.

## Post 29 - Build #2: MCP server from scratch

- **Model Context Protocol.** "Python SDK." GitHub, 2024 to 2025. https://github.com/modelcontextprotocol/python-sdk
- MCP specification: see Post 15. Introducing the Model Context Protocol: see Post 01. AGENTS.md: see Post 08.

## Post 30 - Capstone: email reply agent

- **Google.** "Gmail API." *Documentation* (latest). https://developers.google.com/gmail/api
- **Vercel.** "Functions." *Documentation* (latest). https://vercel.com/docs/functions
- **Railway.** "Cron jobs and workers." *Documentation* (latest). https://docs.railway.app/
- Everything else in the capstone traces to posts 01 to 29; see those sections.

---

A missing or out-of-date citation is a bug in the series; corrections go through the series website.
