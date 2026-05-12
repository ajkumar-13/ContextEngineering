# 22 · RAG Chatbot — runnable companion

A small, framework-light RAG chatbot in Python. Implements every step from
[Post 22](../../posts/22-build-rag-chatbot/index.md): chunking with overlap,
contextual headers, hybrid retrieval (dense + BM25) with reciprocal rank
fusion, cross-encoder reranking, bookend packing with citations, and a
four-metric eval harness.

Designed to be readable end-to-end in one sitting (~350 lines total).

## Quickstart

```powershell
cd code/22-rag-chatbot
uv sync                          # or: pip install -e .
copy .env.example .env           # then edit with your API keys
uv run python -m rag.ingest data/corpus
uv run python -m rag.chat
```

Then ask a question at the `>` prompt.

## Required keys

The starter uses three providers by default; swap freely.

- `OPENAI_API_KEY` — generation (`gpt-4o-mini`).
- `VOYAGE_API_KEY` — embeddings (`voyage-3-lite`).
- `COHERE_API_KEY` — reranking (`rerank-english-v3.0`).

Cheaper / local alternatives:

- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` via `sentence-transformers`.
- Reranking: skip; the hybrid + RRF pipeline still works without it.
- Generation: any OpenAI-compatible endpoint (Ollama, vLLM, Together).

## Layout

```
.
├── README.md
├── pyproject.toml
├── .env.example
├── data/corpus/                 # drop .md / .txt files here
├── prompts/
│   ├── system.md
│   └── chunk_header.md
├── src/rag/
│   ├── __init__.py
│   ├── llm.py                   # thin LLM wrappers
│   ├── ingest.py                # chunk + header + embed + index
│   ├── retrieve.py              # hybrid + RRF + rerank
│   ├── prompt.py                # five-block system prompt + bookend pack
│   ├── chat.py                  # the chat loop
│   └── eval.py                  # the four Ragas metrics
└── tests/
    ├── fixtures.json            # eval Q/A pairs
    ├── test_chunker.py
    └── test_retriever.py
```

## Running the eval

```powershell
uv run python -m rag.eval
```

Prints the four Ragas metrics (faithfulness, answer relevancy, context
precision, context recall). Wire the `pytest` test that asserts they stay
within 5 % of baseline into your CI of choice.

## What this starter is not

- It is not a multi-tenant service. One user, one corpus, one shell.
- It is not streaming. Add SSE around `answer()` for that.
- It is not multi-turn. Append last-N turns + a query rewriter at the top
  of `answer()` for conversation memory; the post explains the shape.

See [Post 22 §8](../../posts/22-build-rag-chatbot/index.md) for the full
list of extensions and where each principle in this code traces back to.

## License

MIT for code (this folder); CC BY 4.0 for prose. See repo root.
