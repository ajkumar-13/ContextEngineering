# 03 - How LLMs actually read context

> **TL;DR.** A large language model (LLM) does not read its context the way a person reads a page: it splits the input into tokens, turns each token into a vector, and lets every position attend to the positions before it, all at once, before predicting the next token. Four properties of that machinery explain most of what this series does with the six layers: tokens are the unit of cost, attention has no sense of order until positions are added, models use the start and the end of a long input better than its middle, and the key-value (KV) cache lets a provider reuse the computation for an identical prefix. This post explains each, shows the measured lost-in-the-middle curve, and turns the four into a placement rule.
>
> **Prerequisites:** [Post 02](../02-six-layers-of-context/index.md).
> **Safe to skip?** Skip it if tokens, causal self-attention, rotary position embeddings, the lost-in-the-middle result and the KV cache can already be explained in a sentence each, with what they imply for where a prompt's layers go.
>
> **After reading, you will be able to:**
>
> - Explain in one sentence each what tokens, attention, positions, and the KV cache are.
> - Predict where in a long prompt a model is likely to under-use information, and place content to avoid it.
> - Decide which part of a prompt a prefix cache can reuse on the next call, and why one changed token ends the reuse.
> - Count the tokens of a string with tiktoken and explain why questions about single letters are hard for a model.
> - State what a needle-in-a-haystack score measures and what it does not.

![A line chart from Liu et al. (2023): accuracy against the position of the answer among 20 documents. GPT-3.5-Turbo falls from 75.8% at position 1 to 53.8% at position 10, below its 56.1% with no documents, and recovers to 63.2% at position 20; Claude-1.3 is flatter.](diagrams/01-lost-in-the-middle.svg)

*Measured, not sketched: the same question and the same 20 documents, with only the position of the right one changed.*

---

## 1. The question: what does a model do with the window?

Post 02 split the window into six layers, from layer 01, the system prompt, to layer 06, the user instruction, and sent the stable layers first and the user instruction last. This post asks why that order pays: which properties of tokenisation, attention, positions and the KV cache make the order, the position and the stability of a prefix change what a prompt costs and what the model recalls?

The answer needs only a small part of the transformer: the model splits the input into tokens, maps each token to a vector, runs a stack of attention layers over the sequence, and produces a probability distribution over the next token. Each step has one consequence for context engineering.

---

## 2. From characters to tokens to vectors

Before the model sees anything, a deterministic tokeniser breaks the input into **tokens**. The tokenisers of the GPT family, and of many other models, are variants of byte-pair encoding (BPE): the vocabulary is built by repeatedly merging the most frequent adjacent pair of symbols in a training corpus, so common words become single tokens and rare strings fall apart into fragments (Sennrich et al., 2016). OpenAI's "Tokenizer" page gives the rule of thumb that one token is about four characters, or three quarters of a word, of common English text; code, other languages and punctuation differ. The same string can also split differently under different vocabularies. The first practical consequence is that **counting words is not counting cost**; post 04 is about that cost.

The splits can be checked with OpenAI's tokeniser library `tiktoken`. The snippet `snippets/tokens.py` prints four strings and their pieces under the `o200k_base` encoding:

```python
import tiktoken

enc = tiktoken.get_encoding("o200k_base")  # the encoding tiktoken uses for GPT-4o

TEXTS = ["context engineering", "strawberry", " strawberry", "tokenisation"]

for text in TEXTS:
    ids = enc.encode(text)
    pieces = [enc.decode([i]) for i in ids]
    unit = "token" if len(ids) == 1 else "tokens"
    print(f"{text!r:23} {len(text):2} characters -> {len(ids)} {unit}: {pieces}")
```

It prints:

```text
'context engineering'   19 characters -> 2 tokens: ['context', ' engineering']
'strawberry'            10 characters -> 3 tokens: ['st', 'raw', 'berry']
' strawberry'           11 characters -> 1 token: [' strawberry']
'tokenisation'          12 characters -> 2 tokens: ['token', 'isation']
```

The figure below draws the same output, characters above and tokens below.

![Four strings as rows of character cells with their tokens beneath: strawberry splits into st, raw and berry; the same word after a space is one token; context engineering is two tokens; tokenisation is token and isation.](diagrams/02-tokens-not-letters.svg)

