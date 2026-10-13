# 28 - Build #1: RAG chatbot from scratch

> **TL;DR.** The companion `code/28-rag-chatbot` is a retrieval-augmented generation (RAG) chatbot in 369 lines of Python whose every stage traces to an earlier post: sentence-aware chunks with a model-written header, hybrid retrieval fused by reciprocal rank fusion and re-ranked by a cross-encoder, a bookend-packed prompt under a block-structured system prompt, and a Ragas evaluation. Its five tests pass offline with no key; indexing, answering and scoring need Voyage AI, Cohere and OpenAI keys. Read against the posts it implements, it also shows what hardening means: an index that forgets stale chunks, a larger golden set, and the regression gate it does not yet have.
>
> **Prerequisites:** [Post 09](../09-select-strategies/index.md), [Post 11](../11-rag-in-depth/index.md), [Post 14](../14-system-prompt-as-software/index.md), [Post 20](../20-evaluation/index.md).
> **Safe to skip?** Skip it if a RAG service with hybrid retrieval, re-ranking, cited answers and an evaluation gate has already been built and run end to end.
>
> **After reading, you will be able to:**
>
> - Trace one question through the build's offline and online lanes, naming the module and function that runs each stage from ingest to cited answer.
> - Map each module of the build to the earlier post and section whose principle it implements, and spot where the code departs from it.
> - Read the packed prompt the build sends and name the layer each part fills, the bookend order of the chunks and the blocks of the system prompt.
> - Run the build's offline tests and core, and say what they prove and which steps need the Voyage AI, Cohere and OpenAI keys.
> - Harden a starter for real traffic: lazy clients, an index that drops stale chunks and re-embeds on a model change, a regression gate, the omitted extensions.

![Three lanes. Offline, run by python -m rag.ingest: corpus files, chunk, header, embed, into a Chroma collection. Online, run by answer: dense and BM25 candidates, fused by RRF to top-50, re-ranked to top-5, packed, then generated. Evaluation: fixtures, eval.py, four Ragas means, then a dashed regression gate that the companion does not have. Each stage that calls Voyage AI, Cohere or OpenAI names the provider.](diagrams/00-hero-build-rag-chatbot.svg)

*The offline lane writes the index once per corpus change; the online lane selects from it on every question; the evaluation lane replays fixed questions through the online lane.*

---

## 1. The question: how do the earlier posts compose into one chatbot?

Parts I to IV took retrieval, prompts and evaluation apart one lever at a time. This post puts them together in one program and asks of every function which earlier post it implements and where it falls short of it. The program is the companion [`code/28-rag-chatbot`](../../code/28-rag-chatbot/), a single-user chatbot over a folder of Markdown or text files. Its scope:

- **Chunks with contextual headers**: sentence-aware chunking with overlap and a model-written header per chunk ([post 11](../11-rag-in-depth/index.md), section 2).
- **Hybrid candidates fused by reciprocal rank fusion** (RRF): a dense and a BM25 (Best Match 25, a keyword-ranking function) ranking merged by rank ([post 09](../09-select-strategies/index.md), section 3).
- **Cross-encoder re-ranking** of the fused candidates (post 09, section 4).
- **Bookend packing with citation tags** (post 09, section 5).
- **A system prompt in blocks**, the checklist of [post 14](../14-system-prompt-as-software/index.md), section 2.
- **An evaluation** with the four Ragas metrics of [post 20](../20-evaluation/index.md), section 5.

Out of scope: streaming, multi-turn conversation, multi-tenant authentication, memory, GraphRAG, fine-tuning; section 9 says where the context-engineering ones attach.

---

## 2. Architecture and layout

The build has two lanes and a third that measures them, drawn in the figure at the top of the post. **Offline**, `python -m rag.ingest` splits each file into overlapping chunks, asks a small model for a one-sentence header per chunk, embeds the headed chunks and adds them to a Chroma collection on disk. **Online**, `answer(query)` takes a dense ranking from Chroma and a BM25 ranking over the same chunks, fuses them with RRF, re-ranks the fused list with Cohere's hosted cross-encoder, packs the best five and calls the generator. The **evaluation** lane replays fixture questions through `answer` and scores the results with Ragas.

The companion's layout:

