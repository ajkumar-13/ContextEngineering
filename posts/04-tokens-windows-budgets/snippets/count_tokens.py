# count_tokens.py: count the tokens of the same content in different shapes with two OpenAI encodings
import json

import tiktoken

ENCODINGS = ["cl100k_base", "o200k_base"]

# One support ticket, written three ways: as prose, as Python, and as indented JSON.
PROSE = (
    "Order 48213 was placed by Priya Sharma on 3 March 2026 and shipped two days later "
    "by ground courier to Pune. It held two items: a steel water bottle at 899 rupees and "
    "a canvas backpack at 2,499 rupees. The customer says the parcel has not arrived, "
    "the tracking page has not changed for six days, and she would like a refund if it "
    "cannot be found by Friday."
)
TICKET = {
    "order_id": 48213,
    "customer": {"name": "Priya Sharma", "city": "Pune"},
    "placed": "2026-03-03",
    "shipped": "2026-03-05",
    "carrier": "ground courier",
    "items": [
        {"sku": "BTL-STEEL-750", "name": "steel water bottle", "price_inr": 899},
        {"sku": "BAG-CANVAS-20L", "name": "canvas backpack", "price_inr": 2499},
    ],
    "status": {"tracking_unchanged_days": 6, "delivered": False},
    "request": "refund if not found by Friday",
}
CODE = f"ticket = {TICKET!r}\n"
JSON = json.dumps(TICKET, indent=2)

# One customer message in English and in Hindi.
ENGLISH = "My order has not arrived yet. Please tell me where it is."
HINDI = "मेरा ऑर्डर अभी तक नहीं आया है। कृपया बताइए कि वह कहाँ है।"

SHORT = ["context engineering", "def parse_iso8601(s: str) -> datetime:"]


def main() -> None:
    encs = {name: tiktoken.get_encoding(name) for name in ENCODINGS}
    print("vocabulary size:")
    for name, enc in encs.items():
        print(f"  {name:12} {enc.n_vocab}")

    print("\nshort strings (tokens):")
    for s in SHORT:
        counts = "  ".join(f"{len(enc.encode(s)):3d}" for enc in encs.values())
        print(f"  {counts}  {s!r}")

    print("\nthe same ticket, three shapes (characters, then tokens per encoding):")
    base = {name: len(enc.encode(PROSE)) for name, enc in encs.items()}
    for label, text in [("prose", PROSE), ("python", CODE), ("json", JSON)]:
        cells = []
        for name, enc in encs.items():
            n = len(enc.encode(text))
            cells.append(f"{n:4d} ({n / base[name]:.2f}x prose)")
        print(f"  {label:7} {len(text):4d} chars  " + "  ".join(cells))

    words = len(PROSE.split())
    print(f"\nprose: {words} words")
    for name, enc in encs.items():
        n = len(enc.encode(PROSE))
        print(f"  {name:12} {n} tokens, {words / n:.2f} words per token")

    print("\none message, two languages (characters, then tokens per encoding):")
    for label, text in [("english", ENGLISH), ("hindi", HINDI)]:
        counts = "  ".join(f"{len(enc.encode(text)):3d}" for enc in encs.values())
        print(f"  {label:7} {len(text):3d} chars  {counts}")


if __name__ == "__main__":
    main()
