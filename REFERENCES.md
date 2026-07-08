# References

Master bibliography for the series, grouped by post. Where a source is referenced from multiple posts, it is listed once — under the first post that cites it — and later posts cross-link to that entry. URLs are given where a stable canonical URL exists; living vendor docs cite the documentation root.

> Citation style: author(s) or org, title, venue or publisher, year. A one-line note explains which point the source supports where that is not obvious. See [templates/citation-style.md](templates/citation-style.md).

---

## Post 01 — Why context engineering

- **Karpathy, A.** "+1 for context engineering over prompt engineering…" *X (Twitter), thread*, June 2025. — popularised the term in the broader ML community.
- **Anthropic Engineering.** "Effective context engineering for AI agents." *Anthropic blog*, September 2025. https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- **IBM Think.** "What is context engineering?" *IBM Think*, September 2025. https://www.ibm.com/think/topics/context-engineering
- **Martin, L.** "Context Engineering for Agents." *Personal blog*, 2025. — source of the WSCI vocabulary used throughout this series.
- **Horthy, D.** "12-Factor Agents." *humanlayer/12-factor-agents*, GitHub, 2025. https://github.com/humanlayer/12-factor-agents

## Post 02 — Six layers of context

- **Anthropic.** "Prompt caching." *Anthropic documentation*, 2024–25. https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- **Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., Liang, P.** "Lost in the Middle: How Language Models Use Long Contexts." *TACL*, 2024 (arXiv:2307.03172, 2023). https://arxiv.org/abs/2307.03172
- Effective context engineering, IBM Think — see Post 01.

## Post 03 — How LLMs read context

- **Xiao, G., Tian, Y., Chen, B., Han, S., Lewis, M.** "Efficient Streaming Language Models with Attention Sinks." *ICLR 2024* (arXiv:2309.17453, 2023). https://arxiv.org/abs/2309.17453
- **Su, J. *et al.*** "RoFormer: Enhanced Transformer with Rotary Position Embedding." *arXiv:2104.09864*, 2021. https://arxiv.org/abs/2104.09864
- **Hsieh, C.-P. *et al.*** "RULER: What's the Real Context Size of Your Long-Context Language Models?" *NVIDIA, arXiv:2404.06654*, 2024. https://arxiv.org/abs/2404.06654
- **Press, O., Smith, N. A., Lewis, M.** "Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation." *ICLR 2022* (arXiv:2108.12409). https://arxiv.org/abs/2108.12409
- Lost in the Middle, Prompt caching — see Post 02.

## Post 04 — Tokens, windows, budgets

- **OpenAI.** "Tokenizer" (interactive). https://platform.openai.com/tokenizer — and the `tiktoken` library, https://github.com/openai/tiktoken
- **Anthropic.** "Token counting." *Anthropic documentation*, 2024–25. https://docs.anthropic.com/en/docs/build-with-claude/token-counting
- **Google.** "Long context." *Gemini API documentation*, 2024–25. https://ai.google.dev/gemini-api/docs/long-context
- **Sennrich, R., Haddow, B., Birch, A.** "Neural Machine Translation of Rare Words with Subword Units." *ACL 2016* (arXiv:1508.07909). https://arxiv.org/abs/1508.07909 — the original BPE paper.
- **Pope, R. *et al.*** "Efficiently Scaling Transformer Inference." *MLSys 2023* (arXiv:2211.05102, 2022). https://arxiv.org/abs/2211.05102 — prefill/decode mechanics.
- Prompt caching — see Post 02.

## Post 05 — The economics of context

- **Anthropic.** "Pricing." *Anthropic* (per-million-token rates; current as of early 2026). https://www.anthropic.com/pricing
- Prompt caching (Anthropic) — see Post 02. Efficiently Scaling Transformer Inference (Pope et al.) — see Post 04.

## Post 06 — Context failure modes

- **Breunig, D.** "How Long Contexts Fail." *Personal blog*, June 2025. https://www.dbreunig.com/ — the essay the failure-mode taxonomy is rooted in.
- **Greshake, K. *et al.*** "Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection." *arXiv:2302.12173*, 2023. https://arxiv.org/abs/2302.12173
- **LangChain.** "LangGraph documentation." 2024–25. https://langchain-ai.github.io/langgraph/
- Lost in the Middle — see Post 02. Effective context engineering — see Post 01.

