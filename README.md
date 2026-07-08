<div align="center">

# Context Engineering

**A free, framework-agnostic series on engineering the entire input an LLM sees on every call.**

System prompt · tools · memory · retrieval · history · user instruction.

[![License: CC BY 4.0](https://img.shields.io/badge/Prose-CC--BY--4.0-blue.svg)](https://creativecommons.org/licenses/by/4.0/)
[![License: MIT](https://img.shields.io/badge/Code-MIT-green.svg)](LICENSE)
[![Posts](https://img.shields.io/badge/posts-30-orange.svg)](#-the-series)
[![Status](https://img.shields.io/badge/status-in%20progress-yellow.svg)](PLAN.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Read the cheatsheet](CHEATSHEET.md) · [Glossary](GLOSSARY.md) · [References](REFERENCES.md) · [Plan](PLAN.md) · [Contribute](CONTRIBUTING.md)

</div>

---

## Why this exists

Most LLM applications fail not because the model is weak but because the **context** assembled around the user's question is wrong: the system prompt is too vague, the wrong chunks were retrieved, history has buried the rules, or the tools are described badly. *Context engineering* is the discipline of doing that assembly well — across all six layers — so that the model has the right information, in the right place, at the right cost.

This repository is the source for **30 posts**, every **diagram**, every **code companion** (runnable), plus a one-page **cheatsheet** and a printable **reference-architecture poster**.

> No marketing voice. Neutral, textbook tone. Examples first, formalism second. Framework-agnostic.

---

## Quick start

**If you have one hour, read these three:**

1. [01 · Why context engineering](posts/01-why-context-engineering/index.md)
2. [02 · The six layers of context](posts/02-six-layers-of-context/index.md)
3. [07 · Write, select, compress, isolate](posts/07-write-select-compress-isolate/index.md)

**If you have ten minutes, read the [one-page cheatsheet](CHEATSHEET.md).**

**If you have ten seconds:**

> Every LLM call is a stack of six layers. Four operations — **W**rite, **S**elect, **C**ompress, **I**solate — let you engineer each layer. Five recurring **failure modes** explain almost every production bug. The rest of the series is depth on each.

---

## 📚 The series

Thirty posts in five parts. Reading order is linear; the six posts marked ★ were
added after the first draft and slot into the flow where they belong.

### Part I — Foundations

| #  | Title | Folder |
|----|-------|--------|
| 01 | [Why context engineering — and why now](posts/01-why-context-engineering/index.md) | `01-why-context-engineering` |
| 02 | [The six layers of context](posts/02-six-layers-of-context/index.md) | `02-six-layers-of-context` |
| 03 | [How LLMs actually read context](posts/03-how-llms-read-context/index.md) | `03-how-llms-read-context` |
| 04 | [Tokens, windows, and budgets](posts/04-tokens-windows-budgets/index.md) | `04-tokens-windows-budgets` |
| 05 ★ | [The economics of context — pricing, caching, latency](posts/05-economics-of-context/index.md) | `05-economics-of-context` |
| 06 | [Five context failure modes](posts/06-context-failure-modes/index.md) | `06-context-failure-modes` |

### Part II — The four primitives (WSCI)

| #  | Title | Folder |
|----|-------|--------|
| 07 | [Write, select, compress, isolate](posts/07-write-select-compress-isolate/index.md) | `07-write-select-compress-isolate` |
| 08 | [Write strategies](posts/08-write-strategies/index.md) | `08-write-strategies` |
| 09 | [Select strategies](posts/09-select-strategies/index.md) | `09-select-strategies` |
| 10 ★ | [Data ingestion and document pipelines](posts/10-data-ingestion-pipelines/index.md) | `10-data-ingestion-pipelines` |
| 11 | [RAG in depth](posts/11-rag-in-depth/index.md) | `11-rag-in-depth` |
| 12 | [Compress strategies](posts/12-compress-strategies/index.md) | `12-compress-strategies` |
| 13 | [Isolate strategies](posts/13-isolate-strategies/index.md) | `13-isolate-strategies` |

### Part III — The layers in depth

| #  | Title | Folder |
|----|-------|--------|
| 14 | [The system prompt as software](posts/14-system-prompt-as-software/index.md) | `14-system-prompt-as-software` |
| 15 | [Tools and MCP](posts/15-tools-and-mcp/index.md) | `15-tools-and-mcp` |
| 16 | [Memory systems](posts/16-memory-systems/index.md) | `16-memory-systems` |
| 17 | [Advanced retrieval](posts/17-advanced-retrieval/index.md) | `17-advanced-retrieval` |
| 18 ★ | [Context for reasoning models](posts/18-reasoning-model-context/index.md) | `18-reasoning-model-context` |
| 19 ★ | [Multimodal context — images, PDF pages, and audio](posts/19-multimodal-context/index.md) | `19-multimodal-context` |

### Part IV — Production concerns

| #  | Title | Folder |
|----|-------|--------|
| 20 | [Evaluation](posts/20-evaluation/index.md) | `20-evaluation` |
| 21 ★ | [Structured output and guardrails](posts/21-structured-output-guardrails/index.md) | `21-structured-output-guardrails` |
| 22 | [Observability, tracing, and cost](posts/22-observability/index.md) | `22-observability` |
| 23 | [Security and prompt injection](posts/23-security/index.md) | `23-security` |
| 24 ★ | [Privacy, PII, and data governance](posts/24-privacy-and-governance/index.md) | `24-privacy-and-governance` |
| 25 | [Long context vs. RAG — a decision framework](posts/25-long-context-vs-rag/index.md) | `25-long-context-vs-rag` |

### Part V — Workflow & builds

| #  | Title | Folder |
|----|-------|--------|
| 26 | [The modern agentic workflow](posts/26-modern-agentic-workflow/index.md) | `26-modern-agentic-workflow` |
| 27 | [Remote agentic workflow](posts/27-remote-agentic-workflow/index.md) | `27-remote-agentic-workflow` |
| 28 | [Build #1 — RAG chatbot from scratch](posts/28-build-rag-chatbot/index.md) | `28-build-rag-chatbot` |
| 29 | [Build #2 — MCP server from scratch](posts/29-build-mcp-server/index.md) | `29-build-mcp-server` |
| 30 | [Capstone — Email reply agent](posts/30-capstone-email-reply-agent/index.md) | `30-capstone-email-reply-agent` |

---

## 🧰 Reference assets

| Asset | What it is |
|-------|-----------|
| [`CHEATSHEET.md`](CHEATSHEET.md) | Single printable page: six layers, WSCI, five failure modes, debug checklist. |
| [`GLOSSARY.md`](GLOSSARY.md) | Every term used in any post, alphabetised, one-line definitions. |
| [`REFERENCES.md`](REFERENCES.md) | Master bibliography for every citation in the series. |
| [`assets/poster/`](assets/poster/) | A2 reference-architecture poster: every concept on one canvas. |

---

## 🗂 Repository layout

```
context-engineering/
├── README.md              ← you are here
├── GLOSSARY.md            ← one-line term definitions
├── CHEATSHEET.md          ← printable single page
├── REFERENCES.md          ← master bibliography
├── CONTRIBUTING.md        ← style guide and PR rules
├── LICENSE                ← CC-BY 4.0 (prose) + MIT (code)
│
├── posts/                 ← one folder per post
│   └── NN-kebab-slug/
│       ├── index.md       ← the post
│       ├── diagrams/      ← post-specific SVGs
│       └── snippets/      ← inline code shown in the post
│
├── code/                  ← runnable companions (offline-testable cores)
│   ├── 11-rag-from-scratch/     ← chunk · BM25 · RRF
│   ├── 15-tool-schemas/         ← token budget · schema validation
│   ├── 15-mcp-quickstart/       ← ~60-line MCP server
│   ├── 20-eval-ragas/           ← golden set · gate · judge
│   ├── 28-rag-chatbot/          ← full build (Post 28)
│   ├── 29-mcp-server-full/      ← full build (Post 29)
│   └── 30-email-reply-agent/    ← capstone (Post 30)
│
├── assets/
│   ├── diagrams/
│   │   └── exports/       ← rendered hero SVGs used by posts
│   ├── images/
│   ├── animations/
│   └── poster/            ← reference-architecture poster
```

**Naming rule.** `posts/NN-kebab-slug/`. `NN` is a stable two-digit number; the slug never changes after publishing (URL stability).

---

## 💻 Code companions

Runnable companions live under [`code/`](code/) and are MIT-licensed. They use plain Python and the official provider SDKs first; a framework appears only when it materially changes the shape of the code.

| Companion | Code | Post |
|-----------|------|------|
| RAG from scratch (chunk · BM25 · RRF) | [`code/11-rag-from-scratch/`](code/11-rag-from-scratch/) | [Post 11](posts/11-rag-in-depth/index.md) |
| Tool schemas (token budget · validation) | [`code/15-tool-schemas/`](code/15-tool-schemas/) | [Post 15](posts/15-tools-and-mcp/index.md) |
| MCP quickstart (~60-line server) | [`code/15-mcp-quickstart/`](code/15-mcp-quickstart/) | [Post 15](posts/15-tools-and-mcp/index.md) |
| Eval harness (golden set · gate · judge) | [`code/20-eval-ragas/`](code/20-eval-ragas/) | [Post 20](posts/20-evaluation/index.md) |
| RAG chatbot (full build) | [`code/28-rag-chatbot/`](code/28-rag-chatbot/) | [Post 28](posts/28-build-rag-chatbot/index.md) |
| MCP server (full build) | [`code/29-mcp-server-full/`](code/29-mcp-server-full/) | [Post 29](posts/29-build-mcp-server/index.md) |
| Email reply agent (capstone) | [`code/30-email-reply-agent/`](code/30-email-reply-agent/) | [Post 30](posts/30-capstone-email-reply-agent/index.md) |

Each code folder ships its own `README.md`, `pyproject.toml`, `.env.example`, and `tests/`. The four smaller companions have an offline-runnable core: their whole test suite passes with no API key and no network.

---

## 🤝 Contributing

Typos, broken links, and clarity fixes are very welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for style conventions.

For larger changes — a new post, a new hero diagram, a new code companion — please **open an issue first** so we can align on scope before you spend time on a PR.

Found a factual error or an outdated benchmark? File an issue with a citation; that is the most valuable kind of contribution this series can receive.

---

## 📜 License

This repository is **dual-licensed**:

- **Prose, diagrams, illustrations, and hero images** — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Share and adapt freely with attribution.
- **Code** under [`code/`](code/) and [`tools/`](tools/) — [MIT](LICENSE).

See [LICENSE](LICENSE) for full terms and the required attribution line.

---

<div align="center">

⭐ **If you find this useful, star the repo so others can find it.** ⭐

</div>
