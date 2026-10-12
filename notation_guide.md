# Notation and vocabulary guide

One vocabulary, shared by every post in the series. The goal is that a term means the same thing in every post: a reader who learns in post 02 that layer 04 is "retrieved chunks" never meets it as "the RAG layer" in post 17 and has to wonder whether that is something else. The [glossary](GLOSSARY.md) gives a one-paragraph definition of every term; this page fixes the names, the order, the numbers, and the typography.

Two rules govern everything below:

1. **One concept, one name, everywhere.** The same thing is never "retrieval context" in one post and "retrieved chunks" in the next.
2. **Each term is reintroduced on first use in every post**, and every acronym is expanded on first use in every post, because readers arrive mid-series from a search engine.

## Contents

1. The six layers
2. Lifetime classes
3. The four operations (WSCI)
4. The five failure modes
5. Retrieval numbers
6. Formulas
7. Claim labels
8. House conventions
9. Figure roles
10. Checklist before publishing a post

---

## 1. The six layers

Everything a model receives on one call is one flat sequence of tokens. The series divides it into six layers, always numbered and always in this order, which is the order they are sent:

| Number | Name | One clause |
|---|---|---|
| 01 | system prompt | the instructions sent first on every call: identity, rules, format, knowledge, and tool-use guidance |
| 02 | tools and MCP descriptions | the schemas and descriptions of every tool the model may call, including those an MCP server supplies |
| 03 | memory and state | facts recalled from long-term memory and the state of the current task |
| 04 | retrieved chunks | the evidence selected for this turn by a retrieval pipeline |
| 05 | conversation history | the earlier turns of this session |
| 06 | user instruction | the current request, sent last |

A post names a layer by its number and its name: "layer 04, retrieved chunks", or "04 Retrieved chunks" on a figure. The number is never written with one digit, and the name is never replaced by a synonym ("the RAG layer", "the prompt", "the tools layer"). The system prompt's own tools block carries only the guidance on when to use each tool; the schemas are layer 02.

## 2. Lifetime classes

The six layers fall into four lifetime classes, which decide what caches and what grows:

| Class | Layers | Behaviour |
|---|---|---|
| stable prefix | 01 to 02 | byte-identical across calls; placed first so that it caches |
| per-turn injection | 03 to 04 | assembled fresh for this call |
| growing tail | 05 | grows with every turn until it is compressed |
| trigger | 06 | small, last, never compressed |

## 3. The four operations (WSCI)

WSCI is the series' abbreviation for **write, select, compress, isolate**, always in that order. The four operations are Lance Martin's ("Context Engineering for Agents", 2025); the abbreviation is the series' own. Every technique is placed in exactly one of the four, on two axes:

| Operation | Direction | Scope |
|---|---|---|
| write | out of the window | spans several windows |
| select | into the window | one window |
| compress | out of the window | one window |
| isolate | into the window | spans several windows |

In prose the operations are lower case verbs ("the select step", "a compress technique"), capitalised only at the start of a sentence or in a table heading. A technique that fits none of the four is a reason to revisit the framework, not to invent a fifth term.

## 4. The five failure modes

The five failure modes are **distraction, confusion, conflict, lost-in-the-middle, and tool-storm**, named in that order. Each is described by symptom, mechanism by layer, first fix, and last resort (post 06). The hyphenated forms are fixed: "lost-in-the-middle" for the failure mode (the finding of Liu et al., 2023, may be written "lost in the middle" when the paper is meant), "tool-storm" with a hyphen. Poisoning is not a failure mode: it is a security term, and memory poisoning is treated in post 23.

## 5. Retrieval numbers

| Term | Meaning |
|---|---|
| top-N | the size of the candidate set that candidate generation passes to the reranker |
| top-k | the number of items kept after reranking and packed into the window |
| recall@N | the fraction of the relevant items that appear in the top-N candidates |
| precision@k | the fraction of the top-k packed items that are relevant |

N is always the candidate count and k always the packed count; a post never writes "top-k candidates" for the first stage. Concrete values are written into the name: top-50, recall@50, precision@5.

## 6. Formulas