```text
code/28-rag-chatbot/
  .env.example         keys and the four model ids
  data/corpus/         onboarding.md, refunds.md
  prompts/             system.md, chunk_header.md
  src/rag/
    llm.py             small_llm (headers), chat_llm (answers)
    ingest.py          chunk, contextual_header, ingest_path
    retrieve.py        hybrid, rrf_merge, rerank, retrieve
    prompt.py          pack
    chat.py            answer and the command-line loop
    eval.py            run: the four Ragas metrics
  tests/               fixtures.json, test_chunker.py, test_retriever.py
```

`pyproject.toml` declares `openai`, `voyageai`, `cohere`, `chromadb`, `rank-bm25`, `pydantic`, `python-dotenv`, `ragas`, `langchain-community` and `datasets`, with `pytest` as a development extra; the re-ranker is a hosted call, so no local model is downloaded. Ingestion reads `.md` and `.txt` files only. The snippet of section 11 counts the code: `src/rag` holds 369 lines of Python (`ingest.py` 121, `retrieve.py` 97, `eval.py` 41, `llm.py` 41, `chat.py` 39, `prompt.py` 24, `__init__.py` 6), with the two prompts kept as files in `prompts/`. The table below maps each part to the post it implements.

![A table of nine functions of the build, each with the post section it implements and where it departs: words counted as tokens, a title-only header, stale chunks kept, ranks from 0, re-ranking skipped under another key name, four prompt blocks, a prefix perhaps too short to cache, three fixtures and no gate; only pack matches post 09.](diagrams/01-module-map.svg)

*Every row has a post behind it; sections 3 to 7 say where each row stops short of its post.*

---

## 3. Ingestion: chunks, headers and an idempotent index

`chunk` in `src/rag/ingest.py` groups whole sentences up to a target and carries the tail of each chunk into the next:

```python
def chunk(text: str) -> list[str]:
    sentences = split_sentences(text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for s in sentences:
        s_len = len(s.split())
        if current_len + s_len > CHUNK_TARGET and current:
            chunks.append(" ".join(current))
            overlap: list[str] = []
            tail_len = 0
            for t in reversed(current):
                tail_len += len(t.split())
                overlap.insert(0, t)
                if tail_len >= CHUNK_OVERLAP:
                    break
            current, current_len = overlap, tail_len
        current.append(s)
        current_len += s_len
    if current:
        chunks.append(" ".join(current))
    return chunks
```

This is post 11's sentence-aware splitter, but `CHUNK_TARGET = 500` and `CHUNK_OVERLAP = 80` count words, not tokens. The snippet measures 1.42 tokens per word on the sample corpus, so a full chunk of such prose is about 710 tokens, above post 11's illustrative starting default of 400 to 600. On the companion's 1,200-word test text the chunks are 498, 498 and 366 words, each repeating the last 81 words of the one before. The two sample files (88 and 72 words) make two chunks in all.

`ingest_path` then skips what is stored and heads what is new:

```python
    ids = [_chunk_id(title, i, c) for i, c in enumerate(chunks)]
    existing = set(COLL().get(ids=ids).get("ids") or [])
    new_pairs = [(i, c, cid) for i, (c, cid) in enumerate(zip(chunks, ids)) if cid not in existing]
    if not new_pairs:
        return 0
    docs: list[dict] = []
    for i, c, cid in new_pairs:
        header = contextual_header(title, c)
        full = f"[Document: {title}]\n[Summary: {header}]\n\n{c}"
        docs.append({"id": cid, "text": full, "title": title, "idx": i})
```

The **chunk id** hashes the file name, the chunk's index and its text, so re-ingesting an unchanged file makes no model call: half of the incremental re-indexing of [post 10](../10-data-ingestion-pipelines/index.md), section 8. The **header** is post 11's contextual retrieval: one headed text is embedded with Voyage AI, indexed for BM25 and shown to the generator. The **title** is kept as metadata and becomes the citation tag of section 5.

The header is a weaker variant of Anthropic's method. "Introducing Contextual Retrieval" (Anthropic, September 2024) gives the model the whole document with the chunk, and its figures (the top-20 retrieval failure rate down 35% with contextual embeddings, 49% with contextual BM25 added and 67% with re-ranking, as post 11 quotes them) are for that method. `prompts/chunk_header.md` gives the model only the title and the chunk, the failure post 11 calls context written without the document. Anthropic's numbers do not transfer; the golden set has to show whether this header helps.

