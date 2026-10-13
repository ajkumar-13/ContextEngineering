"""Post 30: the request the companion's drafter sends for thread t-001, assembled offline.

Run from the series root:  uv run python posts/30-capstone-email-reply-agent/snippets/drafter_request.py
No model is called and nothing leaves the machine. The memory bundle comes from the companion's own
memory.py, writing three rows into a throwaway SQLite file (the rows are illustrative: the companion's
runner writes none). The prior replies are the companion's two files in data/sent/, filtered to the
recipient and ranked as its offline path ranks them: its fallback embedding _embed (a hashed bag of words,
compiled from replies.py) and the squared L2 distance that is Chroma's default; they are packed by its
pack_prior_replies; the thread is rendered by its _render_thread; the system prompt has {{USER_NAME}}
filled and the user message is built as draft.py does, both checked against the source. Token counts use
tiktoken's o200k_base encoding, the one for the companion's default model, gpt-4o-mini.
"""
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tiktoken  # noqa: E402

from companion import COMPANION, load_function, load_module, source  # noqa: E402

tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
os.environ["EMAILBOT_DATA_DIR"] = tmp.name          # memory.py reads it at import
memory = load_module("memory")
render_thread = load_function("draft.py", "_render_thread")
pack_prior_replies = load_function("replies.py", "pack_prior_replies")
assert '_WORD_RE = re.compile(r"\\w+")' in source("replies.py")
embed = load_function("replies.py", "_embed",   # offline: no VOYAGE_API_KEY, so _vo() is None
                      {"_vo": lambda: None, "_WORD_RE": re.compile(r"\w+"), "hashlib": hashlib, "os": os})

# the user message exactly as draft.py builds it
DRAFT_SRC = source("draft.py")
for line in ('f"{memory_block}\\n{prior_block}\\n[current thread]\\n{thread_block}\\n\\n"',
             'f"Draft a reply for review. Return JSON only."',
             'prior = retrieve_prior_replies(last_msg, recipient=sender, k=5)',
             '.replace("{{USER_NAME}}", os.environ.get("EMAILBOT_USER_NAME", "Ajay Kumar"))'):
    assert line in DRAFT_SRC, line
INSTRUCTION = "Draft a reply for review. Return JSON only."

SYSTEM = ((COMPANION / "prompts" / "drafter_system.md").read_text(encoding="utf-8")
          .replace("{{USER_NAME}}", os.environ.get("EMAILBOT_USER_NAME", "Ajay Kumar")))
thread = json.loads((COMPANION / "data" / "inbox" / "t-001.json").read_text(encoding="utf-8"))
sender, last_msg = thread[-1]["from"], thread[-1]["body"]

# layer 03: three illustrative rows through the companion's own writer and reader
memory.add_semantic(sender, "role", "COO at PartnerCo", confidence=0.9, source="crm")
memory.add_semantic(sender, "style", "prefers short replies", confidence=0.7, source="sent-folder")
memory.add_episodic(sender, "Partnership terms", "confirmed 70/30 for year one; offered a Thursday call",
                    source="sent:2025-09-12")
memory_block = memory.recall_recipient(sender)

# layer 04: the sent folder as index_sent_folder reads it, filtered to this recipient
hits = []
for p in sorted((COMPANION / "data" / "sent").glob("*.txt")):
    parts = p.stem.split("__")
    meta = {"recipient": parts[1], "subject": parts[2].replace("_", " ")}
    if meta["recipient"] == sender.lower():
        hits.append({"id": p.stem, "text": p.read_text(encoding="utf-8"), "meta": meta})
q_emb = embed([last_msg])[0]
hits.sort(key=lambda h: sum((a - b) ** 2 for a, b in zip(q_emb, embed([h["text"]])[0])))
prior_block = pack_prior_replies(hits)

thread_block = render_thread(thread)
user = (
    f"{memory_block}\n{prior_block}\n[current thread]\n{thread_block}\n\n"
    f"Draft a reply for review. Return JSON only."
)

enc = tiktoken.get_encoding("o200k_base")
n = lambda s: len(enc.encode(s))  # noqa: E731
rows = [("01 System prompt", n(SYSTEM)), ("02 Tools and MCP descriptions", 0), ("03 Memory and state", n(memory_block)),
        ("04 Retrieved chunks", n(prior_block)), ("05 Conversation history", n("[current thread]\n" + thread_block)),
        ("06 User instruction", n(INSTRUCTION))]

def outline(text: str) -> list[str]:
    """The memory lines and every block header of the message; other lines are counted, not printed."""
    out, skipped = [], 0
    for line in text.split("\n"):
        if line.startswith(("[", "--- ", "- ")) or line == INSTRUCTION:
            if skipped:
                out.append(f"    ... {skipped} line(s)")
                skipped = 0
            out.append(line)
        elif line.strip():
            skipped += 1
    return out


if __name__ == "__main__":
    print("user message of the drafter call for thread t-001, outline:")
    for line in outline(user):
        print("  " + line)
    print("tokens by layer, o200k_base:")
    for name, k in rows:
        print(f"  {name:32s}{k:5d}")
    print(f"  {'sum':32s}{sum(k for _, k in rows):5d}   (system message {n(SYSTEM)}, user message {n(user)})")
    left = sorted(set(re.findall(r"\{\{\w+\}\}", SYSTEM)))
    print(f"placeholders left unfilled in the system prompt: {', '.join(left) if left else 'none'}")
    ranks = ["r1", "r2", "r3", "r4", "r5"]
    packed = pack_prior_replies([{"text": r, "meta": {"recipient": "x", "subject": r}} for r in ranks])
    print("bookend order of five ranked replies:", " ".join(re.findall(r"re: (r\d)", packed)))
