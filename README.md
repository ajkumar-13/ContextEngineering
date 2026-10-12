# Context Engineering

A free, framework-agnostic series of 30 posts on engineering the whole input a large language model (LLM) sees on every call: the system prompt, the tool and MCP descriptions, memory, retrieved context, conversation history, and the user instruction. It names the six layers of that input, explains how a model reads them and what they cost, gives the four operations that act on them (write, select, compress, isolate), goes deep on each layer, covers the production disciplines (evaluation, structured output, observability, security, privacy, and the choice between long context and retrieval), and ends with the agentic workflow and three runnable builds. A reader who finishes it can diagnose a misbehaving LLM application by layer and failure mode, size and price a context budget, design a retrieval, memory, and tool stack for a given workload, and ship a retrieval-augmented generation (RAG) chatbot, a Model Context Protocol (MCP) server, and an email-reply agent with an evaluation gate in front of them.

The examples are plain Python against the official provider SDKs (Anthropic, OpenAI, Gemini) and the MCP reference SDK. A framework appears only where it changes the shape of the code, and no framework is the subject of a post.

## What a reader builds

- A vocabulary that holds across the series: six layers, four operations, five failure modes, and the retrieval numbers top-N, top-k, recall@N, and precision@k.
- A context budget for an agent, priced per layer, with a prefix laid out so that it caches.
- A retrieval pipeline from scratch (chunking, BM25, reciprocal rank fusion), a tool-schema budget calculator, a minimal MCP server, and an evaluation harness with a regression gate.
- Three builds in Part V: a RAG chatbot, a production-shaped MCP server with a permission boundary, and an email-reply agent with a triager, memory, retrieval over earlier replies, and a send gate.

## The posts

### Part I - Foundations

After this part a reader can name the six layers in a raw API request, estimate the tokens, latency, and dollars of a prompt without running it, lay out a prefix so it caches, and map a production bug report to one of the five failure modes.

1. [01 - Why context engineering, and why now](posts/01-why-context-engineering/index.md)
2. [02 - The six layers of context](posts/02-six-layers-of-context/index.md)
3. [03 - How LLMs actually read context](posts/03-how-llms-read-context/index.md)
4. [04 - Tokens, windows, and budgets](posts/04-tokens-windows-budgets/index.md)
5. [05 - The economics of context: pricing, caching, and latency](posts/05-economics-of-context/index.md)
6. [06 - Five context failure modes](posts/06-context-failure-modes/index.md)

### Part II - The WSCI operating system

After this part a reader can place any technique under write, select, compress, or isolate (WSCI); choose a write destination and its metadata; tune the four levers of a retrieval pipeline; stand up an ingestion pipeline with provenance; pick a compression policy and measure what it keeps; and decide when a task should be split across sub-agents.

7. [07 - Write, select, compress, isolate](posts/07-write-select-compress-isolate/index.md)
8. [08 - Write strategies](posts/08-write-strategies/index.md)
9. [09 - Select strategies](posts/09-select-strategies/index.md)
10. [10 - Data ingestion and document pipelines](posts/10-data-ingestion-pipelines/index.md)
11. [11 - RAG in depth](posts/11-rag-in-depth/index.md)
12. [12 - Compress strategies](posts/12-compress-strategies/index.md)
13. [13 - Isolate strategies](posts/13-isolate-strategies/index.md)

### Part III - Layers in depth

After this part a reader can write a five-block system prompt under version control and continuous integration, design a tool catalogue and decide when MCP is the integration, route data to episodic, semantic, or procedural memory, pick GraphRAG, late interaction, SQL retrieval, or long-context loading by the shape of a corpus, budget thinking tokens, and account for image tokens.

14. [14 - The system prompt as software](posts/14-system-prompt-as-software/index.md)
15. [15 - Tools and MCP](posts/15-tools-and-mcp/index.md)
16. [16 - Memory systems](posts/16-memory-systems/index.md)
17. [17 - Advanced retrieval](posts/17-advanced-retrieval/index.md)
18. [18 - Context for reasoning models](posts/18-reasoning-model-context/index.md)
19. [19 - Multimodal context: images, PDF pages, and audio](posts/19-multimodal-context/index.md)

### Part IV - Production-grade practice

After this part a reader can wire a four-layer evaluation pyramid with a gate in continuous integration, constrain and validate model output, instrument traces and the four headline dashboard numbers, apply the four architectural defences against prompt injection, govern personal data across prompts, memory, and the trace store, and choose between long context, RAG, and a hybrid with the four-question test.

20. [20 - Evaluation](posts/20-evaluation/index.md)
21. [21 - Structured output and guardrails](posts/21-structured-output-guardrails/index.md)
22. [22 - Observability, tracing, and cost](posts/22-observability/index.md)
23. [23 - Security and prompt injection](posts/23-security/index.md)
24. [24 - Privacy, PII, and data governance](posts/24-privacy-and-governance/index.md)
25. [25 - Long context vs. RAG: a decision framework](posts/25-long-context-vs-rag/index.md)

### Part V - Workflow and builds

After this part a reader has run the agentic workflow locally and remotely and has three working builds whose every function traces to an earlier post.