The idempotence has two gaps, both the stale index that post 11, section 7, lists as a cause of conflict. A changed chunk gets a new id and a new record, and the old record is never deleted. And the id omits the embedding model: after `RAG_EMBED_MODEL` changes, re-ingesting embeds nothing, while queries use the new model. The fix is the manifest of post 10, sections 7 and 8: per document, its hash, its chunk ids and the embedding model, checked before every ingest so that a changed document's old chunks are replaced.

**Model ids.** The defaults, each a hosted model behind its provider's API (application programming interface) and each overridable by an environment variable, as consulted in October 2026: `voyage-3-lite`, which Voyage AI's "Text embeddings" page lists under "Older models", "still accessible from our API", with the `voyage-4` family current; `rerank-english-v3.0`, still listed on Cohere's "Rerank" page beside `rerank-v3.5`, `rerank-v4.0-pro` and `rerank-v4.0-fast`; and `gpt-4o-mini` for headers and answers, which OpenAI's model page prices at 0.15 dollars per million input tokens and 0.60 per million output tokens, with a 128,000-token window.

---

## 4. Retrieval: hybrid candidates, fusion and re-ranking

**Candidates.** `hybrid` in `src/rag/retrieve.py` embeds the question, takes the dense top-50 from Chroma and the BM25 top-50 from `rank-bm25` over every stored chunk (lower-cased, split on letters, digits and underscores, built once per process and cached). Both see the headed text, so the header helps both halves. `top_n=50` is top-N in post 09's terms.

**Fusion.** The two rankings meet in `rrf_merge`:

```python
def rrf_merge(rankings: list[list[str]], *, k: int = 60) -> list[str]:
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, cid in enumerate(ranking):
            scores[cid] += 1.0 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)
```

This is post 09's RRF with one difference: `enumerate` counts ranks from 0, so first place adds $1/(60 + 0) \approx 0.016667$ where post 09's formula, ranking from 1, adds $1/61 \approx 0.016393$. Every score equals the 1-based formula with $k = 59$, a constant the RRF paper found not critical. Exact ties keep their first appearance: on the companion's own test, `x` ranked first and second and `y` ranked second and first both score 0.033060.

**Re-ranking.** `rerank` keeps `k=5`, top-k in post 09's terms:

```python
def rerank(query: str, candidates: list[dict], *, k: int = 5) -> list[dict]:
    if not candidates:
        return []
    if not os.environ.get("COHERE_API_KEY"):
        return candidates[:k]
    resp = _co().rerank(
        model=os.environ.get("RAG_RERANK_MODEL", "rerank-english-v3.0"),
        query=query,
        documents=[c["text"] for c in candidates],
        top_n=k,
    )
    return [candidates[r.index] for r in resp.results]
```

The cross-encoder reads each candidate with the query, which is why it sees only the fused shortlist. Without `COHERE_API_KEY` it returns the fused top-5, and `_co()` builds the Cohere client only after that check, so the program runs without a Cohere key. The check has a blind spot: Cohere's Python SDK (software development kit) reads `CO_API_KEY` first, and with only that name set, `rerank` silently skips re-ranking.

Post 09's first lever, query construction, is absent: the question is embedded as typed, adequate for a single turn and the first thing multi-turn breaks.

---

## 5. The packed prompt

`pack` in `src/rag/prompt.py` builds the two messages the generator receives:

```python
def pack(query: str, hits: list[dict]) -> list[dict]:
    """Bookend layout: best chunk first, second-best last, rest in middle."""
    if not hits:
        ordered: list[dict] = []
    elif len(hits) == 1:
        ordered = hits
    else:
        ordered = [hits[0]] + hits[2:] + [hits[1]]
    sources_block = "\n\n".join(
        f"[{h['meta']['title']}] {h['text']}" for h in ordered
    )
    user = f"Sources:\n\n{sources_block}\n\nQuestion: {query}"
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
    ]
```

**The order is post 09's bookend layout.** Five hits ranked 1 to 5 are packed as 1, 3, 4, 5, 2: the best first, the second best last among the sources, because models use the start and end of a long input more reliably than its middle (Liu et al., 2023, in [post 03](../03-how-llms-read-context/index.md), section 5). Bookend packing is the packing step of select, not compression: nothing is removed. With two hits, as on the sample corpus, the bookend order is the rank order.

**The layers.** The system message is layer 01, the system prompt. The user message carries the sources as layer 04, retrieved chunks, and ends with the `Question:` line as layer 06, the user instruction, last as post 02 orders them. Layers 02, 03 and 05 are empty: no tools, no memory, no history. The figure below draws the packed prompt.

