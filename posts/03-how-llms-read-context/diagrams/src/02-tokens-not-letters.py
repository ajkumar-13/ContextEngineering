"""Post 03, section 2: the model reads tokens, not letters.

Run from the series root:  uv run python posts/03-how-llms-read-context/diagrams/src/02-tokens-not-letters.py
Writes posts/03-how-llms-read-context/diagrams/02-tokens-not-letters.svg.
Every string, character count and token split is computed here by running snippets/tokens.py (tiktoken,
o200k_base) and asserted against what section 2 of the post quotes from that snippet's output.
"""
import contextlib
import io
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "tokens.py"
out = io.StringIO()
with contextlib.redirect_stdout(out):
    ns = runpy.run_path(str(SNIP), run_name="snippet")
enc, TEXTS = ns["enc"], ns["TEXTS"]
SPLITS = {t: [enc.decode([i]) for i in enc.encode(t)] for t in TEXTS}
# what the post quotes from the snippet's output
assert SPLITS["strawberry"] == ["st", "raw", "berry"]
assert SPLITS[" strawberry"] == [" strawberry"]
assert SPLITS["context engineering"] == ["context", " engineering"]
assert SPLITS["tokenisation"] == ["token", "isation"]
assert "-> 3 tokens: ['st', 'raw', 'berry']" in out.getvalue()

# (string, x of its first cell, top of its row)
ROWS = [("strawberry", 40, 104), (" strawberry", 488, 104), ("context engineering", 40, 228),
        ("tokenisation", 40, 352)]
SPACE = "␣"   # the open-box sign for a space character
CELL = 32



def show(s: str) -> str:
    return s.replace(" ", SPACE)


def describe(t: str) -> str:
    n = len(SPLITS[t])
    return f"{len(t)} characters, {n} token" + ("" if n == 1 else "s")


fig = Figure(
    "02-tokens-not-letters", "The model reads tokens, not letters",
    "Four strings, each drawn as a row of character cells with the tokens that tiktoken's o200k_base encoding "
    "splits it into beneath. strawberry: 10 characters, 3 tokens, st, raw and berry. The same word after a "
    "space: 11 characters, 1 token. context engineering: 19 characters, 2 tokens, context and engineering with "
    "its leading space. tokenisation: 12 characters, 2 tokens, token and isation. The open-box sign marks a "
    "space character.",
    subtitle="Printed by snippets/tokens.py (tiktoken, o200k_base). The sign \u2423 marks a space.",
    data_w=True)

for t, x0, y in ROWS:
    fig.text(x0, y + 16, show(t), "code")
    fig.text(x0 + CELL * len(t), y + 16, describe(t), "note", anchor="end")
    top = y + 28
    for i, ch in enumerate(t):
        b = Box(x0 + i * CELL, top, CELL, CELL)
        fig.fill(b, "surface", fit=False)
        fig.outline(b, "rule")
        fig.text(b.cx, top + 20, show(ch), "code", anchor="middle")
    start = 0
    ttop = top + CELL + 8
    for piece in SPLITS[t]:
        b = Box(x0 + start * CELL + 2, ttop, len(piece) * CELL - 4, CELL)
        fig.fill(b, "neutral-soft", radius=8, fit=False)
        fig.outline(b, "ink-muted", width=1.5, radius=8)
        fig.text(b.cx, ttop + 20, show(piece), "code", anchor="middle")
        start += len(piece)

XL = 40 + 19 * CELL + 32
fig.text(XL, 228 + 28 + 20, "characters", "note")
fig.text(XL, 228 + 28 + CELL + 8 + 20, "tokens, as the model reads them", "note")
fig.caption("Inside a sentence, \u201cstrawberry\u201d is one token: no single letter of it reaches the model.")
fig.write()
