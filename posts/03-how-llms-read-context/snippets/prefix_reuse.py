# prefix_reuse.py: how much of call 2 an identical-prefix cache can reuse from call 1, under two layouts
import tiktoken

enc = tiktoken.get_encoding("o200k_base")

SYSTEM = (
    "You are the support assistant for the Acme billing API. Answer in British English, "
    "in at most five sentences, and cite the document id of every fact you use. "
    "If the documents do not contain the answer, say so instead of guessing."
)
TOOLS = (
    '[{"name": "search_docs", "description": "Search the billing documentation by keyword.", '
    '"input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, '
    '"required": ["query"]}}]'
)
CALL_1 = {
    "memory": "<memory>The user's account is on the Team plan.</memory>",
    "chunks": "<chunk id='doc-12'>Invoices are issued on the first day of each month.</chunk>",
    "history": [],
    "question": "When is my next invoice issued?",
}
CALL_2 = {
    "memory": "<memory>The user's account is on the Team plan. The user pays by card.</memory>",
    "chunks": "<chunk id='doc-31'>Card payments are retried three times over seven days.</chunk>",
    "history": ["When is my next invoice issued?", "On the first day of next month (doc-12)."],
    "question": "What happens if my card payment fails?",
}


def tokens(system: str, call: dict) -> tuple[list[int], int]:
    """Tokenise the layers block by block, in the series' order.

    Returns the tokens and how many of them belong to layers 01 and 02, where the cache breakpoint sits.
    """
    blocks = [system, TOOLS, call["memory"], call["chunks"], *call["history"], call["question"]]
    ids = [enc.encode(block) for block in blocks]
    return [t for block in ids for t in block], len(ids[0]) + len(ids[1])


def shared_prefix(a: list[int], b: list[int]) -> int:
    """The number of leading tokens two token sequences have in common."""
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return n


def report(name: str, system_1: str, system_2: str) -> None:
    t1, _ = tokens(system_1, CALL_1)
    t2, stable = tokens(system_2, CALL_2)
    same = shared_prefix(t1, t2)
    reused = stable if same >= stable else 0  # the whole of layers 01 and 02, or nothing
    print(name)
    print(f"  call 2: {len(t2)} tokens; layers 01 and 02: {stable} tokens")
    print(f"  leading tokens identical to call 1: {same}")
    print(f"  breakpoint after layer 02: {reused} read from the cache, {len(t2) - reused} computed")


report("layout A: stable layers first", SYSTEM, SYSTEM)
report("layout B: time of the call in the system prompt",
       "Current time: 09:14:05.\n" + SYSTEM, "Current time: 09:16:42.\n" + SYSTEM)
