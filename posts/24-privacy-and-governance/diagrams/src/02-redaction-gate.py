"""Post 24, section 3: one prompt (call-01) through the detect-and-redact gate of snippets/pii_gate.py.

Run from anywhere:  python posts/24-privacy-and-governance/diagrams/src/02-redaction-gate.py
Writes posts/24-privacy-and-governance/diagrams/02-redaction-gate.svg.
Every hit, placeholder and value is computed here by the post's snippet (loaded with runpy): detect() and
redact() on the first of its twenty prompts, and gate() for what the window and the trace store receive. The
redacted text and the vault are asserted against the output the body quotes.
"""
import runpy
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\Users\admin\Desktop\series-standard\tools")
from figkit import Figure, Box  # noqa: E402

POST = Path(__file__).resolve().parents[2]
BODY = (POST / "index.md").read_text(encoding="utf-8")
M = runpy.run_path(str(POST / "snippets" / "pii_gate.py"), run_name="snippet")
task, text, seeded = M["PROMPTS"][0]
hits = M["detect"](text)
redacted, vault = M["redact"](text, hits)
trace, vaults = [], {}
to_model = M["gate"]("call-01", task, text, trace, vaults)
assert task == "summarise" and to_model == redacted == trace[0]["prompt"]
assert f"  trace: {redacted}" in BODY
assert "  vault: " + ", ".join(f"{k} = {v}" for k, v in vault.items()) in BODY
PATTERN_KINDS = {"CARD", "NINO", "EMAIL", "PHONE"}
pattern_hits = [(k, v) for k, v in hits if k in PATTERN_KINDS]
name_hits = [(k, v) for k, v in hits if k == "PERSON"]
assert [k for k, _ in pattern_hits] == ["CARD", "EMAIL"] and [k for k, _ in name_hits] == ["PERSON"]
assert sorted(v for _, v in hits) == sorted(seeded)
assert "a list of first names standing in for an NER model" in BODY
assert "It costs a model call per check, so it is a fallback for high-risk paths." in BODY
inv = {v: k for k, v in vault.items()}

desc = (f"The prompt of call-01, a summarise task: \"{text}\" It passes three detectors in order. "
        "1 Patterns with a check find " + " and ".join(f"{k} {v}" for k, v in pattern_hits) + ". "
        "2 The name list, standing in for an NER model, finds " + " and ".join(f"{k} {v}" for k, v in name_hits) + ". "
        "3 The LLM classifier is drawn dashed: a fallback for high-risk paths, not run in the snippet. "
        f"The redacted text, \"{redacted}\", goes to the trace store always, and to the window because the task is a "
        "summary. The vault, kept apart with tighter access, holds "
        + ", ".join(f"{k} = {v}" for k, v in vault.items()) + ".")

fig = Figure("02-redaction-gate", "Detect cheapest first, then keep the values apart", desc,
             subtitle="call-01 of snippets/pii_gate.py, a summarise task; every name and number is synthetic.",
             height=720, data_w=False)   # kit gap: text_width scores "<CARD_1>" as markup (width 0), so data-w
                                         # would flag every placeholder; Chrome still checks margins and boxes

# the input
inp = Box(40, 104, 880, 56)
fig.fill(inp, "user-soft", radius=8, fit=False)
fig.outline(inp, "user-line", radius=8)
fig.text(56, 138, text, "label")

# three detectors
CW, CG, CY, CH = 272, 32, 216, 152
heads = [("1 Patterns with a check", "regular expressions, Luhn"),
         ("2 Name list", "stands in for an NER model"),
         ("3 LLM classifier", "fallback for high-risk paths")]
cards = []
for i, (h, n) in enumerate(heads):
    b = Box(40 + i * (CW + CG), CY, CW, CH)
    fig.fill(b, "surface", radius=8, fit=False)
    fig.outline(b, "border" if i < 2 else "rule", radius=8, dash=None if i < 2 else "proj")
    fig.text(b.x + 16, b.y + 32, h, "head")
    fig.text(b.x + 16, b.y + 56, n, "note")
    cards.append(b)
for card, found in ((cards[0], pattern_hits), (cards[1], name_hits)):
    for j, (k, v) in enumerate(found):
        fig.text(card.x + 16, card.y + 96 + 28 * j, inv[v], "code")
        fig.text(card.x + 112, card.y + 96 + 28 * j, "found", "label")
fig.text(cards[2].x + 16, cards[2].y + 96, "not run in the snippet", "note")
fig.arrow((cards[0].cx, inp.bottom + 4), (cards[0].cx, CY - 4))
fig.chain(cards)

# the redacted text
red = Box(40, 416, 880, 56)
fig.fill(red, "neutral-soft", radius=8, fit=False)
fig.outline(red, "border", radius=8)
fig.text(56, 450, redacted, "label")
for c in cards[:2]:
    fig.arrow((c.cx, c.bottom + 4), (c.cx, red.y - 4))

# the three destinations
OY, OH = 520, 120
win = Box(40, OY, 208, OH)
store = Box(272, OY, 208, OH)
vlt = Box(512, OY, 408, OH)
for b, head, note in ((win, "Window", "placeholders, since"), (store, "Trace store", "placeholders, always")):
    fig.fill(b, "neutral-soft", radius=8, fit=False)
    fig.outline(b, "border", radius=8)
    fig.text(b.x + 16, b.y + 32, head, "head")
    fig.text(b.x + 16, b.y + 56, note, "note")
fig.text(win.x + 16, win.y + 80, "a summary needs no values", "note")
fig.fill(vlt, "surface", radius=8, fit=False)
fig.outline(vlt, "ink", radius=8, width=2.5)
fig.text(vlt.x + 16, vlt.y + 32, "Vault, separate access", "head")
for j, (k, v) in enumerate(vault.items()):
    fig.text(vlt.x + 16, vlt.y + 64 + 20 * j, f"{k} = {v}", "code")
for b in (win, store):
    fig.arrow((b.cx, red.bottom + 4), (b.cx, b.y - 4))
fig.arrow((vlt.cx, red.bottom + 4), (vlt.cx, vlt.y - 4), label="the values")

fig.caption("Only the vault can turn a placeholder back into a person, so it gets its own, stricter access rule.")
fig.write()
