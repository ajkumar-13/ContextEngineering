"""Post 10, section 4: a table flattened to text loses a cell; the same table as Markdown keeps it.

Run from the series root:  uv run python posts/10-data-ingestion-pipelines/snippets/flatten_table.py
Standard library only. The prices are illustrative.
"""

HEADER = ["Product", "Basic", "Pro"]
ROWS = [["Product A", "$10", "$20"],
        ["Product B", "$15", "$30"],
        ["Product C", "", "$25"]]          # Product C has no Basic tier: an empty cell


def flatten(header, rows):
    """What a reader of glyphs produces: every non-empty cell, left to right, top to bottom."""
    cells = header + [c for r in rows for c in r]
    return " ".join(c for c in cells if c)


def rebind(flat, header, labels):
    """Read the flat stream back into a grid by position, the only cue it still carries."""
    toks = flat.split()
    out, i = {}, len(" ".join(header).split())
    for label in labels:
        i += len(label.split())
        out[label] = dict(zip(header[1:], toks[i:i + len(header) - 1]))
        i += len(header) - 1
    return out


def to_markdown(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(c if c else " " for c in r) + " |" for r in rows]
    return "\n".join(lines)


def lookup(markdown, product, tier):
    rows = [[c.strip() for c in ln.strip("|").split("|")] for ln in markdown.splitlines()]
    col = rows[0].index(tier)
    return next(r[col] for r in rows[2:] if r[0] == product) or "(empty)"


if __name__ == "__main__":
    flat = flatten(HEADER, ROWS)
    print("flattened:", flat)
    back = rebind(flat, HEADER, [r[0] for r in ROWS])
    for r in ROWS:
        print(f"  read back by position, {r[0]}: {back[r[0]]}")
    md = to_markdown(HEADER, ROWS)
    print("as Markdown:")
    print(md)
    for product, tier in (("Product B", "Pro"), ("Product C", "Basic")):
        print(f"  {product}, {tier}: flat stream says {back[product].get(tier, '(missing)')}, "
              f"Markdown says {lookup(md, product, tier)}")