![Two messages sent top to bottom. The system message, layer 01, holds prompts/system.md with four blocks, Identity, Rules, Format and Knowledge, 187 tokens. The user message holds the label Sources, five chunks in the order 1, 3, 4, 5, 2 as layer 04, each opening with its bracketed title tag, and the Question line as layer 06. Layers 02, 03 and 05 are marked empty.](diagrams/02-packed-prompt.svg)

*Two messages, three layers: the stable system prompt first, the chunks in bookend order, the question last.*

**The system prompt.** `SYSTEM` is read from `prompts/system.md`. Its first two blocks:

```text
# Identity
You are a concise, accurate technical assistant for the Acme product.

# Rules
- Use only the sources below. If the answer is not in them, say
  "I could not find that in the provided sources."
- Cite the source in [brackets] after every claim, e.g. [refunds].
- If sources disagree, surface the disagreement and cite both.
- Refuse anything outside Acme's product documentation.
```

Format (plain prose, at most 200 words, bracketed-title citations) and Knowledge (two stable facts about Acme) follow. That is four of post 14's five blocks: there is no tool-use guidance because the chatbot has no tools, and post 14 asks only that a missing block be missing on purpose. The snippet counts the file at 187 tokens. The rules are post 11's section 5 trio: say so when the sources lack the answer, cite in a parseable form, surface disagreement.

**Citations.** Each source opens with its title in brackets, `[refunds]`, then the stored text, which begins `[Document: refunds]` and the header. A cited title can be checked against the retrieved set, post 20's citation validity; the companion asks for citations but does not check them.

**Caching.** The system message is the same bytes on every call and comes first, the prefix a provider can cache, as [post 05](../05-economics-of-context/index.md), section 4, prescribes; the usage block `answer` returns reports cached tokens. Whether so short a prefix is cached depends on the provider's minimum, which OpenAI's "Prompt caching" guide (consulted October 2026) says varies with request settings for models before GPT-5.6.

---

## 6. Generation: the chat loop

`answer` in `src/rag/chat.py` joins the stages:

```python
def answer(query: str, *, k: int = 5) -> dict:
    hits = retrieve(query, k=k)
    msgs = pack(query, hits)
    out = chat_llm(msgs)
    return {
        "answer": out["text"],
        "sources": [{"title": h["meta"]["title"], "id": h["id"]} for h in hits],
        "usage": out["usage"],
    }
```

`chat_llm` in `src/rag/llm.py` sends the messages to OpenAI's Chat Completions API with `temperature=0.0`, which narrows the variation between runs without making answers identical, and returns the text and the usage block; `llm.py` is the one file to change for another provider. The returned answer, sources in rank order and token usage are the raw material of a trace. `python -m rag.chat` wraps `answer` in a prompt loop.

---

## 7. Evaluation: four Ragas metrics, and the gate the companion lacks

`run` in `src/rag/eval.py` replays the fixtures and averages the four metrics of post 20, section 5:

```python
def run(fixtures_path: Path | str = Path("tests/fixtures.json")) -> dict:
    fixtures = json.loads(Path(fixtures_path).read_text(encoding="utf-8"))
    rows: list[dict] = []
    for fx in fixtures:
        out = answer(fx["question"])
        ctxs = [h["text"] for h in retrieve(fx["question"], k=5)]
        rows.append({
            "question": fx["question"],
            "answer": out["answer"],
            "contexts": ctxs,
            "ground_truth": fx["answer"],
        })
    ds = Dataset.from_list(rows)
    res = evaluate(
        ds,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )
    return res.to_pandas().mean(numeric_only=True).to_dict()
```

The column names are Ragas's older ones; the current documentation uses `user_input`, `response`, `retrieved_contexts` and `reference`, and Ragas 0.4.3, read in October 2026, still converts the older names. Its default judge is `gpt-4o-mini` through OpenAI, the model that wrote the answers, which invites the self-preference post 20, section 6, warns about. Four gaps separate this from post 20's harness:

