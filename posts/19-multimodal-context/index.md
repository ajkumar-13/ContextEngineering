# 19 - Multimodal context: images, PDF pages, and audio

> **TL;DR.** Screenshots, rendered portable document format (PDF) pages, charts and audio enter the same context window as text, as tokens counted by a rule the provider publishes: on Anthropic's application programming interface (API) an image costs one token per 28 by 28 pixel patch, up to a cap, so an A4 page scanned at 130 dots per inch costs 1,551 tokens on the standard tier. This post counts those tokens, decides per page whether a document goes in as pixels or as extracted text, compares visual retrieval (ColPali) with optical character recognition (OCR) followed by text retrieval-augmented generation (RAG), and places images so that stable ones cache and live ones do not break the cache.
>
> **Prerequisites:** [Post 03](../03-how-llms-read-context/index.md), [Post 04](../04-tokens-windows-budgets/index.md).
> **Safe to skip?** Skip it if the token cost of an image of a given size can already be worked out, and the choice between page images and extracted text, and where a screenshot goes in a cached request, are already settled.
>
> **After reading, you will be able to:**
>
> - Estimate how many tokens an image or a rendered page adds to a call from its pixel size, with the provider's published patch or tile rule.
> - Decide, per document or per page, whether to send pixels or extracted text, from whether the layout carries meaning and what each route costs.
> - Choose between visual retrieval and OCR-then-text RAG for a page-image corpus, and name what each keeps, loses and costs.
> - Lay out a multimodal request so that stable images stay in the cached prefix and per-turn screenshots are downscaled, sent last and pruned in batches.

