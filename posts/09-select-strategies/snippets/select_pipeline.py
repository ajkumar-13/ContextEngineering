"""Post 09: the four levers of select on a toy corpus, with recall@N and precision@k.

Run from the series root:  uv run python posts/09-select-strategies/snippets/select_pipeline.py
Standard library only; no network, no model, no API key.

The corpus is 36 one-sentence help-centre articles of a made-up invoicing app, with six questions and
three relevant articles each. Two parts are toy stand-ins, not real models:
  - "dense" maps words to hand-written concept groups (refund ~ reimburse ~ money back) and ranks by
    cosine similarity of concept counts. Like an embedding model, it matches paraphrases; like an
    embedding model that never saw them, it knows nothing of identifiers such as E-4012.
  - "rerank" scores the query and one candidate together by the share of the query's concepts and
    identifiers the candidate covers, the job a cross-encoder does with a trained model.
The numbers show which lever moves which metric on this corpus; they say nothing about how much a
real system gains.
"""
import math
import re
from collections import Counter

N_EACH = 6          # depth of each ranked list before fusion
TOP_N = 6           # candidate-set size: recall@N is measured here
TOP_K = 3           # packed count: precision@k is measured here
RRF_K = 60          # Cormack et al.'s damping constant, unrelated to TOP_K
K1, B = 1.2, 0.75   # BM25 parameters (Robertson and Zaragoza)

CORPUS = {
    "d01": "Refunds for annual plans are prorated for the unused months of the subscription.",
    "d02": "To request a refund, open Billing and choose Request refund within 30 days of the charge.",
    "d03": "Annual subscription refunds go back to the original card within 10 business days.",
    "d04": "The annual plan costs 120 dollars a year and includes unlimited invoices.",
    "d05": "Upgrading from the monthly plan to the annual plan applies a credit for the current month.",
    "d06": "Your card is charged on the same day each month for the monthly plan.",
    "d07": "Cancelling a subscription stops future charges; the plan stays active until the period ends.",
    "d08": "To cancel, open Billing, choose Cancel plan and confirm by email.",
    "d09": "A cancelled account keeps its invoices readable for 12 months.",
    "d10": "E-4012 means the bank connection token expired; reconnect the bank in Settings.",
    "d11": "If E-4012 persists after reconnecting, remove the bank feed and add it again.",
    "d12": "E-3100 means an invoice email could not be delivered.",
    "d13": "E-4021 means the invoice logo is missing.",
    "d14": "Bank feeds sync every four hours and on demand from the Banking page.",
    "d15": "A sync error on the bank feed is shown as a red badge next to the account.",
    "d16": "Error E-5003 appears when a payment provider rejects a card.",
    "d17": "E-4012 can also appear after a password change at the bank.",
    "d18": "Exports to CSV include every invoice line with its tax amount.",
    "d19": "To download invoices as a spreadsheet, choose Export in the Invoices list.",
    "d20": "A CSV export of invoices can be filtered by date range before downloading.",
    "d21": "Invoices can be sent to customers by email with a payment link.",
    "d22": "Reports can be downloaded as PDF from the Reports page.",
    "d23": "The invoice number sequence can be changed in Settings.",
    "d24": "Import customers from a CSV file with one row per customer.",
    "d25": "To add a team member, open Team and send an invitation by email.",
    "d26": "To remove a team member, open Team, choose the person and select Remove access.",
    "d27": "A removed colleague loses access at once; their invoices stay in the account.",
    "d28": "Seats freed by removing users are credited on the next bill.",
    "d29": "To delete an invoice, open it and choose Delete; sent invoices can only be voided.",
    "d30": "Deleting your account erases all invoices after 30 days.",
    "d31": "Team members can be given the Viewer or Editor role.",
    "d32": "VAT on invoices is calculated from the customer's country.",
    "d33": "Change the tax rate of a product in Settings, Taxes.",
    "d34": "Invoices in a foreign currency show the tax amount converted at the invoice date.",
    "d35": "GST and VAT numbers are printed under the customer's address.",
    "d36": "Tax reports summarise VAT collected per quarter.",
}