## Post 07 — Write, Select, Compress, Isolate

- **LangChain Blog.** "Context Engineering for Agents." 2025. https://blog.langchain.com/context-engineering-for-agents/
- Effective context engineering, IBM Think, Karpathy — see Post 01.

## Post 08 — Write strategies

- **Anthropic Engineering.** "Building Effective AI Agents." December 2024. https://www.anthropic.com/engineering/building-effective-agents
- **LangChain Blog.** "Memory for Agents." 2024. https://blog.langchain.com/memory-for-agents/
- **Anthropic.** "Introducing Contextual Retrieval." *Anthropic blog*, September 2024. https://www.anthropic.com/news/contextual-retrieval
- **agents.md project.** "AGENTS.md — a simple, open format for guiding coding agents." 2025. https://agents.md/
- **Park, J. S. *et al.*** "Generative Agents: Interactive Simulacra of Human Behavior." *UIST 2023* (arXiv:2304.03442). https://arxiv.org/abs/2304.03442

## Post 09 — Select strategies

- **Karpukhin, V. *et al.*** "Dense Passage Retrieval for Open-Domain Question Answering." *EMNLP 2020* (arXiv:2004.04906). https://arxiv.org/abs/2004.04906
- **Robertson, S., Zaragoza, H.** "The Probabilistic Relevance Framework: BM25 and Beyond." *Foundations and Trends in Information Retrieval*, 2009.
- **Cormack, G. V., Clarke, C. L. A., Buettcher, S.** "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods." *SIGIR 2009*. — the RRF paper.
- **Gao, L., Ma, X., Lin, J., Callan, J.** "Precise Zero-Shot Dense Retrieval without Relevance Labels." *ACL 2023* (arXiv:2212.10496, 2022). https://arxiv.org/abs/2212.10496 — HyDE.
- **Cohere.** "Rerank." *Cohere documentation*. https://docs.cohere.com/
- **Voyage AI.** "Rerankers." *Voyage AI documentation*. https://docs.voyageai.com/
- **BAAI.** "bge-reranker-v2" model cards. https://huggingface.co/BAAI/bge-reranker-v2-m3
- Contextual Retrieval — see Post 08.

## Post 10 — Data ingestion and document pipelines

- **Smith, R.** "An Overview of the Tesseract OCR Engine." *ICDAR 2007*.
- **Barbaresi, A.** "Trafilatura: A Web Scraping Library and Command-Line Tool for Text Discovery and Extraction." *ACL 2021 (system demonstrations)*. https://trafilatura.readthedocs.io/
- **Mozilla.** "Readability." *GitHub*. https://github.com/mozilla/readability — main-content extraction.
- **Docling, Unstructured, LlamaParse.** Layout-aware document-parsing toolkits, cited as a class. https://github.com/DS4SD/docling · https://unstructured.io/ · https://docs.llamaindex.ai/
- **Smock, B., Pesala, R., Abraham, R.** "PubTables-1M: Towards Comprehensive Table Extraction from Unstructured Documents." *CVPR 2022* (arXiv:2110.00061). https://arxiv.org/abs/2110.00061
- Contextual Retrieval — see Post 08.

## Post 11 — RAG in depth

- **Lewis, P. *et al.*** "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." *NeurIPS 2020* (arXiv:2005.11401). https://arxiv.org/abs/2005.11401
- **Khattab, O., Zaharia, M.** "ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT." *SIGIR 2020* (arXiv:2004.12832). https://arxiv.org/abs/2004.12832
- **Saad-Falcon, J. *et al.*** "ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems." *NAACL 2024* (arXiv:2311.09476, 2023). https://arxiv.org/abs/2311.09476
- **Asai, A. *et al.*** "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection." *arXiv:2310.11511*, 2023. https://arxiv.org/abs/2310.11511
- Contextual Retrieval — see Post 08. RRF — see Post 09.

## Post 12 — Compress strategies

- **Anthropic.** "Claude Code." *Documentation* (auto-compact and the conversation budget), 2024–25. https://docs.anthropic.com/en/docs/claude-code
- **Bai, Y. *et al.*** "LongBench: A Bilingual, Multitask Benchmark for Long Context Understanding." *ACL 2024* (arXiv:2308.14508, 2023). https://arxiv.org/abs/2308.14508
- Context Engineering for Agents (LangChain) — see Post 07. Lost in the Middle — see Post 02.

