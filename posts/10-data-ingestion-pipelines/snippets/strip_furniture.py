"""Post 10, section 5: drop the lines that repeat on most pages (running headers and page footers).

Run from the series root:  uv run python posts/10-data-ingestion-pipelines/snippets/strip_furniture.py
Standard library only. The three pages are a toy policy document.
"""
import re
from collections import Counter

PAGES = [
    ["Acme Ltd refund policy", "Refunds are paid to the original card.",
     "A refund over 500 dollars needs a manager's approval.", "Confidential, page 1 of 3"],
    ["Acme Ltd refund policy", "Approval is given within two working days.",
     "Refused refunds can be appealed once.", "Confidential, page 2 of 3"],
    ["Acme Ltd refund policy", "Store credit never expires.", "Confidential, page 3 of 3"],
]


def shape(line):
    """A line with its digits masked, so 'page 1 of 3' and 'page 2 of 3' count as one line."""
    return re.sub(r"\d+", "#", line.strip().lower())


def strip_furniture(pages, min_share=0.6):
    """Drop every line whose shape appears on at least min_share of the pages."""
    seen = Counter(s for page in pages for s in {shape(ln) for ln in page})
    furniture = {s for s, n in seen.items() if n / len(pages) >= min_share}
    kept = [[ln for ln in page if shape(ln) not in furniture] for page in pages]
    return kept, sorted(furniture)


if __name__ == "__main__":
    kept, furniture = strip_furniture(PAGES)
    before = sum(len(ln.split()) for page in PAGES for ln in page)
    after = sum(len(ln.split()) for page in kept for ln in page)
    print("repeated lines dropped:", furniture)
    print(f"words before {before}, after {after}: {before - after} words "
          f"({100 * (before - after) / before:.0f}%) were page furniture")
    for i, page in enumerate(kept, 1):
        print(f"  page {i}: {' '.join(page)}")
