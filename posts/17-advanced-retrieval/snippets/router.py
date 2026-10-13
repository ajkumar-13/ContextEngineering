"""Post 17: a toy router that sends each question to a retriever by its shape.

Run from the series root:  uv run python posts/17-advanced-retrieval/snippets/router.py
Standard library only; no network, no model, no API key.

Fifteen questions: three for each of the four shapes that defeat hybrid RAG (multi-hop, whole document,
structured data, rare exact term) and three ordinary local lookups. Each carries the route a person
labelled it with. The router is four keyword rules checked in a fixed order, with hybrid RAG as the
fall-through. A production router may be a small model call with a short rubric; it is evaluated
the same way, against labelled questions, and its misroutes are read one by one.
"""
import re

ROUTES = {  # shape -> the technique that serves it
    "rare exact term": "late interaction",
    "structured": "text-to-SQL",
    "multi-hop": "GraphRAG",
    "whole document": "long-context load",
    "local lookup": "hybrid RAG",
}

RULES = [  # (shape, pattern), checked in this order; the first match wins
    ("rare exact term", r"\b[A-Z]{1,4}-?\d{3,}\b"),
    ("structured", r"(?i)\b(how many|average|total|count of|per region|per month)\b"),
    ("multi-hop", r"(?i)\b(downstream|upstream|depend on|maintained by|who manages|managed by)\b"),
    ("whole document", r"(?i)\b(summari[sz]e|main themes|key risks|whole|from start to end)\b"),
]

QUESTIONS = [  # (question, the shape a person labelled it with)
    ("Which suppliers are downstream of vendors that failed our 2024 audit?", "multi-hop"),
    ("Which services depend on libraries maintained by the team that left in March?", "multi-hop"),
    ("Who manages the engineers who approved the Hartley contract?", "multi-hop"),
    ("Summarise the key risks raised in this 200-page filing.", "whole document"),
    ("What are the main themes of this whole contract?", "whole document"),
    ("Summarise how the tone of this report changes from start to end.", "whole document"),
    ("How many tickets did the Bangalore team close last quarter?", "structured"),
    ("What was the average refund amount per region in 2025?", "structured"),
    ("How many enterprise customers in EMEA churned last quarter?", "structured"),
    ("What does error E-4012 mean when exporting invoices?", "rare exact term"),
    ("Which firmware fixes the fault on SKU AX-7731?", "rare exact term"),
    ("What does clause 14.3 of contract MSA-2291 require?", "rare exact term"),
    ("How do I reset my password?", "local lookup"),
    ("What is the refund window for annual plans?", "local lookup"),
    ("How many days of notice does the termination clause require?", "local lookup"),
]


def route(question):
    """The technique for a question: the first rule that matches, else the default."""
    for shape, pattern in RULES:
        if re.search(pattern, question):
            return ROUTES[shape]
    return ROUTES["local lookup"]


if __name__ == "__main__":
    right = 0
    counts = {r: 0 for r in ROUTES.values()}
    print(f"{'#':>2}  {'labelled':<17} {'routed to':<18} question")
    for i, (q, shape) in enumerate(QUESTIONS, start=1):
        got = route(q)
        counts[got] += 1
        ok = got == ROUTES[shape]
        right += ok
        print(f"{i:>2}  {shape:<17} {got:<18} {q}{'' if ok else '   <- misrouted'}")
    print(f"\nrouted as labelled: {right} of {len(QUESTIONS)}")
    print("questions per route: " + ", ".join(f"{r} {n}" for r, n in counts.items()))