## Post 13 — Isolate strategies

- **Anthropic Engineering.** "How we built our multi-agent research system." June 2025. https://www.anthropic.com/engineering/built-multi-agent-research-system
- **Wu, Q. *et al.*** "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation." *arXiv:2308.08155*, 2023. https://arxiv.org/abs/2308.08155
- **OpenAI.** "Swarm: Lightweight multi-agent orchestration." GitHub, 2024. https://github.com/openai/swarm
- Building Effective AI Agents — see Post 08. LangGraph — see Post 06.

## Post 14 — System prompt as software

- **Anthropic.** "Giving Claude a role with a system prompt." *Anthropic documentation*, 2024–25. https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts
- **OpenAI.** "Model Spec." May 2024 (living document). https://model-spec.openai.com/
- **DAIR.AI.** "Prompt Engineering Guide." 2024 edition. https://www.promptingguide.ai/
- AGENTS.md — see Post 08. Prompt caching — see Post 02.

## Post 15 — Tools and MCP

- **Anthropic.** "Introducing the Model Context Protocol." *Anthropic blog*, November 2024. https://www.anthropic.com/news/model-context-protocol
- **Model Context Protocol.** "Specification." (latest). https://modelcontextprotocol.io/
- **Anthropic Engineering.** "Equipping agents for the real world with Agent Skills." October 2025. https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- **Anthropic Engineering.** "Code execution with MCP: building more efficient agents." November 2025. https://www.anthropic.com/engineering/code-execution-with-mcp
- **OpenAI.** "Function calling." *OpenAI documentation*. https://platform.openai.com/docs/guides/function-calling
- **Cognition AI.** "Don't Build Multi-Agents." *Cognition blog*, June 2025. https://cognition.ai/blog/dont-build-multi-agents — counterpoint argument.

## Post 16 — Memory systems

- **Tulving, E.** "Episodic and semantic memory." In Tulving, E. & Donaldson, W. (eds.), *Organization of Memory*, Academic Press, 1972. — source of the three-kind taxonomy.
- **Park, J. S. *et al.*** "Generative Agents: Interactive Simulacra of Human Behavior." *UIST 2023* (arXiv:2304.03442). https://arxiv.org/abs/2304.03442
- **Packer, C. *et al.*** "MemGPT: Towards LLMs as Operating Systems." *arXiv:2310.08560*, 2023. https://arxiv.org/abs/2310.08560
- **Rasmussen, P. *et al.*** "Zep: A Temporal Knowledge Graph Architecture for Agent Memory." *arXiv:2501.13956*, 2025. https://arxiv.org/abs/2501.13956 — the Graphiti engine behind graph-based memory.
- **Letta (formerly MemGPT).** "Building Agents with Long-Term Memory." *Letta documentation*, 2024–25. https://docs.letta.com/
- **Mem0.** "Long-term memory for AI agents." *Mem0 documentation*, 2024–25. https://mem0.ai/
- **OpenAI.** "Memory and new controls for ChatGPT." *OpenAI blog*, 2024. https://openai.com/index/memory-and-new-controls-for-chatgpt/
- **LangChain Blog.** "The state of AI agents — memory." 2024.

## Post 17 — Advanced retrieval

- **Edge, D. *et al.*** "From Local to Global: A Graph RAG Approach to Query-Focused Summarization." *Microsoft Research, arXiv:2404.16130*, 2024. https://arxiv.org/abs/2404.16130
- **Santhanam, K. *et al.*** "ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction." *NAACL 2022* (arXiv:2112.01488). https://arxiv.org/abs/2112.01488
- **Clavié, B.** "JaColBERT and Hard Negatives, Towards Better Japanese-First Embeddings for Retrieval." arXiv:2312.16144, 2023. https://arxiv.org/abs/2312.16144
- **Pourreza, M., Rafiei, D.** "DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction." *NeurIPS 2023* (arXiv:2304.11015). https://arxiv.org/abs/2304.11015
- **Anthropic.** "Long context prompting for Claude 2.1." *Anthropic blog*, December 2023. https://www.anthropic.com/news/claude-2-1-prompting
- ColBERT — see Post 11. Prompt caching — see Post 02.