26. [26 - The modern agentic workflow](posts/26-modern-agentic-workflow/index.md)
27. [27 - Remote agentic workflow](posts/27-remote-agentic-workflow/index.md)
28. [28 - Build #1: RAG chatbot from scratch](posts/28-build-rag-chatbot/index.md)
29. [29 - Build #2: MCP server from scratch](posts/29-build-mcp-server/index.md)
30. [30 - Capstone: email reply agent](posts/30-capstone-email-reply-agent/index.md)

## Where to start

The posts are written to be read in order, and each one names the earlier posts it depends on. A reader with an hour reads [post 01](posts/01-why-context-engineering/index.md), [post 02](posts/02-six-layers-of-context/index.md), and [post 07](posts/07-write-select-compress-isolate/index.md): the reason for the discipline, the six layers, and the four operations. A reader who needs the mental models without the code (a product or strategy reader) can take Parts I and IV without running anything. A reader with ten minutes reads the [cheatsheet](CHEATSHEET.md).

## Before starting

The series assumes working Python, the ability to call one provider SDK (Anthropic, OpenAI, or Gemini), and the vocabulary of a first RAG tutorial: embedding, vector store, chunk. It does not assume transformer internals: post 03 gives the one-post account of tokens, attention, positions, and the key-value (KV) cache that the rest of the series needs. It depends on no other series. The three builds of Part V also assume a shell, `git`, and the ability to set an API key in a `.env` file.

## How a post is organised

Each post opens with a short summary, its prerequisites, and what the reader will be able to do afterwards, then works through numbered sections from the question to the answer, and closes with what can go wrong, the common pitfalls, further reading, and what to read next. Examples come before formalism: a concrete call, trace, or cost table first, the general rule afterwards. Every post names the layer a technique touches and the operation it performs, using the vocabulary fixed in the [notation guide](notation_guide.md). The figures read correctly in light and dark mode. Where a post has review questions, the series website shows them, with hints and explanations, beside the post.

## What is measured, and what is cited

Every price, token count, window size, and percentage in a post is labelled in the sentence that uses it: cited to a dated provider page or paper (the full entry is in [REFERENCES.md](REFERENCES.md)), produced by a snippet or companion test the post names, or marked illustrative. Model names, prices, and windows are stated as of early 2026 and are expected to go stale; the posts say so where they quote them. Nothing unmeasured is presented as a benchmark result, and the information retention ratio of post 12 is labelled a teaching construct, not a standard metric.

## The code

Seven companions live under [code/](code/), each a self-contained Python project with its own README, `pyproject.toml`, and tests:

| Directory | What it is | Post |
|---|---|---|
| [code/11-rag-from-scratch/](code/11-rag-from-scratch/) | chunking, BM25, and reciprocal rank fusion | [11](posts/11-rag-in-depth/index.md) |
| [code/15-tool-schemas/](code/15-tool-schemas/) | a tool-catalogue token budget and schema validation | [15](posts/15-tools-and-mcp/index.md) |
| [code/15-mcp-quickstart/](code/15-mcp-quickstart/) | a minimal MCP server | [15](posts/15-tools-and-mcp/index.md) |
| [code/20-eval-ragas/](code/20-eval-ragas/) | a golden set, a regression gate, and an LLM judge | [20](posts/20-evaluation/index.md) |
| [code/28-rag-chatbot/](code/28-rag-chatbot/) | the RAG chatbot build | [28](posts/28-build-rag-chatbot/index.md) |
| [code/29-mcp-server-full/](code/29-mcp-server-full/) | the MCP server build | [29](posts/29-build-mcp-server/index.md) |
| [code/30-email-reply-agent/](code/30-email-reply-agent/) | the capstone, against a fake mailbox | [30](posts/30-capstone-email-reply-agent/index.md) |

The four smaller companions (11, both 15s, and 20) have an offline core: their test suites run with no API key and no network. Each installs and tests from its own directory:

```bash
cd code/11-rag-from-scratch
python -m pip install -e ".[dev]"
pytest
```

The three builds use [uv](https://docs.astral.sh/uv/):

```bash
cd code/29-mcp-server-full
uv sync
uv run pytest -q
```

Each companion's README gives its quickstart, the keys a live run needs (where it needs any, from its `.env.example` copied to `.env`), and what is deliberately stubbed. The scripts under a post's `snippets/` run from the series root with a plain `python` and the standard library unless the post says otherwise.

## Reference pages

- [Cheatsheet](CHEATSHEET.md): one printable page with the six layers, WSCI, the five failure modes, the select pipeline, the system prompt's five blocks, and the defaults the posts recommend.
- [Glossary](GLOSSARY.md): every term the series uses, one entry each.
- [Notation guide](notation_guide.md): the fixed vocabulary, the claim labels, the spelling, and the figure colours.
- [References](REFERENCES.md): every paper, provider page, and piece of documentation the posts cite, grouped by post.

## The poster

[poster/one-page-of-context-engineering.svg](poster/one-page-of-context-engineering.svg) puts the whole series on one sheet, drawn by hand, in eight panels: the six layers in the order they are assembled, the four operations, the five failure modes and the first move against each, the window as a budget and what it costs, retrieval end to end, the system prompt beside the tool catalogue, the evidence worth keeping, and the security floor. It reads in light and dark mode and prints at A2.

## Corrections and feedback

This repository is the published source of the series and is maintained by its author. It does not take pull requests or issues. Provider prices, model names, and documentation pages move quickly, so a dead link or a stale figure is a real bug: corrections and suggestions go through the series website.

## License

Prose, questions, and figures are licensed under CC BY 4.0. Code is licensed under MIT. See [LICENSE](LICENSE).