![The six layers of post 04's support agent as dashed bars of illustrative size, and an A4 page at 130 dpi, resized to 924 by 1,307 pixels and cut into 33 by 47 patches, 1,551 tokens, carried by an arrow into layer 04 as a solid segment after its 2,500 tokens of text. The input grows from 10,500 to 12,051 tokens.](diagrams/01-page-in-the-window.svg)

*The page is priced and budgeted like the text around it: same window, same rate per token.*

---

## 1. The question: how do pixels and sound share a window built for words?

Every earlier post treated the context window as a place for words. A vision-language model, a large language model (LLM) that also reads images, accepts images in the same request as text. A computer-use agent sees a screenshot on every turn; a document assistant is handed a scanned invoice. Each image lands in the same window as the text, competes for the same budget, and is read through the attention mechanism of [post 03](../03-how-llms-read-context/index.md).

The six layers of [post 02](../02-six-layers-of-context/index.md) do not change. An image travels in the layer whose job it does: a page image that retrieval returns for this turn is layer 04, retrieved chunks; an image attached to the current request is part of layer 06, the user instruction; a screenshot from an earlier turn of an agent is part of layer 05, conversation history. What changes is the arithmetic. A paragraph and a full-page screenshot look nothing alike, yet both become tokens, and the screenshot can cost more than the paragraph, so a budget built on text alone ([post 04](../04-tokens-windows-budgets/index.md)) is wrong the moment images arrive.

The figure at the top of the post shows the change: one retrieved page image adds 1,551 tokens to post 04's illustrative 10,500. The question is how that number is worked out, when a document should go in as pixels rather than text, and how images meet retrieval, the budget and the cache.

---

## 2. How images consume the window

A vision-language model cuts an image into small square patches and encodes each into a vector that enters the input beside the text tokens. Anthropic's "Vision" documentation (consulted October 2026) states the rule its API bills by: each patch is a 28 by 28 pixel block, a visual token, so an image of $w$ by $h$ pixels costs $\lceil w/28 \rceil \times \lceil h/28 \rceil$ tokens, priced at the model's input rate like any other.

The count is capped. The same page gives each model a long-edge limit and a visual-token limit: 1,568 pixels and 1,568 tokens on the standard tier, which covers this series' running models (Claude Opus 4.6, Claude Sonnet 4.5 and Claude Haiku 4.5, as of early 2026), and 2,576 pixels and 4,784 tokens on the high-resolution tier of Claude 4.7 and later models. An image over either limit is downscaled before it is read, to the largest size with the same aspect ratio that meets both; Anthropic's "Coordinates and bounding boxes" page gives the rule and a reference implementation. Its example is an A4 page scanned at 130 dots per inch (dpi), 1,075 by 1,520 pixels: both sides are under 1,568, but the page would cost $39 \times 55 = 2{,}145$ tokens, so on the standard tier it is resized to 924 by 1,307.

Other providers publish other rules. OpenAI's "Images and vision" guide (consulted October 2026) charges some models, GPT-4o, GPT-4.1 and GPT-5.1 among them, a base amount plus a fixed amount per 512-pixel tile after scaling (85 and 170 tokens for GPT-4o), and has others count 32-pixel patches times a per-model factor. Either way, tokens grow with the pixel area, up to a cap that depends on the model.

`snippets/image_tokens.py` implements Anthropic's rule with the standard library and first checks itself against the six example sizes of the "Vision" page and the A4 example. Its core:

```python
def visual_tokens(width, height):
    """One visual token per 28 x 28 patch, rounding each side up."""
    return math.ceil(width / PATCH) * math.ceil(height / PATCH)


def fits(width, height, max_edge, max_tokens):
    return (math.ceil(width / PATCH) * PATCH <= max_edge
            and math.ceil(height / PATCH) * PATCH <= max_edge
            and visual_tokens(width, height) <= max_tokens)
```

Run from the series root as `uv run python posts/19-multimodal-context/snippets/image_tokens.py`, it prints, for one A4 page at three resolutions:

```text
one A4 page sent as an image
   72 dpi, 595x842: standard 595x842 = 682 tokens; high-res 595x842 = 682 tokens
  130 dpi, 1075x1520: standard 924x1307 = 1551 tokens; high-res 1075x1520 = 2145 tokens
  300 dpi, 2480x3508: standard 924x1307 = 1551 tokens; high-res 1623x2296 = 4756 tokens
```

The figure below draws these numbers. Below the cap, tokens track the pixel area: halving each side roughly quarters the patches. At the cap the growth stops. On the standard tier a 300-dpi scan costs exactly what the 130-dpi scan costs, because both are shrunk to 924 by 1,307 pixels before the model sees them: the extra pixels buy nothing, and fine print that needed them is lost. On the high-resolution tier the same scan costs 4,756 tokens, three times as many.

![Two bar charts of the tokens of one A4 page on a shared axis. Standard tier, cap 1,568: 72 dpi 682, 130 dpi 1,551, 300 dpi 1,551. High-resolution tier, cap 4,784: 72 dpi 682, 130 dpi 2,145, 300 dpi 4,756.](diagrams/02-tokens-by-resolution.svg)

*Past the cap the page is shrunk before it is read: the extra pixels are neither paid for nor seen.*

The money follows the tokens. At Claude Opus 4.6's input rate of 5 dollars per million tokens (Anthropic, "Pricing", as of early 2026, as [post 05](../05-economics-of-context/index.md) quotes it), 1,000 pages at 130 dpi cost $1{,}551{,}000 \times 5 / 10^6 = 7.755$ dollars of input; the snippet prints the same.

The budget is where images hurt first. Anthropic's "Computer use tool" documentation (consulted October 2026) says long agent loops accumulate screenshots quickly, at roughly 1,000 to 1,800 input tokens each. A 1,280 by 800 screenshot, a size that page recommends, costs 1,334 tokens; an agent keeping every screenshot carries 26,680 tokens of pixels after 20 turns (an illustrative session), against 4,002 if it keeps the last three. Hence the habit to **resize on purpose**: decide the resolution the task needs and downscale to it in the application, rather than pay for detail nothing reads or let the API shrink the image to a size nobody chose.

---

## 3. PDF pages: pixels or extracted text

A PDF page can enter the window as an **image** of the rendered page or as **text** extracted from it, from the PDF's own text layer or by OCR when there is none. This is the multimodal side of the parsing decisions of [post 10](../10-data-ingestion-pipelines/index.md), section 3.

Providers handle a whole PDF differently. Anthropic's "PDF support" documentation (consulted October 2026) says each page is converted into an image and the page's extracted text is provided alongside it, so a PDF document block pays for both: text at typically 1,500 to 3,000 tokens per page, plus each page's image at the vision rule. Google's Gemini "Document understanding" page (last updated 8 October 2026) states that each document page is equivalent to 258 tokens and for Gemini 3 models, does not charge for the PDF's extracted native text. An application that renders and extracts pages itself decides page by page instead.

**Pass pixels when layout carries meaning.** A page image keeps tables, columns, figures, stamps, handwriting, checkboxes and which value sits beside which label, and a vision model reads them directly, at a token cost paid again on every call that includes the page. Pixels suit forms, invoices, figure-dense papers, complex tables and scans with no reliable text layer.

**Extract text when the words are the content.** For prose, a contract clause or a plain report, extracted text carries the same information in a form the pipeline of [post 09](../09-select-strategies/index.md) can chunk, embed and retrieve. Whether it is also fewer tokens depends on the page: the snippet's illustrative prose page of 600 words is 800 tokens as text, by post 04's rule of three quarters of a word per token, against 1,551 as a 130-dpi image, but a dense page at the top of Anthropic's 1,500 to 3,000 range costs more as text than as a standard-tier image.

The failure to avoid is one method for the whole corpus. A filing might be prose for forty pages and tables for ten; routing per page pays the pixel price only where layout matters. The snippet prices that filing with the sizes above:

```text
page as text 800 tokens, as pixels 1551 tokens
50-page filing (40 prose, 10 tables): all text 40000, all pixels 77550, routed per page 47510, text and image of every page 117550
scanned invoice, no text layer: pixels
```

All text is cheapest and flattens the ten tables into runs of numbers (post 10, section 4). Routing per page keeps the tables for 7,510 tokens more than all text and 30,040 fewer than all pixels. Both forms of every page, as Anthropic's PDF document block sends them, cost the most and earn it only when the questions need the words and the layout of every page.

A silent OCR error ("rn" read as "m", a dropped decimal point) becomes a confidently wrong answer downstream, so post 10's advice holds: measure character accuracy on a sample first. A vision model makes its own errors (Anthropic's vision page names low-quality, rotated and very small images), so neither route is exempt from checking.