*The model receives the lower row of each pair. A leading space changes the split.*

The output explains a well-known failure. Asked how many r's are in "strawberry", chat models have been seen to answer two. The model never receives the ten characters `s-t-r-a-w-b-e-r-r-y`: at the start of a string it receives three opaque tokens, and inside a sentence, after a space, it receives one. No single letter reaches the input, so questions about characters (counting letters, reversing a string, spelling a word out) are harder for a model than they look: the difficulty lies in the input representation.

Each token is then mapped to a learned **embedding vector** of fixed width, the model's hidden dimension, which runs to thousands of dimensions in large models. Stacking the vectors of an $N$-token input gives a matrix of shape `[N, d]`. Everything the model computes is a function of that matrix and of its fixed weights: there is no separate memory it consults, and its only output is a distribution over the next token. The rows of that matrix are the **context window**, and deciding what goes into them, in what order, is context engineering.

---

## 3. Self-attention, in one paragraph

Inside each transformer layer, every token computes three projections of its vector, the **query**, the **key** and the **value**. To update its representation, a token compares its query with the keys of the tokens it may attend to (a dot product), turns the scores into weights that sum to one with a softmax, and takes the weighted sum of their values. In the decoder-only models behind today's chat application programming interfaces (APIs), a token may attend only to itself and to the tokens before it, a rule called the **causal mask**. A small feed-forward network follows; several attention heads run side by side, and a large model stacks dozens of such layers.

Three consequences are easy to miss.

**The prompt is read in parallel.** In the first pass over the prompt, called prefill, the model computes every position at once; only the answer is produced one token at a time.

**Attention looks back, never forward.** Because of the causal mask, what the model computes at a position depends only on that position and the ones before it, so text added at the end cannot change the computation for the text before it. Section 7 returns to this, because it is what makes a prefix cache possible.

**Attention is broad, but quadratic.** Every token can attend to every earlier token, which gives transformers their reach. The cost is about $N^2/2$ query-key products per head and layer for an $N$-token input, so doubling the input roughly quadruples that part of the work. A bigger window shows up as latency and as money.

---

## 4. Positions: where order comes from

Apart from the causal mask, attention carries no notion of distance or order, so transformers add a **positional encoding** that lets the model tell `"dog bites man"` from `"man bites dog"`. Many current models use rotary position embeddings (RoPE), which rotate each token's query and key by angles proportional to its position, so that the score between two tokens depends on how far apart they are (Su et al., 2021). Attention with Linear Biases (ALiBi) instead subtracts from each score a penalty that grows with the distance between the two tokens (Press et al., 2022). Long-context versions of RoPE rescale its rotation frequencies so that a model trained on shorter inputs can be extended to longer ones, usually with further training.

A model learns to use the positions it saw in training. A model trained on inputs of up to 8,192 tokens (an illustrative length) has only ever used positions 0 to 8,191; given 100,000 tokens, every position from 8,192 on is new to it, and quality there is worse the further the input goes. Vendors close this gap with continued pre-training on long inputs, position interpolation and long-context fine-tuning.

Length beyond training is one problem; position inside the trained length is another. Even well within its trained length, a model does not use every position equally well, and that is what the next section measures.

---

## 5. Lost in the middle, measured

In 2023, Liu and colleagues (Stanford University, the University of California, Berkeley and Samaya AI) asked: if a single relevant document is placed among distractors, and the model is asked a question whose answer is in that document, does it find it? They varied the number of documents (10, 20 and 30) and the position of the one holding the answer, using NaturalQuestions-Open questions with retrieved distractor passages, a set-up that mimics retrieval-augmented generation (RAG). They tested six models (MPT-30B-Instruct, LongChat-13B (16K), GPT-3.5-Turbo and its 16K version, Claude-1.3 and its 100K version), with GPT-4 and Llama-2 on smaller runs.