## Post 18 — Context for reasoning models

- **Anthropic.** "Extended thinking" and "Adaptive thinking." *Anthropic documentation*, 2024–25. https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking
- **Wei, J. *et al.*** "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models." *NeurIPS 2022* (arXiv:2201.11903). https://arxiv.org/abs/2201.11903
- **DeepSeek-AI.** "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning." *arXiv:2501.12948*, 2025. https://arxiv.org/abs/2501.12948
- Prompt caching — see Post 02. Building Effective AI Agents — see Post 08.

## Post 19 — Multimodal context

- **Faysse, M. *et al.*** "ColPali: Efficient Document Retrieval with Vision Language Models." *arXiv:2407.01449*, 2024. https://arxiv.org/abs/2407.01449 — and the ViDoRe benchmark.
- **OpenAI.** "Vision" and "Computer use." *OpenAI documentation*, 2024–25. https://platform.openai.com/docs/guides/vision
- **Anthropic.** "Vision" and "Computer use." *Anthropic documentation*, 2024–25. https://docs.anthropic.com/en/docs/build-with-claude/vision
- ColBERT (late interaction) — see Post 11.

## Post 20 — Evaluation

- **Zheng, L. *et al.*** "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena." *NeurIPS 2023 Datasets and Benchmarks* (arXiv:2306.05685). https://arxiv.org/abs/2306.05685 — source for position, verbosity/length, and self-preference bias.
- **Chiang, W.-L. *et al.*** "Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference." *LMSYS, ICML 2024* (arXiv:2403.04132). https://arxiv.org/abs/2403.04132
- **Es, S., James, J., Espinosa-Anke, L., Schockaert, S.** "RAGAS: Automated Evaluation of Retrieval Augmented Generation." *EACL 2024 demo* (arXiv:2309.15217, 2023). https://arxiv.org/abs/2309.15217
- **Liu, Y. *et al.*** "G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment." *EMNLP 2023* (arXiv:2303.16634). https://arxiv.org/abs/2303.16634
- **Anthropic.** "Create strong empirical evaluations." *Anthropic documentation*, 2024–25. https://docs.anthropic.com/en/docs/test-and-evaluate
- **promptfoo.** Documentation. https://www.promptfoo.dev/docs/
- **DeepEval (Confident AI).** Documentation. https://docs.confident-ai.com/
- **OpenAI Evals.** GitHub. https://github.com/openai/evals
- ARES — see Post 11. LangSmith — see Post 22.

## Post 21 — Structured output and guardrails

- **OpenAI.** "Structured Outputs." *OpenAI documentation*. https://platform.openai.com/docs/guides/structured-outputs
- **Anthropic.** "Tool use." *Anthropic documentation* — see also Post 15.
- **Pydantic**, **Instructor**, **Outlines.** Structured-output libraries. https://docs.pydantic.dev/ · https://python.useinstructor.com/ · https://dottxt-ai.github.io/outlines/
- **Guardrails AI** and **NVIDIA NeMo Guardrails.** Output-guardrail frameworks. https://www.guardrailsai.com/ · https://github.com/NVIDIA/NeMo-Guardrails

## Post 22 — Observability

- **LangSmith.** "Tracing and evaluation." *Documentation*, 2024–25. https://docs.smith.langchain.com/
- **Langfuse.** "Open source LLM observability." *Documentation*, 2025. https://langfuse.com/docs
- **Arize.** "Phoenix." *Documentation*, 2024–25. https://docs.arize.com/phoenix
- **Helicone.** "Proxy-based LLM observability." *Documentation*, 2025. https://docs.helicone.ai/
- **OpenTelemetry.** "Semantic conventions for generative AI systems." (in development, 2025). https://opentelemetry.io/docs/specs/semconv/gen-ai/

## Post 23 — Security

