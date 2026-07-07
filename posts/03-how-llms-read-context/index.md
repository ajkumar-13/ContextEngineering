# 03 · How LLMs actually read context

> **TL;DR.** A large language model does not "read" its context the way a human reads a document. It tokenises the whole input into a single long vector sequence, runs **self-attention** over it in parallel, and produces one next-token distribution. Three properties of this machinery (positional bias, attention sinks, and the KV-cache) explain almost every counter-intuitive thing the rest of this series will talk about: why ordering matters, why the middle of a long context is forgotten, why repeating yourself sometimes helps, and why your bill drops by 10× the moment your prefix stops changing.
>
> **After reading this you will be able to:**
> - Explain in one sentence each what tokens, attention, positions, and the KV-cache are.
> - Predict where in a long prompt a model will under-attend, and design around it.
> - Reason about which parts of a prompt are cacheable and which are not.

![Lost-in-the-middle U-curve](../03-how-llms-read-context/diagrams/03-lost-in-the-middle.svg)

*Recall as a function of where a fact sits in a long context: a U-curve, high at the start and end, sagging in the deep middle (Liu et al., 2023).*

---

## 1. From characters to vectors

Before the model sees anything, the input string is broken into **tokens** by a deterministic tokeniser, almost always a byte-pair encoding (BPE) variant, where BPE means the tokeniser greedily merges the most frequent adjacent character pairs into a fixed vocabulary. As a rough heuristic, a token is about three quarters of an English word (roughly four characters), though the exact ratio depends on language, code, and punctuation (OpenAI, "Tokenizer", 2024). Tokenisation is also tokeniser-specific: the same string can split into a different number of tokens under different vocabularies. Under OpenAI's `o200k_base` encoding, for example, `"context engineering"` is two tokens (`context`, ` engineering`), while a word absent from the vocabulary is broken into fragments. The first practical consequence is that **counting words is not counting cost**. The next post is dedicated to this; for the rest of *this* post, treat tokens as the atomic unit.

You can check any of this yourself with the tokeniser library `tiktoken`:

```python
import tiktoken

enc = tiktoken.get_encoding("o200k_base")  # the GPT-4-class vocabulary
for word in ["context engineering", "strawberry", "tokenisation"]:
    ids = enc.encode(word)
    print(word, "->", len(ids), "tokens:", [enc.decode([i]) for i in ids])

# context engineering -> 2 tokens: ['context', ' engineering']
# strawberry          -> 3 tokens: ['st', 'raw', 'berry']
# tokenisation        -> 2 tokens: ['token', 'isation']  (counts are vocabulary-dependent)
```

This snippet also explains a famous failure. Asked how many R's are in "strawberry", models often answer "two". The reason is right here: the word is not stored as the ten characters `s-t-r-a-w-b-e-r-r-y` but as three opaque tokens (`st`, `raw`, `berry`). The model never sees the individual letters, so character-level questions (counting letters, reversing a string, spelling out a word) are structurally hard for it. This is a limit of the input representation, not of reasoning, and it is the cleanest illustration of why tokens, not words or characters, are the unit that matters.