- **The golden set is three questions.** `tests/fixtures.json` holds three pairs; one case moves a mean by a third. Grow it from real failures, labelled by answer, never by chunk id.
- **The contexts are fetched twice.** `run` retrieves again after `answer` did, so each question pays for two embeddings and two re-rank calls, and the scored contexts need not be the ones the answer saw. `answer` should return the hit texts.
- **One fixture is answered by the system prompt.** It asks how a refund over 1,000 dollars is handled, a fact also in the Knowledge block, so its answer can be right with retrieval broken.
- **There is no gate.** `run` prints four means and compares them with nothing. The missing step is post 20's, section 4: save the means of an approved run and, in CI (continuous integration), fail when any metric falls by more than an absolute 0.05 below its baseline, as post 20's `check_regression` does. The companion README's "within 5 % of baseline" names a test that does not exist.

Nothing here is quoted from a live evaluation run; it needs an OpenAI key and the network.

---

## 8. Deployment

**Secrets.** `.env.example` lists `OPENAI_API_KEY`, `VOYAGE_API_KEY`, `COHERE_API_KEY`, the four model ids and `RAG_CHROMA_PATH`; `rag/__init__.py` loads a local `.env`. In production the same variables come from the platform's secret store.

**A service.** A thin HTTP (Hypertext Transfer Protocol) layer, such as a FastAPI route `POST /chat` returning `answer(query)` as JSON (JavaScript Object Notation), turns the script into a service. Ingestion stays a separate job, run when the corpus changes, so serving never waits on embedding. The companion builds its clients on first use (section 11), so the service, its tests and its health check start without every key.

**State.** The serving process is stateless; the Chroma directory and the corpus need a persistent volume or a managed store. On one server, `pgvector` in an existing Postgres removes a moving part (post 11, section 3). Section 7's gate then runs on every pull request that touches a prompt, the chunker or a model id.

---

## 9. What the build leaves out, and how to add it

- **Multi-turn conversation.** Append recent turns as layer 05, conversation history, and rewrite the query before `retrieve` (post 09, section 2).
- **Memory.** Retrieve rows of the nine-field memory row ([post 16](../16-memory-systems/index.md), section 3) and render them as one block of layer 03, memory and state, after the system prompt (post 16, section 9).
- **Untrusted sources.** Retrieved chunks come from outside the application; tag them as external with the trust tag of [post 23](../23-security/index.md), section 5.
- **Observability.** One span per retrieval and per model call, with candidates, packed top-k and usage ([post 22](../22-observability/index.md), section 3), kept in post 22's trace store.
- **Compression.** Once history exists, summarise older turns when the window passes a budget share ([post 12](../12-compress-strategies/index.md), section 3; the series' 80 and 95 percent triggers are its section 9).
- **Sub-agents.** A tool-using sub-agent for a request such as "draft a refund email for this ticket", returning only its result ([post 13](../13-isolate-strategies/index.md), section 2).
- **Long-context routing.** A per-query router in front of `answer` that loads a short document whole ([post 25](../25-long-context-vs-rag/index.md), section 6; [post 17](../17-advanced-retrieval/index.md), section 6).

---

## 10. The lesson: one select pipeline around a write

In the operations of [post 07](../07-write-select-compress-isolate/index.md), the build is two of the four. `ingest` is **write**: it parks the corpus in an index outside the window, the offline side of layer 04 in post 07's section 7. `retrieve` and `pack` are **select**: post 09's four levers with the first missing. The starter does no **compress** (every packed chunk goes in whole) and no **isolate** (one window serves the question).

The larger lesson is in the module map. Every function implements an earlier post, and almost every one departs from it somewhere: words counted as tokens, a header written without its document, an index that cannot forget, a re-ranker a key name can switch off, a golden set of three with no gate. None shows in a demo; each is found by reading the code against the post it came from.

---

## 11. Make it run

**Offline, today.** The five tests check the chunker (three tests) and `rrf_merge` (two). The modules they import need their packages (all but `ragas` and `datasets`) but no key: the OpenAI, Voyage AI and Cohere clients and the Chroma collection are opened on first use, and no test uses them. From the series root:

```text
uv run --with pytest --with rank-bm25 --with python-dotenv --with openai --with cohere --with voyageai --with chromadb python -m pytest -q -p no:cacheprovider code/28-rag-chatbot/tests
```

It ends with `5 passed`, with no key set and no Chroma directory created; `pytest` takes the source path from the companion's `pyproject.toml`. The tests prove that the chunker keeps to its word budget and that fusion ranks consistently high items above a consistently low one; they do not touch the header, the index, the re-ranker, the packing or the generator.

The snippet `offline_core.py` reads the companion's source, executes only its pure parts (`chunk`, `rrf_merge`, `pack`) and prints what they do on the sample corpus, counting tokens with tiktoken's `o200k_base` encoding, the one `gpt-4o-mini` uses. It runs in under a second:

```text
uv run python posts/28-build-rag-chatbot/snippets/offline_core.py
```

Its packing lines:

```text
4. Packing (prompt.py)
   five hits in rank order 1 to 5 are packed as: 1, 3, 4, 5, 2
   two hits are packed as: 1, 2
   messages: ['system', 'user']
   system prompt blocks: ['Identity', 'Rules', 'Format', 'Knowledge']; 187 tokens
```

**Live, with keys.** These steps follow the companion's README and were not run for this post. In `code/28-rag-chatbot`: `uv sync`; copy `.env.example` to `.env` and fill in the three keys; `uv run python -m rag.ingest data/corpus` (an OpenAI header call per new chunk, a Voyage AI embedding call per file); `uv run python -m rag.chat` (per question, a Voyage AI embedding, a Cohere re-rank, an OpenAI generation); `uv run python -m rag.eval` (the same per fixture, plus the judge's OpenAI calls). `pyproject.toml` pins `ragas` 0.4.3 and holds `langchain-community` below 0.4: with 0.4.2, which an unpinned install resolved in October 2026, `import ragas` fails on a missing `langchain_community.chat_models.vertexai`.

