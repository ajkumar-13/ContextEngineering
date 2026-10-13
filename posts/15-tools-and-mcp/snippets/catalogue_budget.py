"""Post 15: the token budget of a fifty-tool catalogue, cut to five by a selection step.

Run from the series root:  uv run python posts/15-tools-and-mcp/snippets/catalogue_budget.py
It imports the companion package toolschemas from code/15-tool-schemas/src (no install needed) and
tiktoken (o200k_base, cached offline). It calls no model and no network. The catalogue is a toy written
for this post: ten services of an online shop, five operations each.
"""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import tiktoken

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code" / "15-tool-schemas" / "src"))
from toolschemas import catalog_cost_usd, catalog_tokens, trim, validate  # noqa: E402

SERVICES = ["order", "refund", "shipment", "invoice", "customer",
            "subscription", "product", "ticket", "coupon", "review"]
FIELDS = {"order": "its items, its total and whether it has shipped", "refund": "its amount, reason and state",
          "shipment": "its carrier, tracking number and delivery date", "invoice": "its lines, tax and due date",
          "customer": "their contact details and order count", "subscription": "its plan, price and renewal date",
          "product": "its price, stock level and variants", "ticket": "its messages, owner and priority",
          "coupon": "its discount, limits and expiry", "review": "its rating, text and author"}
STATUS = {"order": ["open", "shipped", "closed"], "shipment": ["in_transit", "delivered", "delivery_failed"]}


def rich_tool(verb, noun):
    """One tool with all six parts: name, summary, when to use, when not to use, parameters, example."""
    plural = noun + "s"
    summary = {
        "search": f"Find {plural} that match a customer email, a start date" + (" or a status." if noun in STATUS else "."),
        "get": f"Return one {noun} by its id, with {FIELDS[noun]}.",
        "create": f"Create a new {noun} from the fields given and return its id.",
        "update": f"Change named fields of one existing {noun} and return the new version.",
        "cancel": f"Cancel one {noun} by its id; the change cannot be undone.",
    }[verb]
    use = {
        "search": f"Use it when the user describes {plural} but gives no {noun} id.",
        "get": f"Use it when the user gives a {noun} id.",
        "create": f"Use it only after the user has confirmed every field of the new {noun}.",
        "update": f"Use it when the user asks to change a {noun} they have named by id.",
        "cancel": f"Use it only after the user has confirmed the cancellation in this turn.",
    }[verb]
    avoid = {
        "search": f"Do not use it when a {noun} id is known; use get_{noun} instead.",
        "get": f"Do not use it to list several {plural}; use search_{plural} instead.",
        "create": f"Do not use it to change an existing {noun}; use update_{noun} instead.",
        "update": f"Do not use it to cancel a {noun}; use cancel_{noun} instead.",
        "cancel": f"Do not use it to change a {noun}; use update_{noun} instead.",
    }[verb]
    props = {f"{noun}_id": {"type": "string", "description": f"The {noun} id, for example A-4821."}}
    if verb == "search":
        props = {"email": {"type": "string", "description": "The customer's email address."},
                 "since": {"type": "string", "description": "Earliest date, as YYYY-MM-DD."}}
        if noun in STATUS:
            props["status"] = {"type": "string", "enum": STATUS[noun], "description": f"Only {plural} in this state."}
    elif verb in ("create", "update"):
        props = dict(props) if verb == "update" else {}
        props["fields"] = {"type": "object", "description": f"The {noun} fields to set, by name."}
    required = [k for k in props if k.endswith("_id") or k == "fields"]
    example = {k: ("A-4821" if k.endswith("_id") else "ana@example.com" if k == "email"
                   else "2026-09-01" if k == "since" else {"note": "gift"} if k == "fields" else STATUS[noun][1])
               for k in props}
    name = f"search_{plural}" if verb == "search" else f"{verb}_{noun}"
    return {"name": name, "description": f"{summary} {use} {avoid}",
            "input_schema": {"type": "object", "properties": props, "required": required,
                             "additionalProperties": False},
            "input_examples": [example]}


def thin_tool(tool):
    """The same tool cut to fit: the summary sentence only, parameter types without descriptions or enums, no example."""
    props = {k: {"type": v["type"]} for k, v in tool["input_schema"]["properties"].items()}
    return {"name": tool["name"], "description": tool["description"].split(". ")[0] + ".",
            "input_schema": {"type": "object", "properties": props}}


CATALOGUE = [rich_tool(v, n) for n in SERVICES for v in ("search", "get", "create", "update", "cancel")]
THIN = [thin_tool(t) for t in CATALOGUE]
STOP = {"a", "an", "the", "is", "it", "my", "has", "not", "where", "still", "for", "of", "to", "by", "and",
        "or", "but", "no", "i", "use", "do", "when", "user", "one", "be", "this", "with", "its", "that", "every", "only", "new"}


def words(text):
    return {w[:-1] if w.endswith("s") else w for w in re.findall(r"[a-z]+", text.lower())} - STOP


def select_tools(turn, catalogue, k=5):
    """Score each schema by the words it shares with the turn, rarer words weighing more; keep the top k."""
    docs = [words(json.dumps(tool)) for tool in catalogue]
    df = Counter(w for d in docs for w in d)
    query = words(turn)
    scores = [sum(math.log(len(docs) / df[w]) for w in query & d) for d in docs]
    ranked = sorted(range(len(catalogue)), key=lambda i: -scores[i])  # ties keep catalogue order
    return [catalogue[i] for i in ranked[:k]]


TURN = "Order A-4821 shipped last week, but the tracking number shows no delivery. Where is it?"
CHOSEN = select_tools(TURN, CATALOGUE)
ENC = tiktoken.get_encoding("o200k_base")


def o200k(tools):
    return sum(len(ENC.encode(json.dumps(t, separators=(",", ":")))) for t in tools)


if __name__ == "__main__":
    print(f"catalogue: {len(CATALOGUE)} tools; one turn: {TURN!r}")
    print("selected:", ", ".join(t["name"] for t in CHOSEN))
    cut = trim(CATALOGUE, keep=5)
    print("trim(keep=5) instead:", ", ".join(t["name"] for t in cut), f"({catalog_tokens(cut)} estimated tokens)")
    print()
    print("tools in layer 02            estimate  o200k_base  dollars per call at 3 per million")
    for label, tools in [("50 rich, no selection", CATALOGUE), ("50 thin, no selection", THIN),
                         ("5 rich, selected", CHOSEN)]:
        print(f"{label:28s} {catalog_tokens(tools):8d} {o200k(tools):11d}  {catalog_cost_usd(tools):.6f}")
    full, kept = catalog_tokens(CATALOGUE), catalog_tokens(CHOSEN)
    print(f"selection keeps {kept} of {full} estimated tokens ({100 * kept / full:.1f} percent)")
    print(f"50 rich read from cache at 0.30 per million: {catalog_cost_usd(CATALOGUE, 0.30):.6f} dollars per call")
    print()
    search = next(t for t in CHOSEN if t["name"] == "search_shipments")["input_schema"]
    for args in ({"email": "ana@example.com", "status": "delivery_failed"}, {"email": "ana@example.com", "status": "failed"},
                 {"shipment": "A-4821"}):
        print(f"validate {json.dumps(args)}: {validate(args, search) or 'valid'}")
