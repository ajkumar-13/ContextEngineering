"""Post 17, section 8: where each route's cost falls, offline or on every question, at stated sizes.

Run from the series root:  uv run python posts/17-advanced-retrieval/diagrams/src/03-route-costs.py
Writes posts/17-advanced-retrieval/diagrams/03-route-costs.svg.

Every number is computed from snippets/route_costs.py (imported), from its cited rates (Claude Sonnet 4.5 as of
early 2026, Anthropic's cache multipliers, ColBERT and ColBERTv2 bytes per vector, GraphRAG's chunking) and its
illustrative sizes, and each printed string is asserted against the snippet's own output quoted in index.md.
"""
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
POST = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(POST / "snippets"))
from figkit import Figure  # noqa: E402
import route_costs as rc  # noqa: E402

rag = rc.dollars(rc.TOP_K * rc.CHUNK)
doc = rc.PAGES * rc.PER_PAGE
uncached, read = rc.dollars(doc), rc.dollars(doc, factor=rc.READ)
sql = rc.dollars(rc.SQL_IN, rc.SQL_OUT)
chunks = math.ceil((rc.CORPUS - rc.G_CHUNK) / (rc.G_CHUNK - rc.G_OVERLAP)) + 1
build = chunks * rc.dollars(rc.G_CHUNK + rc.EXTRACT_PROMPT, rc.EXTRACT_OUT)
single = (rc.CORPUS // rc.CHUNK) * rc.DENSE_DIM * rc.DENSE_BYTES / 1e6
colbert, colbert_v2 = rc.CORPUS * rc.COLBERT_BYTES / 1e6, rc.CORPUS * rc.COLBERT_V2_BYTES / 1e6

BODY = (POST / "index.md").read_text(encoding="utf-8")
for s in (f"{rag:.5f}", f"{uncached:.5f}", f"{read:.5f}", f"one call {sql:.5f}", f"{chunks:,} extraction calls",
          f"{build:.2f} dollars", f"per chunk {single:.2f} MB", f"ColBERT {colbert:.0f} MB", f"ColBERTv2 {colbert_v2:.0f} MB",
          "The figure below lays the routes side by side."):
    assert s in BODY, s


def d(v, places):
    return f"{v:.{places}f} dollars"


ROWS = [
    ["Route", "Offline, per 1,000,000 tokens", "Per question"],
    ["Hybrid RAG", f"one vector per chunk: {single:.2f} MB", f"{rc.TOP_K * rc.CHUNK:,} tokens, {d(rag, 3)}"],
    ["GraphRAG", f"{chunks:,} extraction calls: {d(build, 2)}", "a walk that grows with hop depth"],
    ["Late interaction", f"one vector per token: {colbert:.0f} MB, {colbert_v2:.0f} MB compressed",
     "MaxSim over the candidates"],
    ["Text-to-SQL", "schema descriptions indexed", f"{d(sql, 4)}, {d(2 * sql, 4)} with a repair"],
    ["Long-context load", "nothing", f"{d(uncached, 3)} uncached, {d(read, 4)} cached"],
]
assert f"{rag:.3f}" == "0.006" and f"{sql:.4f}" == "0.0087" and f"{read:.4f}" == "0.0075"

desc = ("A table of five retrieval routes, with the work each does offline for a 1,000,000-token corpus and the cost "
        "it adds per question, computed at illustrative sizes on Claude Sonnet 4.5 rates as of early 2026. Hybrid "
        f"RAG: one vector per chunk, {single:.2f} MB; {rc.TOP_K * rc.CHUNK:,} tokens, {d(rag, 3)}. GraphRAG: "
        f"{chunks:,} extraction calls, {d(build, 2)}; a walk that grows with hop depth. Late interaction: one vector "
        f"per token, {colbert:.0f} MB, or {colbert_v2:.0f} MB compressed; MaxSim over the candidates. Text-to-SQL: "
        f"schema descriptions indexed; {d(sql, 4)} a call, {d(2 * sql, 4)} with a repair. Long-context load: nothing "
        f"offline; {d(uncached, 3)} uncached, {d(read, 4)} on a cache read.")

fig = Figure("03-route-costs", "Some routes pay offline, others on every question", desc,
             subtitle="Computed by snippets/route_costs.py: Claude Sonnet 4.5 rates as of early 2026, illustrative "
                      "sizes.", data_w=True)
fig.table(40, 120, ROWS, [176, 360, 344], row_h=48, highlight_row={2: "neutral-soft", 3: "neutral-soft"})
fig.text(40, 448, "Shaded: the two routes whose main cost is built offline, before any question arrives.", "note")
fig.caption("Long context costs most per question until it is cached; GraphRAG and late interaction pay up front.")
fig.write()
