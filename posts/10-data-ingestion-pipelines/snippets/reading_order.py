"""Post 10, section 3: a two-column page read by position interleaves; read by column it does not.

Run from the series root:  uv run python posts/10-data-ingestion-pipelines/snippets/reading_order.py
Standard library only. The page is a toy: each word is (x, y, text), as a text-layer library reports glyph runs.
"""

LEFT = ["Refunds over 500 dollars", "need a manager's approval", "within two working days."]
RIGHT = ["Shipping is free on orders", "above 50 dollars to the", "mainland only."]
COLUMN_X = {"left": 72, "right": 320}      # x of each column's left edge, in points
LINE_H = 14                                # line height, in points


def layout(left, right):
    """Place every word of both columns on the page: (x, y, word)."""
    words = []
    for x0, lines in ((COLUMN_X["left"], left), (COLUMN_X["right"], right)):
        for row, line in enumerate(lines):
            x = x0
            for w in line.split():
                words.append((x, 100 + row * LINE_H, w))
                x += 6 * len(w) + 4                # a crude advance width
    return words


def by_position(words):
    """Top to bottom, then left to right: what a naive text-layer read produces."""
    return " ".join(w for _, _, w in sorted(words, key=lambda t: (t[1], t[0])))


def by_column(words, gutter_x):
    """Split at the gutter first, then read each column top to bottom."""
    cols = ([t for t in words if t[0] < gutter_x], [t for t in words if t[0] >= gutter_x])
    return " ".join(by_position(c) for c in cols)


if __name__ == "__main__":
    page = layout(LEFT, RIGHT)
    print("by position:", by_position(page))
    print("by column:  ", by_column(page, gutter_x=COLUMN_X["right"] - 8))