# Six questions, three relevant articles each. q4 is a follow-up turn: "asked" is what the user typed,
# "rewritten" the self-contained query a rewriting step would produce from the conversation.
QUERIES = [
    {"id": "q1", "asked": "How do I get reimbursed for a yearly membership?",
     "relevant": {"d01", "d02", "d03"}},
    {"id": "q2", "asked": "What does E-4012 mean?",
     "relevant": {"d10", "d11", "d17"}},
    {"id": "q3", "asked": "How can I download my bills as a spreadsheet?",
     "relevant": {"d18", "d19", "d20"}},
    {"id": "q4", "asked": "And how do I take one away?",
     "rewritten": "How do I remove a team member's access?",
     "relevant": {"d26", "d27", "d28"}},
    {"id": "q5", "asked": "How do I terminate my subscription?",
     "relevant": {"d07", "d08", "d09"}},
    {"id": "q6", "asked": "Where do I set the VAT rate on a product?",
     "relevant": {"d32", "d33", "d35"}},
]

# The dense stand-in's vocabulary: each word belongs to one concept. Words outside it are invisible.
CONCEPTS = {
    "refund": "refund", "refunds": "refund", "reimbursed": "refund", "reimburse": "refund",
    "credit": "refund", "credited": "refund",
    "annual": "annual", "yearly": "annual", "year": "annual",
    "monthly": "monthly", "month": "monthly", "months": "monthly",
    "plan": "subscription", "plans": "subscription", "subscription": "subscription",
    "membership": "subscription",
    "cancel": "cancel", "cancelling": "cancel", "cancelled": "cancel", "terminate": "cancel",
    "stops": "cancel",
    "invoice": "invoice", "invoices": "invoice", "bill": "invoice", "bills": "invoice",
    "card": "pay", "charge": "pay", "charged": "pay", "charges": "pay", "payment": "pay",
    "bank": "bank", "banking": "bank", "feed": "bank", "feeds": "bank",
    "sync": "sync", "synchronisation": "sync", "reconnect": "sync", "reconnecting": "sync",
    "connection": "sync",
    "error": "error", "persists": "error", "rejects": "error", "means": "error", "mean": "error",
    "appear": "error", "appears": "error",
    "export": "export", "exports": "export", "download": "export", "downloading": "export",
    "downloaded": "export", "csv": "export", "spreadsheet": "export",
    "team": "team", "member": "team", "members": "team", "colleague": "team", "users": "team",
    "seats": "team", "person": "team",
    "remove": "remove", "removed": "remove", "removing": "remove",
    "delete": "remove", "deleting": "remove", "erases": "remove",
    "access": "access", "role": "access", "invitation": "access",
    "tax": "tax", "taxes": "tax", "vat": "tax", "gst": "tax",
    "rate": "rate", "calculated": "rate", "converted": "rate",
    "product": "product", "customer": "customer", "customers": "customer",
}

STOP = set("a an and the to of in on for by as at is are be can do does how i my your what "
           "where when it its their with from after before every one each same".split())


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower()) if t not in STOP]


def is_identifier(tok):
    return any(ch.isdigit() for ch in tok) and any(ch.isalpha() for ch in tok)


# ---- lever 2: candidate generation --------------------------------------------------------------
DOC_TOKENS = {d: tokens(t) for d, t in CORPUS.items()}
AVG_LEN = sum(len(t) for t in DOC_TOKENS.values()) / len(DOC_TOKENS)
DF = Counter(tok for toks in DOC_TOKENS.values() for tok in set(toks))


def bm25_rank(query, depth):
    """Sparse retrieval: BM25 with the non-negative idf that Lucene uses."""
    n = len(CORPUS)
    scores = {}
    for d, toks in DOC_TOKENS.items():
        tf = Counter(toks)
        s = 0.0
        for q in set(tokens(query)):
            if tf[q]:
                idf = math.log(1 + (n - DF[q] + 0.5) / (DF[q] + 0.5))
                s += idf * tf[q] * (K1 + 1) / (tf[q] + K1 * (1 - B + B * len(toks) / AVG_LEN))
        if s > 0:
            scores[d] = s
    return sorted(scores, key=lambda d: (-scores[d], d))[:depth]


def concepts(text):
    return Counter(CONCEPTS[t] for t in tokens(text) if t in CONCEPTS)


def dense_rank(query, depth):
    """The dense stand-in: cosine similarity of concept counts."""
    qv = concepts(query)
    scores = {}
    for d, text in CORPUS.items():
        dv = concepts(text)
        dot = sum(qv[c] * dv[c] for c in qv)
        if dot:
            scores[d] = dot / math.sqrt(sum(v * v for v in qv.values()) * sum(v * v for v in dv.values()))
    return sorted(scores, key=lambda d: (-scores[d], d))[:depth]