The result is the curve at the top of the post, drawn from the paper's Table 6 for 20 documents. Accuracy was often highest when the relevant document sat at the start or the end of the input and dropped significantly when it sat in the middle. For GPT-3.5-Turbo it fell from 75.8% with the answer in the first document to 53.8% with it in the tenth, a drop of 22.0 points, and recovered to 63.2% in the twentieth. With no documents at all, the same model scored 56.1% (Table 1): with the answer in the middle, the distractors left it worse off than having no evidence. Claude-1.3's curve is flatter, from 59.9% at the first position to 60.1% at the last with its lowest values in between. On a second task, finding the value of one key in a long list of key-value pairs, GPT-3.5-Turbo and MPT-30B-Instruct again did worst in the middle, while both Claude-1.3 versions were nearly perfect.

These inputs were short. The 20-document inputs averaged 2,946 tokens for GPT-3.5-Turbo (Table 3), inside its 4K-token window, and the extended-context versions of the models did no better on the same inputs. The dip is therefore not the out-of-range problem of section 4: it appears at positions the model was trained on.

The order of the window is part of the model's input, and it changes what gets used. Two design rules follow:

1. **Put what matters most at the start or the end.** Layer 01, the system prompt, sits at the very beginning, and layer 06, the user instruction, at the very end. Background the model should have read, but need not dwell on, can sit in the middle.
2. **Keep the middle short.** As memory, retrieved chunks and history grow, so does the middle; select or compress them ([post 09](../09-select-strategies/index.md) and [post 12](../12-compress-strategies/index.md)) before reaching for a bigger window.

---

## 6. Attention sinks

A subtler effect was documented by Xiao et al. (2023). In the attention maps of models such as Llama-2, a large share of attention goes to the first few tokens of the input, whatever those tokens are. They named these positions **attention sinks**.

The explanation is mechanical. The softmax forces the weights of every query to sum to one, so a query with nothing useful to attend to must still put its weight somewhere, and the initial tokens, visible to every later token, become the default place. The effect is about position, not content: replacing the first four tokens with line breaks kept it. The authors built StreamingLLM on it: a serving scheme that keeps the keys and values of only a window of recent tokens collapses once the first tokens fall out of the window, while keeping four initial tokens beside the window keeps the model stable over streams of millions of tokens without fine-tuning. The window still forgets; StreamingLLM keeps a model fluent, but does not let it use text that has left the window.

Two consequences matter for an application engineer. A large attention weight is not evidence of importance: an attention map that lights up the first tokens shows the sink, not the influence of the opening words. And deleting the opening words of a prompt does not remove the sink, because whatever comes first takes its place. Keeping sink tokens in a sliding-window cache is the serving stack's job, which hosted APIs do not expose.

---

## 7. The KV cache, and why prefix caching exists

Every token computes a key and a value at every layer. During generation the model produces tokens one at a time, and without help each new token would require the keys and values of the whole sequence to be computed again.

Serving stacks avoid this with a **KV cache**: two tensors, for keys and for values, each of shape `[layers, heads, N, d_head]`. For the next token the model computes that one token's query, key and value, appends the key and value to the cache, and attends over the cache, so the work per new token grows with the length of the sequence instead of its square. Prefill computes the cache for the whole prompt, which is why a long prompt delays the first output token.

That is the cache within one request. What matters for context engineering is its use across requests: **prompt caching**, also called prefix caching. Because of the causal mask, the keys and values of the first $k$ tokens depend only on those $k$ tokens, so if a second call starts with exactly the same $k$ tokens, the provider can reuse them. Anthropic's "Prompt caching" documentation, as consulted in October 2026, requires the cached segments to be 100% identical up to the block marked for caching, bills a cache read at 0.1 times the base input price for most models, keeps an entry for five minutes by default (refreshed on each read, with a one-hour option at a higher write price), and sets a minimum cacheable length of 512 to 4,096 tokens depending on the model. Other providers offer similar caches on different terms; [post 05](../05-economics-of-context/index.md) prices them.

The rule can be checked on a small example. The snippet `snippets/prefix_reuse.py` tokenises two consecutive calls of a support assistant, layer by layer in the series' order, under two layouts, and counts how much of call 2 a cache with its breakpoint after layer 02 could reuse. Its core counts identical leading tokens:

```python
def shared_prefix(a: list[int], b: list[int]) -> int:
    """The number of leading tokens two token sequences have in common."""
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return n
```

Layout A keeps the stable layers first; layout B writes the time of the call at the top of the system prompt. It prints:

