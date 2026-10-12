# tokens.py: split a few strings into tokens with tiktoken and print every piece
import tiktoken

enc = tiktoken.get_encoding("o200k_base")  # the encoding tiktoken uses for GPT-4o

TEXTS = ["context engineering", "strawberry", " strawberry", "tokenisation"]

for text in TEXTS:
    ids = enc.encode(text)
    pieces = [enc.decode([i]) for i in ids]
    unit = "token" if len(ids) == 1 else "tokens"
    print(f"{text!r:23} {len(text):2} characters -> {len(ids)} {unit}: {pieces}")
