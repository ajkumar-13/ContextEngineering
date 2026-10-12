"""Post 11: the companion's offline core (ragkit) over a toy corpus and a ten-question golden set.

Run from the series root:  uv run python posts/11-rag-in-depth/snippets/toy_rag.py
It imports ragkit from code/11-rag-from-scratch/src (no install needed), calls no model and no network.
The corpus is a toy written for this post; its numbers show the mechanisms, not the size of the effects.
"""
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code" / "11-rag-from-scratch" / "src"))
from ragkit import BM25, bookend_pack, chunk, rrf  # noqa: E402

CORPUS = {
    "refunds-policy.md": {
        "Eligibility": "Most items can be returned within 30 days of delivery. Items must be unused and "
        "in their original packaging. Digital downloads and gift cards are excluded. Sale items earn "
        "store credit only.",
        "Approval limits": "Support agents can approve up to 1,000 dollars on their own. Anything above "
        "that needs a manager's sign-off before money moves. The manager queue is staffed on weekdays "
        "from 8:00 to 18:00. Weekend requests wait until Monday morning.",
        "Payment method": "Money goes back to the original payment method. Card payments take five to "
        "ten business days to appear. Bank transfers usually arrive within three days. Store credit is "
        "issued at once.",
    },
    "shipping-policy.md": {
        "Delivery times": "Standard delivery takes three to five business days. Express delivery arrives "
        "the next business day if the order is placed before 14:00. Orders to remote areas can take up to "
        "ten days.",
        "Lost parcels": "A parcel counts as lost after 15 business days without a tracking update. The "
        "customer then gets a replacement or the full amount back. Agents must open a claim with the "
        "carrier first.",
        "Costs": "Shipping is free on orders over 50 dollars. Below that, standard delivery costs 5 "
        "dollars and express delivery costs 12 dollars.",
    },
    "escalations.md": {
        "When to escalate": "Escalate when a customer threatens legal action, reports a safety issue, or "
        "has contacted support three times about the same problem. Do not escalate billing questions that "
        "the agent can answer.",
        "How to escalate": "Write a summary of the case in three sentences or fewer. Attach the order "
        "number and every previous ticket. Assign the case to the escalation queue, not to a named person.",
    },
    "accounts.md": {
        "Password reset": "Customers reset their password from the sign-in page. The link expires after "
        "30 minutes. Agents never ask for a password and never set one on a customer's behalf.",
        "Closing an account": "A closed account cannot be reopened. Its order history is kept for seven "
        "years for tax purposes. Any store credit left on it is paid out before closing.",
    },
}

GOLDEN = [  # (question as a user might type it, a phrase only the answer-bearing chunk contains)
    ("Who signs off on a refund of 2,000 dollars?", "needs a manager's sign-off"),
    ("How many days until a card refund shows up?", "five to ten business days"),
    ("Can I get a refund on a gift card?", "gift cards are excluded"),
    ("My parcel has not moved for three weeks. Is it lost?", "after 15 business days"),
    ("What does next-day shipping cost?", "express delivery costs 12 dollars"),
    ("Can a big refund be approved on a Saturday?", "Weekend requests wait"),
    ("What should an escalation write-up contain?", "three sentences or fewer"),
    ("How long is the password reset link valid?", "expires after 30 minutes"),
    ("Can a deleted account be restored?", "cannot be reopened"),
    ("What happens to leftover credit when an account is closed?", "paid out before closing"),
]

# Offline half: chunk every section (sizes in words, as ragkit approximates tokens), and keep a
# second copy of each chunk with a contextual header: the document title and the section path.
chunks, headed = [], []
for doc, sections in CORPUS.items():
    for section, text in sections.items():
        for c in chunk(text, target_tokens=30, overlap_tokens=8):
            chunks.append(c.text)
            headed.append(f"[{doc} > {section}] {c.text}")


def trigrams(text):
    t = " " + " ".join(text.lower().split()) + " "
    return Counter(t[i:i + 3] for i in range(len(t) - 2))


def trigram_ranking(docs, query):
    """A character-trigram cosine ranking: an offline stand-in for the dense half of hybrid search."""
    q, grams = trigrams(query), [trigrams(d) for d in docs]
    def cos(g):
        return sum(q[t] * g[t] for t in q) / math.sqrt(sum(v * v for v in q.values()) * sum(v * v for v in g.values()))
    return sorted(range(len(docs)), key=lambda i: -cos(grams[i]))


bm25_bare, bm25_headed = BM25(chunks), BM25(headed)


def rankings(question):
    lexical = [i for i, _ in bm25_headed.search(question, top_k=len(headed))]
    fuzzy = trigram_ranking(headed, question)
    return {
        "BM25, bare chunks": [i for i, _ in bm25_bare.search(question, top_k=len(chunks))],
        "BM25, headed chunks": lexical,
        "trigram, bare chunks": trigram_ranking(chunks, question),
        "trigram, headed chunks": fuzzy,
        "RRF of the two, headed": [i for i, _ in rrf([lexical, fuzzy], k=60)],
    }


def hit(n, ranked, phrase):
    """True when one of the first n chunks carries the gold phrase."""
    return any(phrase in chunks[i] for i in ranked[:n])


print(f"{len(CORPUS)} documents, {sum(map(len, CORPUS.values()))} sections, {len(chunks)} chunks")
print(f"{'retriever':<24}{'recall@1':>10}{'recall@3':>10}  missed at 3")
for name in rankings(GOLDEN[0][0]):
    r1 = sum(hit(1, rankings(q)[name], p) for q, p in GOLDEN) / len(GOLDEN)
    r3 = sum(hit(3, rankings(q)[name], p) for q, p in GOLDEN) / len(GOLDEN)
    missed = [str(j + 1) for j, (q, p) in enumerate(GOLDEN) if not hit(3, rankings(q)[name], p)]
    print(f"{name:<24}{r1:>10.1f}{r3:>10.1f}  {', '.join(missed) or '-'}")

question = GOLDEN[0][0]
top5 = rankings(question)["RRF of the two, headed"][:5]
print(f"\n{question}")
print("top-5 by RRF:", top5)
print("bookend order:", bookend_pack(top5))
