"""Post 17: what each route costs, offline and per question, at stated sizes.

Run from the series root:  uv run python posts/17-advanced-retrieval/snippets/route_costs.py
Standard library only; no network, no model, no API key.

Cited values: Claude Sonnet 4.5 at 3 dollars per million input tokens and 15 per million output tokens,
a five-minute cache write at 1.25 times and a cache read at 0.1 times the base input price (Anthropic,
"Pricing" and "Prompt caching", as of early 2026, consulted October 2026; post 05); 256 bytes per
ColBERT token vector (128 dimensions at 16 bits) and 36 bytes per ColBERTv2 vector with 2-bit residuals
(Santhanam et al., 2022, section 3.3); GraphRAG's 600-token chunks with 100-token overlap (Edge et al.,
2024). Every size marked ILLUSTRATIVE is a round number chosen for the arithmetic, not a measurement.
Only the retrieved material (layer 04) and the calls a route adds are priced: the rest of the call is
the same whichever route serves it.
"""
import math

IN, OUT = 3.00, 15.00                 # dollars per million tokens, Claude Sonnet 4.5 (cited)
WRITE, READ = 1.25, 0.10              # cache multipliers on the input price (cited)
COLBERT_BYTES, COLBERT_V2_BYTES = 256, 36   # bytes per token vector (cited)

CHUNK = 400                           # ILLUSTRATIVE: tokens per chunk (post 11's 400 to 600 default)
TOP_K = 5                             # ILLUSTRATIVE: chunks packed per question
PAGES, PER_PAGE = 50, 500             # ILLUSTRATIVE: a 50-page contract at 500 tokens a page
SESSION = 10                          # ILLUSTRATIVE: questions asked about one contract
CORPUS = 1_000_000                    # ILLUSTRATIVE: corpus size in tokens
DENSE_DIM, DENSE_BYTES = 768, 4       # ILLUSTRATIVE: one 768-dimension float32 vector per chunk
G_CHUNK, G_OVERLAP = 600, 100         # cited: GraphRAG's chunking
EXTRACT_PROMPT, EXTRACT_OUT = 1_000, 300   # ILLUSTRATIVE: extraction prompt and output per chunk
TABLES, PER_TABLE = 500, 60           # ILLUSTRATIVE: a 500-table warehouse, 60 tokens per table description
SQL_IN, SQL_OUT = 2_150, 150          # ILLUSTRATIVE: retrieved schema 1,500 + examples 600 + question 50


def dollars(tokens_in, tokens_out=0, factor=1.0):
    return tokens_in * IN * factor / 1e6 + tokens_out * OUT / 1e6


if __name__ == "__main__":
    rag = dollars(TOP_K * CHUNK)
    doc = PAGES * PER_PAGE
    uncached, write, read = dollars(doc), dollars(doc, factor=WRITE), dollars(doc, factor=READ)
    sql = dollars(SQL_IN, SQL_OUT)
    print("dollars per question, retrieved material only (Claude Sonnet 4.5, as of early 2026)")
    print(f"  hybrid RAG     {TOP_K * CHUNK:,} tokens        {rag:.5f}")
    print(f"  long context   {doc:,} tokens       uncached {uncached:.5f}, write {write:.5f}, read {read:.5f}")
    print(f"  text-to-SQL    one call {sql:.5f}, with a repair {2 * sql:.5f}; "
          f"full schema {dollars(TABLES * PER_TABLE):.5f}")
    print(f"  {SESSION} questions   RAG {SESSION * rag:.5f}; long context uncached {SESSION * uncached:.5f}, "
          f"cached {write + (SESSION - 1) * read:.5f}")

    chunks = math.ceil((CORPUS - G_CHUNK) / (G_CHUNK - G_OVERLAP)) + 1
    build = chunks * dollars(G_CHUNK + EXTRACT_PROMPT, EXTRACT_OUT)
    single = (CORPUS // CHUNK) * DENSE_DIM * DENSE_BYTES
    colbert, colbert_v2 = CORPUS * COLBERT_BYTES, CORPUS * COLBERT_V2_BYTES
    print(f"offline, {CORPUS:,}-token corpus")
    print(f"  GraphRAG       {chunks:,} extraction calls, {build:.2f} dollars (summaries not included)")
    print(f"  index          per chunk {single / 1e6:.2f} MB; per token: ColBERT {colbert / 1e6:.0f} MB "
          f"({colbert / single:.1f} times), ColBERTv2 {colbert_v2 / 1e6:.0f} MB ({colbert_v2 / single:.1f} times)")