- **OWASP.** "Top 10 for Large Language Model Applications." 2025 edition. https://owasp.org/www-project-top-10-for-large-language-model-applications/
- **Willison, S.** "Prompt injection" essay series, 2022–25. https://simonwillison.net/series/prompt-injection/
- **Willison, S.** "The Dual LLM pattern for building AI assistants that can resist prompt injection." *Personal blog*, April 2023. https://simonwillison.net/2023/Apr/25/dual-llm-pattern/
- **Bai, Y. *et al.*** "Constitutional AI: Harmlessness from AI Feedback." *Anthropic, arXiv:2212.08073*, 2022. https://arxiv.org/abs/2212.08073
- **Anthropic.** "Responsible Scaling Policy." (ongoing). https://www.anthropic.com/news/anthropics-responsible-scaling-policy
- **NIST.** "AI 600-1: Artificial Intelligence Risk Management Framework — Generative AI Profile." July 2024. https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
- Greshake et al. — see Post 06.

## Post 24 — Privacy, PII, and data governance

- **NIST.** "AI 600-1: Artificial Intelligence Risk Management Framework — Generative AI Profile." July 2024 — see also Post 23.
- **OWASP.** "Top 10 for Large Language Model Applications." 2025 — see also Post 23.
- **European Union.** "General Data Protection Regulation (GDPR)," Articles 5(1)(e) and 17. 2016. https://gdpr-info.eu/
- **Microsoft.** "Presidio" (PII detection and anonymisation). https://github.com/microsoft/presidio
- **Anthropic**, "Privacy and data usage"; **OpenAI**, "Enterprise privacy." *Vendor documentation*, 2024–25.

## Post 25 — Long context vs RAG

- **Kuratov, Y. *et al.*** "In Search of Needles in a 11M Haystack: Recurrent Memory Finds What LLMs Miss." *arXiv:2402.10790*, 2024. https://arxiv.org/abs/2402.10790 — BABILong.
- **Vodrahalli, K. *et al.*** "Michelangelo: Long Context Evaluations Beyond Haystacks via Latent Structure Queries." *Google DeepMind, arXiv:2409.12640*, 2024. https://arxiv.org/abs/2409.12640
- **Gemini Team, Google.** "Gemini 1.5: Unlocking multimodal understanding across millions of tokens of context." *arXiv:2403.05530*, 2024. https://arxiv.org/abs/2403.05530
- **Anthropic.** "Pricing." *Anthropic*, 2026. https://www.anthropic.com/pricing — per-token rates for the §7 cost arithmetic; prices change often.
- RULER — see Post 03. LongBench — see Post 12. Long context prompting for Claude 2.1 — see Post 17. Prompt caching — see Post 02. Long context (Gemini API) — see Post 04.

## Post 26 — Modern agentic workflow

- **Cursor.** "Rules and Composer." *Documentation*, 2025. https://docs.cursor.com/
- **Aider.** "Architect mode and conventions." *Documentation*, 2024–25. https://aider.chat/docs/
- Claude Code docs — see Post 12. AGENTS.md — see Post 08. Agent Skills, Don't Build Multi-Agents — see Post 15.

## Post 27 — Remote agentic workflow

- **AWS.** "Connect using EC2 Instance Connect." *EC2 documentation*, 2024–25. https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-connect-methods.html
- **VS Code.** "Remote Development using SSH." *Documentation* (latest). https://code.visualstudio.com/docs/remote/ssh
- ***OpenClaude*, *claude-code-remote*** and similar community projects (Telegram and web bridges). GitHub, 2024–25. — cited as a class; no single canonical repo.
- Aider docs — see Post 26.

## Post 28 — Build a RAG chatbot

- **LangChain.** "RAG from scratch" cookbook. GitHub, 2024. https://github.com/langchain-ai/rag-from-scratch
- **Voyage AI.** "voyage-3" model cards. https://docs.voyageai.com/
- Contextual Retrieval — see Post 08. Cohere Rerank — see Post 09. RAGAS — see Post 20.

## Post 29 — Build an MCP server

- **Model Context Protocol.** "Python SDK." GitHub, 2024–25. https://github.com/modelcontextprotocol/python-sdk
- MCP specification, MCP announcement — see Post 15. AGENTS.md — see Post 08.

## Post 30 — Capstone: email reply agent

- **Google.** "Gmail API." *Documentation* (latest). https://developers.google.com/gmail/api
- **Vercel.** "Functions." *Documentation* (latest). https://vercel.com/docs/functions
- **Railway.** "Cron jobs and workers." *Documentation* (latest). https://docs.railway.app/
- Everything else in the capstone traces to Posts 01–29; see those sections.

---

> If you find a citation missing or out-of-date, please open an issue. Accuracy here matters more than completeness.