Each token is then mapped to a learned **embedding vector** whose width (the model's hidden dimension) is a fixed architectural choice, on the order of a few thousand dimensions for frontier models, though vendors rarely publish the exact figure. Stack the embeddings for an *N*-token input and you get a matrix of shape `[N, d]`. Everything the model does internally is a function of that matrix and the (very large) parameter tensors of the network. There is no separate "memory" the model consults; its only input is this matrix, and its only output is a distribution over the next token.

That single fact is the whole reason this series exists. The matrix is the **context window**. Engineering the rows of that matrix (what goes in, in what order, with what neighbours) is context engineering.

---

## 2. Self-attention, in one paragraph

Inside each transformer layer, every token computes three projections of its embedding called the **query**, **key**, and **value**. To produce its updated representation, the token compares its query against the keys of every other token in the context (a dot product), softmaxes the scores into weights, and takes a weighted sum of the values. The output is then passed through a small feed-forward network and added back to the token's representation. Stack many such layers, on the order of a few dozen to roughly a hundred in a typical frontier model, and you have a modern LLM.

Two things follow from this design that are easy to miss.

**Attention is parallel, not sequential.** The model does not "read left to right". It sees all *N* tokens at once on every layer. There is no notion of "earlier" or "later" baked into the math itself.

**Attention is global, but quadratic.** Every token can in principle attend to every other token, which is what gives transformers their reach. But the cost grows as $O(N^2)$ in the number of tokens. Doubling the context quadruples the attention compute. This is why "just make the window bigger" is never a free move; it shows up as latency and as money.

---

## 3. Positions: where order comes from

Because attention itself is order-blind, transformers add a **positional encoding** so the model can tell `"dog bites man"` from `"man bites dog"`. Modern models use *rotary position embeddings* (RoPE), which rotate each token's query and key vectors by an angle proportional to its position, or one of several long-context variants of the same idea. These variants stretch a model trained on short inputs to longer ones: ALiBi (Attention with Linear Biases) adds a distance-based penalty instead of rotating; NTK-aware RoPE rescales RoPE's rotation frequencies so nearby positions stay distinguishable; and YaRN (Yet another RoPE extensioN) refines that rescaling with a fine-tuning step. The exact scheme is not important here; what matters is the consequence.

Positional encodings are **learned in the regime they were trained on**. A model trained on inputs up to 8 k tokens has only ever seen position vectors for indices 0–8 191. When you feed it 100 k tokens at inference time, even if the architecture nominally allows it, the position vectors at indices 50 000+ are *extrapolated*. The model has never seen tokens at those positions during training. Quality at those positions is, on average, worse, and degrades as you push further out of distribution.

Vendors close this gap with continued pre-training, position-interpolation tricks, and long-context fine-tuning. The result is impressive but never perfect. The empirical consequence is a U-curve: information at the very start and very end is recovered well; information in the deep middle of a long context is recovered poorly. This is the **lost-in-the-middle** phenomenon, and it has its own paper.

---

## 4. Lost in the middle, measured

In 2023 Liu and colleagues at Stanford asked a deceptively simple question: if you put a single relevant document somewhere inside a long context full of distractors, and then ask a question whose answer is in that document, does the model find it? They varied two things: the total context length (10–30 documents) and the position of the relevant document (1st, 2nd, …, last). They tested every model they could get their hands on, open and proprietary.

The result is the U-shape you see in the figure above. Across every model, accuracy was highest when the relevant document sat at position 1 or at the last position, and lowest when it sat near the middle. The drop was not small; for some models, accuracy at the middle was below the *no-document* baseline, meaning the distractors were actively misleading the model.

The paper has been cited several thousand times because the implication is so practical. The order of your context is not a stylistic choice; it is part of the model's input distribution, and it directly determines what gets used. A 100 k-token context where the answer sits at token 50 000 may be functionally equivalent to a 5 k-token context where the answer is missing.

The two design rules that fall out of this are:

1. **Put the most important content at the start or the end.** The system prompt sits at the very beginning. The user's current question sits at the very end. Background facts that the model should "have read" but does not need to actively reason over can live in the middle.
2. **Compress the middle.** If your retrieval, history, or memory layers grow past a few tens of thousands of tokens, reach for compression ([Posts 12](../12-compress-strategies/index.md) and [16](../16-memory-systems/index.md)) before you reach for a bigger window.

---

## 5. Attention sinks

A second, subtler phenomenon was documented by Xiao et al. (2023): when researchers visualised the attention patterns of a streaming language model, they discovered that an enormous fraction of attention weight was being spent on **the first one to four tokens**, regardless of what those tokens were. Removing those tokens, even though they carried no semantic content, destroyed the model.

The explanation is mechanical. Softmax forces the attention weights from any given query to sum to one. When a later token has nothing useful to attend to, it must still spend its budget *somewhere*. Early tokens, present in every attention computation since they appeared, become a default sink for that "leftover" attention. The authors named these positions **attention sinks** and showed that explicitly preserving them (the StreamingLLM trick) lets a model handle inputs longer than it was trained on without quality collapse.

The practical takeaway for an application engineer is small but real: **never strip the first few tokens of your prompt as a "compression" trick**. They look uninformative but the model is using them as scaffolding. The same principle is one reason providers warn against editing the cached prefix of a prompt; you are removing the model's anchor, not just saving tokens.

---

## 6. The KV-cache, and why prefix caching exists

Recall that for every token the model computes a key vector and a value vector at every layer. During *generation*, the model produces tokens one at a time. Naively, every new token would force the model to recompute keys and values for the entire prompt all over again; the cost would be quadratic in the output length.

In practice, every serving stack stores those keys and values in a **KV-cache**: a tensor of shape `[layers, heads, N, d_head]` keyed by the input token sequence. When the next token is generated, the model only needs to compute one new query, one new key, and one new value, then attend over the cache. Generation becomes linear in output length instead of quadratic.

That is the *intra-request* KV-cache (KV stands for the *keys* and *values* it stores). The interesting part for context engineering is its *inter-request* cousin: **prompt caching**, sometimes called prefix caching. If two API calls share the same first *k* tokens, byte-for-byte, the provider can reuse the KV-cache it computed for those tokens on the previous call. You are billed at a heavily discounted rate on the reused prefix, and latency drops correspondingly. The size of the discount is vendor-specific: Anthropic bills a cache read at roughly a tenth of the base input price, about ten times cheaper (Anthropic, "Prompt caching with Claude", 2024), whereas OpenAI's automatic prompt caching discounts cached input by about half. **[Post 04](../04-tokens-windows-budgets/index.md)** owns the exact pricing; treat these as the shape, not the last word.

![How a stable prefix turns into a cache hit](./diagrams/01-kv-cache-reuse.svg)

*A byte-identical prefix (system prompt plus tool schemas) is served from the cache; only the changing tail is recomputed.*

The mechanics dictate three rules that come up over and over again in production:

- **Caches are prefix-keyed.** If you change byte zero of the prompt, every later byte is invalidated. Stable layers (system prompt, tool schemas) belong at the front.
- **Caches are byte-identical.** A timestamp, a UUID, or a freshly-formatted "today is …" line at the top of your system prompt is enough to make every call a cache miss. Move volatile content past the cacheable prefix.
- **Caches expire.** TTLs vary by vendor: Anthropic's default is five minutes of inactivity, with an optional one-hour tier (Anthropic, "Prompt caching with Claude", 2024). High-throughput agents naturally hit warm caches; low-traffic side projects rarely do. [Post 25](../25-long-context-vs-rag/index.md) quantifies the trade-off.

---

## 7. Needle-in-a-haystack, and what it does and does not measure

Vendors love to publish "needle-in-a-haystack" (NIAH) results: hide a single sentence (the *needle*) inside a very long document (the *haystack*), ask the model to retrieve it, and report accuracy. The test was popularised by Greg Kamradt's open harness (Kamradt, "Needle In A Haystack", 2023), and vendors now routinely report near-ceiling recall on it at context lengths in the hundreds of thousands to low millions of tokens. Take those headline numbers as evidence of one narrow ability, not general long-context competence, for the reasons below.

Two things are important to keep in mind when reading these charts.

First, **needle tests measure recall, not reasoning.** Finding a single planted fact is the easiest thing a long-context model can be asked to do. It does not measure whether the model can *combine* facts spread across the haystack, *notice contradictions*, or *use* the recovered information to answer a non-trivial question. Independent benchmarks (RULER, LongBench, BABILong) routinely show large drops in performance the moment the task moves from "find the fact" to "use the facts", and Chroma's "Context Rot" study (Chroma, 2025) documents accuracy sagging steadily as input length grows even on tasks the model handles easily when they are short.

Second, **needle tests are also sensitive to position**. If you re-run the same haystack with the needle at the 50 % mark instead of 95 %, accuracy almost always drops. The needle plot and the U-curve are two views of the same phenomenon.

The operational rule: trust your own evals at your own context length, not the vendor's needle chart. [Post 20](../20-evaluation/index.md) covers eval design.

---

## 8. Putting it together: a placement heuristic

The four mechanics above (attention, position, sinks, and the cache) converge on a single placement strategy that the rest of this series will assume.

![Placement heuristic at a glance](./diagrams/02-attention-bias-bar.svg)

*Effective attention by position: high at the front (cached, sink-anchored) and the end (the live question), low through the middle.*

Read the figure as a histogram of **how much the model effectively uses content as a function of where you put it**. The two ends are well attended and well cached (if stable). The middle is where information goes to be forgotten. So:

| Where in the prompt | What belongs there | Why |
|---|---|---|
| Front (cached prefix) | System prompt, tool schemas, immutable knowledge | Cache-friendly, attention-rich, anchors the sinks |
| Middle | Long retrieved documents, conversation history, anything the model should "have read" | Cheap, but recall is weak; compress aggressively |
| End | Memory, *just-in-time* facts, the current user question | Highest recall, near-perfect attention |

There is nothing magical about three buckets. Real prompts have many more layers ([Post 02](../02-six-layers-of-context/index.md)) and many more sub-decisions. But the heuristic explains why the standard ordering (system → tools → memory → retrieval → history → user) keeps reappearing across frameworks built by people who do not talk to each other. It is the order the machinery rewards.

---

## Common pitfalls

- **Ranking retrieval results best-to-worst, top-to-bottom.** The model attends best to the top *and* bottom. A common improvement is to put the top-ranked chunk first and the second-best chunk last, the so-called *bookend* layout.
- **Putting the user's question at the top.** It is the highest-priority message; it goes *last*. Repeating it at both the top and the bottom is a fine tactic, and it is what tools like Claude Code do internally.
- **Stuffing a timestamp into the system prompt.** Now the cached prefix changes every minute. Move time-of-day into the user turn or pin it to a coarse bucket (e.g., date only).
- **Believing the vendor's needle chart implies reasoning quality at that length.** It only implies recall of a single planted fact. Always run a domain eval at the length you actually use.
- **Stripping the first few "useless" tokens to save space.** Those are attention sinks. Compress the middle, not the head.
- **Editing a system prompt every deployment "to keep it fresh".** Every edit invalidates the cache for every user, everywhere. Treat the cached prefix the way a database team treats a primary index.

---

## Further reading

- Liu, N. F. *et al.*, *"Lost in the Middle: How Language Models Use Long Contexts"* (2023): the source paper for the U-curve.
- Xiao, G. *et al.*, *"Efficient Streaming Language Models with Attention Sinks"* (2023): the StreamingLLM paper that named attention sinks.
- Su, J. *et al.*, *"RoFormer: Enhanced Transformer with Rotary Position Embedding"* (2021): RoPE, the dominant positional scheme.
- Anthropic Engineering, *"Prompt caching with Claude"* (2024): the canonical write-up of prefix caching, with pricing and TTL tiers.
- OpenAI, *"Tokenizer"* and the `tiktoken` library (2024): the tokeniser behind the token-count examples in §1.
- Kamradt, G., *"Needle In A Haystack — Pressure Testing LLMs"* (2023): the open harness that popularised the NIAH test.
- Chroma, *"Context Rot: How Increasing Input Tokens Impacts LLM Performance"* (2025): degradation with length beyond simple recall.
- Hsieh, C-P. *et al.*, *"RULER: What's the Real Context Size of Your Long-Context Language Models?"* (2024): needle-test critique.
- Press, O. *et al.*, *"Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation"* (2022): ALiBi, the long-context alternative to RoPE.

Full citations in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 04 — Tokens, windows, and budgets](../04-tokens-windows-budgets/index.md)**: turns the mechanics in this post into numbers you can plan around.
- **[Post 06 — Five context failure modes](../06-context-failure-modes/index.md)**: what happens when the placement rules above are violated.
- **[Post 25 — Long context vs RAG](../25-long-context-vs-rag/index.md)**: when the production economics tip toward RAG instead of stuffing.