---

## 12. What can go wrong?

- **An edited document answered from its old version.** A refund limit changes in `refunds.md`; re-ingestion adds the new chunk and keeps the old, and the bot cites both limits. Delete a file's previous chunk ids before adding new ones.
- **A changed embedding model that changes nothing.** `RAG_EMBED_MODEL` is switched and the corpus re-ingested; every id exists, so nothing is re-embedded, and queries come from another model than the index. With other dimensions Chroma rejects the query; with equal ones retrieval silently degrades. Record the model per document and re-embed on change.
- **A re-ranker switched off by a key name.** The Cohere key is exported as `CO_API_KEY`, the name the SDK reads first; `rerank` looks only for `COHERE_API_KEY`, returns the fused order, and nothing reports it. Accept both names; log skipped re-ranks.
- **A header that guesses.** The header model sees a title and one chunk and writes a plausible sentence about a document it never read. Pass the whole document, cached, as post 11 does.
- **A green evaluation that proves little.** Three fixtures, one answerable from the system prompt, judged by the model that answered: the means can stay high while retrieval breaks.
- **Swapping the re-ranker off on the sample corpus.** Two chunks pass the top-5 either way, so turning re-ranking off only reorders them, and the comparison shows nothing. The corpus needs more chunks than k.

---

## Common pitfalls

1. **Reading `CHUNK_TARGET` as tokens.** It counts words; at the sample's 1.42 tokens per word a 500-word chunk is about 710 tokens.
2. **Quoting Anthropic's contextual-retrieval numbers for a title-only header.** The 35, 49 and 67 percent reductions belong to the method that shows the model the whole document.
3. **Calling the bookend layout compression.** It reorders the packed chunks and removes nothing; it is the packing step of select.
4. **Logging the answer without the packed prompt.** A bad answer cannot be debugged without the exact messages and ranked hits.
5. **Treating `top_n=50` and `k=5` as settled.** They are post 09's illustrative starting values; the golden set decides them for each corpus.

---

## Further reading

- Anthropic, "Introducing Contextual Retrieval" (September 2024): the header method with the whole document, and its retrieval-failure figures.
- Cormack, G. V. *et al.*, "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods" (SIGIR 2009).
- Es, S. *et al.*, "RAGAS: Automated Evaluation of Retrieval Augmented Generation" (EACL 2024 demo), and the Ragas documentation (consulted October 2026).
- Voyage AI, "Text embeddings"; Cohere, "Rerank"; OpenAI, `gpt-4o-mini` model page and "Prompt caching" (documentation, consulted October 2026).
- LangChain, "RAG from scratch": notebooks that accompany a video playlist building RAG from indexing to generation (GitHub, consulted October 2026).

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 29 - Build #2: MCP server from scratch](../29-build-mcp-server/index.md):** the second build, which puts tools behind the Model Context Protocol (MCP) with a permission boundary.
- **[Post 30 - Capstone: email reply agent](../30-capstone-email-reply-agent/index.md):** reuses this pipeline over prior replies inside an agent with memory and a send gate.