---

## 4. Multimodal retrieval: ColPali against OCR-then-text RAG

Over a corpus of page images, retrieval faces the choice of section 3 again. The traditional path is **OCR-then-text RAG**: run OCR over every page, chunk and embed the text, and retrieve with the hybrid pipeline of [post 11](../11-rag-in-depth/index.md). It works, but it inherits every OCR error and throws away what the layout encoded: a chart becomes at best a caption, a table a run of numbers, a figure nothing.

The alternative is **visual retrieval**: embed the page image and retrieve on the pixels, with no OCR step. The reference technique is **ColPali** (Faysse et al., "ColPali: Efficient Document Retrieval with Vision Language Models", 2024, published at the International Conference on Learning Representations, ICLR 2025), which applies the late-interaction idea that [post 17](../17-advanced-retrieval/index.md) covers for ColBERT to image patches instead of text tokens. ColPali keeps one vector per image patch, embeds the query tokens, and scores a page with MaxSim: for each query token the highest similarity to any patch, summed over the query, $s(q, d) = \sum_i \max_j \mathbf{q}_i \cdot \mathbf{d}_j$. Because it never runs OCR, it can match a question about a bar chart to the page that holds the chart, which text retrieval cannot do when the chart was never text.

![Two pipelines. OCR then text RAG: page image, OCR and parse, where layout and charts are lost and misread characters enter, chunk, embed and score, top-k chunks into layer 04. ColPali: page image, embed the patches with no OCR, MaxSim, top-k pages into layer 04. Cited values: average nDCG@5 66.1 against 81.3; 8.60 KB a vector against 257.5 KB a page.](diagrams/03-ocr-vs-visual-retrieval.svg)

*The visual route keeps the layout that OCR drops, and pays for it in index size.*

The paper measures both routes on ViDoRe, a benchmark of ten page-retrieval tasks it introduces. In its Table 2 the average normalised discounted cumulative gain at 5 (nDCG@5, a 0 to 100 score that rewards the right page near the top) is 65.5 for OCR text ranked with BM25 (Best Matching 25), 66.1 with the BGE-M3 embedding model, 67.0 for the best text pipeline (captions added, BGE-M3), and 81.3 for ColPali. The gap varies by task, so it is measured on the reader's own pages before it is relied on. The price is post 17's late-interaction price: Table 4 gives 257.5 kilobytes (KB) per page for ColPali in 16-bit floats, against 8.60 KB for one BGE-M3 vector, with text pipelines typically keeping two to five vectors per page. The figure above sets the routes and these numbers side by side.

