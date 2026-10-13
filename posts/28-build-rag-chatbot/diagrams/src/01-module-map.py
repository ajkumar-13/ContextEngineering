"""Post 28, section 2: each part of the companion, the earlier post it implements, and where it departs from it.

Run from the series root:  uv run python posts/28-build-rag-chatbot/diagrams/src/01-module-map.py
Writes posts/28-build-rag-chatbot/diagrams/01-module-map.svg.
No measured number is drawn. Every function named is checked to exist in the companion's source, every post
and section pointer is checked against the heading of the committed post, and every departure is a phrase the
body states, asserted below.
"""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure  # noqa: E402

POST = Path(__file__).resolve().parents[2]
ROOT = POST.parents[1]
COMP = ROOT / "code" / "28-rag-chatbot"
BODY = (POST / "index.md").read_text(encoding="utf-8")

# file, function, (post, section, a word of that section's heading), departure, the body phrase behind it
ROWS = [
    ("ingest.py", "chunk", ("11", "2", "chunking"), "counts words, not tokens",
     "count words, not tokens"),
    ("ingest.py", "contextual_header", ("11", "2", "contextual retrieval"), "sees the title, not the document",
     "gives the model only the title and the chunk"),
    ("ingest.py", "ingest_path", ("10", "8", "Incremental re-indexing"), "never deletes a stale chunk",
     "the old record is never deleted"),
    ("retrieve.py", "rrf_merge", ("09", "3", "candidate generation"), "ranks from 0: RRF with k = 59",
     "Every score equals the 1-based formula with $k = 59$"),
    ("retrieve.py", "rerank", ("09", "4", "re-ranking"), "skipped if the key is named CO_API_KEY",
     "`rerank` silently skips re-ranking"),
    ("prompt.py", "pack", ("09", "5", "packing"), "as post 09: best first, second best last",
     "Five hits ranked 1 to 5 are packed as 1, 3, 4, 5, 2"),
    ("system.md", "four blocks", ("14", "2", "five blocks"), "no tool-use guidance (no tools)",
     "there is no tool-use guidance because the chatbot has no tools"),
    ("llm.py", "chat_llm", ("05", "4", "Prompt caching"), "prefix perhaps too short to cache",
     "Whether so short a prefix is cached depends on the provider's minimum"),
    ("eval.py", "run", ("20", "5", "Ragas"), "three fixtures and no gate",
     "**There is no gate.**"),
]
for file, func, (post, sec, word), _, phrase in ROWS:
    assert phrase in BODY, phrase
    src = (COMP / "prompts" / file) if file.endswith(".md") else (COMP / "src" / "rag" / file)
    text = src.read_text(encoding="utf-8")
    if func == "four blocks":
        assert re.findall(r"^# (.+)$", text, re.M) == ["Identity", "Rules", "Format", "Knowledge"]
    else:
        assert f"def {func}(" in text, func
    target = next((ROOT / "posts").glob(f"{post}-*"))
    heading = next(h for h in (target / "index.md").read_text(encoding="utf-8").splitlines()
                   if h.startswith(f"## {sec}. "))
    assert word.lower() in heading.lower(), (post, sec, heading)
    assert f"post {post}, section {sec}" in BODY or f"post {post}, sections" in BODY or \
        f"[post {post}]" in BODY or f"Post {post}]" in BODY, (post, sec)

table = [["File", "Function", "Implements", "Departs from it"]]
table += [[f, fn, f"post {p}, section {s}", d] for f, fn, (p, s, _), d, _ in ROWS]

desc = ("A table with one row per part of the companion and four columns: file, function, the earlier post and "
        "section it implements, and where it departs from it. ingest.py chunk, post 11 section 2, counts words, "
        "not tokens. contextual_header, post 11 section 2, sees the title, not the document. ingest_path, post 10 "
        "section 8, never deletes a stale chunk. retrieve.py rrf_merge, post 09 section 3, ranks from 0, RRF with "
        "k = 59. rerank, post 09 section 4, skipped if the key is named CO_API_KEY. prompt.py pack, post 09 section 5, as "
        "post 09. system.md, four blocks, post 14 section 2, no tool-use guidance because there are no tools. "
        "llm.py chat_llm, post 05 section 4, a prefix perhaps too short to cache. eval.py run, post 20 section 5, three "
        "fixtures and no gate.")

fig = Figure("01-module-map", "Every part traces to a post, and most depart from it", desc,
             subtitle="The companion code/28-rag-chatbot, file by file; the last column is what hardening fixes.",
             data_w=True)
fig.table(40, 112, table, [128, 184, 176, 392], row_h=36, highlight_row={6: "turn"})
fig.caption("Only the packing matches its post exactly; every other row is something to harden.")
fig.write()