```text
layout A: stable layers first
  call 2: 166 tokens; layers 01 and 02: 99 tokens
  leading tokens identical to call 1: 109
  breakpoint after layer 02: 99 read from the cache, 67 computed
layout B: time of the call in the system prompt
  call 2: 176 tokens; layers 01 and 02: 109 tokens
  leading tokens identical to call 1: 6
  breakpoint after layer 02: 0 read from the cache, 176 computed
```

The prompts are far below any provider's minimum cacheable length, so the counts show the rule rather than a bill. The figure below draws both layouts to scale.

![Two panels of two consecutive calls as strips of the six layers, widths to scale. In layout A, 99 tokens of layers 01 and 02 are read from the cache and 67 are computed; in layout B only the first 6 tokens match and all 176 are computed.](diagrams/03-prefix-reuse.svg)

*In layout A the calls agree for ten tokens past layer 02, but the breakpoint sits at the end of layer 02, so those ten are computed anyway.*

Three rules follow and recur in production:

- **Caches are prefix-keyed.** A change at any point invalidates everything after it, because every later key and value was computed with the changed token in view. Layer 01, the system prompt, and layer 02, tools and Model Context Protocol (MCP) descriptions, belong at the front.
- **Caches are exact.** A timestamp, a request id or a "today is" line at the top of the system prompt makes every call a miss, as layout B shows. Volatile content goes after the cacheable prefix.
- **Caches expire.** An entry not read within its lifetime is dropped: steady traffic keeps a prefix warm, while a call every ten minutes may pay the full input price, and the write premium, every time. Post 05 works through that trade-off.

---

## 8. Needle-in-a-haystack, and what it does and does not measure

The needle-in-a-haystack (NIAH) test hides one sentence, the needle, in a long document, the haystack, asks the model to retrieve it, and reports accuracy for each document length and needle depth. Greg Kamradt's open harness popularised it in 2023, and model announcements have since reported near-perfect needle recall at hundreds of thousands of tokens and more. Such a result shows one narrow ability, for two reasons.

First, **a needle test measures recall, not reasoning.** Finding one planted fact is about the easiest thing a long-context model can be asked to do. It does not show whether the model can combine facts spread across the haystack, notice that two contradict each other, or use what it found to answer a harder question. RULER (Hsieh et al., 2024) adds multi-needle retrieval, tracing, aggregation and question answering, and reports that almost all of the models it evaluated, despite nearly perfect plain needle scores, drop sharply as the context grows. Chroma's "Context Rot" study (Hong et al., 2025) finds performance degrading with input length, unevenly, even on tasks the same models handle easily when the input is short.

Second, **a needle test is sensitive to position.** The harness varies the needle's depth as well as the length for this reason, and a good result at one depth does not carry over to another; the needle chart and the U-curve of section 5 come from related effects.

The operational rule is to trust an evaluation of the application's own task at its own context length, not a vendor's needle chart. [Post 20](../20-evaluation/index.md) covers evaluation design.

---

## 9. Putting it together: a placement heuristic

The four mechanics (tokens, attention, position and the cache) converge on one placement rule that the rest of the series assumes. Mapped onto the six layers:

| Where in the window | Layers | Why |
|---|---|---|
| Front | layer 01, the system prompt; layer 02, tools and MCP descriptions | Identical on every call, so a prefix cache can reuse them; the start is one of the two best-used positions |
| Middle | layer 03, memory and state; layer 04, retrieved chunks; layer 05, conversation history | Assembled or grown on every call, so not part of a stable prefix; the least-used region, so keep it short and put the strongest evidence at its edges |
| End | layer 06, the user instruction | New on every call, so last keeps the reusable prefix long; the end is the other best-used position |

The heuristic explains why the order of post 02 is the order the machinery rewards. Inside layer 04 the same logic gives the bookend layout of [post 09](../09-select-strategies/index.md): the strongest chunk first and the second strongest last.

---

## 10. Make it run

Both snippets run from the series root with the root environment, which provides `tiktoken`:

```text
uv run python posts/03-how-llms-read-context/snippets/tokens.py
uv run python posts/03-how-llms-read-context/snippets/prefix_reuse.py
```