As a guide: reach for visual retrieval when the corpus is visually rich (slides, dashboards, forms, figure-heavy papers) and OCR loses what the questions need; stay with OCR-then-text RAG for mostly clean prose with a reliable text layer, which is cheaper to store and composes with everything else. Either way the top-k pages or chunks end in layer 04.

---

## 5. Screenshots for computer-use agents

The most demanding multimodal workload is the **computer-use agent**, a model driving a graphical interface from screenshots; its context is a stream of images, one per turn, interleaved with the actions taken. On Anthropic's API the application returns each screenshot as a tool result ("Computer use tool", consulted October 2026); OpenAI's "Computer use" guide (consulted October 2026) describes the same loop. Anthropic's page is specific about the budget:

- **Downscale, and keep the scale factor.** The page recommends 1,024 by 768 or 1,280 by 720 for desktop tasks and 1,280 by 800 or 1,366 by 768 for web applications, and nothing above 1,920 by 1,080. Coordinates come back in the screenshot's pixels, so each click is scaled back to the real display. A screenshot in a tool result that exceeds the model's limits is rejected with a validation error, not resized.
- **Prune old screenshots, in batches.** Above 20 images in a request a stricter per-image size limit applies, and pruning one screenshot every turn changes the prefix every turn and invalidates the cache. The page's default is to keep the last three screenshots and prune every 25 turns; for some newer models it advises server-side clearing of old tool results instead, so the current page decides.
- **Replace pixels with a note.** Once the model has acted on a screen, a short note of what it did ("earlier: opened the settings panel, changed the timezone") is far cheaper than the pixels: the compress operation of [post 12](../12-compress-strategies/index.md) applied to images.

Post 03's lost-in-the-middle measurements (Liu et al., 2023) were made on text documents, not strips of screenshots, so they say nothing direct here; post 03's rule, keep the middle short, still costs nothing to follow, and pruning is how.

---

## 6. Audio and transcription

Audio enters the window by one of two paths. The first is **transcription**: a speech recognition model turns speech into text, which flows through the text pipeline as if typed. Meeting notes, call transcripts and voice interfaces that take this path become text workloads under the same rules.

The second is **native audio input**: the model takes the waveform and encodes it into tokens, as a vision model encodes an image. This keeps what a transcript discards (tone, hesitation, who is speaking, background sound) and costs tokens in proportion to the duration. Google's Gemini "Audio understanding" page (last updated 23 September 2026) counts 32 tokens per second, 1,920 a minute, with up to 9.5 hours of audio per prompt; other providers publish their own rates. At that rate the snippet's illustrative 30-minute call is 57,600 tokens as audio, against 6,000 for its transcript at an illustrative 150 words a minute.

Transcribe-then-treat-as-text remains the practical default: here the transcript is under a ninth of the audio's tokens, and easy to store and chunk. Native audio is for tasks in which the non-verbal signal is part of the answer.

---

## 7. Multimodal caching and token accounting

Two accounting facts change once images enter the window.

First, **images count against the window and the bill as tokens**, with no separate image budget. A prompt of 30,000 tokens of text and 20,000 of images (illustrative numbers) is a 50,000-token prompt for the window ceiling, the input price, and the prefill that delays the first token ([post 05](../05-economics-of-context/index.md), section 5).

Second, **caching applies to image tokens, with a sharp caveat**. Anthropic's "Prompt caching" documentation (consulted October 2026) lists images and documents among the blocks that can be cached. As post 05 sets out, a write costs 1.25 times the base input price for the five-minute lifetime and 2 times for the one-hour lifetime, and a read 0.1 times the base input price on most models, lower on some newer ones. A reference image that stays the same across many turns is a good candidate: one write, then reads at a tenth of its input price on this series' running models. The caveat is the page's rule: a hit needs 100% identical prompt segments, including all text and images, up to the block marked for caching, and the page warns that adding or removing images affects the cached messages; the computer-use page's batch pruning treats that as a change before the breakpoint, which a live call's `cache_read_input_tokens` confirms.