def rrf(*ranked_lists, k=RRF_K):
    """Reciprocal rank fusion: each item scores the sum of 1 / (k + rank) over the lists it is in."""
    score = Counter()
    for ranked in ranked_lists:
        for rank, d in enumerate(ranked, start=1):
            score[d] += 1 / (k + rank)
    return sorted(score, key=lambda d: (-score[d], d))


# ---- lever 3: re-ranking --------------------------------------------------------------------------
def rerank(query, candidates):
    """The cross-encoder stand-in: the share of the query's concepts and identifiers a candidate covers."""
    want = set(concepts(query)) | {t for t in tokens(query) if is_identifier(t)}

    def score(d):
        have = set(concepts(CORPUS[d])) | {t for t in DOC_TOKENS[d] if is_identifier(t)}
        return len(want & have) / len(want)

    return sorted(candidates, key=lambda d: -score(d))   # stable: ties keep the fused order


# ---- lever 4: packing -----------------------------------------------------------------------------
def bookend(ranked):
    """Best first, second-best last, the rest in between in rank order."""
    if len(ranked) < 3:
        return list(ranked)
    return [ranked[0]] + ranked[2:] + [ranked[1]]


def pack(ranked):
    return "\n".join(f"[source: help/{d}] {CORPUS[d]}" for d in bookend(ranked))


# ---- the pipeline and the two metrics ---------------------------------------------------------------
def select(query, sparse=True, dense=True, rerank_on=True):
    lists = []
    if sparse:
        lists.append(bm25_rank(query, N_EACH))
    if dense:
        lists.append(dense_rank(query, N_EACH))
    candidates = rrf(*lists)[:TOP_N]
    ranked = rerank(query, candidates) if rerank_on else candidates
    return candidates, ranked[:TOP_K]


def recall_at(relevant, candidates):
    return len(relevant & set(candidates)) / len(relevant)


def precision_at(relevant, packed, k=TOP_K):
    return len(relevant & set(packed)) / k


CONFIGS = [
    ("BM25 only", dict(sparse=True, dense=False, rerank_on=False)),
    ("dense only", dict(sparse=False, dense=True, rerank_on=False)),
    ("hybrid (RRF)", dict(sparse=True, dense=True, rerank_on=False)),
    ("hybrid + re-rank", dict(sparse=True, dense=True, rerank_on=True)),
]


def evaluate(rewrite=True):
    """Mean recall@N and precision@k per configuration, and the per-query values."""
    rows = []
    for name, cfg in CONFIGS:
        per_query = {}
        for q in QUERIES:
            text = q.get("rewritten", q["asked"]) if rewrite else q["asked"]
            cands, packed = select(text, **cfg)
            per_query[q["id"]] = (recall_at(q["relevant"], cands), precision_at(q["relevant"], packed))
        r = sum(v[0] for v in per_query.values()) / len(QUERIES)
        p = sum(v[1] for v in per_query.values()) / len(QUERIES)
        rows.append((name, r, p, per_query))
    return rows


def main():
    print(f"corpus: {len(CORPUS)} articles; {len(QUERIES)} questions, 3 relevant articles each")
    print(f"each list top-{N_EACH}, fused by RRF (k = {RRF_K}) into top-N = {TOP_N}; packed top-k = {TOP_K}")
    print()
    print(f"{'configuration':<18}{'recall@' + str(TOP_N):>10}{'precision@' + str(TOP_K):>14}")
    for name, r, p, _ in evaluate():
        print(f"{name:<18}{r:>10.2f}{p:>14.2f}")
    print()
    print(f"per question, recall@{TOP_N} / precision@{TOP_K}, in the order above:")
    rows = evaluate()
    for q in QUERIES:
        cells = "  ".join(f"{pq[q['id']][0]:.2f}/{pq[q['id']][1]:.2f}" for _, _, _, pq in rows)
        print(f"  {q['id']}  {cells}")
    print()
    q4 = QUERIES[3]
    for label, text in (("asked", q4["asked"]), ("rewritten", q4["rewritten"])):
        cands, packed = select(text)
        print(f"q4 {label:<9} {text!r}: recall@{TOP_N} {recall_at(q4['relevant'], cands):.2f}, "
              f"precision@{TOP_K} {precision_at(q4['relevant'], packed):.2f}")
    print()
    q2 = QUERIES[1]
    _, packed = select(q2["asked"])
    print(f"q2 re-ranked top-{TOP_K}: {', '.join(packed)}; packed in bookend order:")
    print(pack(packed))


if __name__ == "__main__":
    main()
