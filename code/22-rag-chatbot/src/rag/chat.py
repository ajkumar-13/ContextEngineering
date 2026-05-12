"""The chat loop. Single-turn for the starter; see README for multi-turn."""
from __future__ import annotations

from .llm import chat_llm
from .prompt import pack
from .retrieve import retrieve


def answer(query: str, *, k: int = 5) -> dict:
    hits = retrieve(query, k=k)
    msgs = pack(query, hits)
    out = chat_llm(msgs)
    return {
        "answer": out["text"],
        "sources": [{"title": h["meta"]["title"], "id": h["id"]} for h in hits],
        "usage": out["usage"],
    }


def main() -> None:
    print("rag chatbot — empty line to quit")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            break
        out = answer(q)
        print()
        print(out["answer"])
        if out["sources"]:
            uniq = sorted({s["title"] for s in out["sources"]})
            print(f"\n  sources: {', '.join(uniq)}")
        print()


if __name__ == "__main__":
    main()