The design rule follows, and the figure below draws it. Stable images (a reference document, a fixed diagram) go early, right after layers 01 and 02 and before a cache breakpoint; volatile images (this turn's screenshot) go last, with layer 06, so that their churn changes nothing before them. A live screenshot placed early ends the reusable prefix, and every block after it, the reference page included, is processed again at full price on every call.

![Two layouts of one computer-use call with breakpoints after layer 02 and after a reference page image. Top: this turn's screenshot sits in layer 03, before the reference page; only 01 and 02 are read from the cache. Bottom: the reference page follows layer 02 and the screenshot travels with 06; 01, 02 and the reference page are read from the cache.](diagrams/04-image-cache-boundary.svg)

*An image that changes every call ends the reusable prefix wherever it sits.*

The same rule explains the batch pruning of section 5. In a long computer-use loop the earlier turns can themselves be cached as they accumulate; deleting one old screenshot changes the prompt at that turn, so every turn after it is processed again. Pruning a batch every 25 turns pays that cost once per batch, not on every call.

An image is a block of tokens that can be measured, budgeted, cached and pruned with the tools this series gives for text, once it is counted. Sending the snippet's page at its three resolutions to a live model and reading `usage.input_tokens` from each response is the direct check of the counts above.

---

## 8. What can go wrong?

- **Image tokens left out of the budget.** An agent sized on its text sends a screenshot per turn; the `usage` block reports input tokens far above the estimate, and long sessions hit the window limit early.
- **An image resized by hand to the edge limit.** A 1,920 by 1,080 image is scaled to 1,568 by 882 on the assumption that only the long edge matters. The API still resizes it, to 1,456 by 819, because of the token limit, and every returned coordinate lands off target; the "Coordinates and bounding boxes" page calls overlooking the token limit the most common cause of misaligned coordinates.
- **An oversized screenshot in a tool result.** A loop returns full-resolution screenshots from a large display; the API rejects the tool result with a validation error instead of downscaling it, and the loop fails on its first screenshot.
- **A 300-dpi scan on a standard-tier model.** Scanned at 300 dpi to keep footnotes legible, each page is shrunk to the same 924 by 1,307 pixels as a 130-dpi scan, and the footnotes are unreadable again; cropping the region that matters, or a high-resolution-tier model, helps.
- **A live screenshot before the breakpoint.** The usage block reports `cache_read_input_tokens` covering layers 01 and 02 only, and the reference document after the screenshot is billed in full on every call.
- **A screenshot pruned every turn.** Dropping the oldest screenshot on each turn changes the prefix each time, so `cache_creation_input_tokens` appears on every call and the reads shrink.

---

## Common pitfalls

1. **Quoting one image-token number for every model.** The count depends on the pixel size, the provider's rule and the model's tier; this post's 1,551 tokens is one model family's standard tier.
2. **Sending full resolution by default.** Past the cap, extra pixels are shrunk away before the model reads them; below it, they cost tokens the task may not need.
3. **One document method for the whole corpus.** Every page as pixels pays for layout nobody needed; every page as text destroys tables and figures. Routing per page avoids both.
4. **Trusting OCR, or a vision model, silently.** A misread digit becomes a confident wrong answer either way; accuracy is measured on the worst scans before either route is trusted.
5. **Volatile images early in the prompt.** A per-turn screenshot ahead of stable content breaks the cached prefix on every call; stable images go first, live ones last.

---

## Further reading

- Anthropic, *"Vision"* and *"Coordinates and bounding boxes"* (consulted October 2026): the patch rule, the two tiers and the resize rule.
- Anthropic, *"PDF support"* and *"Computer use tool"* (consulted October 2026): pages as text and image, screenshot sizes and pruning.
- Anthropic, *"Prompt caching"* (consulted October 2026): images as cacheable blocks and the identical-prefix rule.
- OpenAI, *"Images and vision"* and *"Computer use"* (consulted October 2026): tile and patch counts, and the screenshot loop.
- Google, *"Document understanding"* and *"Audio understanding"* (Gemini API, consulted October 2026): page and audio token counts.
- Faysse, M. *et al.*, *"ColPali: Efficient Document Retrieval with Vision Language Models"* (2024, ICLR 2025): visual late interaction and ViDoRe.
- Khattab, O. and Zaharia, M., *"ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT"* (2020): the mechanism ColPali applies to patches.

Full citations are in [REFERENCES.md](../../REFERENCES.md).

---

## What to read next

- **[Post 20 - Evaluation](../20-evaluation/index.md):** how to measure whether a pipeline, multimodal or not, retrieves and answers correctly before it is trusted.
- **[Post 10 - Data ingestion and document pipelines](../10-data-ingestion-pipelines/index.md):** the text side of section 3: born-digital extraction, OCR and layout-aware parsing, and when each is needed.
