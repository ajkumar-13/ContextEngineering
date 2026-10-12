"""Post 04, section 1: the same content costs different numbers of tokens by shape and by language.

Run from the series root (needs the root environment's tiktoken):
    uv run python posts/04-tokens-windows-budgets/diagrams/src/02-same-content-tokens.py
Writes posts/04-tokens-windows-budgets/diagrams/02-same-content-tokens.svg.

Every count is measured here with the texts of snippets/count_tokens.py (imported) and the two OpenAI encodings
it uses, and asserted against the counts section 1 quotes from the snippet's printed output. The counts are
measured, so the bars are solid.
"""
import runpy
import sys
from pathlib import Path

import tiktoken

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure  # noqa: E402

SNIP = Path(__file__).resolve().parents[2] / "snippets" / "count_tokens.py"
S = runpy.run_path(str(SNIP), run_name="snippet")
CL, O2 = (tiktoken.get_encoding(n) for n in S["ENCODINGS"])


def count(enc, text):
    return len(enc.encode(text))


SHAPES = [("Prose", S["PROSE"]), ("Python dictionary", S["CODE"]), ("Indented JSON", S["JSON"])]
shape_counts = [(label, count(CL, t)) for label, t in SHAPES]
assert shape_counts == [("Prose", 87), ("Python dictionary", 148), ("Indented JSON", 183)]
assert [count(O2, t) for _, t in SHAPES] == [87, 148, 183]       # the same under o200k_base

LANG = [("English, cl100k", count(CL, S["ENGLISH"])), ("English, o200k", count(O2, S["ENGLISH"])),
        ("Hindi, cl100k", count(CL, S["HINDI"])), ("Hindi, o200k", count(O2, S["HINDI"]))]
assert [v for _, v in LANG] == [14, 14, 61, 22]
assert len(S["ENGLISH"]) == len(S["HINDI"]) == 57

fig = Figure(
    "02-same-content-tokens", "The same content, a different number of tokens",
    "Two bar charts of token counts measured with OpenAI's cl100k_base and o200k_base encodings. Left, one "
    "support ticket written three ways: prose 87 tokens, a Python dictionary 148 (1.70 times the prose) and "
    "indented JSON 183 (2.10 times), the "
    "same under both encodings. Right, one 57-character customer message: English 14 tokens under both "
    "encodings, Hindi 61 under cl100k_base and 22 under o200k_base.",
    subtitle="Counted by snippets/count_tokens.py with OpenAI's cl100k_base and o200k_base encodings.",
    data_w=True)

left, right = fig.row(2)
b1 = fig.panel(left, "One ticket, three shapes")
PROSE_N = shape_counts[0][1]
RATIO = {v: f"{v / PROSE_N:.2f}" for _, v in shape_counts}
assert RATIO == {87: "1.00", 148: "1.70", 183: "2.10"}                # section 1 quotes 1.70 and 2.10
fig.bar_chart(b1, [(lab, v, "ink") for lab, v in shape_counts], 0, 200, [0, 100, 200],
              label_w=136, value_w=120, axis_label="tokens, same under both encodings",
              fmt_value=lambda v: f"{v:.0f}" if v == PROSE_N else f"{v:.0f}, {RATIO[v]} × prose")
b2 = fig.panel(right, "One message, two languages")
fig.bar_chart(b2, [(lab, v, "ink") for lab, v in LANG], 0, 80, [0, 40, 80],
              label_w=128, value_w=40, axis_label="tokens, 57 characters in each language")

fig.caption("Keys, quotes and indentation are tokens; so are the pieces of a script the vocabulary rarely saw.")
fig.write()