The series carries a few formulas and no derivations. Math is inline, written `$...$`, and follows the family's typography: vectors bold lower case ($\mathbf{q}$), scalars italic lower case ($r$, $k$).

- **Recall and precision.** With $R$ the set of relevant items, $\mathrm{recall@}N = |R \cap \mathrm{top}N| / |R|$ and $\mathrm{precision@}k = |R \cap \mathrm{top}k| / k$.
- **Reciprocal rank fusion.** An item $d$ that appears in several ranked lists scores $\mathrm{RRF}(d) = \sum_i 1/(k + r_i(d))$, where $r_i(d)$ is its rank in list $i$. Here $k$ is the damping constant of Cormack et al. (2009), often 60; it is unrelated to top-k, and a post that uses both says so.
- **MaxSim.** Late interaction (ColBERT, ColPali) scores a query with token embeddings $\mathbf{q}_i$ against a document with token or patch embeddings $\mathbf{d}_j$ as $s(q, d) = \sum_i \max_j \mathbf{q}_i \cdot \mathbf{d}_j$.

## 7. Claim labels

Every price, token count, window size, latency, and percentage in a post carries one of three labels, in the sentence that uses it:

| Label | What it means | How the sentence shows it |
|---|---|---|
| cited | taken from a provider page or a paper | the source and its date are named in the sentence; the full entry is in [REFERENCES.md](REFERENCES.md) |
| measured | produced by code the reader can run | the sentence names the snippet or the companion test that prints or asserts it |
| illustrative | an example chosen to make the arithmetic concrete | the word "illustrative" appears in the sentence, caption, or table heading |

Model names, prices, and windows are stated "as of early 2026" and are expected to go stale; a post that quotes them says so. The information retention ratio of post 12 is labelled a teaching construct, not a standard metric. No number is presented as a benchmark result unless it is cited or measured.

## 8. House conventions

- **Post numbers** are two digits: "post 06", "posts 09 and 11". A cross-reference to another series uses the target's id in backticks (`mcp-001`), never a path or a URL.
- **Spelling** is British: *summarise*, *optimisation*, *tokenisation*, *behaviour*, *catalogue*, *artefact*, *labelled*, *modelling*. A quoted title and a code identifier keep their own spelling (*Organization of Memory*, `tokenizer`).
- **Acronyms** are expanded on first use in every post: retrieval-augmented generation (RAG), Model Context Protocol (MCP), key-value (KV) cache, and so on.
- **Voice** is third person and neutral: "the reader", "a team", "the agent", never "you" in body prose.
- **Punctuation:** no em or en dashes; a range is written "400 to 600 tokens".
- **Code identifiers, field names, and file names** are in code spans with their exact casing: `system`, `tools`, `messages`, `generateContent`, `AGENTS.md`.

## 9. Figure roles

Every figure in the series uses one colour per lifetime class, so that colour carries the lifetime of a layer and the written number and name carry its identity:

- **Blue (stable):** layers 01 system prompt and 02 tools and MCP descriptions, the stable prefix; anything cached or cacheable.
- **Orange (turn):** layers 03 memory and state and 04 retrieved chunks, the per-turn injection; anything assembled fresh for this call.
- **Green (history):** layer 05 conversation history, the growing tail.
- **Purple (user):** layer 06 user instruction, the trigger.
- **Red (error):** a failure, a wasted or overrun budget, the dip of a lost-in-the-middle curve, a rejected or dropped item. Red never means a layer.

The model, an operation box (write, select, compress, isolate), a vector store, a host application, and every neutral quantity are drawn in ink and neutral fills. There is no series accent colour, and no figure relies on colour alone to tell layers apart: every layer shape carries its number and name ("01 System prompt").

## 10. Checklist before publishing a post

- [ ] Every layer named by number and name, in the fixed order of Section 1.
- [ ] WSCI in the order write, select, compress, isolate; every technique in exactly one.
- [ ] The five failure modes spelled as Section 4 spells them.
- [ ] top-N and top-k, recall@N and precision@k used as Section 5 defines them.
- [ ] Every number cited, measured, or labelled illustrative (Section 7).
- [ ] Every acronym expanded on first use in this post; British spelling; no em or en dashes.
- [ ] Every relative link resolves, with forward slashes only.