Each finishes in about a second, prints the output quoted in sections 2 and 7, and calls no model. The first use of an encoding downloads its vocabulary file once, and `tiktoken` caches it for offline runs. Adding a page of code or a paragraph in another language to `TEXTS` shows how far the four-characters rule holds; passing a system prompt that differs from `SYSTEM` by one character as the third argument of the first `report` call in `prefix_reuse.py` shows the reuse dropping to zero.

The position effect needs a live model: a fact placed at the end of a prompt of about 20,000 tokens (an illustrative length), then moved to the middle with the same question, shows whether the model in use still finds it.

---

## 11. What can go wrong?

- **A timestamp lands in the system prompt.** The current time is formatted into layer 01 "so the model knows". Answers look fine, but every response reports no cache reads (`cache_read_input_tokens` stays at 0 on Anthropic) and the cost per call never falls. Moving the time into layer 06, or rounding it to the date, restores the prefix.
- **The best evidence is buried in the middle.** Retrieved chunks are pasted in rank order after a long history, thousands of tokens from either end. The answer misses a fact that is visibly in the prompt, and retrieval is blamed although the chunk was retrieved and packed.
- **The window is filled because it is there.** A model with a very long window and a perfect needle chart is given whole document sets instead of selected chunks. Answers that need two or three facts combined get worse, and each call is slower and dearer.
- **Token counts are guessed from words.** A budget of "about 3,000 words" is set for a prompt full of JSON (JavaScript Object Notation) and code. The real token count is far above what the four-characters rule predicts for prose, and the prompt is truncated or rejected on the longest inputs only.
- **A heavy attention weight is read as importance.** An attention visualisation shows the first tokens lit up, and the opening words are rewritten to steer the model. The weight was the attention sink; the rewrite changes nothing except the cache.

---

## Common pitfalls

1. **Ranking retrieved chunks best to worst, top to bottom.** The end of the input is the other well-used position, so put the best chunk first and the second best last (the bookend layout).
2. **Putting the user's question at the top.** It goes last; repeating it before the evidence as well is a reasonable extra, though Liu et al. found that a query at both ends nearly solved the key-value task while changing little on multi-document question answering.
3. **Editing the system prompt on every deployment.** Every edit ends the reusable prefix for every call that shared it; treat the stable prefix as a versioned artefact.
4. **Reading a needle chart as reasoning quality at that length.** It shows recall of one planted fact; evaluate the application's own task at its own length.
5. **Assuming a long window removes the middle.** Liu et al. measured the dip in inputs of about 3,000 tokens; a larger window gives a longer middle, not a shorter one.

---

## Further reading

- Liu, N. F. *et al.*, *"Lost in the Middle: How Language Models Use Long Contexts"* (arXiv 2023, TACL 2024): section 5; Tables 1, 3 and 6 hold the numbers it quotes.
- Xiao, G. *et al.*, *"Efficient Streaming Language Models with Attention Sinks"* (2023): attention sinks and StreamingLLM.
- Su, J. *et al.*, *"RoFormer: Enhanced Transformer with Rotary Position Embedding"* (2021): RoPE.
- Press, O. *et al.*, *"Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation"* (2022): ALiBi.
- Sennrich, R. *et al.*, *"Neural Machine Translation of Rare Words with Subword Units"* (2016): byte-pair encoding.
- OpenAI, *"Tokenizer"* and the `tiktoken` library: the tokeniser of section 2.
- Anthropic, *"Prompt caching"* documentation: the cache rules of section 7.
- Kamradt, G., *"Needle In A Haystack: Pressure Testing LLMs"* (2023): the harness that popularised the needle test.
- Hsieh, C.-P. *et al.*, *"RULER: What's the Real Context Size of Your Long-Context Language Models?"* (2024): needle tests extended to harder tasks.
- Hong, K. *et al.*, *"Context Rot: How Increasing Input Tokens Impacts LLM Performance"* (Chroma, 2025): degradation with input length.

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 04 - Tokens, windows, and budgets](../04-tokens-windows-budgets/index.md):** turns tokens and the window into budgets that can be estimated before a call is made.
- **[Post 25 - Long context vs. RAG: a decision framework](../25-long-context-vs-rag/index.md):** uses the needle results, and the benchmarks that go past them, to decide when to load a whole corpus and when to retrieve.
