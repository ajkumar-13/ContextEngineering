"""Post 28: the companion's offline core, run with no API key, no vector store and no install.

Run from the series root:  uv run python posts/28-build-rag-chatbot/snippets/offline_core.py

Importing the companion code/28-rag-chatbot needs its runtime packages (chromadb, voyageai, cohere, openai,
rank-bm25, python-dotenv), though no key, since its clients are built on first use. This script reads the
companion's source files instead, executes only their pure parts (the chunking constants, `split_sentences`,
`chunk`, `rrf_merge`, `pack`) exactly as written, and prints what they do on the companion's sample corpus.
Token counts use tiktoken's o200k_base encoding, the one gpt-4o-mini uses. Standard library plus tiktoken.
"""
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

import tiktoken

ROOT = Path(__file__).resolve().parents[3]
COMP = ROOT / "code" / "28-rag-chatbot"
SRC = COMP / "src" / "rag"
ENC = tiktoken.get_encoding("o200k_base")


def tokens(text: str) -> int:
    return len(ENC.encode(text))


def load(module: str, names: set[str], extra: dict | None = None) -> dict:
    """Execute only the named top-level functions and assignments of one companion module."""
    tree = ast.parse((SRC / module).read_text(encoding="utf-8"))
    keep = [n for n in tree.body
            if (isinstance(n, ast.FunctionDef) and n.name in names)
            or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in n.targets))]
    assert {getattr(n, "name", None) or n.targets[0].id for n in keep} == names, module
    ns = {"re": re, "defaultdict": defaultdict, **(extra or {})}
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(SRC / module), "exec"), ns)
    return ns


ing = load("ingest.py", {"CHUNK_TARGET", "CHUNK_OVERLAP", "split_sentences", "chunk"})
ret = load("retrieve.py", {"rrf_merge"})
SYSTEM = (COMP / "prompts" / "system.md").read_text(encoding="utf-8")   # as prompt.py reads it
prm = load("prompt.py", {"pack"}, {"SYSTEM": SYSTEM})
chunk, rrf_merge, pack = ing["chunk"], ret["rrf_merge"], prm["pack"]

print("1. Size of the build")
total = 0
for f in sorted(SRC.glob("*.py")):
    n = f.read_bytes().count(b"\n")
    total += n
    print(f"   {f.name:<12} {n:>4} lines")
print(f"   {'src/rag':<12} {total:>4} lines of Python")

print("\n2. Chunking (ingest.py)")
print(f"   CHUNK_TARGET = {ing['CHUNK_TARGET']}, CHUNK_OVERLAP = {ing['CHUNK_OVERLAP']}, both counted in words")
n_words = n_tokens = 0
for f in sorted((COMP / "data" / "corpus").glob("*.md")):
    text = f.read_text(encoding="utf-8")
    cs = chunk(text)
    n_words, n_tokens = n_words + len(text.split()), n_tokens + tokens(text)
    print(f"   {f.name:<15} {len(text.split()):>3} words, {tokens(text):>3} tokens -> {len(cs)} chunk")
ratio = n_tokens / n_words
print(f"   sample corpus: {ratio:.2f} tokens per word, so a full 500-word chunk of such prose is about "
      f"{round(500 * ratio, -1):.0f} tokens")
long_text = " ".join(f"Sentence number {i}." for i in range(400))   # the text of the companion's test
cs = chunk(long_text)
words = [len(c.split()) for c in cs]
toks = [tokens(c) for c in cs]
shared = []
for a, b in zip(cs, cs[1:]):
    sa, sb = ing["split_sentences"](a), ing["split_sentences"](b)
    k = max(i for i in range(1, min(len(sa), len(sb)) + 1) if sa[-i:] == sb[:i])
    shared.append(sum(len(s.split()) for s in sb[:k]))
print(f"   test text, {len(long_text.split())} words -> {len(cs)} chunks of {words} words ({toks} tokens)")
print(f"   words repeated from the previous chunk: {shared}")

print("\n3. Fusion (retrieve.py)")
a, b = ["x", "y", "z"], ["y", "x", "z"]
merged = rrf_merge([a, b])
score = {d: sum(1 / (60 + r.index(d)) for r in (a, b)) for d in merged}
print(f"   rrf_merge({a}, {b}) -> {merged}")
print("   scores: " + ", ".join(f"{d} {score[d]:.6f}" for d in merged) + "  (x and y tie)")
print(f"   first place adds 1/(60 + 0) = {1 / 60:.6f}; the 1-based formula with k = 60 adds 1/61 = {1 / 61:.6f}")
same = all(1 / (60 + r) == 1 / (59 + (r + 1)) for r in range(50))
print(f"   0-based ranks with k = 60 score as 1-based ranks with k = 59: {same}")

print("\n4. Packing (prompt.py)")
hits = [{"id": f"c{i}", "text": f"chunk ranked {i}", "meta": {"title": f"rank{i}"}} for i in range(1, 6)]
msgs = pack("q", hits)
RANK = re.compile(r"\[rank(\d)\]")
print(f"   five hits in rank order 1 to 5 are packed as: {', '.join(RANK.findall(msgs[1]['content']))}")
two = pack("q", hits[:2])
print(f"   two hits are packed as: {', '.join(RANK.findall(two[1]['content']))}")
print(f"   messages: {[m['role'] for m in msgs]}")
blocks = re.findall(r"^# (.+)$", SYSTEM, flags=re.M)
print(f"   system prompt blocks: {blocks}; {tokens(SYSTEM)} tokens")
corpus_hits = []
for f in sorted((COMP / "data" / "corpus").glob("*.md")):
    title, c = f.stem, chunk(f.read_text(encoding="utf-8"))[0]
    full = f"[Document: {title}]\n[Summary: <one sentence from the header model>]\n\n{c}"   # as ingest.py builds it
    corpus_hits.append({"id": title, "text": full, "meta": {"title": title}})
q = "How long is a workspace invite valid?"
user = pack(q, corpus_hits)[1]["content"]
print(f"   sample corpus, both chunks: user message {tokens(user)} tokens, of which the question line "
      f"{tokens('Question: ' + q)}")
print("   user message, first and last lines (blank lines left out):")
lines = [line for line in user.splitlines() if line.strip()]
for line in lines[:2] + ["..."] + lines[-1:]:
    print(f"     {line}")

print("\n5. Evaluation fixtures (tests/fixtures.json)")
fx = json.loads((COMP / "tests" / "fixtures.json").read_text(encoding="utf-8"))
print(f"   {len(fx)} question and answer pairs; keys {sorted(fx[0])}")
